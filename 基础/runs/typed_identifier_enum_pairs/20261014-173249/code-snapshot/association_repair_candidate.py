"""独立声明提取候选；跨类型编号不自动视为同一业务对象。"""
import copy
import re
import two_step_candidate as selection
import two_step_linked_candidate as original

# 通用对象后缀，不枚举项目、题目或具体编号。
OBJECT = r'[一-鿿]{0,12}(?:组代号|批次(?:代号|编号)?|主测|评审|清单|表|集|组)'
IDENTIFIER = re.compile(r'(?P<label>' + OBJECT + r')\s*(?P<code>[A-Za-z]+[0-9]+)(?![A-Za-z0-9_-])')
SUPPLEMENT = r'(?:复核)?(?:补页|补充页|补充记录|补充说明|续页)'
DECLARATION = re.compile(r'\s*的?\s*(?:记录|显示|固定|列出|列明|有|包含|登记|统计|保存|给出|采用|使用|收录|执行|处理|完成)|\s*(?:经|通过)[^。；\n]{0,60}(?:完成|执行|处理|记录|统计)')


def object_name(label):
    # 去掉声明连接词和范围前缀；原label和原句仍保留供核验。
    label = re.sub(r'^.*项目', '', label)
    label = re.sub(r'^(?:版本|的记录|对应|指向|参见|用于|上述|前述|该|本)+', '', label)
    for ending, kind in [('组代号','group_code'),('批次代号','batch'),('批次编号','batch'),
                         ('批次','batch'),('主测','test'),('评审','review'),('清单','list'),
                         ('表','table'),('集','collection'),('组','group')]:
        if label.endswith(ending):
            name = ending if kind in ('batch','test','group_code') else label
            return kind, name
    raise ValueError('unrecognized_object_suffix')


def statement(text, start, end):
    separators = '。！？；;\n'
    left = max((text.rfind(c, 0, start) for c in separators), default=-1) + 1
    right = min((p for c in separators if (p := text.find(c, end)) >= 0), default=len(text))
    if right < len(text):
        right += 1
    return {'text': text[left:right], 'start': left, 'end': right}


def describe(text):
    mentions = []
    for match in IDENTIFIER.finditer(text):
        kind, name = object_name(match['label'])
        tail = text[match.end():]
        ref = re.match(r'\s*的?\s*' + SUPPLEMENT, tail)
        prefix = text[max(0, match.start()-24):match.end('label')]
        bridge = bool(re.search(r'(?:对应|指向|参见)\s*' + re.escape(match['label'].removeprefix('对应').removeprefix('指向').removeprefix('参见')) + r'$', prefix))
        # 已验证批次等声明保留原语境要求；新对象须有声明谓词或明确补页指称。
        declared = bool(ref or bridge or DECLARATION.match(tail) or kind in ('batch','test','group_code'))
        row = {'object_type':kind,'object_name':name,'raw_label':match['label'],
               'code':match['code'],'start':match.start(),'end':match.end(),
               'code_start':match.start('code'),'code_end':match.end('code'),
               'statement':statement(text,match.start(),match.end()),
               'declared':declared,'supplement_reference':bool(ref),'explicit_bridge':bridge}
        mentions.append(row)
    _, scope, legacy_supplemental = original.linked.passage_context(text)
    return {'mentions':mentions,'declarations':[m for m in mentions if m['declared']],
            'references':[m for m in mentions if m['supplement_reference']],
            'bridges':[m for m in mentions if m['explicit_bridge']],
            'scope':{k:sorted(v) for k,v in zip(('project','version','date'),scope)},
            'supplemental':legacy_supplemental}


def complete_passages(question, passages, validation):
    selected = selection.select_original_passages(passages, validation)
    seeds = {p['id'] for p in selected}
    included = set(seeds)
    contexts = [describe(p['text']) for p in passages]
    trace = []
    for passage, context in zip(passages, contexts):
        if not context['supplemental']:
            continue
        refs = context['references']
        row = {'supplement_id':passage['id'],'target_id':None,'added':False,
               'reference_evidence':refs,'candidate_target_ids':[],
               'unknown_scope_fields':[],'semantic_support_verified':False}
        objects = {(m['object_type'],m['object_name'],m['code']) for m in refs}
        if not objects:
            row['reason']='no_explicit_reference'
        elif len(objects)!=1:
            row['reason']='multiple_reference_objects'
        else:
            ref = refs[0]
            codes = {m['code'] for m in context['declarations']}
            possible = [(p,c) for p,c in zip(passages,contexts) if not c['supplemental']
                        and any(m['code']==ref['code'] for m in c['declarations'])]
            row['candidate_target_ids']=[p['id'] for p,c in possible]
            if len(codes)>1:
                row['reason']='multiple_supplement_objects'
            elif not possible:
                row['reason']='zero_targets'
            elif len(possible)>1:
                row['reason']='multiple_targets'
            else:
                target, other = possible[0]
                row['target_declarations']=other['declarations']
                scopes = [context['scope'],other['scope']]
                row['unknown_scope_fields']=[k for k in scopes[0] if not scopes[0][k] or not scopes[1][k]]
                identities={(m['object_type'],m['object_name'],m['code']) for m in other['declarations']}
                if any(len(v)>1 for s in scopes for v in s.values()):
                    row['reason']='multiple_scopes'
                elif len(identities)>1:
                    row['reason']='multiple_main_objects'
                elif any(scopes[0][k] and scopes[1][k] and scopes[0][k]!=scopes[1][k] for k in scopes[0]):
                    row['reason']='scope_conflict'
                else:
                    declared = other['declarations'][0]
                    same = (ref['object_type'],ref['object_name'])==(declared['object_type'],declared['object_name'])
                    # 跨类型必须在同一补充指称句中明示对应的目标对象。
                    bridges=[m for m in context['bridges'] if m['code']==ref['code']
                             and (m['object_type'],m['object_name'])==(declared['object_type'],declared['object_name'])
                             and m['statement']['start']==ref['statement']['start']]
                    if not same and not bridges:
                        row['reason']='cross_type_or_name_without_explicit_bridge'
                    else:
                        row.update(target_id=target['id'],reason='unique_direct_reference',
                                   bridge_evidence=bridges,same_object_type_and_name=same)
                        if target['id'] in seeds and passage['id'] not in seeds:
                            included.add(passage['id']);row['added']=True
                        elif passage['id'] in seeds:
                            row['completion_reason']='already_selected'
                        else:
                            row['completion_reason']='target_not_original_seed_no_multihop'
        trace.append(row)
    return [copy.deepcopy(p) for p in passages if p['id'] in included], trace
