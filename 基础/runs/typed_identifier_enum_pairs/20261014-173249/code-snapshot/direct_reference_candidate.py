"""唯一可靠声明与直接完整编号指称；类型标签仅作记录，不当身份判据。"""
import copy
import re
import association_repair_candidate as extraction
import two_step_candidate as selection

IDENTIFIER = re.compile(r'(?P<label>'+extraction.OBJECT+r')\s*(?P<code>[A-Za-z]+[0-9]+(?:[-_][A-Za-z0-9]+)*)(?![A-Za-z0-9_-])')
OWNED_RECORD = re.compile(r'\s*的[一-鿿]{1,16}?(?:记录|显示|固定|列明|采用|使用|执行|处理|完成|包含|统计)')
REFERENCE_PREFIX = re.compile(r'提及|提到|引用|参考|参见|涉及')
NAMESPACE = re.compile(r'(?:编号命名空间|命名空间|编号域|编号体系)\s*[:：=]\s*([一-鿿A-Za-z0-9_.-]+)')
RELATION_CONFLICT = re.compile(
    r'(?:不是|并非|不对应|不属于)\s*(?:该|上述|前述|同一|主|原)(?:业务|主)?(?:对象|记录|批次|表|清单|评审|组|项目)'
    r'|(?:另一个|另一|不同的|独立的)(?:业务)?对象|另一项目'
    r'|与[^。；\n]{0,20}(?:主记录|主对象)[^。；\n]{0,8}无关'
    r'|编号(?:相同|一样)但(?:对象|命名空间)不同')


def describe(text):
    mentions=[]
    for match in IDENTIFIER.finditer(text):
        kind,name=extraction.object_name(match['label'])
        tail=text[match.end():]
        direct=re.match(r'\s*的?\s*'+extraction.SUPPLEMENT,tail)
        predicate=extraction.DECLARATION.match(tail) or OWNED_RECORD.match(tail)
        prefix=text[max(0,match.start()-16):match.end('label')]
        mere_reference=bool(REFERENCE_PREFIX.search(prefix))
        reliable=bool(predicate and not direct and not mere_reference)
        mentions.append({'object_type':kind,'object_name':name,'raw_label':match['label'],
            'code':match['code'],'start':match.start(),'end':match.end(),
            'code_start':match.start('code'),'code_end':match.end('code'),
            'statement':extraction.statement(text,match.start(),match.end()),
            'reliable_declaration':reliable,'direct_supplement_reference':bool(direct),
            'mere_reference':mere_reference,
            'declaration_predicate':None if not predicate else {
                'text':predicate.group(0),'start':match.end()+predicate.start(),'end':match.end()+predicate.end()}})
    scope=copy.deepcopy(extraction.describe(text)['scope'])
    scope['namespace']=sorted(set(NAMESPACE.findall(text)))
    return {'mentions':mentions,'declarations':[m for m in mentions if m['reliable_declaration']],
        'references':[m for m in mentions if m['direct_supplement_reference']],
        'scope':scope,'supplemental':bool(re.search(extraction.SUPPLEMENT,text)),
        'explicit_relation_conflicts':[m.group(0) for m in RELATION_CONFLICT.finditer(text)]}


def complete_passages(question,passages,validation):
    seeds={p['id'] for p in selection.select_original_passages(passages,validation)}
    included=set(seeds)
    contexts=[describe(p['text']) for p in passages]
    decisions=[]
    for passage,context in zip(passages,contexts):
        if not context['supplemental']:
            continue
        refs=context['references']
        row={'supplement_id':passage['id'],'target_id':None,'added':False,
             'reference_evidence':refs,'candidate_target_ids':[],
             'unknown_scope_fields':[],'semantic_support_verified':False}
        identities={(r['object_type'],r['object_name'],r['code']) for r in refs}
        if not identities:
            row['reason']='no_direct_business_reference'
        elif len(identities)>1:
            row['reason']='multiple_reference_objects'
        elif len({m['code'] for m in context['mentions']})>1:
            row['reason']='multiple_supplement_identifiers'
        elif context['explicit_relation_conflicts']:
            row.update(reason='explicit_relation_conflict',conflict_evidence=context['explicit_relation_conflicts'])
        else:
            ref=refs[0]
            possible=[(p,c) for p,c in zip(passages,contexts) if not c['supplemental']
                      and any(d['code']==ref['code'] for d in c['declarations'])]
            row['candidate_target_ids']=[p['id'] for p,c in possible]
            if not possible:
                row['reason']='zero_reliable_targets'
            elif len(possible)>1:
                row['reason']='multiple_reliable_targets'
            else:
                target,other=possible[0]
                declarations=other['declarations']
                scope=context['scope'];other_scope=other['scope']
                row.update(target_declarations=declarations,
                    unknown_scope_fields=[k for k in scope if not scope[k] or not other_scope[k]])
                if len({(d['object_type'],d['object_name'],d['code']) for d in declarations})>1:
                    row['reason']='multiple_main_objects'
                elif any(len(values)>1 for s in (scope,other_scope) for values in s.values()):
                    row['reason']='multiple_scopes_or_namespaces'
                elif any(scope[k] and other_scope[k] and scope[k]!=other_scope[k] for k in scope):
                    row['reason']='scope_or_namespace_conflict'
                elif other['explicit_relation_conflicts']:
                    row.update(reason='explicit_relation_conflict',conflict_evidence=other['explicit_relation_conflicts'])
                else:
                    declared=next(d for d in declarations if d['code']==ref['code'])
                    row.update(target_id=target['id'],reason='unique_reliable_direct_reference',
                        object_labels_equal=(ref['object_type'],ref['object_name'])==(declared['object_type'],declared['object_name']),
                        identity_basis='完整编号直接補充指称+全输入唯一可靠声明+无明示冲突；不是仅按类型或编号相等。')
                    if target['id'] in seeds and passage['id'] not in seeds:
                        included.add(passage['id']);row['added']=True
                    elif passage['id'] in seeds:
                        row['completion_reason']='already_selected'
                    else:
                        row['completion_reason']='target_not_original_seed_no_multihop'
        decisions.append(row)
    return [copy.deepcopy(p) for p in passages if p['id'] in included],decisions
