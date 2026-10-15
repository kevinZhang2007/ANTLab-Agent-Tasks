"""复核调用结束后的原文辅助评价；不把模型verdict当语义标签。"""
from pathlib import Path
from datetime import datetime
import copy,hashlib,json,sys

repo=Path(__file__).resolve().parents[2]
folder=Path(sys.argv[1]).resolve()
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
now=lambda:datetime.now().astimezone().isoformat()
def write(name,value):
    p=folder/name;assert not p.exists();p.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
execution=load(folder/'execution-summary.json')
assert execution['completed_answers']==8 and not execution['technical_stop'] and execution['service_stopped']
records=sorted([load(p) for p in folder.glob('run-*.json')],key=lambda r:r['sequence'])
old_rows=load(repo/'基础/runs/direct_reference_pairs/20261014-134901/evaluations.json')['rows']
evidence_dir=repo/'基础/runs/formal_review/round1'
reason_notes={
 'T01':'P761989是段落ID，原文没有把它列为release_snapshot；该段是发布规则，不能支持把自身ID作为快照。T01的S24有条件推导及字面边界保留，不影响此ID错答。',
 'T02':'分母100在P552476，完全支持76及定义在P169676，可推导76%。contradicted识别了原拒答错误，但reason称无法确认具体数值不符合完整输入。',
 'T03':'2.6可由9.4-6.8推出；P385105只给基础9.4，候选6.8和可比条件在P362285。reason错把两个操作数都归给P385105，引用仍缺候选来源。',
 'T04':'P660995只给资格门槛和选择次序，不明确宣布流程乙已选；甲/乙/丙的实际计数在P758661。reason添加了该段明确选乙的说法，引用仍缺数据。',
 'T05':'P452207明示未采集功率与能耗，P286497是目标校内组采集边界。原证据不足及检查来源有效。insufficient可能指无法计算焦耳，reason与缺证事实一致；不能把标签歧义判成确定事实误报。',
 'T06':'P873502给45合法、8超时、7格式异常，P721388定义后两类为技术失败；实际可算(8+7)/60=25%。原证据不足错误，reason把45/60=75%的合法结果率说成技术失败率，与原答案也不一致。未将其写回答案。',
 'T07':'P313278给候选数据，P850395给支持率≥85%且P50≤7秒的双门槛；丙正确，但数据段没有完整决策规则或已选结论，仍缺规则引用。',
 'T08':'P183430是段落ID，检查结果是K16/K17/K18，配合P223300规则可选K17。把段落ID判为符合快照信息属于错误支持。',
}
rows=[];original_metrics=[]
for record in records:
    cid=record['case_id'];old=next(r for r in old_rows if r['case_id']==cid and r['variant']=='new')
    basis=load(evidence_dir/('evidence-'+cid+'.json'))
    passages=record['used_passages'];visible={p['id']:p for p in passages}
    required={e['id'] for e in basis['required_evidence']}
    assert all(e['quote'] in visible[e['id']]['text'] for e in basis['required_evidence'])
    original=record['original_response'];post=record['postprocessing'];candidate=post['candidate_response']
    assert original=={'answer':old['answer'],'citations':old['citations']}
    assert candidate['answer']==original['answer']
    def citation_grade(citations):
        ids=bool(citations and all(i in visible for i in citations) and len(citations)==len(set(citations)))
        coverage=bool(set(citations)&required) if cid=='T05' else required.issubset(citations)
        irrelevant=[i for i in citations if i in {e['id'] for e in basis['excluded_evidence']}]
        support=bool(old['answer_correct'] is True and ids and coverage)
        return {'citation_ids_exist':ids,'necessary_coverage':coverage,'support_actual_answer':support,
                'irrelevant_ids':irrelevant,'strict_complete_success':bool(old['answer_correct'] is True and ids and coverage and support and not irrelevant)}
    grade=citation_grade(candidate['citations'])
    value=post['review_validation'].get('value') or {}
    verdict=value.get('verdict');reported_ids=value.get('citations',[])
    reported_grade=citation_grade(reported_ids) if isinstance(reported_ids,list) and all(isinstance(i,str) for i in reported_ids) else {'support_actual_answer':False}
    false_support=verdict=='supported' and reported_grade['support_actual_answer'] is not True
    wrong_answer_support=bool(verdict=='supported' and old['answer_correct'] is False)
    row={'reviewed_at':now(),'case_id':cid,'review_run_id':record['run_id'],
        'original_record_path':record['source_path'],'old_side':'historical_reuse_not_synchronous_generation',
        'original_response':original,'raw_review_content':record['raw_content'],'parsed_review':value,
        'postprocessing':post,'candidate_response':candidate,'answer_exactly_unchanged':True,
        'citations_actually_changed':candidate['citations']!=original['citations'],
        'original_answer_correct':old['answer_correct'],'candidate_answer_correct':old['answer_correct'],
        'format_complete':set(candidate)=={'answer','citations'} and isinstance(candidate['answer'],str)
            and isinstance(candidate['citations'],list) and all(isinstance(i,str) for i in candidate['citations']),
        **grade,'review_supported_false_positive':false_support,'wrong_answer_marked_supported':wrong_answer_support,
        'correct_answer_but_incomplete_citations_marked_supported':bool(false_support and old['answer_correct'] is True),
        'verdict_label_ambiguity':cid=='T05' and verdict=='insufficient',
        'raw_verdict_is_not_evaluation':True,'judgment_basis':reason_notes[cid],
        'source_basis':[{'id':p['id'],'source':p['source'],'text':p['text'],
                         'used_by_original':p['id'] in original['citations'],'used_by_candidate':p['id'] in candidate['citations']} for p in passages],
        'additional_review_request_seconds':record['elapsed_seconds'],
        'reviewer_note':'Codex辅助原文复核，尚未经本人逐项确认。','official_score':False}
    rows.append(row)
    original_metrics.append({'case_id':cid,'answer_correct':old['answer_correct'],**citation_grade(original['citations'])})
write('evaluations.json',{'reviewed_at':now(),'rows':rows,'generation_calls_in_evaluation':0})
old_strict=sum(r['strict_complete_success'] for r in original_metrics)
new_strict=sum(r['strict_complete_success'] for r in rows)
selection='candidate' if new_strict>old_strict else 'original'
summary={'reviewed_at':now(),'denominator':8,'answer_exactly_unchanged':sum(r['answer_exactly_unchanged'] for r in rows),
    'original_answer_correct':sum(r['answer_correct'] is True for r in original_metrics),
    'candidate_answer_correct':sum(r['candidate_answer_correct'] is True for r in rows),
    'original_necessary_citation_coverage':sum(r['necessary_coverage'] for r in original_metrics),
    'candidate_necessary_citation_coverage':sum(r['necessary_coverage'] for r in rows),
    'original_citation_support':sum(r['support_actual_answer'] for r in original_metrics),
    'candidate_citation_support':sum(r['support_actual_answer'] for r in rows),
    'original_irrelevant_reference_records':sum(bool(r['irrelevant_ids']) for r in original_metrics),
    'candidate_irrelevant_reference_records':sum(bool(r['irrelevant_ids']) for r in rows),
    'original_strict_complete_success':old_strict,'candidate_strict_complete_success':new_strict,
    'review_structure_and_id_passed':sum(r['postprocessing']['review_validation']['valid'] for r in rows),
    'reported_supported':sum(r['parsed_review'].get('verdict')=='supported' for r in rows),
    'supported_false_positives':sum(r['review_supported_false_positive'] for r in rows),
    'wrong_answer_support_false_positives':sum(r['wrong_answer_marked_supported'] for r in rows),
    'correct_answer_incomplete_citation_false_positives':sum(r['correct_answer_but_incomplete_citations_marked_supported'] for r in rows),
    'replacement_gate_applied':sum(r['postprocessing']['citation_replacement_applied'] for r in rows),
    'citations_actually_changed':sum(r['citations_actually_changed'] for r in rows),
    'selected':selection,'selection_reason':'严格成功同为1/8，答案正确同为4/8，引用实际变化0；保留原方案。',
    'supported_error_cases':[r['case_id'] for r in rows if r['review_supported_false_positive']],
    'wrong_answer_support_cases':[r['case_id'] for r in rows if r['wrong_answer_marked_supported']],
    'label_ambiguity_cases':[r['case_id'] for r in rows if r['verdict_label_ambiguity']],
    'scope':'评测后开发；旧侧历史复用。引用后处理不改变原答案，不代表推理准确率改善。',
    'reviewer_note':'Codex辅助原文复核，尚未经本人逐项确认。'}
write('evaluation-summary.json',summary)
write('derived-candidates.json',{'saved_at':now(),'items':[{'case_id':r['case_id'],'source_path':r['original_record_path'],
    'review_run_id':r['review_run_id'],'original_response':r['original_response'],'candidate_response':r['candidate_response'],
    'response_origin':r['postprocessing']['response_origin'],'not_raw_model_response':True,'answer_exactly_unchanged':True} for r in rows]})
print(json.dumps(summary,ensure_ascii=False,indent=2))
