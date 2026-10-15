"""生成全部结束后另存原文辅助暂判；不被生成入口导入。"""
import hashlib
import importlib.util
import json
import shutil
import statistics
from datetime import datetime
from pathlib import Path

ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
FOLDER=ROOT/'基础/runs/proof_full_r0_repeat/20261015-124627'
HISTORY=ROOT/'基础/runs/eligibility_r0_repeat/20261014-231852/full'
OUT=FOLDER/'review'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now().astimezone().isoformat()
NOTE='Codex辅助原文复核，尚未经本人逐项确认。非官方成绩或独立人工评分；属于评测后重复测试。'
def write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as out:json.dump(value,out,ensure_ascii=False,indent=2);out.write('\n')
def parse(raw):
    try:
        value=json.loads(raw) if isinstance(raw,str) else raw
        valid=isinstance(value,dict) and set(value)=={'answer','citations'} and isinstance(value['answer'],str) and isinstance(value['citations'],list) and all(isinstance(i,str) for i in value['citations'])
        return value if valid else {},valid
    except (ValueError,TypeError):return {},False

def evaluate(task,response,basis):
    value,valid=parse(response);answer=value.get('answer','');ids=value.get('citations',[])
    visible={p['id']:p for p in task.get('used_passages',[])}
    original={p['id']:p for p in task['original_passages']}
    required={e['id'] for e in basis['required_evidence']}
    excluded={e['id']:e['reason'] for e in basis['excluded_evidence']}
    acceptable=basis.get('accepted_equivalent_forms',[basis['derived_answer']])
    cid=task['case_id']
    if cid=='T04':acceptable=['流程乙','乙']
    if cid=='T07':acceptable=['方案丙','丙']
    correct=answer in acceptable;semantic=correct
    if cid=='T03' and answer in ['2.6秒','2.6 秒']:semantic=True
    if cid=='T07' and answer in ['选择方案丙','采用方案丙','最终选择方案丙']:semantic=True
    ids_ok=bool(valid and ids and all(i in visible for i in ids))
    coverage=required.issubset(ids);input_coverage=required.issubset(visible)
    unrelated=[i for i in ids if i in excluded]
    support=bool(semantic and ids_ok and coverage)
    reason=basis['derivation']+' 实际answer='+repr(answer)+'，不改写。'
    support_reason='原文数据与必要计算/选择/发布条件需共同覆盖；不是仅看ID有效或系统proof标记。'
    ambiguity=None
    if cid=='T05':
        coverage=bool(required & set(ids));input_coverage=bool(required & set(visible))
        support=bool(correct and ids_ok and coverage)
        support_reason='沿用既有澄清：目标校内组的采集边界或明确缺能耗记录可作有效缺证来源，不要求固定引用；不推出现实绝对无采集。'
    if cid=='T01':
        ambiguity='保持S24完成三项的有条件推导与未关闭问题为零未明示的严格字面边界，尚待本人确认。'
        if answer in ['S24','证据不足']:
            correct=semantic='ambiguous';support='ambiguous' if ids_ok and coverage else False
        elif answer=='S23':reason+=' S23明示缺坐标映射，与必要检查冲突；不依赖S24争议即可判失败。'
        elif answer=='S25':reason+=' S25明示未关闭问题，与发布规则冲突。'
    if cid in ['T02','T06'] and answer=='证据不足':reason+=' 完整R0有推导依据；拒答或定位漏选不能计为端到端成功。'
    strict=bool(correct is True and valid and ids_ok and coverage and support is True and not unrelated)
    return {'answer':answer,'citations':ids,'answer_correct':correct,'semantic_consistent':semantic,'format_complete':valid,
        'citation_ids_exist':ids_ok,'necessary_input_coverage':input_coverage,'necessary_coverage':coverage,
        'support_actual_answer':support,'has_unrelated_references':bool(unrelated),'irrelevant_ids':unrelated,
        'strict_complete_success':strict,'ambiguity':ambiguity,
        'reasons':{'answer':reason,'coverage':'必要原文来源='+','.join(sorted(required))+'；实际引用='+','.join(ids),
            'support':support_reason,'unrelated':[{'id':i,'reason':excluded[i]} for i in unrelated]},
        'source_evidence':[{'id':e['id'],'quote':e['quote'],'full_original_text':original[e['id']]['text'],'visible':e['id'] in visible,'cited':e['id'] in ids} for e in basis['required_evidence']]}

def main():
    execution=load(FOLDER/'execution-summary.json')
    assert not execution['technical_stop'] and execution['service_stopped'] and execution['completed_main_tasks']==8
    assert not OUT.exists();OUT.mkdir()
    freeze=load(FOLDER/'freeze.json')
    assert all(sha(ROOT/p)==v for p,v in {**freeze['code_hashes'],**freeze['data_hashes']}.items())
    assert load(FOLDER/'protected-file-audit.json')['all_unchanged']
    spec=importlib.util.spec_from_file_location('positions_review',ROOT/'基础/runs/eligibility_proof/20261015-000204/prepare_eligibility_proof.py')
    helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
    tasks=[load(FOLDER/f'task-{i:02d}.json') for i in range(1,9)]
    rows=[];paired=[]
    for task in tasks:
        cid=task['case_id'];basis_path=ROOT/f'基础/runs/formal_review/round1/evidence-{cid}.json';basis=load(basis_path)
        original={p['id']:p for p in task['original_passages']}
        assert basis['source_sha256']==freeze['data_hashes']['基础/data/cases.json']
        assert all(e['id'] in original and e['quote'] in original[e['id']]['text'] for e in basis['required_evidence'])
        historical_task=load(HISTORY/f"task-{task['sequence']:02d}.json")
        assert historical_task['question']==task['question'] and historical_task['original_passages']==task['original_passages']
        assert task['selection_is_fresh'] and len(task['stages'])==2
        assert min(s['started_at'] for s in task['stages'])>freeze['frozen_at']
        assert task['raw_response']==task['stages'][-1]['response']
        raw=evaluate(task,task.get('raw_answer',''),basis)
        final=evaluate(task,task.get('actual_final_output'),basis)
        derived=task.get('derived_response')
        if derived is not None:
            assert derived['answer']==raw['answer'] and derived==task['actual_final_output']
        else:
            assert parse(task.get('actual_final_output'))==parse(task.get('raw_answer',''))
        proof=task.get('proof_record',{})
        helpers.positions(proof,task['original_passages'])
        helpers.positions(task['local_rule_processing'],task['original_passages'])
        # 语义复核不读取proof_established作为评分标签；核对获选对象自身原文及唯一规则。
        proof_review={'applicable':proof.get('proof_status')!='not_applicable' and bool(proof),
            'established_by_checker':proof.get('proof_established',False),'derived':derived is not None,
            'refused_when_applicable':bool(proof) and proof.get('proof_status')!='not_applicable' and derived is None,
            'reason':proof.get('reason',proof.get('proof_status')),'independent_semantic_check':None,
            'erroneous_derivation':derived is not None and final['support_actual_answer'] is not True,
            'limit':'系统规则不是独立语义核验；保持有限语法、集合指称解释及原有歧义。'}
        if derived is not None:
            desc=proof['candidate_description'];rule=proof['rule_info']['rule']
            proof_review['independent_semantic_check']={'candidate_original_quote':desc,'release_rule_original_quote':rule,
                'condition_quotes':[{k:c[k] for k in ['name','status','evidence','rule']} for c in proof['conditions']],
                'judgment':'依据获选项自身明示检查通过与同一记录唯一直接规则列明的必要集合，复核集合支持；不是由其他项失败推定。',
                'aggregate_binding_limit':'若使用数量表达承接同记录检查集合，此有限指称解释尚待本人确认。',
                'all_citation_sources_actual':all(i in {p['id'] for p in task['used_passages']} for i in derived['citations'])}
        previous=load(HISTORY/f'review/review-{cid}.json')['row']
        comparison={'case_id':cid,'previous_raw':{'answer':previous['answer'],'citations':previous['citations'],'answer_correct':previous['answer_correct'],'strict_complete_success':previous['strict_complete_success']},
            'current_raw':{'answer':raw['answer'],'citations':raw['citations'],'answer_correct':raw['answer_correct'],'strict_complete_success':raw['strict_complete_success']},
            'current_system_final':{'answer':final['answer'],'citations':final['citations'],'answer_correct':final['answer_correct'],'strict_complete_success':final['strict_complete_success']},
            'raw_strict_change':'improved' if raw['strict_complete_success'] and not previous['strict_complete_success'] else 'regressed' if previous['strict_complete_success'] and not raw['strict_complete_success'] else 'unchanged',
            'system_strict_change':'improved' if final['strict_complete_success'] and not previous['strict_complete_success'] else 'regressed' if previous['strict_complete_success'] and not final['strict_complete_success'] else 'unchanged'}
        row={'reviewed_at':now(),'reviewer_note':NOTE,'status':'provisional_not_personally_confirmed','case_id':cid,
            'main_task_id':task['main_task_id'],'run_ids':[s['run_id'] for s in task['stages']],
            'basis_path':basis_path.relative_to(ROOT).as_posix(),'basis_sha256':sha(basis_path),
            'basis_applicability':'问题及完整R0资料与上次完整流程逐字一致；原文摘录和数据哈希通过，不借不可见资料补引用。',
            'raw_review':raw,'system_final_review':final,'derived_response':derived,'proof_review':proof_review,
            'actual_final_output':task['actual_final_output'],'timing_summary':task['timing_summary'],
            'selection':task['selection_validation'],'added_ids':task.get('added_ids',[])}
        write(OUT/f'review-{cid}.json',{'basis':basis,'row':row,'history_comparison':comparison})
        rows.append(row);paired.append(comparison)
    def metric(key,side):
        vals=[r[side][key] for r in rows]
        return {'true':sum(v is True for v in vals),'false':sum(v is False for v in vals),'ambiguous':sum(v=='ambiguous' for v in vals),'denominator':8,'percent':sum(v is True for v in vals)*100/8}
    metrics={side:{k:metric(k,side) for k in ['answer_correct','semantic_consistent','format_complete','citation_ids_exist','necessary_input_coverage','necessary_coverage','support_actual_answer','has_unrelated_references','strict_complete_success']} for side in ['raw_review','system_final_review']}
    rules={'supported_branch':sum(r['proof_review']['applicable'] for r in rows),'not_applicable':sum(not r['proof_review']['applicable'] for r in rows),
        'derived':sum(r['proof_review']['derived'] for r in rows),'refused_when_applicable':sum(r['proof_review']['refused_when_applicable'] for r in rows),
        'erroneous_derivation':sum(r['proof_review']['erroneous_derivation'] for r in rows),'denominator':8}
    write(OUT/'effective-reviews.json',{'reviewed_at':now(),'reviewer_note':NOTE,'rows':rows})
    write(OUT/'summary.json',{'reviewed_at':now(),'reviewer_note':NOTE,'metrics':metrics,'rule_counts':rules,'denominator':8,
        'all_failures_and_nonapplicable_remain_in_denominator':True,
        'end_to_end_seconds':{'min':min(t['end_to_end_seconds'] for t in tasks),'median':statistics.median(t['end_to_end_seconds'] for t in tasks),'max':max(t['end_to_end_seconds'] for t in tasks)}})
    write(OUT/'historical-comparison.json',{'reviewed_at':now(),'reviewer_note':NOTE,'historical_root':HISTORY.relative_to(ROOT).as_posix(),
        'configuration_differences':['历史完整R0为重复出现先于范围；当前为范围优先及完整词边界版本提取。','当前仅快照正向证明成立时进行local_rule引用组装；答案逐字保留，不能称为模型原始引用。','模型、最终提示词、采样、预算、服务设置相同；重新定位且不是同步随机配对。'],
        'rows':paired,'system_improvements':sum(p['system_strict_change']=='improved' for p in paired),'system_regressions':sum(p['system_strict_change']=='regressed' for p in paired),
        'not_independent_blind_evaluation':True})
    generated={}
    for path in (ROOT/'基础/runs').rglob('*.json'):
        value=load(path)
        if not isinstance(value,dict):continue
        usage=value.get('usage')
        if not isinstance(usage,dict) and isinstance(value.get('response'),dict):usage=value['response'].get('usage')
        if value.get('run_id') and isinstance(usage,dict) and usage.get('completion_tokens',0)>0:
            generated.setdefault(value['run_id'],[]).append(path.relative_to(ROOT).as_posix())
    assert len(generated)==340+execution['confirmed_generation_calls']
    write(FOLDER/'generation-count.json',{'checked_at':now(),'previous':340,'this_round':execution['confirmed_generation_calls'],'unique_generated_run_ids':len(generated),'sources':generated})
    assert load(FOLDER/'protected-file-audit.json')['all_unchanged']
    protected=load(FOLDER/'protected-hashes.json')
    changed=[p for p,h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
    assert not changed
    write(FOLDER/'final-audit.json',{'checked_at':now(),'frozen_before_generation':True,'raw_response_preserved':True,
        'derived_answer_unchanged':True,'service_stopped':True,'old_protected_count':len(protected),'old_protected_files_changed':changed,
        'this_round_generations':execution['confirmed_generation_calls'],'cumulative':len(generated),
        'all_review_labels_auxiliary_and_provisional':True,'new_files':sorted(p.relative_to(ROOT).as_posix() for p in FOLDER.rglob('*') if p.is_file())})
    shutil.copyfile(Path(__file__),OUT/Path(__file__).name)
    print(json.dumps({'rows':[{'case_id':r['case_id'],'raw':{'answer':r['raw_review']['answer'],'citations':r['raw_review']['citations']},
        'derived':r['derived_response'],'answer_correct':r['system_final_review']['answer_correct'],'raw_strict':r['raw_review']['strict_complete_success'],
        'final_strict':r['system_final_review']['strict_complete_success'],'seconds':round(r['timing_summary']['end_to_end_seconds'],3),'proof_status':r['proof_review']['reason']} for r in rows],
        'answer_correct':metrics['system_final_review']['answer_correct'],'raw_strict':metrics['raw_review']['strict_complete_success'],
        'system_strict':metrics['system_final_review']['strict_complete_success'],'rules':rules,'cumulative':len(generated)},ensure_ascii=False))

if __name__=='__main__':main()
