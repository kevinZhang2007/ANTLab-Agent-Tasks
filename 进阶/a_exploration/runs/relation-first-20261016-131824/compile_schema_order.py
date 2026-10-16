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
rows=[]
for item in cases:
    grammar=native_convert(item['schema']);(folder/('compiled-'+item['name']+'.gbnf')).write_text(grammar,encoding='utf-8')
    root_line=next(line for line in grammar.splitlines() if line.startswith('root ::='))
    fields=['relation','explanation','sentence_ids','label'];positions=[root_line.find(k+'-kv') for k in fields]
    forced=all(x>=0 for x in positions) and positions==sorted(positions) and root_line.count('-kv')==4 and '|' not in root_line
    rows.append({'case':item['name'],'root':root_line,'positions':positions,'forced':forced})
save('schema-order-compilation.json',{'at':datetime.now().astimezone().isoformat(),'rows':rows,'all_forced':all(x['forced'] for x in rows),'generation_calls':0})
handles.close()
