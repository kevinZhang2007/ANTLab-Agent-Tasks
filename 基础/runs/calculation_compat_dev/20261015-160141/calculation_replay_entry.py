"""冻结候选的纯离线后处理；不定位、不调用生成、不修改原响应。"""
import copy, json, time
import general_citation_proof as reference
import ratio_calculation_proof as ratio
import difference_calculation_proposal as difference
from proof_pipeline_candidate import position_records

def replay(task):
    before=copy.deepcopy(task);started=time.perf_counter()
    question=task['question'];passages=task['used_passages'];raw=task['raw_answer'];original=task['original_passages']
    proof=reference.prove_answer(question,passages,raw,original)
    rp=ratio.propose(question,passages,raw,original)
    dp=difference.propose(question,passages,raw,original)
    assert not(rp['proposed_response'] is not None and dp['proposed_response'] is not None)
    suggestion=dp['proposed_response'] if dp['proposed_response'] is not None else rp['proposed_response']
    final=copy.deepcopy(suggestion if suggestion is not None else proof['derived_response'] if proof['derived_response'] is not None else json.loads(raw))
    source=('local_rule_difference_new_answer' if dp['proposed_response'] else 'local_rule_ratio_new_answer' if rp['proposed_response'] else
        'local_rule_citation_assembly' if proof['derived_response'] else 'raw_model_response')
    parsed=json.loads(raw)
    if proof['derived_response'] is not None:assert proof['derived_response']['answer']==parsed['answer']
    needed={p['id']:p['text'] for p in passages}
    diff_facts=position_records([v for v in dp['trace'] if v.get('stage')=='difference_proof'])
    ratio_facts=position_records({k:rp[k] for k in ['definition','denominator','category_counts','statistical_scope','category_assignment','numerator'] if k in rp})
    for source_record in diff_facts+ratio_facts:
        assert source_record['passage_id'] in needed and needed[source_record['passage_id']][source_record['start']:source_record['end']]==source_record['quote']
    for response in [suggestion,proof['derived_response']]:
        if response is not None:assert set(response['citations'])<=needed.keys()
    assert task==before
    return {'run_kind':'offline_saved_input_replay','raw_response':copy.deepcopy(task['raw_response']),'raw_answer':raw,
        'reference_proof':proof,'reference_derived_response':proof['derived_response'],'ratio_proof':rp,'difference_proposal':dp,
        'proposed_response':copy.deepcopy(suggestion),'actual_final_output':final,'output_source':source,
        'answer_changed':final['answer']!=parsed['answer'],'difference_fact_sources':diff_facts,'ratio_fact_sources':ratio_facts,
        'material_scope':copy.deepcopy(task['material_scope']),'elapsed_offline_seconds':time.perf_counter()-started,
        'generation_calls':0,'policy':'计算建议可改答案但不覆盖模型原响应；引用证明只能改引用；不适用/拒绝时保留原答。'}
