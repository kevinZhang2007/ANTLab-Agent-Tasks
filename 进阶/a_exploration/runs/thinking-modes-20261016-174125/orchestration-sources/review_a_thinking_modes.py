from pathlib import Path
import sys,json,shutil,difflib,subprocess,socket
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
from sentence_selection import expand
from sentence_interface import interface_response
from locator import Locator
out=Path(Path('a-thinking-modes-out.txt').read_text(encoding='utf-8').strip());rt=load(out/'runtime.json');assert rt['dispatches']==rt['confirmed_generations']==6 and rt['model_stopped'] and 'error' not in rt
plan=load(out/'intervention-plan.json');inputs={x['id']:x for x in load(out/'diagnostic-inputs.json')};entries=[load(p) for p in sorted(out.glob('item-*.json'))];assert len(entries)==6
refs={x['id']:x for x in load(ROOT/'进阶/materials/a_dev_answers.json')};locator=Locator(load(ROOT/'进阶/materials/page_words.json'))
manual={
 ('AD01','off'):{'consistent':False,'necessary':True,'support':False,'unrelated':False,'basis':'理由改成最终文件加完整可执行流程，而原主张说无需记录。全选11句包含末句明确要求记录文件及目的的反证，不支持实际supported。'},
 ('AD01','on'):{'consistent':True,'necessary':False,'support':False,'unrelated':False,'basis':'最终理由声称流程描述可替代记录文件和目的，原文没有这个豁免；实际末句仍明确要求记录。只选可执行流程及最低限度流程细节3句，漏掉直接记录要求，supported与理由表面一致但事实和引用支持失败。'},
 ('AD02','off'):{'consistent':False,'necessary':False,'support':False,'unrelated':False,'basis':'原主张说仅此不足执行，理由也说不足却给contradicted。选引言问句和Binder环境句，未覆盖静态阅读来源。'},
 ('AD02','on'):{'consistent':True,'necessary':False,'support':False,'unrelated':False,'basis':'最终supported符合公开参考。理由区分静态HTML/PDF阅读和Binder执行环境，与支持原主张方向相容，但把仅此不足概括为两个核心需求，否定限定解释仍不充分。最终只选引言问句、Binder和容器环境sent-0002/0011/0013，缺少Read静态导出来源；理由提及了原段事实不等于实际引用已覆盖，因此必要覆盖和引用集合支持失败。'},
 ('AD03','off'):{'consistent':False,'necessary':False,'support':False,'unrelated':True,'basis':'理由把绘图数据转换变成graphic design和程序版本归档，前8句程序版本/依赖不足以支持只留图满足数据建议。'},
 ('AD03','on'):{'consistent':True,'necessary':False,'support':False,'unrelated':False,'basis':'实际未输入指定S08的绘图变换直接依据，拒判比无据支持更保守，但不符合公开开发参考contradicted。S09仍有详细值及有条件保留数据的相关论述，不能宣称全部输入无关；其替代反证的充分性保留边界。空引用不算必要来源覆盖或引用支持成功。'}
}
rows=[];raws=[];traces=[];md=['# 同1024预算：关闭/开启思考的全部最终结果','仅三道开发题固定自动improved证据重放；本轮不重新检索。Codex辅助原文复核，尚待本人确认。','思考文本是模型输出，不作事实证据、不替最终答案判分，也不作为内部因果机制的直接证明。']
for n,e in enumerate(entries,1):
    r=load(out/e['raw_record']);x=inputs[e['id']];mode=e['variant'];message=r['response']['choices'][0]['message'];obs=load(out/f'mode-observation-{n:02}.json');assert all(obs['verified'].values())
    assert r['messages']==x['messages'][mode] and r['config']==x['configs'][mode]
    ex=load(out/f'expansion-{n:02}.json');assert ex==expand(r['content'],x['blocks'],x['sentence_index'],x['doc_ids'],x['snapshot'])
    obj=ex['parsed_internal'];m=manual[(e['id'],mode)];fmt=isinstance(obj,dict) and set(obj)=={'label','reason','sentence_ids'} and isinstance(obj['sentence_ids'],list) and isinstance(obj['reason'],str)
    label=obj.get('label') if fmt else None;correct=label==refs[e['id']]['label'];selected=ex['selected_sources'];nonempty=bool(selected);source=ex['valid'] and all(next(b for b in x['blocks'] if b['block_id']==s['block_id'])['text'][s['start']:s['end']]==s['text'] for s in selected)
    strict=bool(fmt and ex['valid'] and correct and m['consistent'] and m['necessary'] and m['support'] and not m['unrelated'])
    thought=message.get('reasoning_content');trace_file=None
    if isinstance(thought,str):
        trace_file=f'reasoning-{n:02}-{e["id"]}-{mode}.txt';assert not (out/trace_file).exists();(out/trace_file).write_text(thought,encoding='utf-8',newline='')
    trace={'id':e['id'],'mode':mode,'run_id':r['run_id'],'raw_record':e['raw_record'],'raw_message':message,'reasoning_field_present':'reasoning_content' in message,'reasoning_content':thought,'reasoning_character_count':len(thought) if isinstance(thought,str) else None,'reasoning_text_file':trace_file,'content':message.get('content'),'usage':r['usage'],'finish_reason':r['finish_reason'],'reasoning_token_count':(r['usage'].get('completion_tokens_details') or {}).get('reasoning_tokens','not_echoed'),'not_echoed':['内部enable_thinking布尔状态','本请求编译grammar及PEG对象'],'not_judged_as_final_answer':True}
    traces.append(trace);write(out/f'raw-output-{n:02}.json',trace)
    mapping=interface_response(e['request_id'],x['claim'],x['doc_ids'],x['snapshot'],r['run_id'],ex,r['elapsed_seconds'],locator=locator,actual_input_blocks=x['blocks']);assert mapping['answer']==label and mapping['support_status']=='not_checked';write(out/f'interface-response-{n:02}.json',mapping)
    row={**e,'raw_final_content':r['content'],'parsed_final':obj,'label':label,'public_reference_label':refs[e['id']]['label'],'label_correct':correct,'final_label_evaluable':fmt,'reason_label_consistent':m['consistent'],'format_complete':fmt,'selection_valid':ex['valid'],'source_authenticity':True if source and nonempty else 'not_applicable_empty' if ex['valid'] else 'not_checked_invalid_final','empty_selection':ex['valid'] and not nonempty,'necessary_evidence_coverage':m['necessary'],'citation_support':m['support'],'has_unrelated_citations':m['unrelated'],'strict_complete_success':strict,'basis':m['basis'],'actual_visible_scope_boundary':'ambiguous：S08缺失而S09有部分相关论述，不把参考借入模型输入' if e['id']=='AD03' and mode=='on' else None,'reasoning_produced':isinstance(thought,str) and len(thought)>0,'reasoning_character_count':len(thought) if isinstance(thought,str) else None,'reasoning_token_count':trace['reasoning_token_count'],'input_tokens':r['input_tokens'],'usage':r['usage'],'finish_reason':r['finish_reason'],'budget_exhausted':r['finish_reason']=='length','client_seconds':r['elapsed_seconds'],'truncated':r['truncated'],'expanded_response':ex['expanded_response'],'selected_sources':selected,'judgment_source':'unverified','reviewer':'Codex辅助原文复核，尚待本人确认'}
    rows.append(row);write(out/f'review-item-{n:02}.json',row);raws.append({'id':e['id'],'mode':mode,'run_id':r['run_id'],'actual_http_request_raw':r['actual_http_request_raw'],'raw_response':r['raw_response'],'content':r['content'],'reasoning_content':thought,'usage':r['usage'],'finish_reason':r['finish_reason'],'client_seconds':r['elapsed_seconds']})
    md+=['\n## '+e['id']+' '+mode,'原始最终content：','```json',r['content'],'```',f"总输出tokens={r['usage']['completion_tokens']}；客户端耗时={r['elapsed_seconds']:.6f}秒；结束={r['finish_reason']}；实际reasoning字段={'reasoning_content' in message}。",m['basis'],'思考文本文件：'+str(trace_file)+'（未返回则为None，不虚构空字段）。']
groups={}
for mode in ['off','on']:
    rs=[r for r in rows if r['variant']==mode];groups[mode]={'denominator':3,'format_complete':sum(r['format_complete'] for r in rs),'label_correct':sum(r['label_correct'] for r in rs),'reason_label_consistent':sum(r['reason_label_consistent'] for r in rs),'nonempty_source_authenticity_passed':sum(r['source_authenticity'] is True for r in rs),'empty_selection':sum(r['empty_selection'] for r in rs),'necessary_coverage':sum(r['necessary_evidence_coverage'] for r in rs),'citation_support':sum(r['citation_support'] for r in rs),'strict_complete_success':sum(r['strict_complete_success'] for r in rs),'budget_exhausted':sum(r['budget_exhausted'] for r in rs),'no_valid_final':sum(not r['format_complete'] for r in rs),'reasoning_produced':sum(r['reasoning_produced'] for r in rs),'input_tokens':sum(r['input_tokens'] for r in rs),'total_output_tokens':sum(r['usage']['completion_tokens'] for r in rs),'client_seconds':sum(r['client_seconds'] for r in rs)}
pairs=[]
for task in inputs:
    a=next(r for r in rows if r['id']==task and r['variant']=='off');b=next(r for r in rows if r['id']==task and r['variant']=='on');pairs.append({'id':task,'off_run':a['run_id'],'on_run':b['run_id'],'off_label':a['label'],'on_label':b['label'],'label_improved':not a['label_correct'] and b['label_correct'],'label_regressed':a['label_correct'] and not b['label_correct'],'strict_improved':not a['strict_complete_success'] and b['strict_complete_success'],'strict_regressed':a['strict_complete_success'] and not b['strict_complete_success'],'off_seconds':a['client_seconds'],'on_seconds':b['client_seconds']})
decision={'at':now(),'retain_as_pending_judgment_candidate':'thinking_on','current_entry_modified':False,'basis':'按事前严格成功优先、其次标签正确：严格均0/3，开启标签1/3优于关闭0/3，且没有已正确或严格成功项退步。因此本轮开启在次级指标胜出，保留为待接入独立候选，不把它写成整体引用质量提高。','main_limit':'AD02最终标签虽正确，引用缺Read；AD01继续错误，AD03拒判且空引用。必要覆盖从1/3降0/3，非空来源核验从3条降2条，这些风险与次级指标收益并列，不自动补证。','no_thought_scoring':'不以思考里的说法抵消最终错误；reasoning文字也不是对内部机制的直接证明。','not_generalization':'仅三道开发题、固定历史自动证据及本轮配置。与旧512预算是历史比较，不能把预算变化当作纯模式效果。','new_generations':6,'cumulative':609,'A_used':75,'original_plan_budget':90,'original_plan_remaining':15,'future_reserved_additional':30,'future_reservation_used':0,'future_reservation_authorizes_execution':False,'budget_note':'原计划余额与另行未来预留分列，本轮6次不消耗后续30次预留；未执行七题/变体/反事实。','technical_request_failures':0,'quality_retries':0,'stop':'服务已停止，本轮不追加调用；不修改当前入口或五份文档。'}
write(out/'review.json',{'at':now(),'reviewer':'Codex辅助原文复核，尚待本人确认','groups':groups,'rows':rows,'pairs':pairs,'decision':decision})
write(out/'reasoning-trace-index.json',{'at':now(),'count':6,'traces':traces,'scope':'完整保存实际模型思考和最终content；未回显独立思考token计数时不估计。'})
write(out/'six-raw-http-responses.json',{'at':now(),'responses':raws,'count':6,'no_repair':True})
write(out/'budget-ledger.json',{'at':now(),'cumulative_before':603,'new_generations':6,'cumulative_after':609,'A_before':69,'A_after':75,'original_plan_budget':90,'original_plan_remaining':15,'future_reserved_additional':30,'future_reservation_used':0,'future_reservation_authorizes_execution':False,'B_offline_replay_not_added':88})
(out/'raw-finals-and-review.md').write_text('\n\n'.join(md)+'\n\n'+json.dumps({'groups':groups,'decision':decision},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
protected=load(out/'protected-before.json');changed=[p for p,h in protected.items() if sha(ROOT/p)!=h];assert not changed,changed
for p,h in plan['code_hashes'].items():assert sha(ROOT/p)==h,p
assert sha(out/'serialized-request-plan.json')==plan['serialized_requests_sha256']
allruns=[]
for p in (HERE/'runs').rglob('run-*.json'):
    r=load(p)
    if r.get('generation_dispatched') and (r.get('usage') or {}).get('completion_tokens',0)>0:allruns.append((p,r['run_id']))
assert len(allruns)==len({rid for p,rid in allruns})==75
with socket.socket() as s:s.settimeout(1);closed=s.connect_ex(('127.0.0.1',8080))!=0
assert closed
git=r'C:\Users\86186\AppData\Local\Programs\Git\cmd\git.exe'
def g(*args):
    r=subprocess.run([git,'--no-optional-locks','-c','core.quotepath=false',*args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8');return {'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
resources={'before_GiB':rt['memory_before']['available_bytes']/2**30,'after_load_GiB':rt['memory_after_load']['available_bytes']/2**30,'minimum_sampled_GiB':min(x['available_bytes'] for x in rt['memory_samples'])/2**30,'after_stop_GiB':rt['memory_after_stop']['available_bytes']/2**30,'load_seconds':rt['load_seconds'],'model_stopped':rt['model_stopped'],'port8080_closed':closed}
write(out/'completion-audit.json',{'at':now(),'old_files_checked':len(protected),'old_files_changed':changed,'code_and_plan_hashes_match':True,'A_unique_generations':75,'A_run_ids':[{'path':p.relative_to(ROOT).as_posix(),'run_id':rid} for p,rid in allruns],'new':6,'cumulative':609,'all_6_mode_observation_checks_passed':True,'truncated_flags':[r['truncated'] for r in rows],'all_fit_with_1024':all(r['input_tokens']+1024<=4096 for r in rows),'resources':resources,'git_status':g('status','--short','--branch'),'git_diff_check':g('diff','--check'),'staged_diff':g('diff','--cached','--stat'),'AT_read':False,'no_new_query':True})
diff=''
for name in ['thinking_modes.py','diagnose_thinking_modes.py']:
    p=HERE/name;diff+=''.join(difflib.unified_diff([],p.read_text(encoding='utf-8').splitlines(keepends=True),fromfile='/dev/null',tofile='b/'+p.relative_to(ROOT).as_posix()))
(out/'complete-code.diff').write_text(diff,encoding='utf-8')
orch=out/'orchestration-sources';orch.mkdir()
for name in ['a_thinking_modes.py','prepare_a_thinking_modes.py','review_a_thinking_modes.py']:shutil.copy2(name,orch/name)
write(out/'file-manifest.json',{'at':now(),'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.rglob('*') if p.is_file() and not {'slot-cache','__pycache__'}&set(p.parts)],'new_runtime_files':['进阶/a_exploration/thinking_modes.py','进阶/a_exploration/diagnose_thinking_modes.py'],'self_excluded':True})
print(json.dumps({'groups':groups,'decision':decision,'resources':resources,'protected_unchanged':len(protected),'results':[(r['id'],r['variant'],r['label'],round(r['client_seconds'],3),r['usage']['completion_tokens'],r['reasoning_character_count']) for r in rows]},ensure_ascii=False,indent=2))
