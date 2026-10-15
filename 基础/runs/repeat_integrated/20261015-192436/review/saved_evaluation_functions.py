import json

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
