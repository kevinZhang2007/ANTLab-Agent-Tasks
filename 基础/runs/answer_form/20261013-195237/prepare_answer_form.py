from pathlib import Path
from datetime import datetime
import json,hashlib,subprocess,urllib.request
repo=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');work=Path(__file__).parent
at=datetime.now().astimezone();folder=repo/'基础/runs/answer_form'/at.strftime('%Y%m%d-%H%M%S');folder.mkdir(parents=True,exist_ok=False)
def save(name,value):(folder/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
save('protected-hashes.json',{p.relative_to(repo).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in repo.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts})
binary=Path(r'C:\Users\86186\AppData\Local\ANTLabLocalModel\llama-b11429')
version=subprocess.run([str(binary/'llama-server.exe'),'--version'],capture_output=True,text=True,encoding='utf-8',check=True)
save('design-plan.json',{'recorded_at':at.isoformat(),'status':'designed_before_implementation_and_generation','binary_version':version.stdout+version.stderr,
 'role':'评测后独立开发探索，首次正式结果及冻结方案保持。','hypothesis':'仅从明确输出要求派生answer pattern可能避免单位/说明导致的指定答法失败。','competing_explanation':'形式约束不能补计算、拒答或必要引用；也可能只将错误答案变为合规格式。',
 'input_source':'基础/runs/two_step_linked/20261013-193700/task-D01.json至task-D04.json中的linked_answer.used_passages，按完整原段落历史重放；不重新定位或补页，不称完整两步重跑。',
 'settings':'Qwen3-0.6B-Q8_0，llama.cpp b11429，4096/单槽/CPU4线程，关闭思考、上下文移位和预热，旧采样数值参数/seed42/max_tokens256及统一提示词不改。',
 'pattern_rules':'只识别question末尾明确的只输出数值或只输出百分数；冲突或不可靠则沿用原Schema。允许正负整数、小数、科学记数；百分数加%符号。保留证据不足分支，不限制正确数值或引用。',
 'support_preflight':'核对同commit官方转换源码；用两种自造Schema作本机零输出预算编译检查并保留日志；自造合法/非法字符串核对。若有不支持pattern或fallback告警则停止，不能当生效。',
 'native_string_validation':'若能用本机grammar sampler离线核验自造JSON则保存结果；不额外生成自造答案。不能完成可靠支持核验时停止开发生成。',
 'call_order':[{'case_id':c,'variants':(['original_schema','answer_form_schema'] if i%2==0 else ['answer_form_schema','original_schema'])} for i,c in enumerate(['D01','D02','D03','D04'])],
 'generation_limit':8,'evaluation':'全部调用结束后才评价，分别指定答法、语义、引用支持和严格成功；不得处理原回答。','timing':'仅本轮回答阶段客户端完整请求耗时，不和共享定位完整流程比较。',
 'stop':'不支持/回退、容量或参数不符、技术失败保存后停止；质量错误不重试；结束关闭自有服务。','previous_generation_count':136})
save('initial-read-note.json',{'recorded_at':at.isoformat(),'issue':'沙箱LOCALAPPDATA指向隔离路径，初次版本读取未找到文件；用明确真实安装路径在授权环境读取成功。','model_requests':0})
sources=[]
for rel,name in [('common/json-schema-to-grammar.cpp','official-json-schema-to-grammar.cpp'),('include/llama.h','official-llama.h'),('tests/test-json-schema-to-grammar.cpp','official-pattern-tests.cpp')]:
 url='https://raw.githubusercontent.com/ggml-org/llama.cpp/d81235049/'+rel
 try:
  raw=urllib.request.urlopen(url,timeout=30).read();(folder/name).write_bytes(raw)
  sources.append({'url':url,'revision':'d81235049','path':name,'sha256':hashlib.sha256(raw).hexdigest()})
 except Exception as e:
  save('source-fetch-failure.json',{'recorded_at':datetime.now().astimezone().isoformat(),'url':url,'error':repr(e),'generation_calls':0});raise
save('official-source-index.json',{'recorded_at':datetime.now().astimezone().isoformat(),'sources':sources,'reused_api_format_evidence':'基础/runs/format/schema_r0/official-evidence.json','request_path':'response_format.json_schema.schema'})
(work/'answer_form_folder.txt').write_text(str(folder),encoding='utf-8');print(folder)
