from pathlib import Path
import sys,json,shutil,difflib,subprocess,socket
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
from sentence_interface import interface_response
from locator import Locator
out=Path(Path('a-relation-single-out.txt').read_text(encoding='utf-8').strip());rt=load(out/'runtime.json');assert rt['confirmed_generations']==rt['dispatches']==6 and rt['model_stopped'] and 'error' not in rt
inputs={x['id']:x for x in load(out/'diagnostic-inputs.json')};plan=load(out/'intervention-plan.json');entries=[load(p) for p in sorted(out.glob('item-*.json'))]
refs={r['id']:r for r in load(ROOT/'进阶/materials/a_dev_answers.json')};locator=Locator(load(ROOT/'进阶/materials/page_words.json'))
manual={
 ('AD01','original'):{'relation_correct':'not_applicable','reason_consistent':False,'reason_preserves_claim':False,'reason_supported':False,'necessary':True,'support':False,'unrelated':False,'basis':'label为supported，但理由改为保存文件加可执行流程这个不同主张；全选11句包含末句明确记录文件及目的的反证，覆盖反证不等于支持实际label。'},
 ('AD01','revised'):{'relation_correct':False,'reason_consistent':True,'reason_preserves_claim':False,'reason_supported':False,'necessary':True,'support':False,'unrelated':False,'basis':'原主张以手工操作不可避免为条件，理由却转为资料是否说明手工操作必要，并漏用已选sent-0011的明确记录要求。理由的缺证叙述与undetermined表面一致，但实际完整输入可直接反驳无需记录，映射insufficient错误。'},
 ('AD02','original'):{'relation_correct':'not_applicable','reason_consistent':False,'reason_preserves_claim':False,'reason_supported':False,'necessary':False,'support':False,'unrelated':False,'basis':'理由将仅静态导出不足执行称为反驳，但原主张正是仅此不足；只选引言问句和Binder运行环境，漏Read静态导出来源。'},
 ('AD02','revised'):{'relation_correct':False,'reason_consistent':True,'reason_preserves_claim':True,'reason_supported':False,'necessary':False,'support':False,'unrelated':False,'basis':'reason保留了主张的不足执行方向，并以没有直接明说为由给undetermined；完整实际输入的Read静态档案与Run环境可组合支持该区别，不能因没有逐字复述就拒判。只选sent-0002/0011，缺Read必要依据，引用也不能支持拒判。'},
 ('AD03','original'):{'relation_correct':'not_applicable','reason_consistent':False,'reason_preserves_claim':False,'reason_supported':False,'necessary':False,'support':False,'unrelated':True,'basis':'理由把绘图数据转换变成graphic design及程序版本归档，选中前8句均为程序依赖与版本，不支持只存最终图足够。'},
 ('AD03','revised'):{'relation_correct':False,'reason_consistent':True,'reason_preserves_claim':True,'reason_supported':False,'necessary':False,'support':False,'unrelated':True,'basis':'entails与reason支持原主张在文字上相符，但只选程序版本/依赖前8句，不能推出只留最终图满足底层数据建议。实际未输入指定S08，不能借参考补证；S09实际含检查详细值的相关论述，不能笼统说完全没有相关材料，也不能把它改判为支持只留图。'}
}
rows=[];raws=[];md=['# 关系单输出与确定性标签映射：六条原始输出','Codex辅助原文复核，尚待本人确认。固定自动证据重放，不是端到端成绩。候选模型不输出label；以下外部标签均由模型关系确定性映射。']
for n,e in enumerate(entries,1):
    r=load(out/e['raw_record']);x=inputs[e['id']];v=e['variant'];exp=load(out/f'expansion-{n:02}.json');obj=exp['parsed_internal'];m=manual[(e['id'],v)]
    assert r['messages']==x['messages'][v] and r['config']==x['configs'][v]
    if v=='revised':
        from relation_single import expand,RELATION_TO_LABEL
        assert exp==expand(r['content'],x['blocks'],x['sentence_index'],x['doc_ids'],x['snapshot'])
        label=exp['expanded_response']['label'] if exp['valid'] else None;mapping_ok=exp['valid'] and label==RELATION_TO_LABEL[obj['relation']];model_label=None;relation=obj['relation'];origin='deterministic_mapping_from_model_relation'
    else:
        from sentence_selection import expand
        assert exp==expand(r['content'],x['blocks'],x['sentence_index'],x['doc_ids'],x['snapshot'])
        label=obj.get('label');model_label=label;relation='not_applicable';mapping_ok='not_applicable';origin='model_original_label'
    source=exp['valid'] and all(next(b for b in x['blocks'] if b['block_id']==s['block_id'])['text'][s['start']:s['end']]==s['text'] for s in exp['selected_sources'])
    fields={'relation','reason','sentence_ids'} if v=='revised' else {'label','reason','sentence_ids'};fmt=isinstance(obj,dict) and set(obj)==fields and isinstance(obj['reason'],str) and isinstance(obj['sentence_ids'],list)
    correct=label==refs[e['id']]['label'];strict=bool(fmt and exp['valid'] and correct and m['reason_consistent'] and m['reason_supported'] and m['necessary'] and m['support'] and not m['unrelated'])
    mapped=interface_response(e['request_id'],x['claim'],x['doc_ids'],x['snapshot'],r['run_id'],exp,r['elapsed_seconds'],locator=locator,actual_input_blocks=x['blocks'])
    assert mapped['answer']==label and mapped['support_status']=='not_checked'
    if v=='revised':
        mapped.update(label=label,model_original_label=None,model_relation=relation,relation_judgment_source='model',claim_judgment_source='rule',external_label_origin=origin,external_label_run_kind='local_rule',mapping_consistency=mapping_ok)
        mapped['derivation'].update(operation='fixed_relation_to_label_mapping_and_selected_sentence_expansion',mapping=RELATION_TO_LABEL,mapping_created_label=True,label_changed=None,label_changed_null_reason='模型未输出label，程序新增映射字段，不是改写原始label',semantic_support='not_checked')
    write(out/f'interface-response-{n:02}.json',mapped)
    row={**e,'raw_internal_content':r['content'],'parsed_internal':obj,'model_original_relation':relation,'model_original_label':model_label,'external_label':label,'external_label_origin':origin,'mapping_consistency':mapping_ok,'model_relation_correct':m['relation_correct'],'public_reference_label':refs[e['id']]['label'],'external_label_correct':correct,'reason_relation_or_baseline_label_consistent':m['reason_consistent'],'reason_preserves_original_claim':m['reason_preserves_claim'],'reason_semantically_supported':m['reason_supported'],'format_complete':fmt,'selection_valid':exp['valid'],'source_authenticity':source,'selected_sentence_ids':obj['sentence_ids'],'selected_sources':exp['selected_sources'],'necessary_evidence_coverage':m['necessary'],'citation_support':m['support'],'has_unrelated_evidence':m['unrelated'],'strict_complete_success':strict,'basis':m['basis'],'expanded_response':exp['expanded_response'],'client_seconds':r['elapsed_seconds'],'input_tokens':r['input_tokens'],'usage':r['usage'],'finish_reason':r['finish_reason'],'truncated':r['truncated'],'judgment_source':'unverified','reviewer':'Codex辅助原文复核，尚待本人确认'}
    rows.append(row);write(out/f'review-item-{n:02}.json',row)
    raws.append({'id':e['id'],'variant':v,'run_id':r['run_id'],'actual_http_request_raw':r['actual_http_request_raw'],'raw_response':r['raw_response'],'content':r['content'],'usage':r['usage'],'finish_reason':r['finish_reason'],'client_seconds':r['elapsed_seconds'],'external_label':label,'external_label_origin':origin})
    md+=['\n## '+e['id']+' '+v,'模型原始输出：','```json',r['content'],'```','外部标签：'+str(label)+'；来源：'+origin,f"客户端耗时 {r['elapsed_seconds']:.3f} 秒；输出 {r['usage']['completion_tokens']} tokens；结束 {r['finish_reason']}。",m['basis'],'展开的外部接口内容（映射/展开为local_rule，不是原始模型响应）：','```json',json.dumps(exp['expanded_response'],ensure_ascii=False,indent=2),'```']
groups={}
for v in ['original','revised']:
    rs=[r for r in rows if r['variant']==v]
    groups[v]={'denominator':3,'format_complete':sum(r['format_complete'] for r in rs),'model_relation_correct':sum(r['model_relation_correct'] is True for r in rs) if v=='revised' else 'not_applicable','mapping_consistency':sum(r['mapping_consistency'] is True for r in rs) if v=='revised' else 'not_applicable','external_label_correct':sum(r['external_label_correct'] for r in rs),'reason_relation_or_label_consistent':sum(r['reason_relation_or_baseline_label_consistent'] for r in rs),'source_authenticity':sum(r['source_authenticity'] for r in rs),'necessary_coverage':sum(r['necessary_evidence_coverage'] for r in rs),'citation_support':sum(r['citation_support'] for r in rs),'strict_complete_success':sum(r['strict_complete_success'] for r in rs),'budget_exhausted':sum(r['finish_reason']=='length' for r in rs),'client_seconds':sum(r['client_seconds'] for r in rs),'output_tokens':sum(r['usage']['completion_tokens'] for r in rs)}
decision={'at':now(),'adopt_relation_single':False,'retain_current_sentence_selection':True,'reason':'严格成功均0/3，外部标签正确均0/3，引用支持均0/3；同分保留旧流程。单关系加映射消除了独立双字段矛盾，却没有提高语义正确性。','existing_correct_items_regressed':0,'history_replay_limit':'历史relation-first的AD02映射后标签正确，不代表本轮新生成还输出同一relation；本轮实际为undetermined，不能拼接历史较好结果。','mapping_not_semantic':'3/3映射一致只是程序枚举映射正确，不是原文关系或引用支持正确。候选理由与关系可表面一致但事实/推断错误，原样保留。','prior_decisions_preserved':True,'stop':'本轮结束，不追加生成或提示优化，不读七道评测。','new_generations':6,'cumulative':591,'A_used':57,'A_cap':90,'A_remaining':33,'technical_request_failures':0,'quality_retries':0}
write(out/'review.json',{'at':now(),'reviewer':'Codex辅助原文复核，尚待本人确认','groups':groups,'rows':rows,'decision':decision})
write(out/'six-raw-http-responses.json',{'at':now(),'count':6,'responses':raws,'no_repair':True})
(out/'raw-and-mapped-results.md').write_text('\n\n'.join(md)+'\n\n'+json.dumps({'groups':groups,'decision':decision},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
diffs=[]
for x in inputs.values():
    a=next(r for r in rows if r['id']==x['id'] and r['variant']=='original');b=next(r for r in rows if r['id']==x['id'] and r['variant']=='revised');aa=json.loads(load(out/a['raw_record'])['actual_http_request_raw']);bb=json.loads(load(out/b['raw_record'])['actual_http_request_raw'])
    assert aa['messages'][1:]==bb['messages'][1:] and aa['max_tokens']==bb['max_tokens']==512
    assert {k:v for k,v in aa.items() if k not in ['messages','response_format']}=={k:v for k,v in bb.items() if k not in ['messages','response_format']}
    diffs.append({'id':x['id'],'same_user_claim_evidence_sentence_index':True,'same_sampling_budget_model':True,'changed':['system_relation_single_output_instruction','internal_schema_relation_instead_of_label','external_deterministic_mapping'],'actual_baseline_body':aa,'actual_candidate_body':bb})
write(out/'actual-request-differences.json',diffs)
protected=load(out/'protected-before.json');changed=[p for p,h in protected.items() if sha(ROOT/p)!=h];assert not changed,changed
for p,h in plan['code_hashes'].items():assert sha(ROOT/p)==h,p
allruns=[]
for p in (HERE/'runs').rglob('run-*.json'):
    r=load(p)
    if r.get('generation_dispatched') and (r.get('usage') or {}).get('completion_tokens',0)>0:allruns.append((p,r['run_id']))
assert len(allruns)==len({rid for p,rid in allruns})==57
with socket.socket() as s:s.settimeout(1);closed=s.connect_ex(('127.0.0.1',8080))!=0
assert closed
git=r'C:\Users\86186\AppData\Local\Programs\Git\cmd\git.exe'
def g(*args):
    r=subprocess.run([git,'--no-optional-locks','-c','core.quotepath=false',*args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8');return {'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
resources={'before_GiB':rt['memory_before']['available_bytes']/2**30,'after_load_GiB':rt['memory_after_load']['available_bytes']/2**30,'minimum_sampled_GiB':min(x['available_bytes'] for x in rt['memory_samples'])/2**30,'load_seconds':rt['load_seconds'],'model_stopped':rt['model_stopped'],'port8080_closed':closed}
write(out/'completion-audit.json',{'at':now(),'old_files_checked':len(protected),'changed':changed,'plan_code_hashes_match':True,'A_unique_generations':57,'A_run_ids':[{'path':p.relative_to(ROOT).as_posix(),'run_id':rid} for p,rid in allruns],'new_generations':6,'cumulative':591,'A_cap':90,'A_remaining':33,'B_offline_replay_not_added':88,'resources':resources,'max_input_tokens':max(r['input_tokens'] for r in rows),'all_fit_with_512':all(r['input_tokens']+512<=4096 for r in rows),'truncated':[r['truncated'] for r in rows],'git_status':g('status','--short','--branch'),'diff_check':g('diff','--check'),'staged_diff':g('diff','--cached','--stat'),'AT_read':False,'new_page_validation':False,'historical_mapping_added_generation':0})
diff=''
for name in ['relation_single.py','diagnose_relation_single.py']:
    p=HERE/name;diff+=''.join(difflib.unified_diff([],p.read_text(encoding='utf-8').splitlines(keepends=True),fromfile='/dev/null',tofile='b/'+p.relative_to(ROOT).as_posix()))
(out/'complete-code.diff').write_text(diff,encoding='utf-8')
orch=out/'orchestration-sources';orch.mkdir()
for name in ['a_relation_single.py','prepare_a_relation_single.py','review_a_relation_single.py']:shutil.copy2(name,orch/name)
write(out/'file-manifest.json',{'at':now(),'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.rglob('*') if p.is_file() and not {'slot-cache','__pycache__'}&set(p.parts)],'new_runtime_files':['进阶/a_exploration/relation_single.py','进阶/a_exploration/diagnose_relation_single.py'],'self_excluded':True})
print(json.dumps({'groups':groups,'decision':decision,'resources':resources,'old_files_unchanged':len(protected),'times':[(r['id'],r['variant'],r['external_label'],round(r['client_seconds'],3)) for r in rows]},ensure_ascii=False,indent=2))
