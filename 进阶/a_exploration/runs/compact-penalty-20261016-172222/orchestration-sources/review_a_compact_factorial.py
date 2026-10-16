from pathlib import Path
import sys,json,shutil,difflib,subprocess,socket
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
from sentence_selection import expand
from sentence_interface import interface_response
from locator import Locator
out=Path(Path('a-compact-factorial-out.txt').read_text(encoding='utf-8').strip());rt=load(out/'runtime.json');assert rt['confirmed_generations']==rt['dispatches']==12 and rt['model_stopped'] and 'error' not in rt
plan=load(out/'intervention-plan.json');inputs={x['id']:x for x in load(out/'diagnostic-inputs.json')};entries=[load(p) for p in sorted(out.glob('item-*.json'))];assert len(entries)==12
refs={x['id']:x for x in load(ROOT/'进阶/materials/a_dev_answers.json')};locator=Locator(load(ROOT/'进阶/materials/page_words.json'))
manual={
 ('AD01','repeated_15'):{'consistent':False,'necessary':True,'support':False,'unrelated':False,'basis':'理由改成最终文件加可执行流程，而原主张是无需记录。所选全部11句含P1-S03末句明确要求记录哪些文件和目的，必要反证在，但不支持实际supported。'},
 ('AD01','repeated_0'):{'consistent':True,'necessary':True,'support':False,'unrelated':False,'basis':'理由声称不用记录修改细节，和supported表面一致，但与选中sent-0011的you should as a minimum note down...and for what purpose直接相反，惩罚归零未修语义。'},
 ('AD01','compact_15'):{'consistent':True,'necessary':False,'support':False,'unrelated':False,'basis':'理由把不可避免条件改成手工修改是否必要或充分的子问题；实际原段仍完整含明确记录要求，insufficient错误。空选择没有来源造假，但不能算非空引文真实性通过，也未覆盖反证。'},
 ('AD01','compact_0'):{'consistent':True,'necessary':False,'support':False,'unrelated':False,'basis':'原文明确要求记录文件及目的，回复却称没有反例；拒判理由与label表面一致但事实错误。空引用未证明缺证。'},
 ('AD02','repeated_15'):{'consistent':False,'necessary':False,'support':False,'unrelated':False,'basis':'原主张说仅此不足执行，理由也说不足，却判contradicted，否定方向仍错。引言问句和Binder句未覆盖静态阅读的必要来源。'},
 ('AD02','repeated_0'):{'consistent':False,'necessary':False,'support':False,'unrelated':False,'basis':'理由与原主张同向却判contradicted。所引问句、静态档案及Nbviewer阅读句没有给完整的执行环境对比；不能只凭出处真算支持反驳。'},
 ('AD02','compact_15'):{'consistent':True,'necessary':True,'support':False,'unrelated':True,'basis':'sent-0006静态档案与0007在执行技术失败时仍可读、另需依赖列表重建环境，可作区分read与run的替代组合，不强制固定Run段ID；所以覆盖按实际内容成立。但回复以未明说足以执行为由拒判，忽略原主张正是仅此不足，引用不支持实际insufficient。0004的仓库许可不提供该区别，另记无关。'},
 ('AD02','compact_0'):{'consistent':False,'necessary':True,'support':False,'unrelated':True,'basis':'理由逐字语义支持仅此不足执行，却给insufficient，理由与标签不一致。同一组0006/0007替代依据可以覆盖判断，但不能支持这个拒判；0004许可来源另记无关。'},
 ('AD03','repeated_15'):{'consistent':False,'necessary':False,'support':False,'unrelated':True,'basis':'理由把绘图数据转换改成graphic design与程序归档，选中前8句均为程序版本/依赖，不支持只留图足够。'},
 ('AD03','repeated_0'):{'consistent':True,'necessary':False,'support':False,'unrelated':True,'basis':'理由直接说作者建议只留最终图，和supported表面一致但没有原文支持。选了程序归档和多数S09句；S09检查详细值及有条件保留数据不是只留图足够的依据。'},
 ('AD03','compact_15'):{'consistent':True,'necessary':False,'support':False,'unrelated':False,'basis':'未输入指定S08的绘图变换直接依据，拒判比无据支持更保守，但不符合公开参考contradicted。实际S09仍有底层值相关论述，其替代反证充分性有边界，不认定所有资料都无关；空引用未覆盖可检查来源。'},
 ('AD03','compact_0'):{'consistent':True,'necessary':False,'support':False,'unrelated':False,'basis':'与紧凑1.5一样保留缺少S08直接依据的边界；不借未输入参考补证。公开参考口径标签不对，实际可见证据下的拒判充分性另记ambiguous，空引用不算支持成功。'}
}
rows=[];raws=[];md=['# 输入组织与presence_penalty四组合：全部原始结果','本轮12次0.6B生成，仅三道开发题固定自动证据回答重放，不是端到端检索成绩。','Codex辅助原文复核，尚待本人确认。空引用可合法，但不能当作非空来源真实性通过。']
for n,e in enumerate(entries,1):
    r=load(out/e['raw_record']);x=inputs[e['id']];v=e['variant'];ex=load(out/f'expansion-{n:02}.json');assert ex==expand(r['content'],x['blocks'],x['sentence_index'],x['doc_ids'],x['snapshot'])
    assert r['messages']==x['messages'][v] and r['config']==x['configs'][v] and all(load(out/f'parameter-check-{n:02}.json').values())
    obj=ex['parsed_internal'];selected=ex['selected_sources'];m=manual[(e['id'],v)];nonempty=bool(selected)
    source=ex['valid'] and all(next(b for b in x['blocks'] if b['block_id']==s['block_id'])['text'][s['start']:s['end']]==s['text'] for s in selected)
    fmt=isinstance(obj,dict) and set(obj)=={'label','reason','sentence_ids'} and isinstance(obj['sentence_ids'],list) and isinstance(obj['reason'],str)
    label=obj.get('label') if fmt else None;correct=label==refs[e['id']]['label'];strict=bool(fmt and ex['valid'] and correct and m['consistent'] and m['necessary'] and m['support'] and not m['unrelated'])
    mapped=interface_response(e['request_id'],x['claim'],x['doc_ids'],x['snapshot'],r['run_id'],ex,r['elapsed_seconds'],locator=locator,actual_input_blocks=x['blocks']);assert mapped['answer']==label and mapped['support_status']=='not_checked';write(out/f'interface-response-{n:02}.json',mapped)
    row={**e,'raw_content':r['content'],'parsed':obj,'label':label,'public_reference_label':refs[e['id']]['label'],'label_correct':correct,'reason_label_consistent':m['consistent'],'format_complete':fmt,'selection_valid':ex['valid'],'source_authenticity':True if source and nonempty else 'not_applicable_empty' if not nonempty and ex['valid'] else False,'empty_selection':not nonempty,'source_truth_failure':not source,'necessary_evidence_coverage':m['necessary'],'citation_support':m['support'],'has_unrelated_evidence':m['unrelated'],'strict_complete_success':strict,'basis':m['basis'],'visible_evidence_semantic_boundary':'ambiguous：缺S08直接资料，S09仍可能提供相关替代依据' if e['id']=='AD03' and v.startswith('compact') else None,'selected_sources':selected,'expanded_response':ex['expanded_response'],'input_tokens':r['input_tokens'],'usage':r['usage'],'client_seconds':r['elapsed_seconds'],'finish_reason':r['finish_reason'],'truncated':r['truncated'],'presence_penalty_request':r['actual_http_request_body']['presence_penalty'],'presence_penalty_echo':r['slot_after'][0]['params']['presence_penalty'],'repeat_penalty_echo':r['slot_after'][0]['params']['repeat_penalty'],'judgment_source':'unverified','reviewer':'Codex原文辅助复核，尚待本人确认'}
    rows.append(row);write(out/f'review-item-{n:02}.json',row);raws.append({'id':e['id'],'variant':v,'run_id':r['run_id'],'actual_http_request_raw':r['actual_http_request_raw'],'raw_response':r['raw_response'],'content':r['content'],'usage':r['usage'],'client_seconds':r['elapsed_seconds'],'finish_reason':r['finish_reason']})
    md+=['\n## '+e['id']+' '+v,'```json',r['content'],'```',f"输入{r['input_tokens']}、输出{r['usage']['completion_tokens']} tokens，客户端{r['elapsed_seconds']:.6f}秒；结束{r['finish_reason']}。",m['basis']]
groups={};variants=plan['variants']
for v in variants:
    rs=[r for r in rows if r['variant']==v];groups[v]={'denominator':3,'format_complete':sum(r['format_complete'] for r in rs),'selection_valid':sum(r['selection_valid'] for r in rs),'label_correct':sum(r['label_correct'] for r in rs),'reason_label_consistent':sum(r['reason_label_consistent'] for r in rs),'nonempty_source_authenticity_passed':sum(r['source_authenticity'] is True for r in rs),'empty_selection':sum(r['empty_selection'] for r in rs),'source_truth_failures':sum(r['source_truth_failure'] for r in rs),'necessary_coverage':sum(r['necessary_evidence_coverage'] for r in rs),'citation_support':sum(r['citation_support'] for r in rs),'unrelated_citations':sum(r['has_unrelated_evidence'] for r in rs),'strict_complete_success':sum(r['strict_complete_success'] for r in rs),'input_tokens':sum(r['input_tokens'] for r in rs),'output_tokens':sum(r['usage']['completion_tokens'] for r in rs),'client_seconds':sum(r['client_seconds'] for r in rs),'budget_exhausted':sum(r['finish_reason']=='length' for r in rs)}
def compare(name,a,b):
    pairs=[]
    for task in inputs:
        old=next(r for r in rows if r['id']==task and r['variant']==a);new=next(r for r in rows if r['id']==task and r['variant']==b)
        pairs.append({'id':task,'old_label':old['label'],'new_label':new['label'],'delta_label_correct':int(new['label_correct'])-int(old['label_correct']),'delta_strict':int(new['strict_complete_success'])-int(old['strict_complete_success']),'old_necessary':old['necessary_evidence_coverage'],'new_necessary':new['necessary_evidence_coverage'],'old_empty':old['empty_selection'],'new_empty':new['empty_selection'],'delta_input_tokens':new['input_tokens']-old['input_tokens'],'delta_output_tokens':new['usage']['completion_tokens']-old['usage']['completion_tokens'],'delta_client_seconds':new['client_seconds']-old['client_seconds']})
    return {'name':name,'old':a,'new':b,'paired_claims':3,'pairs':pairs,'delta_correct':sum(p['delta_label_correct'] for p in pairs),'delta_strict':sum(p['delta_strict'] for p in pairs),'delta_input_tokens':sum(p['delta_input_tokens'] for p in pairs),'delta_client_seconds':sum(p['delta_client_seconds'] for p in pairs)}
contrasts=[compare('A：惩罚1.5下组织因素','repeated_15','compact_15'),compare('A：惩罚0下组织因素','repeated_0','compact_0'),compare('B：重复输入下惩罚归零','repeated_15','repeated_0'),compare('B：紧凑输入下惩罚归零','compact_15','compact_0'),compare('共同变化：原方案到紧凑+0','repeated_15','compact_0')]
decision={'at':now(),'replace_current_entry':False,'keep_presence_penalty':1.5,'quality_gain_claimed':False,'basis':'四组合标签正确与严格成功均0/3，引用支持均0/3。惩罚归零没有质量胜出，保留原1.5。紧凑确实降低输入与本轮耗时，但两题变为空引用，不能把来源真实性核验由3个非空集合降为1个时宣称已证无损；不自动采用为质量相同的替代。','coverage_detail':'必要覆盖总数均1/3，但紧凑使AD01已覆盖反证丢失、AD02得到静态档案/依赖环境的替代组合；不是逐题完全不变。AD02替代依据没有强制固定Run段引用。','source_detail':'空引用是合法质量结果，不是假引用或格式失败；单列not_applicable_empty，不计作真实性通过。剩余非空引用均真实，但真实不等于支持实际label。','efficiency':'紧凑每组三题输入7843→3320，减少4523 tokens；本轮各题均更快，输出长度同时变化，不能声称稳定性能或单独归因去重。作为效率候选保留，未写回当前入口。','factor_limit':'因素A同时改变冗余、字段组织和claim位置；因素B仅presence。条件内和共同变化分别列出，不把三题12个请求当独立12题，不从一次请求判断普遍机制。','new_generations':12,'cumulative':603,'A_used':69,'A_cap':90,'A_remaining':21,'technical_request_failures':0,'quality_retries':0,'stop':'本轮结束，不追加调用或读取七题。'}
write(out/'review.json',{'at':now(),'reviewer':'Codex辅助原文复核，尚待本人确认','rows':rows,'groups':groups,'contrasts':contrasts,'decision':decision})
write(out/'twelve-raw-http-responses.json',{'at':now(),'count':12,'responses':raws,'no_repair':True})
(out/'raw-results-and-review.md').write_text('\n\n'.join(md)+'\n\n'+json.dumps({'groups':groups,'contrasts':contrasts,'decision':decision},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
protected=load(out/'protected-before.json');changed=[p for p,h in protected.items() if sha(ROOT/p)!=h];assert not changed,changed
for p,h in plan['code_hashes'].items():assert sha(ROOT/p)==h,p
assert sha(out/'serialized-request-plan.json')==plan['serialized_requests_sha256']
allruns=[]
for p in (HERE/'runs').rglob('run-*.json'):
    r=load(p)
    if r.get('generation_dispatched') and (r.get('usage') or {}).get('completion_tokens',0)>0:allruns.append((p,r['run_id']))
assert len(allruns)==len({rid for p,rid in allruns})==69
with socket.socket() as s:s.settimeout(1);closed=s.connect_ex(('127.0.0.1',8080))!=0
assert closed
git=r'C:\Users\86186\AppData\Local\Programs\Git\cmd\git.exe'
def g(*args):
    r=subprocess.run([git,'--no-optional-locks','-c','core.quotepath=false',*args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8');return {'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
resources={'before_GiB':rt['memory_before']['available_bytes']/2**30,'after_load_GiB':rt['memory_after_load']['available_bytes']/2**30,'minimum_sampled_GiB':min(x['available_bytes'] for x in rt['memory_samples'])/2**30,'after_stop_GiB':rt['memory_after_stop']['available_bytes']/2**30,'load_seconds':rt['load_seconds'],'model_stopped':rt['model_stopped'],'port8080_closed':closed}
write(out/'completion-audit.json',{'at':now(),'protected_count':len(protected),'changed':changed,'code_and_serialized_plan_hashes_match':True,'A_unique_generations':69,'A_run_ids':[{'path':p.relative_to(ROOT).as_posix(),'run_id':rid} for p,rid in allruns],'new':12,'cumulative':603,'A_cap':90,'A_remaining':21,'B_offline_replay_not_added':88,'resources':resources,'all_12_parameter_checks_passed':True,'all_12_truncated_flags':[r['truncated'] for r in rows],'all_fit_4096_with_512':all(r['input_tokens']+512<=4096 for r in rows),'git_status':g('status','--short','--branch'),'diff_check':g('diff','--check'),'staged_diff':g('diff','--cached','--stat'),'AT_read':False,'no_page_run':True,'no_retrieval_or_prompt_change':True})
diff=''
for name in ['compact_factorial.py','diagnose_compact_factorial.py']:
    p=HERE/name;diff+=''.join(difflib.unified_diff([],p.read_text(encoding='utf-8').splitlines(keepends=True),fromfile='/dev/null',tofile='b/'+p.relative_to(ROOT).as_posix()))
(out/'complete-code.diff').write_text(diff,encoding='utf-8')
orch=out/'orchestration-sources';orch.mkdir()
for name in ['a_compact_factorial.py','prepare_a_compact_factorial.py','review_a_compact_factorial.py']:shutil.copy2(name,orch/name)
write(out/'file-manifest.json',{'at':now(),'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.rglob('*') if p.is_file() and not {'slot-cache','__pycache__'}&set(p.parts)],'new_runtime_files':['进阶/a_exploration/compact_factorial.py','进阶/a_exploration/diagnose_compact_factorial.py'],'self_excluded':True})
print(json.dumps({'groups':groups,'decision':decision,'contrasts':[{k:v for k,v in c.items() if k!='pairs'} for c in contrasts],'resources':resources,'protected_unchanged':len(protected),'times':[(r['id'],r['variant'],r['label'],round(r['client_seconds'],3),r['usage']['completion_tokens']) for r in rows]},ensure_ascii=False,indent=2))
