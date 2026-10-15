"""独立离线资格证明；原答案不变，引用派生明确标为local_rule。"""
import copy
import json
import re
import direct_reference_candidate as relation
import explicit_state_checker as state_checker
import eligibility_exclusion_candidate as exclusion
from scope_first_occurrences import audit_occurrences
from typed_enum_role_revision import constrain_revised_roles

NUMBER = r'(?:[0-9]+|[零〇一二两三四五六七八九十]+)'
PASS_REQUIREMENT = re.compile(r'(?P<items>[一-鿿、，,和及\s]+?)(?:(?P<count>'+NUMBER+r')项)?检查全部通过')
BAN_REQUIREMENT = re.compile(r'(?:不存在|禁止|不得存在)(?P<item>[一-鿿]+)')
AGGREGATE_PASS = re.compile(r'\s*(?P<claim>(?P<count>'+NUMBER+r')项检查(?:全部)?通过)\s*[。；;]*\s*')
DECLARED_SET = re.compile(r'(?:检查集合|检查清单|检查项目)(?:为|是|[:：=])(?P<items>[^。；;\n]+)')


def evidence(passage, start, end, role):
    return {'passage_id': passage['id'], 'source': passage['source'], 'start': start,
            'end': end, 'quote': passage['text'][start:end], 'role': role}


def split_items(text):
    return [i.strip() for i in re.split(r'[、，,]|和|及', text) if i.strip()]


def requirements(passage):
    found = list(exclusion.RULE.finditer(passage['text']))
    if len(found) != 1:
        return [], {'reason': 'zero_or_multiple_rule_statements'}
    raw = found[0]
    spans = []
    begin = 0
    for separator in re.finditer(r'[，,]?且', raw['body']):
        spans.append((begin, separator.start()))
        begin = separator.end()
    spans.append((begin, len(raw['body'])))
    conditions = []
    for left, right in spans:
        body = raw['body'][left:right].strip()
        if not body:
            continue
        start = raw.start('body')+left
        while start < raw.start('body')+right and passage['text'][start].isspace():
            start += 1
        end = raw.start('body')+right
        passed = PASS_REQUIREMENT.fullmatch(body)
        banned = BAN_REQUIREMENT.fullmatch(body)
        if passed and not exclusion.ANAPHORA.search(passed['items']):
            items = split_items(passed['items'])
            declared_count = state_checker.parse_integer(passed['count']) if passed['count'] else len(items)
            reliable = bool(items and len(items) == len(set(items)) and declared_count == len(items))
            for item in items:
                conditions.append({'kind': 'required_pass', 'name': item, 'status': 'unknown',
                    'rule': evidence(passage, start, end, '发布必检条件'),
                    'defined_check_set': items, 'defined_count': declared_count,
                    'collection_definition_reliable': reliable, 'evidence': []})
        elif banned:
            conditions.append({'kind': 'forbidden_state', 'name': banned['item'], 'status': 'unknown',
                'rule': evidence(passage, start, end, '发布禁止条件'), 'evidence': []})
        else:
            conditions.append({'kind': 'unparsed_requirement', 'name': body, 'status': 'unknown',
                'rule': evidence(passage, start, end, '未解析发布条件'), 'evidence': []})
    return conditions, {'rule': evidence(passage, raw.start(), raw.end(), '完整发布规则')}


def prove_answer(question, passages, raw_answer_json, universe=None):
    untouched = copy.deepcopy((question, passages, raw_answer_json, universe))
    result = {'run_kind': 'offline_proof', 'judgment_source': 'local_rule',
              'raw_response': raw_answer_json, 'proof_established': False, 'proof_status': 'unknown',
              'conditions': [], 'final_response': None,
              'no_exclusion_as_positive_proof': True,
              'requires_independent_original_text_review': True}
    try:
        raw = json.loads(raw_answer_json)
    except (ValueError, TypeError):
        result['reason'] = 'invalid_original_answer_json'
        return result
    if not isinstance(raw, dict) or set(raw) != {'answer', 'citations'} or not isinstance(raw['answer'], str):
        result['reason'] = 'invalid_original_answer_structure'
        return result
    answer = raw['answer']
    result['answer_unchanged'] = answer
    original = copy.deepcopy(passages if universe is None else universe)
    view, occurrence_audit, scope_audit = audit_occurrences(question, original, [answer], {p['id'] for p in passages})
    result.update(scope_audit=scope_audit, occurrence_audit=occurrence_audit)
    if answer not in occurrence_audit or not occurrence_audit[answer]['eligible_for_exclusion_check']:
        result['reason'] = 'answer_identity_or_scope_not_reliably_confirmed'
        return result
    targets = occurrence_audit[answer]['target_occurrences']
    source = next((p for p in view if p['id'] in {o['passage_id'] for o in targets} and p['id'] in {v['id'] for v in passages}), None)
    if source is None:
        result['reason'] = 'selected_candidate_source_not_in_actual_final_input'
        return result
    _, type_info = constrain_revised_roles(question, passages, {'type': 'object', 'properties': {'answer': {'type': 'string'}, 'citations': {'type': 'array', 'items': {'type': 'string'}}}})
    values = list(dict.fromkeys(type_info['values']+[answer]))
    candidates = []
    for value in values:
        locations = []
        for index, passage in enumerate(view):
            for match in re.finditer(r'(?<![A-Za-z0-9_-])'+re.escape(value)+r'(?![A-Za-z0-9_-])', passage['text']):
                locations.append({'passage_id': passage['id'], 'passage_index': index, 'start': match.start(), 'end': match.end()})
        if locations:
            candidates.append({'snapshot': value, 'sources': locations})
    states = state_checker.inspect_explicit_states(view, candidates)
    chosen = [s for s in states if s['snapshot'] == answer and s['passage_id'] == source['id']]
    if len(chosen) != 1 or chosen[0].get('association_reason'):
        result['reason'] = 'candidate_description_ownership_unknown'
        return result
    state = chosen[0]
    result['candidate_description'] = evidence(source, state['start'], state['end'], '实际获选候选描述')
    result['explicit_state'] = state
    _, traces = relation.complete_passages(question, view, {'valid': True, 'selected_ids': [source['id']]})
    links = [t for t in traces if t.get('target_id') == source['id'] and t['reason'] == 'unique_reliable_direct_reference'
             and t['supplement_id'] in {p['id'] for p in passages}]
    result['rule_relationships'] = links
    if len(links) != 1:
        result['reason'] = 'zero_or_multiple_unique_visible_release_rules'
        return result
    rule_source = next(p for p in view if p['id'] == links[0]['supplement_id'])
    conditions, rule_info = requirements(rule_source)
    result.update(conditions=conditions, rule_info=rule_info)
    required = [c for c in conditions if c['kind'] == 'required_pass']
    defined_set = required[0]['defined_check_set'] if required else []
    description = source['text'][state['candidate_end']:state['end']]
    aggregate = AGGREGATE_PASS.fullmatch(description)
    count = state_checker.parse_integer(aggregate['count']) if aggregate else None
    inventories = [{'items': split_items(m['items']), 'evidence': evidence(source, m.start(), m.end(), '主记录明示检查集合')}
                   for m in DECLARED_SET.finditer(source['text'])]
    inventories_agree = all(set(i['items']) == set(defined_set) for i in inventories)
    group_supported = bool(aggregate and required and all(c['collection_definition_reliable'] for c in required)
        and count == len(defined_set) and inventories_agree and all(e['status'] == 'explicit_pass' for e in state['events']))
    result['aggregate_check_set_binding'] = {'accepted': group_supported, 'candidate_count': count,
        'defined_set': defined_set, 'main_record_inventories': inventories,
        'basis': '获选候选自身明示完整数量通过；唯一同业务记录直接发布规则定义唯一同数量检查集合；已有明示集合不能不同。不是数量相等单独证明，也不使用其他候选的失败。',
        'limit': '有限文本指称解释；仍需原文人工核对，不保证发现所有隐含的其他集合。'}
    for condition in conditions:
        evidence_items = []
        observed = []
        if condition['kind'] == 'required_pass' and group_supported:
            begin = state['candidate_end']+aggregate.start('claim');end = state['candidate_end']+aggregate.end('claim')
            observed.append('pass')
            evidence_items.append(evidence(source, begin, end, '获选候选自身数量通过；承接唯一规则检查集合'))
        for event in state['events']:
            name = exclusion.check_name(event, source['text'])
            if condition['kind'] == 'required_pass' and name == condition['name']:
                if event['status'] == 'explicit_pass':observed.append('pass')
                elif event['status'] == 'explicit_defect':observed.append('fail')
                else:observed.append('unknown')
            elif condition['kind'] == 'forbidden_state' and event['trigger'] == condition['name']:
                if event['status'] == 'explicit_absence':observed.append('pass')
                elif event['status'] == 'explicit_defect':observed.append('fail')
                else:observed.append('unknown')
            else:
                continue
            evidence_items.append(evidence(source, event['description_start'], event['description_end'], '获选候选明示检查状态'))
        if 'pass' in observed and 'fail' in observed:
            condition['status'] = 'conflict'
        elif 'fail' in observed:condition['status'] = 'fail'
        elif observed and all(s == 'pass' for s in observed):condition['status'] = 'pass'
        else:condition['status'] = 'unknown'
        condition['evidence'] = evidence_items
    established = bool(conditions and all(c['status'] == 'pass' for c in conditions))
    result['proof_established'] = established
    result['proof_status'] = 'established' if established else 'failed' if any(c['status'] in {'fail','conflict'} for c in conditions) else 'unknown'
    if established:
        ids = {e['passage_id'] for c in conditions for e in c['evidence']}
        ids.update(c['rule']['passage_id'] for c in conditions)
        citations = [p['id'] for p in passages if p['id'] in ids]
        result['final_response'] = {'answer': answer, 'citations': citations}
        result['derived_response_kind'] = 'local_rule_citation_assembly_not_raw_model_output'
        assert result['final_response']['answer'] == raw['answer']
    else:
        result['reason'] = 'not_all_necessary_conditions_reliably_proved'
    assert (question, passages, raw_answer_json, universe) == untouched
    return result
