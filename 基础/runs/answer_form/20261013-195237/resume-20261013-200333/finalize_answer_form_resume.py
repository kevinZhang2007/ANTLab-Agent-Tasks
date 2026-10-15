from pathlib import Path
from datetime import datetime
import json,hashlib,difflib,socket,subprocess,shutil
repo=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');work=Path(__file__).parent
folder=repo/'基础/runs/answer_form/20261013-195237/resume-20261013-200333';old=folder.parent
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
def save(name,value):
 p=folder/name;assert not p.exists();p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
records=[load(p) for p in sorted(folder.glob('run-*.json'))];runtime=load(folder/'runtime.json');plan=load(old/'design-plan.json')
assert len(records)==8 and runtime['generation_attempts']==8 and runtime['server_stopped'] and not runtime['stopped_on_technical_failure']
native=load(folder/'native-pattern-validation.json');assert native['passed'] and len(native['tests'])==41 and native['generation_requests']==0
assert len({r['run_id'] for r in records})==8
protected=load(folder/'protected-hashes.json');changed=[p for p,h in protected.items() if hashlib.sha256((repo/p).read_bytes()).hexdigest()!=h];assert not changed
old_ids={p.stem.split('run-')[-1] for p in [repo/name for name in protected] if p.name.startswith('run-')}
assert not ({r['run_id'] for r in records}&old_ids)
planned_order=[(item['case_id'],v) for item in plan['call_order'] for v in item['variants']]
index=load(folder/'result-index.json');assert [(r['case_id'],r['variant']) for r in index]==planned_order
checks=[]
history=load(old/'historical-replay-inputs-and-schemas.json')
for cid in ['D01','D02','D03','D04']:
 a=next(r for r in records if r['case_id']==cid and r['variant']=='original_schema')
 b=next(r for r in records if r['case_id']==cid and r['variant']=='answer_form_schema')
 h=next(r for r in history if r['case_id']==cid)
 assert a['messages']==b['messages'] and a['used_passages']==b['used_passages']==h['passages']
 without_schema=lambda r:{k:v for k,v in r['actual_http_request_body'].items() if k!='response_format'}
 assert without_schema(a)==without_schema(b)
 assert a['actual_http_request_body']['response_format']['json_schema']['schema']==h['original_schema']
 assert b['actual_http_request_body']['response_format']['json_schema']['schema']==h['constrained_schema']
 for r in [a,b]:
  assert r['actual_http_request_body']['max_tokens']==256 and all(r['parameter_checks'].values()) and r['total_capacity']<4096
 checks.append({'case_id':cid,'messages_and_passages_identical':True,'match_saved_historical_input':True,'all_non_schema_request_fields_identical':True,'schema_changed':h['original_schema']!=h['constrained_schema'],'original_run_id':a['run_id'],'constrained_run_id':b['run_id'],'used_ids':a['original_passage_ids'],'original_seconds':a['elapsed_seconds'],'constrained_seconds':b['elapsed_seconds']})
ports={}
for port in [8080,8088]:
 with socket.socket() as s:s.settimeout(1);ports[str(port)]=s.connect_ex(('127.0.0.1',port))!=0
assert all(ports.values())
git=r'C:\Users\86186\AppData\Local\Programs\Git\cmd\git.exe'
def command(*args):
 p=subprocess.run([git,*args],cwd=repo,text=True,encoding='utf-8',capture_output=True);return {'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
audit={'checked_at':datetime.now().astimezone().isoformat(),'model_generation_calls':8,'native_grammar_checks':41,'native_generated_tokens':0,'cumulative_generation_calls':144,'technical_generation_failures':0,'quality_retries':0,'unique_new_run_ids':8,'old_protected_files':len(protected),'changed_old_files':changed,'original_plan_failures_stop_record_unchanged':True,'first_formal_freeze_responses_reviews_and_three_documents_unchanged':True,'pair_checks':checks,'actual_order_matches_old_plan':True,'precall_plan_precedes_generation':load(folder/'precall-plan.json')['recorded_at']<min(r['recorded_at'] for r in records),'owned_service_pid':runtime['owned_service_pid'],'cleanup_result':runtime['cleanup_result'],'ports_not_listening':ports,'build_info':runtime['props']['build_info'],'truncation_flags':load(folder/'summary.json')['truncation_flags'],'finish_reasons':[r['response']['choices'][0]['finish_reason'] for r in records],'driver_actual_bytes_match_snapshot':(repo/'基础/tests/run_answer_form_pairs.py').read_bytes()==(folder/'snapshot-run_answer_form_pairs.py').read_bytes(),'reviewer_actual_bytes_match_snapshot':(repo/'基础/tests/review_answer_form_pairs.py').read_bytes()==(folder/'snapshot-review_answer_form_pairs.py').read_bytes(),'driver_header_note':'沿用旧驱动头部注释中有十二次两步字样；本次实际逻辑、计划、硬上限和唯一run记录均为8次回答，不将其作为完整两步流程。执行文件与快照保留，不在运行后改写。','git_status':command('-c','core.quotepath=false','status','--short','--branch'),'staged_diff':command('diff','--cached','--stat'),'production_diff':command('diff','--','基础/starter','report.md','README.md','基础/开发记录.md')}
assert audit['driver_actual_bytes_match_snapshot'] and audit['reviewer_actual_bytes_match_snapshot'] and not audit['staged_diff']['stdout'] and not audit['production_diff']['stdout']
save('final-audit.json',audit)
save('native-support-method.json',{'recorded_at':datetime.now().astimezone().isoformat(),'official_commit':'d81235049','sources':['https://github.com/ggml-org/llama.cpp/blob/d81235049/common/json-schema-to-grammar.h','https://github.com/ggml-org/llama.cpp/blob/d81235049/common/json-schema-to-grammar.cpp','https://github.com/ggml-org/llama.cpp/blob/d81235049/common/json.h','https://github.com/ggml-org/llama.cpp/blob/d81235049/include/llama.h','https://github.com/ggml-org/llama.cpp/blob/d81235049/common/sampling.cpp'],'native_conversion':'直接调用装机common_json::parse和json_schema_to_grammar(common_json,true)导出，实际GBNF保存native-*.gbnf；不从props读取grammar。','native_validation':'同包llama_sampler_init_grammar/apply/accept，逐个检查人工token串与EOS。这里只加载词表，不decode、不生成。','command_reference':'native-v2-command-result.json','proof_reference':'native-pattern-validation.json','all_old_preparation_errors_preserved':True,'source_fetch_failure':'source-fetch-failure.json：unicode.cpp的TLS失败保留；未重试或关闭证书校验，转用已安装库，不需要源码构建。','scope_limit':'桥接针对本次核对的Windows x64/MSVC布局及本包导出，不声称跨平台通用接口。'})
for name in ['prepare_answer_form_resume.py','verify_run_native_v2.py','build_answer_form_driver.py','finalize_answer_form_resume.py']:shutil.copyfile(work/name,folder/name)
combined=(folder/'repair-full.diff').read_text(encoding='utf-8')+(folder/'driver-full.diff').read_text(encoding='utf-8')
review=repo/'基础/tests/review_answer_form_pairs.py'
combined+=''.join(difflib.unified_diff([],review.read_text(encoding='utf-8').splitlines(True),fromfile='/dev/null',tofile=review.relative_to(repo).as_posix()))
(folder/'all-code.diff').write_text(combined,encoding='utf-8')
paths=['基础/tests/run_answer_form_pairs.py','基础/tests/review_answer_form_pairs.py']+[p.relative_to(repo).as_posix() for p in sorted(folder.rglob('*')) if p.is_file()]+[(folder/'new-files.json').relative_to(repo).as_posix()]
save('new-files.json',{'count':len(paths),'all_new':True,'files':paths})
out=work.parent/'outputs/answer-form-resume';out.mkdir(parents=True,exist_ok=True)
for n in ['all-code.diff','repair-full.diff','native-pattern-validation.json','native-v2-command-result.json','native-support-method.json','summary.json','semantic-review.json','result-index.json','final-audit.json','new-files.json']:(out/n).write_bytes((folder/n).read_bytes())
print(json.dumps({'new_files':len(paths),'pair_checks':checks,'old_protected_files_unchanged':len(protected),'new_generations':8,'cumulative':144,'native_tests':41,'ports_stopped':ports,'owned_pid':runtime['owned_service_pid'],'driver_snapshot_matches':audit['driver_actual_bytes_match_snapshot']},ensure_ascii=False,indent=2))
