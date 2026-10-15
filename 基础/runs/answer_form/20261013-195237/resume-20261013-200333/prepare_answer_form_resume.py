from pathlib import Path
from datetime import datetime
import json,hashlib,urllib.request
repo=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');work=Path(__file__).parent
old=repo/'基础/runs/answer_form/20261013-195237'
at=datetime.now().astimezone();folder=old/('resume-'+at.strftime('%Y%m%d-%H%M%S'));folder.mkdir(exist_ok=False)
def save(n,v):(folder/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
save('protected-hashes.json',{p.relative_to(repo).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in repo.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts})
plan=json.loads((old/'design-plan.json').read_text(encoding='utf-8'))
save('repair-plan.json',{'recorded_at':at.isoformat(),'old_plan':old.relative_to(repo).as_posix()+'/design-plan.json','generation_count_before':136,'existing_this_round_generations':0,'call_order_unchanged':plan['call_order'],'generation_limit':8,'repairs':['不用props.grammar；同commit官方C++ Schema转换器输出GBNF，装机llama.dll的原生grammar sampler过滤人工token串。','清理仅操作本工具记录的自有Popen/PID，空列表可处理。','新文件实现修复，旧计划/异常/停止记录/源码均保留；逐项检查实际新文件和diff，不靠文本替换成功假设。'],'offline_scope':'转换和grammar过滤不调用llama_decode/encode，不生成token；开发请求仍严格最多8次。','stop':'原生正反例、构建或请求技术失败保存后停止，不自动重试。'})
build=work/'answer-form-native-build';build.mkdir(exist_ok=True)
sources=[]
for rel in ['common/json-schema-to-grammar.h','common/json-schema.h','common/json-schema.cpp','common/json.h','common/trie.h','common/unicode.h','common/unicode.cpp','vendor/nlohmann/json.hpp']:
 url='https://raw.githubusercontent.com/ggml-org/llama.cpp/d81235049/'+rel
 try:
  raw=urllib.request.urlopen(url,timeout=25).read()
  name=Path(rel).name;(build/name).write_bytes(raw);(folder/('official-'+name)).write_bytes(raw)
  sources.append({'url':url,'revision':'d81235049','file':'official-'+name,'sha256':hashlib.sha256(raw).hexdigest()})
 except Exception as e:
  save('source-fetch-failure.json',{'url':url,'error':repr(e),'model_calls':0});raise
(build/'json-schema-to-grammar.cpp').write_bytes((old/'official-json-schema-to-grammar.cpp').read_bytes())
save('source-index.json',sources)
(work/'answer_form_resume_folder.txt').write_text(str(folder),encoding='utf-8');print(folder);print(build)
