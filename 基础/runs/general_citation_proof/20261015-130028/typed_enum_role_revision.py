"""只在所有可靠角色明确非目标、无未知或冲突时排除正文编号。"""
import copy
import re
import typed_identifier_enum_candidate as prior

UNKNOWN_ROLE = re.compile(r'(?P<label>对象|记录|编号)[\s:：]*(?P<code>'+prior.WORD+r')')
BUSINESS_TARGETS = {'批次':'batch', '评审':'review', '表':'table', '清单':'list',
                    '组':'group', '集':'collection', '主测':'test', '组代号':'group_code'}

def target_role(question):
    match = re.search(r'只输出(?P<target>[一-鿿]{1,12})编号[。.!！\s]*$', question)
    if not match:
        return None
    label = match['target']
    if label == '版本':
        return ('version', 'version')
    if label in ('快照', '方案', '设备型号', '型号', '样本', '用例', '工单', '任务', '组件'):
        return ('other', label)
    if label in BUSINESS_TARGETS:
        return ('business', BUSINESS_TARGETS[label])
    return None

def constrain_revised_roles(question, passages, original_schema):
    _, old = prior.constrain_typed_identifiers(question, passages, original_schema)
    schema = copy.deepcopy(original_schema)
    target = target_role(question)
    roles = [copy.deepcopy(r) for d in old['decisions'] for r in d['roles']]
    for index, passage in enumerate(passages):
        text = passage['text']
        known = [r for r in roles if r['passage_index'] == index]
        for match in UNKNOWN_ROLE.finditer(text):
            # “版本编号/快照编号”等已确定类型的标签内匹配不另造未知角色。
            if any(r['recognition_start'] <= match.start() and r['recognition_end'] >= match.end()
                   and r['start'] == match.start('code') and r['end'] == match.end('code') for r in known):
                continue
            roles.append({'value':match['code'], 'category':'unknown', 'object_type':match['label'],
                          'passage_index':index, 'start':match.start('code'), 'end':match.end('code'),
                          'recognition_text':match.group(0), 'recognition_start':match.start(), 'recognition_end':match.end(),
                          'basis':'只声明泛称对象/记录/编号，不能可靠区分目标类型。'})
        for mention in prior.business.describe(text)['mentions']:
            if mention['reliable_declaration'] or mention['direct_supplement_reference']:
                continue
            roles.append({'value':mention['code'], 'category':'unknown', 'object_type':mention['object_type'],
                          'passage_index':index, 'start':mention['code_start'], 'end':mention['code_end'],
                          'recognition_text':mention['statement']['text'],
                          'recognition_start':mention['statement']['start'], 'recognition_end':mention['statement']['end'],
                          'basis':'业务标签提及未形成现有提取器认可的可靠声明或直接补充指称。'})
    decisions=[]
    for value in old['old_values']:
        evidence=[r for r in roles if r['value']==value]
        target_present=bool(target and any((r['category'],r['object_type'])==target for r in evidence))
        unknown=not evidence or any(r['category']=='unknown' for r in evidence)
        conflicts=[{'passage_index':r['passage_index'], 'text':m.group(0)} for r in evidence
                   for m in prior.business.RELATION_CONFLICT.finditer(r['recognition_text'])]
        all_non_target=bool(target and evidence and all(r['category'] in ('version','business')
                        and (r['category'],r['object_type'])!=target for r in evidence))
        exclude=bool(old['enabled'] and all_non_target and not target_present and not unknown and not conflicts)
        reason=('all_reliable_roles_explicitly_non_target' if exclude else
                'target_role_keep' if target_present else 'unknown_role_keep' if unknown or target is None else
                'explicit_semantic_conflict_keep' if conflicts else 'not_proven_non_target_keep')
        decisions.append({'value':value,'excluded':exclude,'reason':reason,'target_role':target,
                          'roles':evidence,'semantic_conflicts':conflicts})
    removed={d['value'] for d in decisions if d['excluded']}
    values=[v for v in old['old_values'] if v not in removed]
    if old['enabled']:
        schema['properties']['answer']['enum']=values+['证据不足']
    return schema, {**old,'values':values,'target_role':target,'decisions':decisions,
                    'limit':'规则仅识别已保存的有限明确声明；不保证穷尽语义冲突。普通无标签复述不推断角色。'}
