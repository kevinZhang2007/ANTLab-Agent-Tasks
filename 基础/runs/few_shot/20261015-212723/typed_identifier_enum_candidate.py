"""按明确正文角色排除；角色不唯一或无可靠声明时保留。"""
import copy
import re
import body_identifier_enum_candidate as original
import direct_reference_candidate as business
import association_repair_candidate as extraction

WORD = r'(?<![A-Za-z0-9_])(?=[A-Za-z0-9]*[A-Za-z])(?=[A-Za-z0-9]*[0-9])[A-Za-z0-9]+(?![A-Za-z0-9_])'
VERSION_BEFORE = re.compile(r'版本(?:编号)?[\s:：]*(?P<code>'+WORD+r')')
VERSION_AFTER = re.compile(r'(?P<code>'+WORD+r')\s*版本')
OTHER_ROLE = re.compile(r'(?P<label>快照|方案|设备型号|型号|样本|用例|工单|任务|组件)(?:编号)?[\s:：]*(?P<code>'+WORD+r')')

def constrain_typed_identifiers(question, passages, original_schema):
    schema, detail = original.constrain_body_identifiers(question, passages, original_schema)
    roles = []
    for index, passage in enumerate(passages):
        text = passage['text']
        for pattern in (VERSION_BEFORE, VERSION_AFTER):
            for match in pattern.finditer(text):
                roles.append({'value': match['code'], 'category': 'version', 'object_type': 'version',
                              'passage_index': index, 'start': match.start('code'), 'end': match.end('code'),
                              'recognition_text': match.group(0), 'recognition_start': match.start(), 'recognition_end': match.end(),
                              'basis': '正文明确版本标签，不依据编号前缀。'})
        for mention in business.describe(text)['mentions']:
            if not (mention['reliable_declaration'] or mention['direct_supplement_reference']):
                continue
            roles.append({'value': mention['code'], 'category': 'business', 'object_type': mention['object_type'],
                          'passage_index': index, 'start': mention['code_start'], 'end': mention['code_end'],
                          'recognition_text': mention['statement']['text'],
                          'recognition_start': mention['statement']['start'], 'recognition_end': mention['statement']['end'],
                          'extractor_evidence': mention, 'basis': '现有业务提取器的可靠声明或直接补充指称。'})
        for match in OTHER_ROLE.finditer(text):
            roles.append({'value': match['code'], 'category': 'other', 'object_type': match['label'],
                          'passage_index': index, 'start': match.start('code'), 'end': match.end('code'),
                          'recognition_text': match.group(0), 'recognition_start': match.start(), 'recognition_end': match.end(),
                          'basis': '明确其他角色只用于保留/冲突检查，不用于排除。'})
    decisions = []
    for value in detail['values']:
        evidence = [r for r in roles if r['value'] == value]
        types = {(r['category'], r['object_type']) for r in evidence}
        # 不把不同业务标签自行归并；多个角色也保守保留。
        exclude = detail['enabled'] and len(types) == 1 and next(iter(types))[0] in ('version', 'business')
        reason = 'unique_explicit_excludable_role' if exclude else ('multiple_roles_keep' if len(types)>1 else 'unknown_or_other_role_keep')
        decisions.append({'value': value, 'excluded': exclude, 'reason': reason, 'roles': evidence})
    excluded = {d['value'] for d in decisions if d['excluded']}
    kept = [v for v in detail['values'] if v not in excluded]
    if detail['enabled']:
        schema['properties']['answer']['enum'] = kept + ['证据不足']
    return schema, {**detail, 'old_values': detail['values'], 'values': kept, 'decisions': decisions,
                    'limit': '普通未带标签提及不推断新角色；发现多个明确角色则保留，无法穷尽自然语言角色声明。'}
