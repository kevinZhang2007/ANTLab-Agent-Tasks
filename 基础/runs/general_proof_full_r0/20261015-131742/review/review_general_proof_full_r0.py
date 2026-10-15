"""全部生成结束后原文辅助复核，单独保存，不供生成链导入。"""
import hashlib,importlib.util,json,shutil,statistics
from pathlib import Path
from datetime import datetime
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
FOLDER=ROOT/'基础/runs/general_proof_full_r0/20261015-131742'
HISTORY=ROOT/'基础/runs/proof_full_r0_repeat/20261015-124627'
PROOF=ROOT/'基础/runs/project_boundary_proof/20261015-131007'
OUT=FOLDER/'review'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now().astimezone().isoformat()
NOTE='Codex辅助原文复核，尚未经本人逐项确认；非官方成绩。属于评测后重复测试，不是独立泛化评价。'
def write(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as out:json.dump(v,out,ensure_ascii=False,indent=2);out.write('\n')
def module(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
    execution=load(FOLDER/'execution-summary.json')
    assert not execution['technical_stop'] and execution['service_stopped'] and execution['completed_main_tasks']==8
    assert not OUT.exists();OUT.mkdir()
    frozen=load(FOLDER/'freeze.json')
    assert all(sha(ROOT/p)==h for p,h in {**frozen['code_hashes'],**frozen['data_hashes']}.items())
    evaluator=module(HISTORY/'review/review_proof_full_repeat.py','existing_raw_text_scoring')
    helper=module(ROOT/'基础/runs/eligibility_proof/20261015-000204/prepare_eligibility_proof.py','source_positions')
    rows=[];paired=[];material=[]
    for index in range(1,9):
        task=load(FOLDER/f'task-{index:02d}.json');cid=task['case_id'];assert cid==f'T{index:02d}'
        basis_path=ROOT/f'基础/runs/formal_review/round1/evidence-{cid}.json';basis=load(basis_path)
        originals={p['id']:p for p in task['original_passages']}
        assert basis['source_sha256']==frozen['data_hashes']['基础/data/cases.json']
        assert all(e['id'] in originals and e['quote'] in originals[e['id']]['text'] for e in basis['required_evidence'])
        oldtask=load(HISTORY/f'task-{index:02d}.json')
        assert task['question']==oldtask['question'] and task['original_passages']==oldtask['original_passages']
        assert task['selection_is_fresh'] and task['stages'][0]['stage']=='selection'
        assert all(s['started_at']>frozen['frozen_at'] for s in task['stages'])
        if task['status']=='completed':assert task['raw_response']==task['stages'][-1]['response']
        raw=evaluator.evaluate(task,task.get('raw_answer',''),basis)
        final=evaluator.evaluate(task,task.get('actual_final_output'),basis)
        derived=task.get('derived_response');proof=task.get('proof_record',{})
        if derived is not None:
            assert derived['answer']==raw['answer'] and task['actual_final_output']==derived
        elif raw['format_complete']:
            assert task['actual_final_output']==json.loads(task['raw_answer'])
        helper.positions(proof,task['original_passages'])
        helper.positions(task['proof_fact_sources'],task.get('used_passages',[]))
        used_ids={p['id'] for p in task.get('used_passages',[])}
        if derived is not None:assert set(derived['citations'])<=used_ids
        assert set(task['material_scope']['audit_only_ids']).isdisjoint(used_ids)
        applicable=proof.get('proof_kind') is not None
        row={'reviewed_at':now(),'reviewer_note':NOTE,'case_id':cid,'main_task_id':task['main_task_id'],
            'stage_run_ids':[s['run_id'] for s in task['stages']],'raw_review':raw,'system_final_review':final,
            'raw_response':task.get('raw_response'),'derived_response':derived,'actual_final_output':task.get('actual_final_output'),
            'proof_kind':proof.get('proof_kind'),'proof_status':proof.get('proof_status'),'proof_reason':proof.get('reason'),
            'proof_applicable':applicable,'proof_refused':applicable and derived is None,
            'proof_not_applicable':proof.get('proof_status')=='not_applicable','upstream_selection_failure':task['status']=='selection_output_failure',
            'derived':derived is not None,'erroneous_derivation':derived is not None and final['support_actual_answer'] is not True,
            'basis_path':basis_path.relative_to(ROOT).as_posix(),'basis_sha256':sha(basis_path),
            'basis_applicability':'问题、完整原始可见资料与上次完整R0一致；必要摘录及数据哈希已核对。引用仅按实际最终输入核验。',
            'judgment_independence':'复用已保存原文计算/资格推导和澄清，不将proof_established当语义评分。',
            'material_scope':task['material_scope'],'timing_summary':task['timing_summary'],
            'selection_validation':task.get('selection_validation'),'added_ids':task.get('added_ids',[])}
        old=load(HISTORY/f'review/review-{cid}.json')['row']
        old_system=old['system_final_review'];old_raw=old['raw_review']
        def change(before,after):return 'improved' if after and not before else 'regressed' if before and not after else 'unchanged'
        comparison={'case_id':cid,'old_raw':{'answer':old_raw['answer'],'citations':old_raw['citations'],'strict':old_raw['strict_complete_success']},
            'old_final':{'answer':old_system['answer'],'citations':old_system['citations'],'strict':old_system['strict_complete_success']},
            'new_raw':{'answer':raw['answer'],'citations':raw['citations'],'strict':raw['strict_complete_success']},
            'new_final':{'answer':final['answer'],'citations':final['citations'],'strict':final['strict_complete_success']},
            'raw_strict_change':change(old_raw['strict_complete_success'],raw['strict_complete_success']),
            'system_strict_change':change(old_system['strict_complete_success'],final['strict_complete_success']),
            'answer_correct_change':change(old_raw['answer_correct'] is True,raw['answer_correct'] is True)}
        write(OUT/f'review-{cid}.json',{'basis':basis,'review':row,'history_comparison':comparison})
        rows.append(row);paired.append(comparison);material.append({'case_id':cid,**task['material_scope']})
    def metric(side,key):
        values=[r[side][key] for r in rows]
        return {'numerator':sum(v is True for v in values),'denominator':8,'percent':sum(v is True for v in values)*100/8,
            'ambiguous':sum(v=='ambiguous' for v in values),'not_checked':sum(v=='not_checked' for v in values)}
    metrics={side:{key:metric(side,key) for key in ['answer_correct','semantic_consistent','format_complete','citation_ids_exist','necessary_input_coverage','necessary_coverage','support_actual_answer','has_unrelated_references','strict_complete_success']} for side in ['raw_review','system_final_review']}
    rules={'applicable':sum(r['proof_applicable'] for r in rows),'refused':sum(r['proof_refused'] for r in rows),
        'not_applicable':sum(r['proof_not_applicable'] for r in rows),'upstream_failure':sum(r['upstream_selection_failure'] for r in rows),
        'derived':sum(r['derived'] for r in rows),'erroneous_derivation':sum(r['erroneous_derivation'] for r in rows),'denominator':8,
        'per_task_reasons':[{'case_id':r['case_id'],'kind':r['proof_kind'],'status':r['proof_status'],'reason':r['proof_reason']} for r in rows]}
    times=[r['timing_summary']['end_to_end_seconds'] for r in rows]
    summary={'reviewed_at':now(),'reviewer_note':NOTE,'denominator':8,'metrics':metrics,'rule_counts':rules,
        'end_to_end_seconds':{'median':statistics.median(times),'minimum':min(times),'maximum':max(times),'sum':sum(times)},
        'quality_failures_and_nonapplicable_remain_in_denominator':True,'generation_calls':execution['confirmed_generation_calls']}
    write(OUT/'effective-reviews.json',{'reviewed_at':now(),'reviewer_note':NOTE,'rows':rows})
    write(OUT/'summary.json',summary)
    write(OUT/'history-comparison.json',{'reviewed_at':now(),'reviewer_note':NOTE,'previous_complete_R0':HISTORY.relative_to(ROOT).as_posix(),
        'configuration_differences':['本轮最终引用证明扩展为快照、差值和资格选择，并使用新项目实体解析；只在回答后派生引用。',
            '生成侧范围解析、模型、提示词、Schema派生、采样及预算与上次完整R0保持一致；证明依赖单独导入，不反向改变生成请求。',
            '全部定位和回答重新执行；历史侧复用，非同步随机对照，不声称单次性能差异稳定。'],
        'rows':paired,'system_improvements':sum(p['system_strict_change']=='improved' for p in paired),
        'system_regressions':sum(p['system_strict_change']=='regressed' for p in paired),
        'raw_regressions':sum(p['raw_strict_change']=='regressed' for p in paired)})
    write(OUT/'material-scope.json',{'recorded_at':now(),'rows':material,'all_derived_fact_and_citation_sources_within_final_model_input':True,
        'audit_only_original_material_never_claimed_as_final_model_input':True})
    ids={}
    for path in (ROOT/'基础/runs').rglob('*.json'):
        v=load(path)
        if not isinstance(v,dict):continue
        usage=v.get('usage')
        if not isinstance(usage,dict) and isinstance(v.get('response'),dict):usage=v['response'].get('usage')
        if v.get('run_id') and isinstance(usage,dict) and usage.get('completion_tokens',0)>0:
            ids.setdefault(v['run_id'],[]).append(path.relative_to(ROOT).as_posix())
    assert len(ids)==356+execution['confirmed_generation_calls']
    write(FOLDER/'generation-count.json',{'checked_at':now(),'previous':356,'this_round':execution['confirmed_generation_calls'],'unique_generation_run_ids':len(ids),'sources':ids})
    protected=load(FOLDER/'protected-hashes.json');changed=[p for p,h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
    assert not changed
    assert load(FOLDER/'protected-file-audit.json')['all_unchanged']
    shutil.copyfile(Path(__file__),OUT/Path(__file__).name)
    write(FOLDER/'final-audit.json',{'checked_at':now(),'frozen_before_generation':True,'all_original_answers_preserved':True,
        'all_derived_citations_and_fact_sources_in_final_model_input':True,'protected_files':len(protected),'changed':changed,
        'model_service_stopped':True,'confirmed_generation_calls':execution['confirmed_generation_calls'],'cumulative':len(ids),
        'source_reviews_auxiliary_provisional_not_official':True})
    print(json.dumps({'rows':[{'case_id':r['case_id'],'raw':{'answer':r['raw_review']['answer'],'citations':r['raw_review']['citations']},
        'derived':r['derived_response'],'raw_strict':r['raw_review']['strict_complete_success'],'final_strict':r['system_final_review']['strict_complete_success'],
        'seconds':round(r['timing_summary']['end_to_end_seconds'],3),'reason':r['proof_reason']} for r in rows],
        'answer':metrics['system_final_review']['answer_correct'],'raw_strict':metrics['raw_review']['strict_complete_success'],
        'final_strict':metrics['system_final_review']['strict_complete_success'],'rules':rules,'cumulative':len(ids),'e2e':summary['end_to_end_seconds']},ensure_ascii=False))

if __name__=='__main__':main()
