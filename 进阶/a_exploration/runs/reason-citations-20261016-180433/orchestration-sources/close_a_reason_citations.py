from pathlib import Path
import sys,json,socket,subprocess,shutil,difflib
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
out=Path(Path('a-reason-citations-out.txt').read_text(encoding='utf-8').strip());rt=load(out/'runtime.json');plan=load(out/'intervention-plan.json')
assert rt['dispatches']==rt['confirmed_generations']==0 and rt['model_stopped'] and rt['failure_phase']=='health'
assert not list(out.glob('run-*.json')) and not list(out.glob('item-*.json'))
protected=load(out/'protected-before.json');changed=[p for p,h in protected.items() if sha(ROOT/p)!=h];assert not changed,changed
for p,h in plan['code_hashes'].items():assert sha(ROOT/p)==h,p
assert sha(out/'serialized-request-plan.json')==plan['serialized_requests_sha256']
runs=[]
for p in (HERE/'runs').rglob('run-*.json'):
    r=load(p)
    if r.get('generation_dispatched') and (r.get('usage') or {}).get('completion_tokens',0)>0:runs.append({'path':p.relative_to(ROOT).as_posix(),'run_id':r['run_id']})
assert len(runs)==len({r['run_id'] for r in runs})==81
with socket.socket() as s:s.settimeout(1);closed=s.connect_ex(('127.0.0.1',8080))!=0
assert closed
git=r'C:\Users\86186\AppData\Local\Programs\Git\cmd\git.exe'
def g(*args):
    r=subprocess.run([git,'--no-optional-locks','-c','core.quotepath=false',*args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8');return {'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
write(out/'completion-audit.json',{'at':now(),'status':'technical_stop_before_generation','protected_files_checked':len(protected),'changed':changed,'new_generations':0,'A_unique_generations':81,'cumulative':615,'A_run_ids':runs,'planned_not_executed':plan['order'],'service_stopped':True,'port8080_closed':closed,'memory_before_GiB':rt['memory_before']['available_bytes']/2**30,'minimum_sampled_available_GiB':min(x['available_bytes'] for x in rt['memory_samples'])/2**30,'failure_phase':'health','observed':'日志model loaded及listening；运行器120秒内未取得health.status=ok。','not_confirmed':'各次健康请求异常被既有运行器捕获但未分别保存，无法确定具体HTTP或连接失败原因；未据此认定模型、模板或提示语义错误。','actual_http_template_check':'not_executed','numeric_slot_checks':'not_executed','reasoning_production':'not_checked','strict_formula':plan['strict_formula'],'reason_quality_separate':True,'git_status':g('status','--short','--branch'),'diff_check':g('diff','--check'),'staged_diff':g('diff','--cached','--stat'),'AT_read':False})
write(out/'budget-ledger.json',{'at':now(),'cumulative_before':615,'new':0,'cumulative_after':615,'A_used':81,'original_plan_budget':90,'original_plan_remaining':9,'future_reserved_additional':30,'future_reservation_used':0,'future_reservation_authorizes_execution':False})
write(out/'six-result-status.json',{'at':now(),'rows':[{**e,'status':'not_executed_technical_stop_health','raw_response':None,'evaluation':'not_checked'} for e in plan['order']],'new_generations':0,'no_automatic_retry':True,'no_new_quality_conclusion':True,'retained_current_basis':'本人已接受的紧凑输入＋开启思考；本轮候选尚未获得生成结果。'})
parts=[]
for p in [HERE/'reason_citations.py',HERE/'diagnose_reason_citations.py']:parts.extend(difflib.unified_diff([],p.read_text(encoding='utf-8').splitlines(True),fromfile='/dev/null',tofile='b/'+p.relative_to(ROOT).as_posix()))
(out/'complete-code.diff').write_text(''.join(parts),encoding='utf-8')
orch=out/'orchestration-sources';orch.mkdir()
for name in ['prepare_a_reason_citations.py','close_a_reason_citations.py']:shutil.copy2(name,orch/name)
write(out/'file-manifest.json',{'at':now(),'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.rglob('*') if p.is_file() and not {'slot-cache','__pycache__'}&set(p.parts)],'new_code':['进阶/a_exploration/reason_citations.py','进阶/a_exploration/diagnose_reason_citations.py'],'self_excluded':True})
print(json.dumps({'protected_unchanged':len(protected),'new':0,'A_used':81,'cumulative':615,'closed':closed,'files':len(load(out/'file-manifest.json')['files'])},ensure_ascii=False))
