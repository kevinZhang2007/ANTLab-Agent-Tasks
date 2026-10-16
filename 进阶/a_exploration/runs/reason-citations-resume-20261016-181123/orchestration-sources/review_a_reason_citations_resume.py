from pathlib import Path
import sys,json,shutil,difflib,subprocess,socket
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
from sentence_selection import expand
from sentence_interface import interface_response
from locator import Locator
out=Path(Path('a-health-resume-out.txt').read_text(encoding='utf-8').strip());rt=load(out/'runtime.json');assert rt['dispatches']==rt['confirmed_generations']==6 and rt['model_stopped'] and 'error' not in rt
inputs={x['id']:x for x in load(out/'diagnostic-inputs.json')};plan=load(out/'intervention-plan.json');entries=[load(p) for p in sorted(out.glob('item-*.json'))];assert len(entries)==6
refs={x['id']:x for x in load(ROOT/'进阶/materials/a_dev_answers.json')};manual=load(out/'semantic-review-basis.json');locator=Locator(load(ROOT/'进阶/materials/page_words.json'))
rows=[];raws=[];traces=[];md=['# 紧凑输入与开启思考：理由和引用提示六次对照','固定自动improved证据历史重放，不是端到端检索成绩。Codex辅助原文复核，尚待本人确认。','严格成功不加入理由一致性门槛：'+plan['strict_formula']]
for n,e in enumerate(entries,1):
    r=load(out/e['raw_record']);x=inputs[e['id']];v=e['variant'];m=manual[e['id']][v]
    assert all(load(out/f'mode-observation-{n:02}.json')['verified'].values()) and r['messages']==x['messages'][v] and r['config']==x['configs'][v]
    ex=load(out/f'expansion-{n:02}.json');assert ex==expand(r['content'],x['blocks'],x['sentence_index'],x['doc_ids'],x['snapshot'])
    obj=ex['parsed_internal'];fmt=isinstance(obj,dict) and set(obj)=={'label','reason','sentence_ids'} and isinstance(obj['reason'],str) and isinstance(obj['sentence_ids'],list) and obj['label'] in ['supported','contradicted','insufficient'];label=obj.get('label') if fmt else None;correct=fmt and label==refs[e['id']]['label']
    selected=ex['selected_sources'];auth=ex['valid'] and all(next(b for b in x['blocks'] if b['block_id']==s['block_id'])['text'][s['start']:s['end']]==s['text'] for s in selected)
    strict=bool(fmt and ex['valid'] and correct and m['necessary'] is True and m['support'] is True and m['unrelated'] is False)
    message=r['response']['choices'][0]['message'];thought=message.get('reasoning_content');tf=f'reasoning-{n:02}-{e["id"]}-{v}.txt' if isinstance(thought,str) else None
    if tf:assert not (out/tf).exists();(out/tf).write_text(thought,encoding='utf-8',newline='')
    trace={**e,'raw_message':message,'reasoning_content':thought,'reasoning_text_file':tf,'content':message.get('content'),'usage':r['usage'],'finish_reason':r['finish_reason'],'reasoning_not_scored_as_final':True};traces.append(trace)
    row={**e,'raw_content':r['content'],'parsed_final':obj,'public_reference_label':refs[e['id']]['label'],'label_correct':correct,'format_complete':fmt,'selection_valid':ex['valid'],'source_authenticity':True if selected and auth else 'not_applicable_empty' if ex['valid'] else 'not_checked','reason_label_consistent':m['consistent'],'reason_source_attribution_correct':m.get('attribution','not_checked'),'necessary_evidence_coverage':m['necessary'],'citation_support_actual_label':m['support'],'has_unrelated_citations':m['unrelated'],'strict_complete_success':strict,'basis':m['basis'],'selected_sources':selected,'expanded_response':ex['expanded_response'],'input_tokens':r['input_tokens'],'usage':r['usage'],'finish_reason':r['finish_reason'],'budget_exhausted':r['finish_reason']=='length','truncated':r['truncated'],'client_seconds':r['elapsed_seconds'],'reasoning_produced':bool(thought),'judgment_source':'unverified','reviewer':'Codex辅助原文复核，尚待本人确认'}
    rows.append(row);write(out/f'review-item-{n:02}.json',row);write(out/f'raw-output-{n:02}.json',trace)
    interface=interface_response(e['request_id'],x['claim'],x['doc_ids'],x['snapshot'],r['run_id'],ex,r['elapsed_seconds'],locator=locator,actual_input_blocks=x['blocks']);assert interface['support_status']=='not_checked';write(out/f'interface-response-{n:02}.json',interface)
    raws.append({**e,'actual_http_request_raw':r['actual_http_request_raw'],'raw_response':r['raw_response'],'content':r['content'],'reasoning_content':thought,'usage':r['usage'],'finish_reason':r['finish_reason'],'client_seconds':r['elapsed_seconds']})
    md+=['## '+e['id']+' '+v,'```json',r['content'],'```',f"耗时{r['elapsed_seconds']:.3f}秒；输入{r['input_tokens']}、输出{r['usage']['completion_tokens']} tokens；结束{r['finish_reason']}。",m['basis']]
groups={}
for v in ['original','revised']:
    rs=[r for r in rows if r['variant']==v]
    groups[v]={'denominator':3,'label_correct':sum(r['label_correct'] for r in rs),'format_complete':sum(r['format_complete'] for r in rs),'reason_label_consistent':sum(r['reason_label_consistent'] is True for r in rs),'source_authenticity':sum(r['source_authenticity'] is True for r in rs),'necessary_coverage':sum(r['necessary_evidence_coverage'] is True for r in rs),'necessary_coverage_ambiguous':sum(r['necessary_evidence_coverage']=='ambiguous' for r in rs),'citation_support':sum(r['citation_support_actual_label'] is True for r in rs),'citation_support_ambiguous':sum(r['citation_support_actual_label']=='ambiguous' for r in rs),'unrelated_citations':sum(r['has_unrelated_citations'] is True for r in rs),'strict_complete_success':sum(r['strict_complete_success'] for r in rs),'budget_exhausted':sum(r['budget_exhausted'] for r in rs),'input_tokens':sum(r['input_tokens'] for r in rs),'output_tokens':sum(r['usage']['completion_tokens'] for r in rs),'client_seconds':sum(r['client_seconds'] for r in rs)}
pairs=[]
for task in inputs:
    a=next(r for r in rows if r['id']==task and r['variant']=='original');b=next(r for r in rows if r['id']==task and r['variant']=='revised');pairs.append({'id':task,'old_label':a['parsed_final']['label'],'new_label':b['parsed_final']['label'],'label_regressed':a['label_correct'] and not b['label_correct'],'historically_correct_AD02_regressed':task=='AD02' and not b['label_correct'],'old_strict':a['strict_complete_success'],'new_strict':b['strict_complete_success'],'old_necessary':a['necessary_evidence_coverage'],'new_necessary':b['necessary_evidence_coverage'],'old_support':a['citation_support_actual_label'],'new_support':b['citation_support_actual_label'],'old_unrelated':a['has_unrelated_citations'],'new_unrelated':b['has_unrelated_citations'],'old_consistent':a['reason_label_consistent'],'new_consistent':b['reason_label_consistent'],'delta_client_seconds':b['client_seconds']-a['client_seconds']})
veto=any(p['label_regressed'] or p['historically_correct_AD02_regressed'] for p in pairs);a=groups['original'];b=groups['revised'];adopt=not veto and (b['strict_complete_success'],b['label_correct'])>(a['strict_complete_success'],a['label_correct'])
decision={'at':now(),'adopt_prompt_candidate':adopt,'existing_correct_item_regression_veto':veto,'rule':'严格成功优先，其次标签正确；已有正确项不得退步，同分保留旧流程。','retain_base':'紧凑输入＋开启思考由本人决定保留，提示候选独立取舍。','strict_formula':plan['strict_formula'],'reason_quality_separate':True,'no_auto_label_flip_or_citation_removal':True,'AD03_missing_direct_source_preserved':True,'scope':'仅三题固定自动证据；没有读取七题或更新端到端成绩。','new_generations':6,'cumulative':621,'A_used':87,'original_plan_remaining':3,'future_reserved_additional':30,'future_reservation_used':0,'technical_failures':0,'quality_retries':0}
write(out/'review.json',{'at':now(),'rows':rows,'groups':groups,'pairs':pairs,'decision':decision});write(out/'six-raw-http-responses.json',{'at':now(),'count':6,'responses':raws,'no_repair':True});write(out/'reasoning-trace-index.json',{'at':now(),'traces':traces,'count':6})
write(out/'budget-ledger.json',{'at':now(),'cumulative_before':615,'new':6,'cumulative_after':621,'A_used':87,'original_plan_budget':90,'original_plan_remaining':3,'future_reserved_additional':30,'future_reservation_used':0,'future_reservation_authorizes_execution':False})
(out/'raw-finals-and-review.md').write_text('\n\n'.join(md)+'\n\n'+json.dumps({'groups':groups,'pairs':pairs,'decision':decision},ensure_ascii=False,indent=2),encoding='utf-8')
protected=load(out/'protected-before.json');changed=[p for p,h in protected.items() if sha(ROOT/p)!=h];assert not changed,changed
for p,h in plan['code_hashes'].items():assert sha(ROOT/p)==h,p
allruns=[]
for p in (HERE/'runs').rglob('run-*.json'):
    r=load(p)
    if r.get('generation_dispatched') and (r.get('usage') or {}).get('completion_tokens',0)>0:allruns.append({'path':p.relative_to(ROOT).as_posix(),'run_id':r['run_id']})
assert len(allruns)==len({x['run_id'] for x in allruns})==87
with socket.socket() as s:s.settimeout(1);closed=s.connect_ex(('127.0.0.1',8080))!=0
assert closed
git=r'C:\Users\86186\AppData\Local\Programs\Git\cmd\git.exe'
def g(*args):
    r=subprocess.run([git,'--no-optional-locks','-c','core.quotepath=false',*args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8');return {'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
resources={'before_GiB':rt['memory_before']['available_bytes']/2**30,'after_load_GiB':rt['memory_after_load']['available_bytes']/2**30,'minimum_sampled_GiB':min(x['available_bytes'] for x in rt['memory_samples'])/2**30,'model_stopped':rt['model_stopped'],'port8080_closed':closed,'exit_code_before_cleanup':rt['process_exit_code_before_cleanup'],'exit_code_after_cleanup':rt['process_exit_code_after_cleanup']}
write(out/'completion-audit.json',{'at':now(),'protected_count':len(protected),'changed':changed,'A_unique_generations':87,'A_run_ids':allruns,'new':6,'cumulative':621,'all_observation_checks_passed':True,'resources':resources,'git_status':g('status','--short','--branch'),'diff_check':g('diff','--check'),'staged_diff':g('diff','--cached','--stat'),'AT_read':False,'requests_identical_to_original_authorization':sha(out/'serialized-request-plan.json')==plan['serialized_requests_sha256'],'no_new_query':True})
write(out/'health-diagnosis-conclusion.json',{'at':now(),'old_root_cause':'旧轮次缺少HTTP异常证据，无法追溯确定；不能据新启动成功断言已找出旧超时的唯一根因。','confirmed_and_repaired':'吞异常及缺少健康HTTP、进程退出审计；独立修复保留状态、正文、异常类型、URL、超时及进程poll，120秒上限。','new_start_count':1,'new_execution_context':'exec_command require_escalated，执行已授权本机服务；旧启动缺少同级上下文归档，不能证明环境相同。','new_health_http_statuses':[r['http_status'] for r in load(out/'health-checks.json')['attempts']],'new_healthy':True,'no_wait_increase':True,'natural_crash':False,'cleanup':'仅停止登记的自有PID；停止前poll=None，停止后退出码另见runtime。','old_records_unchanged':True})
parts=[]
for p in [HERE/'audited_health.py',HERE/'diagnose_reason_citations_resume.py']:parts.extend(difflib.unified_diff([],p.read_text(encoding='utf-8').splitlines(True),fromfile='/dev/null',tofile='b/'+p.relative_to(ROOT).as_posix()))
(out/'complete-code.diff').write_text(''.join(parts),encoding='utf-8')
orch=out/'orchestration-sources';orch.mkdir()
for name in ['prepare_a_health_resume.py','review_a_reason_citations_resume.py']:shutil.copy2(name,orch/name)
write(out/'file-manifest.json',{'at':now(),'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.rglob('*') if p.is_file() and not {'slot-cache','__pycache__'}&set(p.parts)],'new_runtime_files':['进阶/a_exploration/audited_health.py','进阶/a_exploration/diagnose_reason_citations_resume.py'],'self_excluded':True})
print(json.dumps({'groups':groups,'pairs':pairs,'decision':decision,'resources':resources,'protected_unchanged':len(protected)},ensure_ascii=False,indent=2))
