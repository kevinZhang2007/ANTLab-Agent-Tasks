"""有限资格排除：文字对应与唯一直接补充关系成立才排除，不判断剩余项合格。"""
import copy
import re
import direct_reference_candidate as relation

RULE = re.compile(r'规则要求(?P<body>[^。；;\n]+)')
PASS_RULE = re.compile(r'(?P<items>[一-鿿、，,和及\s]+?)(?:[0-9零〇一二两三四五六七八九十]+项)?检查全部通过')
FORBID = re.compile(r'(?:不存在|禁止|不得存在)(?P<item>[^，,。；;\n]+)')
ANAPHORA = re.compile(r'上述|前述|这些|该项|其余|对应|同一|全部上述')


def parse_rules(passage):
    rules = []
    for match in RULE.finditer(passage['text']):
        body = match['body'].strip()
        passed = PASS_RULE.fullmatch(body)
        explicit_items = []
        if passed and not ANAPHORA.search(passed['items']):
            explicit_items = [i.strip() for i in re.split(r'[、，,]|和|及', passed['items']) if i.strip()]
        forbidden = []
        for ban in FORBID.finditer(body):
            forbidden.append({'name': ban['item'].strip(), 'raw': ban.group(),
                              'start': match.start('body')+ban.start(), 'end': match.start('body')+ban.end()})
        rules.append({'passage_id': passage['id'], 'start': match.start(), 'end': match.end(),
                      'quote': match.group(), 'required_pass_items': explicit_items,
                      'forbidden_literals': forbidden,
                      'unresolved_required_checks': not bool(explicit_items),
                      'limit': '不解析上述指代，不推断完成等于通过，不作同义词映射。'})
    return rules


def check_name(event, passage_text):
    left = event['description_start']
    end = event['trigger_start']
    prefix = passage_text[left:end]
    for quantity in sorted(event['quantity_scope'], key=lambda q:q['start'], reverse=True):
        if left <= quantity['start'] <= quantity['end'] <= end:
            prefix = prefix[:quantity['start']-left]+prefix[quantity['end']-left:]
    # 仅删除语法性描述，不把业务名称变成另一个检查名称。
    prefix = re.sub(r'^(?:有|存在)\s*', '', prefix).strip()
    prefix = re.sub(r'检查$', '', prefix).strip()
    return prefix if re.fullmatch(r'[一-鿿]{1,16}', prefix) else None


def constrain_eligibility(question, passages, type_enum, states):
    original = copy.deepcopy((question, passages, type_enum, states))
    decisions = []
    unresolved = []
    for state in states:
        source = passages[state['passage_index']]
        _, traces = relation.complete_passages(question, passages,
                    {'valid': True, 'selected_ids': [source['id']]})
        links = [t for t in traces if t.get('target_id') == source['id'] and
                 t['reason'] == 'unique_reliable_direct_reference']
        row = {'candidate': state['snapshot'], 'description': state['quote'],
               'passage_id': source['id'], 'start': state['start'], 'end': state['end'],
               'excluded': False, 'eligibility': 'unknown', 'relations': links,
               'rule_evidence': [], 'matches': [], 'unmatched_defects': [],
               'remaining_does_not_mean_eligible': True}
        for link in links:
            supplement = next(p for p in passages if p['id'] == link['supplement_id'])
            rules = parse_rules(supplement)
            row['rule_evidence'].extend(rules)
            # 多规则可能条件不同，不选择其中有利的一条。
            if len(rules) != 1:
                unresolved.append({'candidate': state['snapshot'], 'reason': 'zero_or_multiple_rules'})
                continue
            rule = rules[0]
            if rule['unresolved_required_checks']:
                unresolved.append({'candidate': state['snapshot'], 'reason': 'required_checks_not_explicitly_enumerated',
                                   'rule': rule})
            for event in state['events']:
                if event['status'] != 'explicit_defect':
                    continue
                name = check_name(event, source['text'])
                required = name in rule['required_pass_items'] if name else False
                ban = next((b for b in rule['forbidden_literals'] if b['name'] == event['trigger']), None)
                evidence = {'event': event, 'derived_check_name': name, 'rule': rule,
                            'scope_basis': '全输入唯一可靠主声明与完整编号直接补页指称；明示范围冲突由原关联器拒绝。缺失字段仍登记unknown，不当作相等。',
                            'relation': link}
                if required or ban:
                    row['matches'].append({**evidence, 'matching_basis': 'exact_check_name' if required else 'exact_forbidden_literal',
                                           'reason': '该项明确缺陷与同范围发布规则明示必检项/禁止缺陷逐字对应。'})
                    row['excluded'] = True
                else:
                    row['unmatched_defects'].append({**evidence, 'reason': '检查名称或禁止缺陷未能逐字对应；不添加同义关系。'})
        if row['excluded']:
            row['eligibility'] = 'explicit_violation_of_identified_requirement'
        row['reason'] = ('reliably_identified_required_check_violation' if row['excluded'] else
                         'unknown_keep_no_reliable_rule_link' if not links else 'unknown_keep_no_reliable_violation_match')
        decisions.append(row)
    excluded = {d['candidate'] for d in decisions if d['excluded']}
    values = [v for v in type_enum if v != '证据不足' and v not in excluded]+['证据不足']
    assert (question, passages, type_enum, states) == original
    return {'original_enum': type_enum, 'answer_enum': values, 'changed': values != type_enum,
            'decisions': decisions, 'unresolved_rules': unresolved,
            'needs_manual_correspondence': bool(unresolved),
            'no_automatic_qualification_or_citation': True}
