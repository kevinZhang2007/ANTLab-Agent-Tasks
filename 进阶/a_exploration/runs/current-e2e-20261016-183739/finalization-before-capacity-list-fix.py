from pathlib import Path
import sys,json,copy,shutil,socket,subprocess,difflib
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
from engine import retrieve,neighbors,public,query_messages,Corpus
from current_candidate import build_answer,query_config
from sentence_selection import expand
out=Path(Path('a-current-e2e-out.txt').read_text(encoding='utf-8').strip());rt=load(out/'runtime.json');assert rt['generation_dispatches']==rt['confirmed_generations']==9 and rt['model_stopped'] and not rt['technical_stop']
tasks=load(out/'development-inputs.json');bytask={x['id']:x for x in tasks};refs={x['id']:x for x in load(ROOT/'进阶/materials/a_dev_answers.json')};plan=load(out/'development-plan.json');config=load(out/'configuration.json')
manual={
 ('AD01','baseline'):{'input_coverage':True,'necessary':True,'support':True,'unrelated':False,'consistent':True,'reason_factual':True,'basis':'原始输入含P1-S03-p01最后一句“If manual operations cannot be avoided ... note down which data files ... and for what purpose”。选择sent-0008覆盖直接反证，sent-0003说明手工操作可复现风险，属于相关冗余。contradicted及其证据集合成立；理由重复来源名称另列，不新增严格门槛。'},
 ('AD01','improved'):{'input_coverage':True,'necessary':True,'support':True,'unrelated':False,'consistent':True,'reason_factual':True,'basis':'邻段只新增同章节P1-S02-p02，原直接反证仍在P1-S03-p01的sent-0011。0004及0005—0010均属手工流程记录的相关背景，沿用相关冗余不等于无关的口径。两侧均已完整成功，不能把本题结果说成邻段改善。'},
 ('AD02','baseline'):{'input_coverage':True,'necessary':True,'support':True,'unrelated':True,'consistent':False,'reason_factual':False,'basis':'实际未检索P2-S10-p03，但p02的0006/0007已区分静态可读档案和需完整依赖列表才能重建计算环境，允许这种有充分原文的替代支持，不要求固定Run引用ID。模型选全部十句，集合足以支持实际supported；0004仓库许可对本判断无关，严格失败。理由把Nbviewer/GitHub静态视图误写为执行原计算，且把HTML/PDF归到p01，不能用标签碰巧正确掩盖理由错误。'},
 ('AD02','improved'):{'input_coverage':True,'necessary':True,'support':False,'unrelated':True,'consistent':True,'reason_factual':False,'basis':'邻段新增P2-S10-p03（Binder、容器/依赖环境）；所选0006/0007及0013覆盖Read/Run区分，资料足够但最终insufficient为错误拒判。reason形式上解释缺证判断，却误读了否定限定，静态原句归属也写错。0004许可引用仍无关；不能因摘录真实或资料更全判成功。'},
 ('AD03','baseline'):{'input_coverage':'ambiguous','necessary':'ambiguous','support':False,'unrelated':True,'consistent':False,'reason_factual':False,'basis':'实际只有P1-S04-p01和P1-S09-p01，公开参考指定S08绘图变换直接依据未进入输入。S09保留有条件的底层数据建议和最低详细值检查，可形成替代反证但完整覆盖边界继续ambiguous。所选0004是程序版本归档，无关；0013/0016不能支持“仅图片足够”。理由强调完整数据却判主张一致，方向错误。'},
 ('AD03','improved'):{'input_coverage':'ambiguous','necessary':'ambiguous','support':False,'unrelated':True,'consistent':False,'reason_factual':False,'basis':'两种子各在单段章节，本题没有可补邻段；两侧实际messages、Schema及响应相同，但均为本轮独立真实调用。S08仍缺，不借公开参考补证；0013/0016不支持仅留最终图，0004程序归档无关，公开contradicted未命中。'}
}
rows=[];pairs=[];index=[];closures=[];md=['# 当前采用版本：三道开发题完整配对','Codex辅助原文复核，尚待本人确认。三题分母保留；不是七题评测。','严格成功：完整JSON且选择验证通过、标签正确、必要覆盖=true、引用支持=true、无无关引用。理由一致性不属于综合公式。']
screens=out/'page-evidence';screens.mkdir()
for t in tasks:
    for suffix in ['baseline.png','improved.png','page.txt']:
        p=Path('a-e2e-'+t['id']+'-'+suffix)
        if p.exists():shutil.copy2(p,screens/p.name)
extra=Path('a-e2e-AD03-location.png')
if extra.exists():shutil.copy2(extra,screens/extra.name)
events=[json.loads(l) for l in (out/'events.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
for t in tasks:
    h=next(load(p) for p in out.glob('http-*.json') if load(p).get('task_id')==t['id']);pair=h['response'];assert pair['status']=='completed';pid=pair['request_id'];on_disk=load(out/('pair-'+pid+'.json'));assert {k:v for k,v in pair.items() if k!='normalized_arms'}==on_disk
    assert h['request']['claim']==t['claim'] and h['request']['doc_ids']==t['doc_ids'];q=pair['shared_query'];assert q['messages']==query_messages(t['claim']) and q['config']==query_config()
    assert q['slot_after'][0]['params']['max_tokens']==128 and q['actual_http_request_body']['chat_template_kwargs']=={'enable_thinking':False}
    qcap=load(out/('capacity-query-'+pid+'.json'));assert qcap['actual_generation_suffix']=='<think>\n\n</think>\n\n'
    scope=Corpus(load(ROOT/'进阶/materials/sections.json')).scope(t['doc_ids'],t['snapshot']);assert [public(b) for b in scope]==pair['scope_blocks']
    selected,scores=retrieve(pair['retrieval_terms'],scope);extended,added=neighbors(selected,scope);assert [public(b) for b in selected]==pair['arms']['baseline']['actual_input_passages'] and [public(b) for b in extended]==pair['arms']['improved']['actual_input_passages'] and scores==pair['retrieval_scores']
    # HTTP记录中的scope是public表示，无_order；还原排序元数据仅由当前corpus重新取得。
    index.append({'task_id':t['id'],'stage':'shared_query','run_id':q['run_id'],'raw_record':'run-'+q['run_id']+'.json','request_id':pid,'actual_count':1,'cost_share_each_arm':0.5})
    selected_docs={b['doc_id'] for b in pair['scope_blocks']};assert selected_docs<=set(t['doc_ids'])
    for arm in ['baseline','improved']:
        a=pair['arms'][arm];r=load(out/('run-'+a['raw_record']['run_id']+'.json'));assert r==a['raw_record'];m=manual[(t['id'],arm)]
        ms,conf,si,byte=build_answer(t['claim'],a['actual_input_passages'],t['doc_ids'],t['snapshot'],config['request_common']);assert ms==r['messages'] and conf==r['config'] and si==a['sentence_index']
        ex=expand(r['content'],a['actual_input_passages'],si,t['doc_ids'],t['snapshot']);assert ex==load(out/a['expansion_record']);obj=ex['parsed_internal'];correct=bool(ex['valid'] and obj['label']==refs[t['id']]['label'])
        strict=bool(ex['valid'] and correct and m['necessary'] is True and m['support'] is True and m['unrelated'] is False)
        pdfs=[e['location']['locator_status'] for e in a['evidence']];auth=ex['valid'] and all(b['doc_id'] in t['doc_ids'] for b in a['actual_input_passages'])
        row={'task_id':t['id'],'variant':arm,'request_id':a['main_task_id'],'parent_request_id':pid,'run_id':r['run_id'],'raw_record':'run-'+r['run_id']+'.json','raw_content':r['content'],'model_label':obj.get('label') if isinstance(obj,dict) else None,'reference_label':refs[t['id']]['label'],'label_correct':correct,'json_complete':ex['valid'],'source_authenticity':auth,'input_necessary_coverage':m['input_coverage'],'necessary_citation_coverage':m['necessary'],'citation_support':m['support'],'unrelated_citations':m['unrelated'],'reason_label_consistent':m['consistent'],'reason_factual_correct':m['reason_factual'],'strict_complete_success':strict,'review_basis':m['basis'],'direct_reference_section_in_input':any(b['section_id'] in refs[t['id']]['evidence_sections'] for b in a['actual_input_passages']),'pdf_location_statuses':pdfs,'pdf_valid_all':bool(pdfs) and all(s=='valid' for s in pdfs),'input_tokens':r['input_tokens'],'usage':r['usage'],'finish_reason':r['finish_reason'],'truncated':r['truncated'],'answer_http_seconds':r['elapsed_seconds'],'reconstructed_flow_seconds':a['reconstructed_flow_seconds'],'allocated_cost_seconds':a['allocated_total_seconds'],'query_shared_seconds':pair['shared_query_wall_seconds'],'pair_elapsed_seconds':pair['pair_elapsed_seconds'],'judgment_source':'unverified','reviewer':'Codex辅助原文复核，尚待本人确认'}
        rows.append(row);write(out/f'review-{t["id"]}-{arm}.json',row);index.append({'task_id':t['id'],'stage':arm,'request_id':a['main_task_id'],'parent_request_id':pid,'run_id':r['run_id'],'raw_record':row['raw_record'],'expansion_record':a['expansion_record'],'actual_count':1})
        assert any(e.get('event')=='arm_result' and e.get('request_id')==a['main_task_id'] and e.get('parent_request_id')==pid and e.get('run_id')==r['run_id'] for e in events)
        md+=['## '+t['id']+' '+arm,'```json',r['content'],'```',m['basis']]
    assert any(e.get('event')=='http_response' and e.get('request_id')==pid for e in events)
    text=(screens/('a-e2e-'+t['id']+'-page.txt')).read_text(encoding='utf-8');assert pid in text and pair['shared_query']['run_id'] in text and pair['arms']['improved']['main_task_id'] in text and pair['arms']['improved']['raw_record']['run_id'] in text
    closures.append({'task_id':t['id'],'parent_request_id':pid,'http_record':'http-'+pid+'.json','pair_record':'pair-'+pid+'.json','browser_page_text':f'page-evidence/a-e2e-{t["id"]}-page.txt','screenshots':[p.relative_to(out).as_posix() for p in screens.glob('a-e2e-'+t['id']+'-*.png')],'page_submit_count':1,'page_text_ids_match_http_and_model':True,'same_id_backend_log':'events.jsonl','no_extra_http_generation':True,'semantic_support_display':'not_checked'})
    a=next(r for r in rows if r['task_id']==t['id'] and r['variant']=='baseline');b=next(r for r in rows if r['task_id']==t['id'] and r['variant']=='improved');pairs.append({'task_id':t['id'],'baseline_label':a['model_label'],'improved_label':b['model_label'],'label_regressed':a['label_correct'] and not b['label_correct'],'strict_baseline':a['strict_complete_success'],'strict_improved':b['strict_complete_success'],'pair_elapsed_seconds':pair['pair_elapsed_seconds']})
groups={}
for arm in ['baseline','improved']:
    rs=[r for r in rows if r['variant']==arm];groups[arm]={'denominator':3,'label_correct':sum(r['label_correct'] for r in rs),'json_complete':sum(r['json_complete'] for r in rs),'source_authenticity':sum(r['source_authenticity'] for r in rs),'input_coverage':sum(r['input_necessary_coverage'] is True for r in rs),'input_coverage_ambiguous':sum(r['input_necessary_coverage']=='ambiguous' for r in rs),'necessary_citation_coverage':sum(r['necessary_citation_coverage'] is True for r in rs),'citation_support':sum(r['citation_support'] is True for r in rs),'unrelated_citations':sum(r['unrelated_citations'] for r in rs),'reason_label_consistent':sum(r['reason_label_consistent'] is True for r in rs),'strict_complete_success':sum(r['strict_complete_success'] for r in rs),'pdf_location_all_valid':sum(r['pdf_valid_all'] for r in rs),'answer_http_seconds':sum(r['answer_http_seconds'] for r in rs)}
write(out/'review-summary.json',{'at':now(),'reviewer':'Codex辅助原文复核，尚待本人确认','rows':rows,'groups':groups,'pairs':pairs,'strict_formula':plan['strict_formula'],'reason_consistency_separate':True,'no_method_change_after_results':True,'historical_comparison':'本轮重新查询和检索，旧提示候选对照为固定历史证据重放；不能将变化全部归因于提示。AD01/AD02/AD03本轮improved的消息与上一轮对应候选逐项核对另列。'})
write(out/'nine-raw-response-index.json',{'at':now(),'count':9,'items':index,'shared_query_count':3,'judgment_count':6,'no_reference_in_requests':True})
write(out/'page-closure-index.json',{'at':now(),'rows':closures,'page_submissions':3,'additional_generation_via_http':0,'physical_page_example':'page-evidence/a-e2e-AD03-location.png','server_stopped':True})
write(out/'budget-ledger.json',{'at':now(),'baseline':621,'new':9,'cumulative':630,'A_unique_generations_expected':96,'old_plan_budget':90,'over_old_plan':6,'authorization':'本轮明确授权最多9次；超出旧计划6次单列，不追溯改写90次计划。','future_reserved_30_consumed':0})
old=HERE/'runs/reason-citations-resume-20261016-181123';oldxs={x['id']:x for x in load(old/'diagnostic-inputs.json')};history=[]
for t in tasks:
    row=next(r for r in rows if r['task_id']==t['id'] and r['variant']=='improved');r=load(out/row['raw_record']);history.append({'task_id':t['id'],'historical_fixed_evidence_messages_equal_new_automatic_improved':r['messages']==oldxs[t['id']]['messages']['revised'],'config_equal':r['config']==oldxs[t['id']]['configs']['revised'],'note':'即使输入相同，仍是本轮新生成；不拿旧响应替代。'})
write(out/'historical-comparison.json',{'at':now(),'rows':history,'not_causal_isolation_of_prompt':True})
protected=load(out/'protected-before.json');changed=[p for p,h in protected.items() if sha(ROOT/p)!=h];assert not changed,changed
for p,h in load(out/'offline-preflight.json')['code_hashes'].items():assert sha(ROOT/p)==h,p
allruns=[]
for p in (HERE/'runs').rglob('run-*.json'):
    r=load(p)
    if r.get('generation_dispatched') and (r.get('usage') or {}).get('completion_tokens',0)>0:allruns.append({'path':p.relative_to(ROOT).as_posix(),'run_id':r['run_id']})
assert len(allruns)==len({x['run_id'] for x in allruns})==96
ports={}
for port in [8080,8890]:
    with socket.socket() as s:s.settimeout(1);ports[str(port)]=s.connect_ex(('127.0.0.1',port))!=0
assert all(ports.values())
caps=[load(p) for p in out.glob('capacity-*.json')];assert all(all(c['checks'].values()) for c in caps)
audit={'at':now(),'protected_unchanged':len(protected),'changed':changed,'generation_dispatches':9,'confirmed_generations':9,'unique_A_count':96,'cumulative':630,'A_run_ids':allruns,'all_template_checks_passed':True,'max_actual_input_tokens':max(c['input_tokens'] for c in caps),'technical_failures':0,'quality_retries':0,'budget_exhausted':sum(load(out/x['raw_record'])['finish_reason']=='length' for x in index),'truncated':[load(out/x['raw_record'])['truncated'] for x in index],'ports_closed':ports,'memory_before_GiB':rt['memory_before']['available_bytes']/2**30,'memory_after_load_GiB':rt['memory_after_load']['available_bytes']/2**30,'minimum_memory_GiB':min(x['available_bytes'] for x in rt['memory_samples'])/2**30,'no_AT_read':True,'page_submissions':3,'new_code_files':['current_candidate.py','current_server.py','current_page.html','launch_current.py']};write(out/'completion-audit.json',audit)
(out/'raw-results-and-review.md').write_text('\n\n'.join(md)+'\n\n'+json.dumps({'groups':groups,'pairs':pairs},ensure_ascii=False,indent=2),encoding='utf-8')
shutil.copy2(__file__,out/Path(__file__).name)
write(out/'file-manifest.json',{'at':now(),'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.rglob('*') if p.is_file() and not {'slot-cache','__pycache__'}&set(p.parts)],'self_excluded':True})
print(json.dumps({'groups':groups,'pairs':pairs,'audit':{k:v for k,v in audit.items() if k!='A_run_ids'}},ensure_ascii=False,indent=2))
