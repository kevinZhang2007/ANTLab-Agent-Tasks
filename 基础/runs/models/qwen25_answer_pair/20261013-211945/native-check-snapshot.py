"""直接调用装机C++ Schema转换器与原生grammar sampler；不启动服务、不decode。"""
from pathlib import Path
from datetime import datetime
import ctypes as c
import hashlib
import json
import math
import os
import struct
import sys

folder = Path(sys.argv[1])
old = Path(__file__).resolve().parents[2] / 'runs/answer_form/20261013-195237'
binary = Path(r'C:\Users\86186\AppData\Local\ANTLabLocalModel\llama-b11429')
root = binary.parent

def save(name, value):
    path = folder / name
    assert not path.exists()
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def stop_owned(process, owned):
    # 空状态可清理；只处理本工具登记且对象相同的Popen，不按端口杀进程。
    if process is None:
        return 'no_process'
    if owned.get(process.pid) is not process:
        return 'not_owned_not_stopped'
    if process.poll() is None:
        process.terminate()
        process.wait(timeout=10)
    return 'owned_stopped'

assert stop_owned(None, {}) == 'no_process'
class NotOwned:
    pid = -1
assert stop_owned(NotOwned(), {}) == 'not_owned_not_stopped'

def exports(path):
    raw = path.read_bytes()
    pe = struct.unpack_from('<I', raw, 60)[0]
    count = struct.unpack_from('<H', raw, pe + 6)[0]
    optional = struct.unpack_from('<H', raw, pe + 20)[0]
    start = pe + 24 + optional
    sections = [struct.unpack_from('<IIII', raw, start + i * 40 + 8) for i in range(count)]
    def offset(rva):
        return next(ptr + rva - va for vs, va, size, ptr in sections if va <= rva < va + max(vs, size))
    export = offset(struct.unpack_from('<I', raw, pe + 24 + 112)[0])
    n = struct.unpack_from('<I', raw, export + 24)[0]
    names = offset(struct.unpack_from('<I', raw, export + 32)[0])
    result = []
    for i in range(n):
        p = offset(struct.unpack_from('<I', raw, names + i * 4)[0])
        result.append(raw[p:raw.index(b'\0', p)].decode('ascii'))
    return result

handles = os.add_dll_directory(str(binary))
common = c.CDLL(str(binary / 'llama-common.dll'))
lib = c.CDLL(str(binary / 'llama.dll'))
names = exports(binary / 'llama-common.dll')
parse_name = next(n for n in names if n.startswith('?parse@common_json@@'))
convert_name = next(n for n in names if n.startswith('?json_schema_to_grammar@@') and 'AEBVcommon_json@@_N' in n)
destroy_name = '??1common_json@@QEAA@XZ'
parse = getattr(common, parse_name)
parse.argtypes = [c.c_void_p, c.c_void_p]
parse.restype = c.c_void_p
convert = getattr(common, convert_name)
convert.argtypes = [c.c_void_p, c.c_void_p, c.c_bool]
convert.restype = c.c_void_p
destroy_json = getattr(common, destroy_name)
destroy_json.argtypes = [c.c_void_p]
destroy_json.restype = None

class NativeString(c.Structure):
    # 本包Windows x64/MSVC std::string：16字节union，随后size与capacity。
    _fields_ = [('storage', c.c_ubyte * 16), ('size', c.c_size_t), ('capacity', c.c_size_t)]

assert c.sizeof(NativeString) == 32 and c.sizeof(c.c_void_p) == 8
grammar_storage = []
def native_convert(schema):
    data = json.dumps(schema, ensure_ascii=False).encode('utf-8')
    assert len(data) > 15
    backing = c.create_string_buffer(data)
    string = NativeString()
    c.c_void_p.from_buffer(string).value = c.addressof(backing)
    string.size = len(data)
    string.capacity = len(data)
    # 同版本json.h明确common_json含alignas(8) storage[32]。
    parsed = (c.c_uint64 * 4)()
    result = NativeString()
    parsed_ok = False
    try:
        assert parse(c.byref(parsed), c.byref(string)) == c.addressof(parsed)
        parsed_ok = True
        assert convert(c.byref(result), c.byref(parsed), True) == c.addressof(result)
        assert 0 < result.size < 1048576 and result.capacity >= result.size
        ptr = c.c_void_p.from_buffer(result).value if result.capacity > 15 else c.addressof(result)
        grammar = c.string_at(ptr, result.size).decode('utf-8')
        assert 'root ::=' in grammar
        # 保留两份小字符串到短生命周期检查进程退出，不跨CRT猜测释放函数。
        grammar_storage.append(result)
        return grammar
    finally:
        if parsed_ok:
            destroy_json(c.byref(parsed))

grammars = {}
for kind in ['number', 'percent']:
    schema = json.loads((old / ('schema-self-' + kind + '.json')).read_text(encoding='utf-8'))
    grammar = native_convert(schema)
    grammars[kind] = grammar
    (folder / ('native-' + kind + '.gbnf')).write_text(grammar, encoding='utf-8')
original = json.loads((old / 'config-D02-original.json').read_text(encoding='utf-8'))
grammars['original'] = native_convert(original['parameters']['response_format']['json_schema']['schema'])
(folder / 'native-original.gbnf').write_text(grammars['original'], encoding='utf-8')

class ModelParams(c.Structure):
    _fields_ = [('devices', c.c_void_p), ('tensor_buft_overrides', c.c_void_p), ('n_gpu_layers', c.c_int32), ('split_mode', c.c_int), ('load_mode', c.c_int), ('lazy_mode', c.c_int), ('main_gpu', c.c_int32), ('tensor_split', c.c_void_p), ('progress_callback', c.c_void_p), ('progress_callback_user_data', c.c_void_p), ('kv_overrides', c.c_void_p), ('vocab_only', c.c_bool), ('check_tensors', c.c_bool), ('use_extra_bufts', c.c_bool), ('no_host', c.c_bool), ('no_alloc', c.c_bool), ('load_mtp', c.c_bool)]
class Token(c.Structure):
    _fields_ = [('id', c.c_int32), ('logit', c.c_float), ('p', c.c_float)]
class Tokens(c.Structure):
    _fields_ = [('data', c.POINTER(Token)), ('size', c.c_size_t), ('selected', c.c_int64), ('sorted', c.c_bool)]
def signature(name, args, ret):
    fn = getattr(lib, name)
    fn.argtypes = args
    fn.restype = ret
    return fn
signature('llama_backend_init', [], None)()
default = signature('llama_model_default_params', [], ModelParams)
load = signature('llama_model_load_from_file', [c.c_char_p, ModelParams], c.c_void_p)
free_model = signature('llama_model_free', [c.c_void_p], None)
vocab_of = signature('llama_model_get_vocab', [c.c_void_p], c.c_void_p)
tokenize = signature('llama_tokenize', [c.c_void_p, c.c_char_p, c.c_int32, c.POINTER(c.c_int32), c.c_int32, c.c_bool, c.c_bool], c.c_int32)
eos_of = signature('llama_vocab_eos', [c.c_void_p], c.c_int32)
grammar_init = signature('llama_sampler_init_grammar', [c.c_void_p, c.c_char_p, c.c_char_p], c.c_void_p)
apply = signature('llama_sampler_apply', [c.c_void_p, c.POINTER(Tokens)], None)
accept = signature('llama_sampler_accept', [c.c_void_p, c.c_int32], None)
free_sampler = signature('llama_sampler_free', [c.c_void_p], None)
params = default()
params.vocab_only = True
params.n_gpu_layers = 0
model = load(str(root / 'models/qwen2.5-3b-instruct-q4_k_m.gguf').encode(), params)
assert model
rows = []
try:
    vocab = vocab_of(model)
    eos = eos_of(vocab)
    def native_accepts(kind, value):
        text = json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()
        output = (c.c_int32 * 2048)()
        n = tokenize(vocab, text, len(text), output, len(output), False, False)
        assert 0 < n <= len(output)
        sampler = grammar_init(vocab, grammars[kind].encode(), b'root')
        assert sampler
        try:
            for token in list(output[:n]) + [eos]:
                data = (Token * 1)(Token(token, 0.0, 0.0))
                array = Tokens(data, 1, -1, False)
                apply(sampler, c.byref(array))
                if not math.isfinite(data[0].logit):
                    return False, token
                accept(sampler, token)
            return True, None
        finally:
            free_sampler(sampler)
    tests = json.loads((old / 'offline-regex-check.json').read_text(encoding='utf-8'))['tests']
    cases = [('number' if t['rule']['kind'] == '数值' else 'percent', {'answer': t['answer'], 'citations': []}, t['expected_accept']) for t in tests if t['rule']['kind'] is not None]
    cases += [(k, v, expected) for k in ['number', 'percent', 'original'] for v, expected in [({'answer': '证据不足', 'citations': ['self-id']}, True), ({'answer': '证据不足'}, False), ({'citations': []}, False), ({'answer': 1, 'citations': []}, False), ({'answer': '证据不足', 'citations': [1]}, False), ({'answer': '证据不足', 'citations': [], 'extra': True}, False)]]
    for kind, value, expected in cases:
        actual, failed = native_accepts(kind, value)
        rows.append({'kind': kind, 'json_value': value, 'expected_accept': expected, 'native_accept': actual, 'rejected_token': failed})
        save_progress = {'recorded_at': datetime.now().astimezone().isoformat(), 'passed_so_far': all(r['expected_accept'] == r['native_accept'] for r in rows), 'tests': rows, 'generated_tokens': 0}
        (folder / 'native-check-progress.json').write_text(json.dumps(save_progress, ensure_ascii=False, indent=2), encoding='utf-8')
        assert actual == expected, '原生语法正反例与预期不符'
finally:
    free_model(model)
    signature('llama_backend_free', [], None)()
    handles.close()
save('native-pattern-validation.json', {'checked_at': datetime.now().astimezone().isoformat(), 'passed': True, 'tests': rows, 'native_converter_exports': {'parse': parse_name, 'convert': convert_name, 'destroy_json': destroy_name}, 'dll_sha256': {n: hashlib.sha256((binary / n).read_bytes()).hexdigest() for n in ['llama-common.dll', 'llama.dll']}, 'model_load': 'vocab_only，不加载权重张量；不创建推理context，不调用encode/decode', 'generation_requests': 0, 'generated_tokens': 0, 'checked_model_vocabulary': 'Qwen2.5-3B-Instruct-Q4_K_M', 'owned_service_pids': [], 'cleanup_empty_and_not_owned_tests_passed': True, 'proof': '实际装机C++ JSON Schema转换结果，由同包原生grammar sampler检查人工token串及EOS；不是Python正则。', 'abi_limit': '导出C++函数桥接仅针对本次已核对的Windows x64/MSVC布局及本包；不称跨平台SDK。'})
print('PASS', len(rows), 'native grammar acceptance/rejection cases; zero generation calls')
