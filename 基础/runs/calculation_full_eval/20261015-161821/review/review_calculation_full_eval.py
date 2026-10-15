"""八题全部结束后复用原文依据复核；不被生成入口导入。"""
import hashlib, importlib.util, json, shutil, statistics
from datetime import datetime
from pathlib import Path
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
FOLDER=ROOT/'基础/runs/calculation_full_eval/20261015-161821'
DEVELOPMENT=ROOT/'基础/runs/calculation_full_dev/20261015-160956'
HISTORY=ROOT/'基础/runs/integrated_dev_eval/20261015-134437'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now().astimezone().isoformat()
NOTE='Codex辅助原文复核，尚未经本人逐项确认；非官方成绩。已接触题上的评测后重复测试，不是独立盲测或泛化成绩。'
def write(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as out:json.dump(v,out,ensure_ascii=False,indent=2);out.write('\n')
def module(p,n):
    spec=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def positions(v,passages):
    sources={p['id']:p['text'] for p in passages}
    if isinstance(v,dict):
        if all(k in v for k in ['passage_id','start','end','quote']):assert v['passage_id'] in sources and sources[v['passage_id']][v['start']:v['end']]==v['quote']
        for x in v.values():positions(x,passages)
    elif isinstance(v,list):
        for x in v:positions(x,passages)
def main():
    execution=load(FOLDER/'execution-summary.json')
    assert not execution['technical_stop'] and execution['service_stopped'] and execution['completed_main_tasks']==8
    freeze=load(FOLDER/'freeze.json');parent=load(DEVELOPMENT/'freeze.json')
    assert all(sha(ROOT/p)==h for p,h in {**freeze['code_hashes'],**freeze['data_hashes'],**parent['code_hashes'],**parent['data_hashes']}.items())
    assert sha(DEVELOPMENT/'freeze.json')==freeze['parent_contract']['sha256']
    write(FOLDER/'launch-permission-record.json',{'recorded_at':now(),'first_launch':'自动权限审核未在时限内完成，CreateProcess未创建进程；没有模型请求。',
        'first_failure_exact_time':'未另存精确时间，工具调用记录中保留；本字段不补写时间。','retry':'按工具允许只重试一次启动，成功。',
        'generation_retry_count':0,'generation_dispatches':execution['generation_dispatches'],'not_a_model_technical_failure':True})
    out=FOLDER/'review';out.mkdir(exist_ok=False)
    evaluator=module(ROOT/'基础/runs/proof_full_r0_repeat/20261015-124627/review/review_proof_full_repeat.py','existing_formal_original_text_evaluation')
    old_rows={r['case_id']:r for r in load(HISTORY/'review/effective-reviews.json')['rows'] if r['dataset']=='evaluation_repeat'}
    rows=[];request_ids=[];paired=[]
    for i in range(1,9):
        task=load(FOLDER/f'task-{i:02d}.json');cid=task['case_id'];assert cid==f'T{i:02d}'
        basis_path=ROOT/f'基础/runs/formal_review/round1/evidence-{cid}.json';basis=load(basis_path)
        original={p['id']:p for p in task['original_passages']}
        assert basis['source_sha256']==freeze['data_hashes']['基础/data/cases.json']
        assert all(e['id'] in original and e['quote'] in original[e['id']]['text'] for e in basis['required_evidence'])
        historical_task=load(HISTORY/f'task-{i+4:02d}.json')
        assert task['question']==historical_task['question'] and task['original_passages']==historical_task['original_passages']
        evaluate=lambda response:evaluator.evaluate(task,response,basis)
        raw=evaluate(task.get('raw_answer',''));final=evaluate(task.get('actual_final_output'))
        assert task['selection_is_fresh']
        if task['status']=='completed':assert task['raw_response']==task['stages'][-1]['response']
        for s in task['stages']:
            request_ids.append(s['run_id'])
            assert s['started_at']>freeze['frozen_at'] and s['freeze_sha256']==sha(FOLDER/'freeze.json')
            assert s['actual_http_request_body']['max_tokens']==256 and all(s['parameter_checks'].values()) and s['truncated'] is not True
        for k in ['proof_fact_sources','ratio_fact_sources','difference_fact_sources']:positions(task[k],task.get('used_passages',[]))
        used={p['id'] for p in task.get('used_passages',[])}
        assert used.isdisjoint(task['material_scope']['audit_only_ids'])
        reference=task['reference_derived_response'];proposal=task['proposed_response']
        if reference is not None:assert reference['answer']==raw['answer'] and set(reference['citations'])<=used
        if proposal is not None:assert set(proposal['citations'])<=used
        parsed,valid=evaluator.parse(task.get('raw_answer',''))
        expected=proposal if proposal is not None else reference if reference is not None else parsed if valid else None
        assert task['actual_final_output']==expected
        rr=evaluate(reference) if reference is not None else None;pr=evaluate(proposal) if proposal is not None else None
        erroneous_reference=rr is not None and rr['support_actual_answer'] is not True
        erroneous_calculation=pr is not None and (pr['answer_correct'] is not True or pr['support_actual_answer'] is not True)
        old=old_rows[cid];oldraw=old['raw_review'];oldfinal=old['system_final_review']
        def change(a,b):return 'improved' if b is True and a is not True else 'regressed' if a is True and b is not True else 'unchanged'
        comparison={'case_id':cid,'previous_raw_answer':oldraw['answer'],'previous_final_answer':oldfinal['answer'],
            'previous_raw_strict':oldraw['strict_complete_success'],'previous_final_strict':oldfinal['strict_complete_success'],
            'current_raw_answer':raw['answer'],'current_final_answer':final['answer'],
            'raw_answer_change':change(oldraw['answer_correct'],raw['answer_correct']),
            'system_answer_change':change(oldfinal['answer_correct'],final['answer_correct']),
            'raw_strict_change':change(oldraw['strict_complete_success'],raw['strict_complete_success']),
            'system_strict_change':change(oldfinal['strict_complete_success'],final['strict_complete_success'])}
        row={'reviewed_at':now(),'reviewer_note':NOTE,'case_id':cid,'raw_review':raw,'system_final_review':final,
            'raw_response':task['raw_response'],'reference_derived_response':reference,'reference_derived_review':rr,
            'calculation_proposed_response':proposal,'calculation_review':pr,'actual_final_output':task['actual_final_output'],
            'output_source':task['actual_final_output_source'],'answer_changed':task['answer_changed_from_model_raw'],
            'reference_proof':task['proof_record'],'ratio_proof':task['ratio_proof'],'difference_proposal':task['difference_proposal'],
            'erroneous_reference_derivation':erroneous_reference,'erroneous_calculation_derivation':erroneous_calculation,
            'timing':task['timing_summary'],'material_scope':task['material_scope'],
            'basis_path':basis_path.relative_to(ROOT).as_posix(),'basis_sha256':sha(basis_path),
            'basis_applicability':'问题和原始R0资料逐字一致，必要摘录及数据哈希已核对；支持与引用只按实际最终输入判断，不借审计资料补证。',
            'judgment_source':'复用原文推导和已保存澄清，不将系统proof或模型意见当成正确标签；T01资格歧义不变。',
            'stage_run_ids':[s['run_id'] for s in task['stages']]}
        write(out/f'review-{cid}.json',{'basis':basis,'row':row,'history_comparison':comparison});rows.append(row);paired.append(comparison)
    assert len(request_ids)==len(set(request_ids))==execution['confirmed_generation_calls']
    keys=['answer_correct','semantic_consistent','format_complete','citation_ids_exist','necessary_input_coverage','necessary_coverage','support_actual_answer','has_unrelated_references','strict_complete_success']
    metrics={side:{k:{'numerator':sum(r[side][k] is True for r in rows),'denominator':8,'percent':sum(r[side][k] is True for r in rows)*12.5,
        'ambiguous':sum(r[side][k]=='ambiguous' for r in rows),'not_checked':sum(r[side][k]=='not_checked' for r in rows)} for k in keys} for side in ['raw_review','system_final_review']}
    counts={'erroneous_reference_derivations':sum(r['erroneous_reference_derivation'] for r in rows),
        'erroneous_calculation_derivations':sum(r['erroneous_calculation_derivation'] for r in rows),
        'system_improvements':sum(p['system_strict_change']=='improved' for p in paired),'system_regressions':sum(p['system_strict_change']=='regressed' for p in paired),
        'raw_regressions':sum(p['raw_strict_change']=='regressed' for p in paired),
        'actual_sources':{s:sum(r['output_source']==s for r in rows) for s in sorted({r['output_source'] for r in rows})}}
    times=[r['timing']['end_to_end_seconds'] for r in rows]
    summary={'reviewed_at':now(),'reviewer_note':NOTE,'metrics':metrics,'counts':counts,
        'e2e_seconds':{'median':statistics.median(times),'minimum':min(times),'maximum':max(times),'sum':sum(times)},
        'denominator':8,'all_failure_and_unknown_tasks_kept':True,'this_round_generations':execution['confirmed_generation_calls']}
    write(out/'summary.json',summary);write(out/'effective-reviews.json',{'reviewed_at':now(),'reviewer_note':NOTE,'rows':rows})
    write(out/'previous-version-comparison.json',{'reviewed_at':now(),'reviewer_note':NOTE,'previous_complete_evaluation':HISTORY.relative_to(ROOT).as_posix(),
        'differences':['旧侧为历史8题完整R0，非同步生成对照。','当前使用开发验证过的声明兼容、相同/同样比较集合兼容与独立差值计算建议；提示词、模型、Schema派生、采样和256预算相同。',
            '本轮所有定位和回答重新运行；不得把历史差异归因于某个单一模块或当成泛化验证。'], 'rows':paired})
    ids=set()
    for p in (ROOT/'基础/runs').rglob('*.json'):
        v=load(p)
        if not isinstance(v,dict):continue
        usage=v.get('usage')
        if not isinstance(usage,dict) and isinstance(v.get('response'),dict):usage=v['response'].get('usage')
        if v.get('run_id') and isinstance(usage,dict) and usage.get('completion_tokens',0)>0:ids.add(v['run_id'])
    assert len(ids)==412+execution['confirmed_generation_calls']
    write(FOLDER/'generation-count.json',{'checked_at':now(),'previous':412,'this_round':execution['confirmed_generation_calls'],'unique_generations':len(ids),'run_ids':sorted(ids)})
    # 只提取已有事实，不起草报告正文。命令为实际已执行记录，不承诺可覆盖原目录重跑。
    dev=load(DEVELOPMENT/'review/summary.json');settings=load(FOLDER/'settings.prepared.json')
    command='& "'+str(Path(os.environ['LOCALAPPDATA'])/'Programs/Python/Python314/python.exe')+'" -X utf8 -B "'+str(FOLDER/'run_calculation_full_eval.py')+'" "'+str(FOLDER)+'"'
    facts={'extracted_at':now(),'source_contract':(DEVELOPMENT/'freeze.json').relative_to(ROOT).as_posix(),'source_contract_sha256':sha(DEVELOPMENT/'freeze.json'),
        'execution_freeze':(FOLDER/'freeze.json').relative_to(ROOT).as_posix(),'code_entry':(FOLDER/'scope_candidate.py').relative_to(ROOT).as_posix(),
        'proof_entry':(FOLDER/'proof_pipeline_candidate.py').relative_to(ROOT).as_posix(),'runner':(FOLDER/'run_calculation_full_eval.py').relative_to(ROOT).as_posix(),
        'answer_config':(FOLDER/'config.answer.json').relative_to(ROOT).as_posix(),'selection_config':(FOLDER/'config.selection.json').relative_to(ROOT).as_posix(),
        'executed_command':command,'command_status':'已实际执行；有已有目录保护，不得在此目录重复生成或覆盖。新的复现需先创建独立目录并核对同一候选哈希。',
        'scope':['只用当前question/passages；新定位、直接关联、范围优先、答案形式/资格约束，保留未知与拒绝。',
            '有限快照/差值/资格选择引用证明；明确分类定义的比例和可靠可比集合差值可另存计算新答。',
            '事实和派生引用只来自最终模型输入；其他可见资料仅审计范围、实体和唯一性，不强制纠正不适用题。'],
        'model':freeze['model'],'service_arguments':freeze['service_arguments'],
        'answer_parameters':freeze['answer_config']['parameters'],'selection_parameters':freeze['selection_config']['parameters'],
        'development_metrics':dev['metrics'],'development_source':(DEVELOPMENT/'review/summary.json').relative_to(ROOT).as_posix(),
        'evaluation_metrics':metrics,'evaluation_source':(out/'summary.json').relative_to(ROOT).as_posix(),
        'this_round_generations':execution['confirmed_generation_calls'],'cumulative_generations':len(ids),'reviewer_note':NOTE}
    write(FOLDER/'report-facts.json',facts)
    protected=load(FOLDER/'protected-hashes.json');changed=[p for p,h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h];assert not changed
    shutil.copyfile(Path(__file__),out/Path(__file__).name)
    write(FOLDER/'final-audit.json',{'checked_at':now(),'protected_count':len(protected),'changed':changed,'service_stopped':True,
        'same_user_specified_candidate_verified':True,'all_model_responses_fresh':True,'fact_and_citation_sources_final_input_only':True,
        'this_round':execution['confirmed_generation_calls'],'cumulative':len(ids),'all_labels_auxiliary_provisional':True,
        'new_files':sorted(p.relative_to(ROOT).as_posix() for p in FOLDER.rglob('*') if p.is_file())})
    print(json.dumps({'rows':[{'case_id':r['case_id'],'raw':r['raw_review']['answer'],'final':r['system_final_review']['answer'],
        'citations':r['system_final_review']['citations'],'raw_correct':r['raw_review']['answer_correct'],'final_correct':r['system_final_review']['answer_correct'],
        'raw_strict':r['raw_review']['strict_complete_success'],'final_strict':r['system_final_review']['strict_complete_success'],'source':r['output_source'],
        'seconds':round(r['timing']['end_to_end_seconds'],3),'change':p['system_strict_change']} for r,p in zip(rows,paired)],
        'summary':summary,'cumulative':len(ids)},ensure_ascii=False))

if __name__=='__main__':
    import os
    main()
