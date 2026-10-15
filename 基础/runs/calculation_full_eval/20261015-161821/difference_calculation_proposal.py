"""独立差值计算建议；先从原文确定运算，不修改模型原答或引用证明。"""
import copy, json
import general_citation_proof as shared

def propose(question,passages,raw_answer_json,universe=None):
    before=copy.deepcopy((question,passages,raw_answer_json,universe))
    result={'run_kind':'offline_difference_calculation_proposal','judgment_source':'local_rule',
        'applicable':False,'status':'not_applicable','proof_established':False,'trace':[],
        'proposed_response':None,'answer_changed':False,'not_original_model_response':True}
    try:
        if not shared.DIFFERENCE.search(question):
            result['reason']='question_does_not_request_supported_difference';return result
        result.update(applicable=True,status='unknown')
        # 运算函数不接收原answer；操作数、范围、指标、方向和唯一性检查全部沿用。
        expected,ids=shared.difference(question,passages,passages if universe is None else universe,result['trace'])
        raw=json.loads(raw_answer_json)
        shared.require(isinstance(raw,dict) and set(raw)=={'answer','citations'} and isinstance(raw['answer'],str)
            and isinstance(raw['citations'],list) and all(isinstance(i,str) for i in raw['citations']),'invalid_original_answer')
        needed=set(ids);shared.require(needed<={p['id'] for p in passages},'fact_or_citation_outside_final_input')
        proposal={'answer':expected,'citations':[p['id'] for p in passages if p['id'] in needed]}
        result.update(proof_established=True,status='established',reason='original_operands_unit_metric_scope_direction_and_result_independently_calculated',
            proposed_response=proposal,original_answer=raw['answer'],answer_changed=expected!=raw['answer'],
            proposed_response_kind='local_rule_calculated_new_answer_not_model_output')
    except shared.Refuse as error:result.update(status='refused',reason=str(error),proposed_response=None)
    finally:assert (question,passages,raw_answer_json,universe)==before
    return result
