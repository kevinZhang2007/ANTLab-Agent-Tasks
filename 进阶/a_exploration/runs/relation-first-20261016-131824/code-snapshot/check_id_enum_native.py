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
old = folder.parent
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

cases=json.loads((folder/'schema-cases.json').read_text(encoding='utf-8'))
grammars={item['name']:native_convert(item['schema']) for item in cases}
for name,grammar in grammars.items():(folder/('native-'+name+'.gbnf')).write_text(grammar,encoding='utf-8')
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
model = load(str(root / 'models/Qwen3-0.6B-Q8_0.gguf').encode(), params)
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
    for case in cases:
        for fixture in case['fixtures']:
            actual,failed=native_accepts(case['name'],fixture['response'])
            rows.append({'case':case['name'],'name':fixture['name'],'expected':fixture['accept'],'actual':actual,'rejected_token':failed,'response':fixture['response']})
            save('native-progress-'+str(len(rows))+'.json',{'tests':rows.copy(),'generation_calls':0})
            assert actual==fixture['accept'],'原生enum正反例不符'

finally:
    free_model(model);signature('llama_backend_free',[],None)();handles.close()
save('native-id-enum-validation.json',{'checked_at':datetime.now().astimezone().isoformat(),'passed':True,'tests':rows,'generation_calls':0,'dll_sha256':{n:hashlib.sha256((binary/n).read_bytes()).hexdigest() for n in ['llama-common.dll','llama.dll']},'scope':'同包原生Schema转换及grammar sampler，不加载张量，不创建context或decode；动态ID enum正反例，未知ID由原生grammar拒绝；摘录真实性和语义不由Schema保证'})
print('PASS',len(rows),'native ID-enum cases; zero generation calls',flush=True)
