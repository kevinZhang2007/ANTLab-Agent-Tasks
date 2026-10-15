"""全部生成结束后复核；不被运行入口导入，不改变冻结方案。"""
import hashlib, importlib.util, json, shutil, statistics
from datetime import datetime
from pathlib import Path
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
FOLDER=ROOT/'基础/runs/integrated_dev_eval/20261015-134437'
OUT=FOLDER/'review'
NOTE='Codex辅助原文复核，尚未经本人逐项确认；非官方成绩。T题为评测后重复测试，非独立盲测或泛化验证。'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now().astimezone().isoformat()
def write(p,value):
    with p.open('x',encoding='utf-8',newline='\n') as out:json.dump(value,out,ensure_ascii=False,indent=2);out.write('\n')
def module(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
    execution=load(FOLDER/'execution-summary.json')
    assert not execution['technical_stop'] and execution['service_stopped'] and execution['completed_main_tasks']==12
    frozen=load(FOLDER/'freeze.json')
    assert all(sha(ROOT/p)==h for p,h in {**frozen['code_hashes'],**frozen['data_hashes']}.items())
    assert sha(FOLDER/'freeze.json')==load(FOLDER/'development-stage-complete.json')['freeze_sha256']
    assert not OUT.exists();OUT.mkdir()
    evaluator=module(ROOT/'基础/runs/proof_full_r0_repeat/20261015-124627/review/review_proof_full_repeat.py','old_text_evaluation')
    helper=module(ROOT/'基础/runs/eligibility_proof/20261015-000204/prepare_eligibility_proof.py','positions_helper')
    # 公开开发答案仅在全部生成及服务停止后加载；不进入冻结代码、提示词或模型输入。
    dev_public=load(ROOT/'基础/data/dev_answers.json')
    rows=[];module_rows=[];request_ids=[]
    for i in range(1,13):
        task=load(FOLDER/f'task-{i:02d}.json');cid=task['case_id']
        if cid.startswith('D'):
            basis=development_basis(task,dev_public)
            evaluate=lambda response:development_evaluate(task,response,basis,evaluator)
            basis_path='基础/data/dev_answers.json'
        else:
            basis_path=f'基础/runs/formal_review/round1/evidence-{cid}.json';basis=load(ROOT/basis_path)
            assert basis['source_sha256']==frozen['data_hashes']['基础/data/cases.json']
            originals={p['id']:p for p in task['original_passages']}
            assert all(e['id'] in originals and e['quote'] in originals[e['id']]['text'] for e in basis['required_evidence'])
            evaluate=lambda response:evaluator.evaluate(task,response,basis)
        raw=evaluate(task.get('raw_answer',''));final=evaluate(task.get('actual_final_output'))
        assert task['selection_is_fresh'] and all(s['started_at']>frozen['frozen_at'] for s in task['stages'])
        for stage in task['stages']:
            request_ids.append(stage['run_id'])
            assert stage['freeze_sha256']==sha(FOLDER/'freeze.json')
            assert stage['actual_http_request_body']['max_tokens']==256
            assert all(stage['parameter_checks'].values()) and stage['truncated'] is not True
            assert stage['actual_http_request_body']['messages']==stage['messages']
        operations=[e['operation'] for e in task['local_rule_processing']]
        if task['status']=='completed':assert 'ratio_calculation_proposal' in operations and 'positive_proof_and_citation_assembly' in operations
        module_rows.append({'case_id':cid,'operations':operations,'selection_is_fresh':task['selection_is_fresh'],
            'scope_first_trace_saved':isinstance(task.get('eligibility_rule_audit'),dict),
            'reference_status':task['proof_record'].get('proof_status'),'reference_reason':task['proof_record'].get('reason'),
            'ratio_status':task['ratio_proof'].get('status'),'ratio_reason':task['ratio_proof'].get('reason'),
            'classification':'模块已接入不代表每个问题适用；原始规则轨迹及unknown均保留在task文件。'})
        assert task['status']!='completed' or task['raw_response']==task['stages'][-1]['response']
        for facts in [task['proof_fact_sources'],task['ratio_fact_sources']]:helper.positions(facts,task.get('used_passages',[]))
        used={p['id'] for p in task.get('used_passages',[])}
        assert set(task['material_scope']['audit_only_ids']).isdisjoint(used)
        reference=task.get('reference_derived_response');proposal=task.get('proposed_response')
        if reference is not None:assert reference['answer']==raw['answer'] and set(reference['citations'])<=used
        if proposal is not None:assert set(proposal['citations'])<=used
        expected=proposal if proposal is not None else reference if reference is not None else evaluator.parse(task.get('raw_answer',''))[0]
        assert task['actual_final_output']==expected
        assert task['answer_changed_from_model_raw']==(final['answer']!=raw['answer'])
        reference_review=evaluate(reference) if reference is not None else None
        proposal_review=evaluate(proposal) if proposal is not None else None
        erroneous_reference=reference_review is not None and reference_review['support_actual_answer'] is not True
        erroneous_ratio=proposal_review is not None and (proposal_review['answer_correct'] is not True or proposal_review['support_actual_answer'] is not True)
        row={'reviewed_at':now(),'reviewer_note':NOTE,'case_id':cid,'dataset':task['dataset'],'main_task_id':task['main_task_id'],
             'stage_run_ids':[s['run_id'] for s in task['stages']],'raw_review':raw,'system_final_review':final,
             'raw_response':task.get('raw_response'),'reference_derived_response':reference,'reference_derived_review':reference_review,
             'proposed_response':proposal,'proposal_review':proposal_review,'actual_final_output':task['actual_final_output'],
             'actual_final_output_source':task['actual_final_output_source'],'answer_changed_from_model_raw':task['answer_changed_from_model_raw'],
             'reference_proof':task['proof_record'],'ratio_proof':task['ratio_proof'],'erroneous_reference_derivation':erroneous_reference,
             'erroneous_ratio_derivation':erroneous_ratio,'basis_path':basis_path,'basis_sha256':sha(ROOT/basis_path),
             'material_scope':task['material_scope'],'timing_summary':task['timing_summary'],
             'independent_judgment':'依据问题、完整原文和实际最终输入核对，不把程序proof_established或模型意见当作评分。'}
        write(OUT/f'review-{cid}.json',{'basis':basis,'row':row});rows.append(row)
    summaries={}
    keys=['answer_correct','semantic_consistent','format_complete','citation_ids_exist','necessary_input_coverage','necessary_coverage','support_actual_answer','has_unrelated_references','strict_complete_success']
    for dataset,denominator in [('development',4),('evaluation_repeat',8)]:
        group=[r for r in rows if r['dataset']==dataset];assert len(group)==denominator
        def metric(side,key):
            values=[r[side][key] for r in group];n=sum(v is True for v in values)
            return {'numerator':n,'denominator':denominator,'percent':100*n/denominator,'ambiguous':sum(v=='ambiguous' for v in values),'not_checked':sum(v=='not_checked' for v in values)}
        metrics={side:{k:metric(side,k) for k in keys} for side in ['raw_review','system_final_review']}
        rules={'reference_derived':sum(r['reference_derived_response'] is not None for r in group),
               'ratio_proposed':sum(r['proposed_response'] is not None for r in group),
               'ratio_answer_changed':sum(r['answer_changed_from_model_raw'] for r in group),
               'erroneous_reference_derivation':sum(r['erroneous_reference_derivation'] for r in group),
               'erroneous_ratio_derivation':sum(r['erroneous_ratio_derivation'] for r in group),
               'raw_wrong':sum(r['raw_review']['answer_correct'] is False for r in group),
               'final_wrong':sum(r['system_final_review']['answer_correct'] is False for r in group)}
        times=[r['timing_summary']['end_to_end_seconds'] for r in group]
        summaries[dataset]={'denominator':denominator,'metrics':metrics,'rule_counts':rules,'end_to_end_seconds':{'median':statistics.median(times),'min':min(times),'max':max(times),'sum':sum(times)}}
    write(OUT/'effective-reviews.json',{'reviewed_at':now(),'reviewer_note':NOTE,'rows':rows})
    write(OUT/'summary.json',{'reviewed_at':now(),'reviewer_note':NOTE,'datasets':summaries,'all_failures_and_unknowns_retained_in_denominators':True})
    assert len(request_ids)==len(set(request_ids))==execution['confirmed_generation_calls']
    write(OUT/'module-integration-audit.json',{'checked_at':now(),'rows':module_rows,'single_freeze_sha256':sha(FOLDER/'freeze.json'),
        'request_ids_unique':True,'request_budgets_and_echoed_parameters_checked':True,'no_history_model_outputs_used':True})
    ids={}
    for path in (ROOT/'基础/runs').rglob('*.json'):
        value=load(path)
        if not isinstance(value,dict):continue
        usage=value.get('usage')
        if not isinstance(usage,dict) and isinstance(value.get('response'),dict):usage=value['response'].get('usage')
        if value.get('run_id') and isinstance(usage,dict) and usage.get('completion_tokens',0)>0:ids.setdefault(value['run_id'],[]).append(path.relative_to(ROOT).as_posix())
    assert len(ids)==372+execution['confirmed_generation_calls']
    write(FOLDER/'generation-count.json',{'checked_at':now(),'previous':372,'this_round':execution['confirmed_generation_calls'],'unique_generation_run_ids':len(ids),'sources':ids})
    protected=load(FOLDER/'protected-hashes.json');changed=[p for p,h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h];assert not changed
    assert load(FOLDER/'protected-file-audit.json')['all_unchanged']
    shutil.copyfile(Path(__file__),OUT/Path(__file__).name)
    write(FOLDER/'final-audit.json',{'checked_at':now(),'protected_count':len(protected),'changed':changed,'service_stopped':True,
        'single_freeze_before_all_generations':True,'actual_requests_fresh_not_history_replay':True,
        'reference_assembly_and_ratio_new_answer_separate':True,'all_fact_sources_and_derived_citations_final_input_only':True,
        'this_round':execution['confirmed_generation_calls'],'cumulative':len(ids),
        'new_files':sorted(p.relative_to(ROOT).as_posix() for p in FOLDER.rglob('*') if p.is_file())})
    print(json.dumps({'rows':[{'case_id':r['case_id'],'raw':r['raw_review']['answer'],'final':r['system_final_review']['answer'],
        'raw_correct':r['raw_review']['answer_correct'],'final_correct':r['system_final_review']['answer_correct'],
        'raw_strict':r['raw_review']['strict_complete_success'],'final_strict':r['system_final_review']['strict_complete_success'],
        'source':r['actual_final_output_source'],'seconds':round(r['timing_summary']['end_to_end_seconds'],3)} for r in rows],
        'summaries':summaries,'cumulative':len(ids)},ensure_ascii=False))

# 下列内容仅供运行后的评价，不被候选入口导入。
def development_basis(task,public):
    item=next(p for p in public if p['id']==task['case_id'])
    cid=task['case_id']; originals={p['id']:p for p in task['original_passages']}
    if cid=='D01':
        explanation='目标正式CS41冻结分母85，补页68个必要结论获完整支持，68/85×100%=80%；迁移组和其他版本不能混用。'
    elif cid=='D02':
        explanation='目标QL62只观察HTTP响应和模型显示名；补页未采集资产、设备遥测和推理节点。区域与耗时不能推断具体GPU。目标范围采集边界可作缺证检查来源，不要求引用固定段落。'
    elif cid=='D03':
        explanation='同一BY53批次40问题、同设置，基础方案甲中位数7.6秒，候选乙5.8秒；问乙比甲少多少，应7.6−5.8=1.8，只输出数值。'
    else:
        explanation='WC34签署规则要求覆盖率≥88%且格式失败≤1，再按预算升序；甲86%、4次不合格，乙89%、1次、1980和丙88%、0次、1720合格，丙预算更低。'
    required=list(item['evidence_ids'])
    alternatives=['P406170','P562395'] if cid=='D02' else []
    relevant=set(required+alternatives)
    def first_clause(p):
        # 只做评价摘录，完整原段落同时保存，未用来生成或修正回答。
        return p['text'].split('。')[0]+'。'
    return {'case_id':cid,'question':task['question'],'public_answer':item,
        'derived_answer':item['answer'],'accepted_equivalent_forms':[item['answer'],*item['aliases']],
        'derivation':explanation,'required_evidence':[{'id':pid,'quote':first_clause(originals[pid])} for pid in required],
        'alternative_insufficiency_check_ids':alternatives,
        'related_original_sources':[originals[pid] for pid in relevant],
        'excluded_evidence':[{'id':pid,'reason':'其他项目、版本、月份、压力或迁移范围，不支持所问目标。'} for pid in originals if pid not in relevant],
        'timing':'全部24次生成结束并停止服务后才读取公开开发答案；不进入选择、关联、规则或回答。'}

def development_evaluate(task,response,basis,evaluator):
    value,valid=evaluator.parse(response);answer=value.get('answer','');ids=value.get('citations',[])
    visible={p['id']:p for p in task.get('used_passages',[])}
    required={e['id'] for e in basis['required_evidence']}
    alternative=set(basis['alternative_insufficiency_check_ids'])
    correct=answer in basis['accepted_equivalent_forms'];semantic=correct
    if task['case_id']=='D03' and answer in ['1.8秒','1.8 秒']:semantic=True
    ids_ok=bool(valid and ids and len(set(ids))==len(ids) and all(i in visible for i in ids))
    coverage=bool(alternative&set(ids)) if alternative else required.issubset(ids)
    input_coverage=bool(alternative&set(visible)) if alternative else required.issubset(visible)
    excluded={e['id']:e['reason'] for e in basis['excluded_evidence']};unrelated=[i for i in ids if i in excluded]
    support=bool(semantic and ids_ok and coverage)
    return {'answer':answer,'citations':ids,'answer_correct':correct,'semantic_consistent':semantic,'format_complete':valid,
        'citation_ids_exist':ids_ok,'necessary_input_coverage':input_coverage,'necessary_coverage':coverage,
        'support_actual_answer':support,'has_unrelated_references':bool(unrelated),'irrelevant_ids':unrelated,
        'strict_complete_success':bool(correct and valid and ids_ok and coverage and support and not unrelated),'ambiguity':None,
        'reasons':{'answer':basis['derivation']+' 实际answer='+repr(answer)+'，未改写。',
            'coverage':'必要数据/规则来源必须共同引用；缺证题允许目标范围有效检查来源，不固定引用ID。',
            'support':'按当前实际输入和上述原文推导核对，不把ID存在或系统证明标记当成语义通过。',
            'unrelated':[{'id':i,'reason':excluded[i]} for i in unrelated]},
        'source_evidence':[{'id':p['id'],'quote':p['text'],'visible':p['id'] in visible,'cited':p['id'] in ids} for p in basis['related_original_sources']]}

if __name__=='__main__':main()
