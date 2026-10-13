"""仅检查开发题完整输入容量；允许接口只有health、props、模板和分词。"""
from pathlib import Path
from datetime import datetime, timezone
import csv
import hashlib
import json
import re
import struct
import subprocess
import sys
import urllib.request
import uuid

repo = Path(__file__).resolve().parents[2]
base = repo / '基础'
sys.path.insert(0, str(base/'starter'))
import student

def development_cases(path):
    # 每个顶层对象单独读取；拿到四道开发题后立即停止，不解析后面的正式题。
    with path.open(encoding='utf-8') as stream:
        def nonspace():
            while True:
                char = stream.read(1)
                if not char or not char.isspace(): return char
        assert nonspace()=='['
        for expected in ('D01','D02','D03','D04'):
            char = nonspace()
            if char==',': char=nonspace()
            assert char=='{'
            raw = char
            while not re.match(r'^\{\s*"id"\s*:\s*"[^"\\]+"',raw):
                char=stream.read(1)
                assert char, 'Unexpected EOF in case header'
                raw+=char
                assert len(raw)<200, 'Case ID must appear first; stop rather than read other data'
            case_id=json.loads('"'+re.match(r'^\{\s*"id"\s*:\s*"([^"\\]+)"',raw).group(1)+'"')
            assert case_id==expected, 'Stop before reading a non-development case body'
            depth=1
            in_string=False
            escape=False
            # 已读取的头部以id值的闭引号结束，后续从字符串之外继续。
            while depth:
                char=stream.read(1)
                assert char
                raw+=char
                if in_string:
                    if escape: escape=False
                    elif char=='\\': escape=True
                    elif char=='"': in_string=False
                elif char=='"': in_string=True
                elif char in '{[': depth+=1
                elif char in '}]': depth-=1
            case=json.loads(raw)
            assert case['split']=='dev'
            yield case

calls=[]
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def service(route,body=None):
    assert route in {'health','props','apply-template','tokenize'}
    data=None if body is None else json.dumps(body,ensure_ascii=False).encode()
    request=urllib.request.Request('http://127.0.0.1:8080/'+route,data=data,headers={'Content-Type':'application/json'})
    with opener.open(request,timeout=20) as response:
        result=json.loads(response.read())
    calls.append({'route':route,'method':'GET' if body is None else 'POST'})
    return result

git=Path.home()/'AppData/Local/Programs/Git/cmd/git.exe'
head=subprocess.run([str(git),'rev-parse','HEAD'],cwd=repo,capture_output=True,text=True,encoding='utf-8',check=True).stdout.strip()
assert head=='58a8655a30c50ac565472081fab88fb70b2308f9'
health=service('health')
props=service('props')
assert props['default_generation_settings']['n_ctx']==2048
rows=[]
for case in development_cases(base/'data/cases.json'):
    by_id={p['id']:p for p in case['passages']}
    for condition in ('E','R0','R1','R2','K'):
        ids=case['conditions'][condition]
        passages=[by_id[value] for value in ids]
        messages=student.prepare_messages(case['question'],passages)
        assert json.loads(messages[1]['content'])=={'question':case['question'],'passages':passages}
        prompt=service('apply-template',{'messages':messages})['prompt']
        assert all(message['content'] in prompt for message in messages)
        tokens=service('tokenize',{'content':prompt,'add_special':True,'parse_special':True})['tokens']
        count=len(tokens)
        row={'case_id':case['id'],'condition':condition,'passage_ids':ids,'passage_count':len(passages),
             'input_tokens':count,'capacity_with_256':count+256,'capacity_with_1024':count+1024,
             'fits_2048_input':count<2048,'fits_2048_with_256':count+256<2048,
             'fits_2048_with_1024':count+1024<2048,'messages':messages,'rendered_prompt':prompt,'token_ids':tokens}
        rows.append(row)
        print(case['id'],condition,count,count+256,count+1024,flush=True)
assert len(rows)==20
assert rows[0]['input_tokens']==824, 'D01 E calibration differs from previous real request'

# 从GGUF元数据核对KV估计所需维度，不读取权重张量。
model=Path(props['model_path'])
metadata={}
types={0:('B',1),1:('b',1),2:('H',2),3:('h',2),4:('I',4),5:('i',4),6:('f',4),7:('?',1),10:('Q',8),11:('q',8),12:('d',8)}
with model.open('rb') as stream:
    def integer(fmt): return struct.unpack('<'+fmt,stream.read(struct.calcsize('<'+fmt)))[0]
    def string(): return stream.read(integer('Q')).decode('utf-8')
    def value(kind,keep=False):
        if kind==8:
            length=integer('Q')
            if keep: return stream.read(length).decode('utf-8')
            stream.seek(length,1)
        elif kind==9:
            subtype=integer('I'); length=integer('Q')
            if subtype in types: stream.seek(types[subtype][1]*length,1)
            else:
                for _ in range(length): value(subtype)
        else:
            fmt,size=types[kind]
            return integer(fmt) if keep else stream.seek(size,1)
    assert stream.read(4)==b'GGUF'
    version=integer('I'); tensor_count=integer('Q'); count=integer('Q')
    wanted={'general.architecture','qwen3.block_count','qwen3.attention.head_count_kv','qwen3.attention.key_length','qwen3.attention.value_length','qwen3.embedding_length','qwen3.attention.head_count','qwen3.context_length','general.file_type'}
    for _ in range(count):
        key=string(); kind=integer('I')
        item=value(kind,key in wanted)
        if key in wanted: metadata[key]=item

layers=metadata['qwen3.block_count']
heads=metadata['qwen3.attention.head_count_kv']
key_dim=metadata['qwen3.attention.key_length']
value_dim=metadata['qwen3.attention.value_length']
kv_per_token=layers*heads*(key_dim+value_dim)*2
maximum=max(r['input_tokens'] for r in rows)
result={'record_kind':'context_capacity_check','counts_as_generation':False,'generated_tokens':0,
        'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'source_commit':head,
        'student_sha256':hashlib.sha256((base/'starter/student.py').read_bytes()).hexdigest(),
        'data_scope':'Read only first four development case bodies, then stop before formal case bodies; no answer file read',
        'template_mode':'Same Qwen3 template and thinking-off server as first D01; no prompt variant',
        'tokenization_options':{'add_special':True,'parse_special':True},
        'server_props':props,'model_gguf_metadata':metadata,'rows':rows,'maximum_input_tokens':maximum,
        'capacity_with_256':maximum+256,'capacity_with_1024':maximum+1024,
        'kv_memory_estimate':{'assumed_k_and_v_dtype':'f16 as unchanged runtime defaults','bytes_per_token':kv_per_token,
                              'bytes_2048':kv_per_token*2048,'bytes_4096':kv_per_token*4096,'bytes_8192':kv_per_token*8192,
                              'scope':'KV cache estimate only; excludes buffers, graph, weight pages and OS memory'},
        'http_calls':calls,'no_generation_endpoint_called':True}
props['model_path']='%LOCALAPPDATA%/ANTLabLocalModel/models/Qwen3-0.6B-Q8_0.gguf'
folder=base/'runs/capacity/stage3'
assert not folder.exists(), 'Preserve existing capacity results'
folder.mkdir(parents=True)
(folder/'inputs.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
fields=('case_id','condition','passage_count','input_tokens','capacity_with_256','capacity_with_1024','fits_2048_input','fits_2048_with_256','fits_2048_with_1024')
with (folder/'summary.csv').open('w',encoding='utf-8-sig',newline='') as stream:
    writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore')
    writer.writeheader(); writer.writerows(rows)
print('MAXIMUM:',maximum,'PLUS256:',maximum+256,'PLUS1024:',maximum+1024)
print('GGUF DIMENSIONS:',metadata)
print('KV BYTES PER TOKEN:',kv_per_token)
print('PASS only non-generation endpoints; dev-only streaming; full messages preserved')
