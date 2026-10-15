"""有限原文语法证明；只派生引用，答案不变；不访问题库或答案文件。"""
import copy
import json
import re
from decimal import Decimal, localcontext
import direct_reference_candidate as relation
from scope_first_occurrences import explicit_scope, scope_status
from typed_enum_role_revision import target_role
import eligibility_proof_checker as snapshot

DEC=r'[+-]?[0-9]+(?:\.[0-9]+)?'
UNIT=r'(?:毫秒|分钟|小时|秒|万元|元|焦耳|条|次|个|人|GiB|MiB|GB|MB|ms|s|J|%)'
VALUE=re.compile(r'(?<![A-Za-z0-9_.])(?P<number>'+DEC+r')(?P<unit>'+UNIT+r')')
THRESHOLD=re.compile(r'(?P<metric>[一-鿿A-Za-z0-9_]+?)(?P<op>不超过|不高于|不低于|至少|至多|小于|大于|超过)(?P<number>'+DEC+r')(?P<unit>'+UNIT+r')')
DIFFERENCE=re.compile(r'(?P<left>[^，。？?]+?)的(?P<metric>[^，。？?]+?)比(?P<right>[^，。？?]+?)(?P<direction>少|多)多少(?P<unit>'+UNIT+r')[？?]')
STATISTIC=re.compile(r'中位数|平均值|均值|总数|合计')

class Refuse(ValueError):
    pass

def require(condition,reason):
    if not condition:raise Refuse(reason)

def ev(p,start,end,role):
    return {'passage_id':p['id'],'source':p['source'],'start':start,'end':end,'quote':p['text'][start:end],'role':role}

def first_sentence(p):
    end=p['text'].find('。')
    return p['text'] if end<0 else p['text'][:end]

def linked_pairs(question,passages,universe,trace):
    visible={p['id']:p for p in passages}
    require(len(visible)==len(passages),'duplicate_input_ids')
    expected=explicit_scope(question)
    require(any(expected.values()) and all(len(v)<=1 for v in expected.values()),'question_scope_missing_or_multiple')
    _,links=relation.complete_passages(question,universe,{'valid':True,'selected_ids':list(visible)})
    trace.append({'stage':'direct_relation_audit','links':links})
    pairs=[]
    for link in links:
        if link['reason']!='unique_reliable_direct_reference':continue
        if link['target_id'] not in visible or link['supplement_id'] not in visible:continue
        main,extra=visible[link['target_id']],visible[link['supplement_id']]
        status,fields=scope_status(expected,explicit_scope(main['text']))
        extra_status,extra_fields=scope_status(expected,explicit_scope(extra['text']))
        trace.append({'stage':'pair_scope','main':main['id'],'supplement':extra['id'],'main_status':status,'supplement_status':extra_status,'main_fields':fields,'supplement_fields':extra_fields})
        if status!='matched' or extra_status=='conflict':continue
        pairs.append((main,extra,link))
    require(len(pairs)==1,'zero_or_multiple_unique_same_scope_visible_pairs')
    return pairs[0]

def metric_value(p,object_name,metric,short_metric,allow_short):
    text=first_sentence(p)
    require(text.count(object_name)==1,'object_not_unique_in_operand_source')
    candidates=[]
    for m in re.finditer(r'(?P<label>'+re.escape(metric)+(r'|'+re.escape(short_metric) if allow_short else '')+r')(?:为|是|[:：=])(?P<number>'+DEC+r')(?P<unit>'+UNIT+r')',text):
        # 省略完整指标时，只允许独立子句中的同统计量；其他指标修饰语不能混入。
        if m['label']!=metric:
            left=max(text.rfind(c,0,m.start()) for c in '，,；;：:')+1
            if text[left:m.start()].strip():continue
        if text.find(object_name)>m.start():continue
        candidates.append(m)
    require(len(candidates)==1,'zero_or_multiple_operand_metrics')
    m=candidates[0]
    return {'object':object_name,'metric':metric,'statistic':short_metric,'value':m['number'],'unit':m['unit'],
        'source':ev(p,m.start(),m.end(),'比较操作数原文'),'object_source':ev(p,text.find(object_name),text.find(object_name)+len(object_name),'问题比较对象')}

def difference(question,passages,universe,trace):
    matches=list(DIFFERENCE.finditer(question));require(len(matches)==1,'unsupported_difference_question')
    q=matches[0];stats=list(STATISTIC.finditer(q['metric']))
    require(len(stats)==1 and q['metric'].endswith(stats[0].group()),'statistic_not_explicit_or_ambiguous')
    main,extra,link=linked_pairs(question,passages,universe,trace)
    require(q['left']!=q['right'],'comparison_objects_not_distinct')
    # 两种对象安排均穷举，唯一性在读取answer之前确定。
    options=[]
    for left_source,right_source in [(main,extra),(extra,main)]:
        try:
            left=metric_value(left_source,q['left'],q['metric'],stats[0].group(),True)
            right=metric_value(right_source,q['right'],q['metric'],stats[0].group(),True)
            require(q['metric'] in first_sentence(main),'full_metric_definition_missing_in_main')
            require(left['unit']==right['unit']==q['unit'],'operand_or_question_units_differ')
            # 唯一补页中的“同样N个/条…”与主文相同数量，作为明确可比性依据。
            same=list(re.finditer(r'同样(?P<number>'+DEC+r')(?P<unit>个|条|次|人)',first_sentence(extra)))
            require(len(same)==1,'comparability_not_explicit')
            same=same[0]
            primary=list(re.finditer(r'(?<![A-Za-z0-9_.])'+re.escape(same['number'])+re.escape(same['unit']),first_sentence(main)))
            require(len(primary)==1,'comparability_population_not_unique')
            options.append((left,right,ev(extra,same.start(),same.end(),'同一比较集合明示依据')))
        except Refuse:
            continue
    require(len(options)==1,'zero_or_multiple_reliable_operand_assignments')
    left,right,comparable=options[0]
    with localcontext() as context:
        context.prec=80
        result=Decimal(right['value'])-Decimal(left['value']) if q['direction']=='少' else Decimal(left['value'])-Decimal(right['value'])
    trace.append({'stage':'difference_proof','question_parse':q.groupdict(),'left':left,'right':right,'comparability':comparable,
        'operation':'right_minus_left' if q['direction']=='少' else 'left_minus_right','result':str(result),'operands_chosen_without_answer':True})
    return str(result),[left['source']['passage_id'],right['source']['passage_id']]

def normalized(label,unit):
    label=label.strip().removesuffix('为').removesuffix('是')
    return label[:-1] if unit=='%' and label.endswith('率') else label

def parse_rule(extra):
    text=first_sentence(extra)
    matches=list(re.finditer(r'(?:规则|决策)(?:先)?要求(?P<body>[^。]+)',text))
    require(len(matches)==1,'zero_or_multiple_selection_rule_statements')
    match=matches[0];parts=re.split(r'[，,]再',match['body'])
    require(len(parts)==2,'selection_order_not_explicit')
    qualification,ranking=parts
    clauses=re.split(r'并且|且',qualification)
    conditions=[]
    for clause in clauses:
        m=THRESHOLD.fullmatch(clause.strip());require(m is not None,'unparsed_qualification_condition')
        conditions.append(m.groupdict())
    require(conditions and len({(c['metric'],c['unit']) for c in conditions})==len(conditions),'missing_or_duplicate_qualification')
    suffix=ranking.split('；',1)
    if len(suffix)==2:require(bool(re.fullmatch(r'[^；]+不参与第一轮筛选',suffix[1])),'unparsed_rule_suffix')
    ranking=suffix[0].strip()
    ranks=[];unresolved=False
    for part in re.split(r'[，,]再|再',ranking):
        m=re.fullmatch(r'(?:先)?(?P<op>最大化|最小化)(?P<metric>[一-鿿A-Za-z0-9_]+)',part)
        if m:ranks.append(m.groupdict())
        elif re.fullmatch(r'比较[一-鿿A-Za-z0-9_]+',part):unresolved=True
        else:raise Refuse('unparsed_decision_order')
    return {'conditions':conditions,'ranks':ranks,'ranking_direction_unknown':unresolved,'source':ev(extra,match.start(),match.end(),'资格及决策原文')}

def parse_table(main,rule,kind):
    descriptions=relation.describe(main['text'])['declarations'];require(len(descriptions)==1,'data_declaration_not_unique')
    start=descriptions[0]['declaration_predicate']['end'];end=main['text'].find('。',start)
    if end<0:end=len(main['text'])
    body=main['text'][start:end]
    segments=list(re.finditer(r'[^；;]+',body));require(len(segments)>=2,'too_few_explicit_candidates')
    rows=[];columns=[]
    field_names=[c['metric'] for c in rule['conditions']]+[r['metric'] for r in rule['ranks']]
    for row_index,segment in enumerate(segments):
        row_text=segment.group();row_offset=start+segment.start()
        chunks=list(re.finditer(r'[^、，,]+',row_text));require(chunks,'empty_candidate_row')
        parsed=[];name=None
        for column_index,chunk in enumerate(chunks):
            raw=chunk.group();numbers=list(VALUE.finditer(raw));require(len(numbers)==1,'missing_or_multiple_values_in_column')
            value=numbers[0];prefix=raw[:value.start()].strip();suffix=raw[value.end():].strip()
            if column_index==0:
                if row_index==0:
                    candidates=[]
                    for label in field_names:
                        alias=normalized(label,value['unit'])
                        if prefix.endswith(alias):candidates.append(alias)
                    aliases=sorted(set(candidates),key=len,reverse=True)
                    require(aliases,'first_column_label_not_explicit')
                    longest=aliases[0];require(not any(a!=longest and len(a)==len(longest) for a in aliases),'ambiguous_first_column_label')
                    name=prefix[:-len(longest)].strip();prefix=longest
                else:
                    aliases=columns[0]['aliases']
                    hits=[a for a in aliases if prefix.endswith(a)]
                    if hits:
                        alias=max(hits,key=len);name=prefix[:-len(alias)].strip();prefix=alias
                    else:name=prefix;prefix=''
                require(bool(re.fullmatch(r'(?:[一-鿿]{1,16}|[A-Za-z][A-Za-z0-9_-]*)',name)),'candidate_name_not_reliably_parsed')
            if row_index==0:
                labels=[normalized(s,value['unit']) for s in [prefix,suffix] if s]
                require(labels,'first_row_metric_label_missing')
                columns.append({'unit':value['unit'],'aliases':labels,'definition':ev(main,row_offset+chunk.start(),row_offset+chunk.end(),'首行字段定义')})
            else:
                require(column_index<len(columns) and value['unit']==columns[column_index]['unit'],'column_units_or_count_mismatch')
                for label in [normalized(s,value['unit']) for s in [prefix,suffix] if s]:
                    if label in columns[column_index]['aliases']:continue
                    # 后续行省略字段名只能承接同列；显式短名须唯一对应首行后缀。
                    matching=[i for i,c in enumerate(columns) if any(a.startswith(label) for a in c['aliases']) and len(label)>=2]
                    require(matching==[column_index],'explicit_field_label_conflicts_with_column')
            parsed.append({'value':value['number'],'unit':value['unit'],'source':ev(main,row_offset+chunk.start(),row_offset+chunk.end(),'候选原文数据字段')})
        require(len(parsed)==len(columns),'candidate_column_count_mismatch')
        rows.append({'name':name,'fields':parsed,'source':ev(main,row_offset,row_offset+len(row_text),'候选完整数据行')})
    require(len({r['name'] for r in rows})==len(rows),'duplicate_candidate_names')
    return rows,columns

def metric_column(label,unit,columns):
    hits=[i for i,c in enumerate(columns) if (unit is None or c['unit']==unit) and normalized(label,c['unit']) in c['aliases']]
    require(len(hits)==1,'metric_or_unit_not_uniquely_bound_to_data')
    return hits[0]

def selection(question,passages,universe,trace):
    target=re.search(r'只输出(?P<kind>流程|方案)名称[。.!！\s]*$',question)
    require(target is not None,'unsupported_selection_object_form')
    main,extra,link=linked_pairs(question,passages,universe,trace)
    rule=parse_rule(extra);rows,columns=parse_table(main,rule,target['kind'])
    trace.append({'stage':'selection_sources','rule':rule,'columns':columns,'candidates':rows})
    for row in rows:
        row['conditions']=[]
        for c in rule['conditions']:
            index=metric_column(c['metric'],c['unit'],columns);observed=Decimal(row['fields'][index]['value']);threshold=Decimal(c['number'])
            op=c['op']
            passed=observed<=threshold if op in ['不超过','不高于','至多'] else observed>=threshold if op in ['至少','不低于'] else observed<threshold if op=='小于' else observed>threshold
            row['conditions'].append({'rule':c,'actual':str(observed),'passed':passed,'source':row['fields'][index]['source']})
        row['eligible']=all(c['passed'] for c in row['conditions'])
    qualified=[r for r in rows if r['eligible']];require(qualified,'no_candidate_proven_eligible')
    decision=[]
    if len(qualified)>1:
        require(not rule['ranking_direction_unknown'] and rule['ranks'],'decision_direction_unknown_with_competitors')
        for rank in rule['ranks']:
            index=metric_column(rank['metric'],None,columns)
            values=[Decimal(r['fields'][index]['value']) for r in qualified]
            optimum=max(values) if rank['op']=='最大化' else min(values)
            qualified=[r for r in qualified if Decimal(r['fields'][index]['value'])==optimum]
            decision.append({'rank':rank,'optimum':str(optimum),'remaining_names':[r['name'] for r in qualified]})
            if len(qualified)==1:break
    require(len(qualified)==1,'unresolved_final_tie')
    winner=qualified[0]['name'];trace.append({'stage':'selection_result','qualified_before_order':[r['name'] for r in rows if r['eligible']],
        'decision_steps':decision,'winner':winner,'winner_chosen_without_answer':True,
        'unused_ranking_not_required_when_unique_eligible':len([r for r in rows if r['eligible']])==1})
    return winner,[main['id'],extra['id']],target['kind']

def prove_answer(question,passages,raw_answer_json,universe=None):
    before=copy.deepcopy((question,passages,raw_answer_json,universe))
    result={'judgment_source':'local_rule','run_kind':'offline_proof','proof_established':False,'proof_status':'not_applicable',
        'proof_kind':None,'trace':[],'derived_response':None,'requires_independent_original_text_review':True}
    try:
        raw=json.loads(raw_answer_json)
        require(isinstance(raw,dict) and set(raw)=={'answer','citations'} and isinstance(raw['answer'],str) and isinstance(raw['citations'],list) and all(isinstance(i,str) for i in raw['citations']),'invalid_raw_response')
        answer=raw['answer'];universe=copy.deepcopy(passages if universe is None else universe)
        if target_role(question)==('other','快照'):
            result['proof_kind']='snapshot';result['proof_status']='unknown'
            inherited=snapshot.prove_answer(question,passages,raw_answer_json,universe)
            result['snapshot_proof']=inherited;result['proof_status']=inherited['proof_status']
            result['reason']=inherited.get('reason','positive_snapshot_proof')
            result['proof_established']=inherited['proof_established'];result['derived_response']=inherited['final_response']
        elif DIFFERENCE.search(question):
            result.update(proof_kind='difference',proof_status='unknown')
            expected,ids=difference(question,passages,universe,result['trace'])
            require(bool(re.fullmatch(DEC,answer)) and Decimal(answer)==Decimal(expected),'original_answer_not_equal_to_proven_difference')
            result.update(proof_established=True,proof_status='established',reason='unique_same_scope_metric_unit_direction_and_decimal_result_confirmed')
            selected=set(ids);result['derived_response']={'answer':answer,'citations':[p['id'] for p in passages if p['id'] in selected]}
        elif re.search(r'只输出(?:流程|方案)名称[。.!！\s]*$',question):
            result.update(proof_kind='qualification_selection',proof_status='unknown')
            winner,ids,kind=selection(question,passages,universe,result['trace'])
            # 仅比较原文对象同一性，不改原answer的表达。
            comparable=lambda value:value[len(kind):] if value.startswith(kind) else value
            require(comparable(answer)==comparable(winner),'original_answer_not_proven_winner')
            selected=set(ids);result.update(proof_established=True,proof_status='established',reason='qualification_and_decision_order_proven',
                derived_response={'answer':answer,'citations':[p['id'] for p in passages if p['id'] in selected]})
        else:result['reason']='unsupported_question_branch_original_preserved'
        if result['derived_response'] is not None:
            require(result['derived_response']['answer']==answer,'derived_answer_changed')
            result['derived_response_kind']='local_rule_citation_assembly_not_original_model_response'
    except Refuse as error:
        result.update(proof_established=False,reason=str(error),derived_response=None)
        if result['proof_status']!='not_applicable':result['proof_status']='refused'
    finally:
        # 内部universe副本不参与原参数比较。
        assert question==before[0] and passages==before[1] and raw_answer_json==before[2]
    return result
