from pathlib import Path
from datetime import datetime
import json,hashlib,socket,sys,difflib,subprocess,shutil
work=Path(__file__).parent;folder=Path((work/'answer_form_folder.txt').read_text(encoding='utf-8'));repo=folder.parents[3]
sys.path.insert(0,str(repo/'基础/tests'));import answer_form_candidate as candidate
def save(name,value):
 p=folder/name;assert not p.exists();p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
save('native-validation-failure.json',{'recorded_at':datetime.now().astimezone().isoformat(),'stage':'native_synthetic_string_validation','root_error':"KeyError: props['default_generation_settings']['params']['grammar']",'secondary_error':'IndexError: finally wrote probes[-1] while probes was empty','classification':'检查脚本假设错误，不是pattern不支持的证明','complete_props_response_preserved':False,'observed_http_routes':['health','props'],'generation_requests':0,'development_calls_completed':0,'development_calls_not_executed':8,'decision':'技术检查失败后停止，不自动换协议或追加生成。'})
original=json.loads((repo/'基础/runs/two_step/dev_r0/config.answer.json').read_text(encoding='utf-8'))
base=original['parameters']['response_format']['json_schema']['schema'];rows=[]
history=repo/'基础/runs/two_step_linked/20261013-193700'
for cid in ['D01','D02','D03','D04']:
 task=json.loads((history/('task-'+cid+'.json')).read_text(encoding='utf-8'))
 schema,rule=candidate.constrain_schema(task['question'],base)
 conf=json.loads(json.dumps(original));conf['parameters']['response_format']['json_schema']['schema']=schema
 save('config-'+cid+'-original.json',original);save('config-'+cid+'-constrained.json',conf)
 rows.append({'case_id':cid,'question':task['question'],'passages':task['branches']['linked_answer']['used_passages'],'historical_selection_run_id':task['selection_run_id'],'historical_answer_input_source':(history/('task-'+cid+'.json')).relative_to(repo).as_posix()+':branches.linked_answer.used_passages','rule':rule,'original_schema':base,'constrained_schema':schema,'status':'not_run','selection_reexecuted':False})
save('historical-replay-inputs-and-schemas.json',rows)
source=(folder/'official-json-schema-to-grammar.cpp').read_text(encoding='utf-8').splitlines()
sections=[(362,381),(881,891)]
save('support-evidence.json',{'recorded_at':datetime.now().astimezone().isoformat(),'official_commit':'d81235049','source_url':'https://raw.githubusercontent.com/ggml-org/llama.cpp/d81235049/common/json-schema-to-grammar.cpp','sections':[{'lines':[a,b],'text':'\n'.join(source[a-1:b])} for a,b in sections],'source_supports':'string.pattern进入转换器；首尾须锚定；不支持的表达式会告警并回退任意字符串。','local_binary_version':'0.6.0-dev build 11429 commit d81235049','native_compile_result':'相同Schema字节的ASCII副本零输出编译返回0，无pattern fallback告警。','local_regex_result':'28个自造识别/字符串测试通过，仅为本地规则检查。','unverified':'原生grammar对自造正/反例的实际接受与拒绝未完成；未以HTTP成功或CLI返回0假装完整约束生效。','generation_result':'本轮0次生成，8次开发对照未执行。'})
protected=json.loads((folder/'protected-hashes.json').read_text(encoding='utf-8'));changed=[p for p,h in protected.items() if hashlib.sha256((repo/p).read_bytes()).hexdigest()!=h];assert not changed
ports={}
for port in [8080,8088]:
 with socket.socket() as sock:sock.settimeout(1);ports[str(port)]=sock.connect_ex(('127.0.0.1',port))!=0
assert all(ports.values())
git=r'C:\Users\86186\AppData\Local\Programs\Git\cmd\git.exe'
def command(*args):
 p=subprocess.run([git,*args],cwd=repo,text=True,encoding='utf-8',capture_output=True);return {'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
save('stop-summary.json',{'recorded_at':datetime.now().astimezone().isoformat(),'status':'stopped_before_development_generation','new_generation_calls':0,'cumulative_generation_calls':136,'planned_development_calls':8,'completed_development_calls':0,'unexecuted_development_calls':8,'pattern_supported_by_source':True,'zero_budget_compilation_passed':True,'runtime_pattern_acceptance_tests_complete':False,'reason':'检查脚本取不存在的props.grammar字段失败，次级清理记录失败；不据此判版本不支持。','port_not_listening':ports,'old_protected_files':len(protected),'changed_old_files':changed,'first_freeze_old_responses_reviews_and_three_documents_unchanged':True,'staged_diff':command('diff','--cached','--stat'),'production_diff':command('diff','--','基础/starter/student.py','report.md','README.md','基础/开发记录.md')})
diff=''
for name in ['answer_form_candidate.py','check_answer_form.py']:
 p=repo/'基础/tests'/name;(folder/('snapshot-'+name)).write_bytes(p.read_bytes())
 diff+=''.join(difflib.unified_diff([],p.read_text(encoding='utf-8').splitlines(True),fromfile='/dev/null',tofile=p.relative_to(repo).as_posix()))
for name in ['prepare_answer_form.py','native_schema_compile.py','native_schema_compile_ascii.py','check_native_pattern.py','archive_answer_form_stop.py']:shutil.copyfile(work/name,folder/name)
(folder/'code-full.diff').write_text(diff,encoding='utf-8')
paths=['基础/tests/answer_form_candidate.py','基础/tests/check_answer_form.py']+[p.relative_to(repo).as_posix() for p in sorted(folder.rglob('*')) if p.is_file()]+[(folder/'new-files.json').relative_to(repo).as_posix()]
save('new-files.json',{'count':len(paths),'files':paths,'all_new':True})
out=work.parent/'outputs/answer-form';out.mkdir(parents=True,exist_ok=True)
for n in ['stop-summary.json','support-evidence.json','native-validation-failure.json','historical-replay-inputs-and-schemas.json','code-full.diff','new-files.json']:(out/n).write_bytes((folder/n).read_bytes())
print(json.dumps({'folder':folder.relative_to(repo).as_posix(),'new_files':len(paths),'new_generations':0,'ports_stopped':ports,'protected_files_unchanged':len(protected),'rules':[{k:r[k] for k in ['case_id','rule','status']} for r in rows]},ensure_ascii=False,indent=2))
