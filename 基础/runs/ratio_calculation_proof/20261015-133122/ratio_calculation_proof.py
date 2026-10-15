"""独立比例计算候选：先解析定义与分类，再计算新答案，绝不修改模型原答。"""
import copy,json,re
from decimal import Decimal,localcontext,ROUND_HALF_UP
from fractions import Fraction
import general_citation_proof as shared

DEC=r'[+-]?[0-9]+(?:\.[0-9]+)?'
UNIT=r'条|项|个|次'
COUNT=re.compile(r'(?P<number>'+DEC+r')(?P<unit>'+UNIT+r')')
QUESTION=re.compile(r'(?:^|的)(?P<metric>(?:(?!的)[一-鿿A-Za-z0-9_])+?)率(?:是多少|为多少|多少)[？?]')

def ev(p,start,end,role):return shared.ev(p,start,end,role)
def require(ok,reason):shared.require(ok,reason)
def names(text):return [s.strip() for s in re.split(r'、|和|及',text) if s.strip()]

def definitions(metric,passages):
    found=[]
    for p in passages:
        text=shared.first_sentence(p)
        patterns=[re.escape(metric)+r'(?:只计|仅计|只包含)(?P<categories>[^。；;，,]+)',
            r'(?:把|将)(?P<categories>[^。；;，,]+?)(?:均|都)?列为'+re.escape(metric)+r'(?![一-鿿A-Za-z0-9_])']
        for index,pattern in enumerate(patterns):
            for m in re.finditer(pattern,text):
                selected=names(m['categories'])
                require(selected and len(selected)==len(set(selected)),'definition_categories_duplicate_or_missing')
                found.append({'included':selected,'closed_definition':index==0,
                    'definition_form':'exclusive_only_count' if index==0 else 'enumerated_assignment',
                    'source':ev(p,m.start(),m.end(),'指标分子分类定义')})
    require(len(found)==1,'metric_definition_missing_or_multiple')
    return found[0]

def denominators(passages):
    rows=[]
    for p in passages:
        text=shared.first_sentence(p)
        for pattern in [r'(?P<number>'+DEC+r')(?P<unit>'+UNIT+r')(?P<population>[一-鿿]{0,8})为分母',
            r'分母(?:为|是)(?:全部|所有|固定)?(?P<number>'+DEC+r')(?P<unit>'+UNIT+r')(?P<population>[一-鿿]{0,8})']:
            for m in re.finditer(pattern,text):
                rows.append({'value':m['number'],'unit':m['unit'],'population':m['population'],
                    'source':ev(p,m.start(),m.end(),'明确分母'),'quantity_span':[m.start('number'),m.end('unit')]})
    require(rows,'denominator_not_explicit')
    require(len({(Decimal(r['value']),r['unit']) for r in rows})==1,'denominator_conflict')
    value=Decimal(rows[0]['value']);require(value>0 and value==value.to_integral_value(),'zero_negative_or_fractional_count_denominator')
    return value,rows[0]['unit'],rows

def partition(passages):
    blocks=[]
    for p in passages:
        text=shared.first_sentence(p)
        for block in re.finditer(r'[^；;。]+',text):
            fields=list(re.finditer(r'[^、，,]+',block.group()))
            if len(fields)<2:continue
            rows=[]
            for field in fields:
                quantities=list(COUNT.finditer(field.group()))
                if len(quantities)!=1:break
                m=quantities[0];category=field.group()[m.end():].strip()
                if not re.fullmatch(r'[一-鿿A-Za-z_][一-鿿A-Za-z0-9_]*',category):break
                start=block.start()+field.start()+m.start()
                end=block.start()+field.start()+m.end()
                rows.append({'category':category,'value':m['number'],'unit':m['unit'],
                    'quantity_span':[start,end],'source':ev(p,start,block.start()+field.end(),'并列分类计数')})
            else:
                blocks.append({'rows':rows,'source':ev(p,block.start(),block.end(),'同批并列分类原文')})
    require(len(blocks)==1,'zero_or_multiple_count_partitions')
    result=blocks[0];labels=[r['category'] for r in result['rows']]
    require(len(labels)==len(set(labels)),'duplicate_category_count')
    require(not any(a!=b and (a in b or b in a) for a in labels for b in labels),'nested_category_labels_overlap')
    require(not re.search(r'其中|重叠|重复|交叉|同时属于|可同时|多标签|包括|包含',result['source']['quote']),'explicit_overlap_or_inclusion_in_partition')
    require(all(Decimal(r['value'])>=0 and Decimal(r['value'])==Decimal(r['value']).to_integral_value() for r in result['rows']),'negative_or_fractional_category_count')
    return result

def statistical_scope(question,passages,counts,denominator,denom_unit,denom_rows):
    texts=[shared.first_sentence(p) for p in passages]
    combined='\n'.join(texts)
    q_first=bool(re.search(r'首次|初次',question))
    explicit_first=bool(re.search(r'(?:每项)?只计(?:初次|首次)(?:结果)?|每项只计初次结果',combined))
    if q_first:require(explicit_first,'first_attempt_scope_not_explicit')
    if re.search(r'含重试|最终执行|全部执行',question) and re.search(r'首次|初次',combined):raise shared.Refuse('question_and_attempt_scope_differ')
    require(not any(re.search(r'重试|复跑|再次',r['category']) for r in counts['rows']),'mixed_first_and_retry_categories')
    if re.search(r'首次|初次',combined) and re.search(r'重试|复跑',combined):
        require(explicit_first or bool(re.search(r'不能剔除|不得剔除|不剔除',combined)),'retry_scope_not_separated')
    for text in texts:
        adjusted=re.sub(r'不能剔除|不得剔除|不剔除','',text)
        require(not re.search(r'剔除|扣除|调整分母',adjusted),'denominator_adjustment_not_supported')
    known={}
    for r in counts['rows']:known.setdefault(r['source']['passage_id'],[]).append(r['quantity_span'])
    for r in denom_rows:known.setdefault(r['source']['passage_id'],[]).append(r['quantity_span'])
    total_evidence=[]
    for p in passages:
        text=shared.first_sentence(p)
        for m in COUNT.finditer(text):
            if [m.start(),m.end()] in known.get(p['id'],[]):continue
            prefix=text[max(0,m.start()-5):m.start()]
            if Decimal(m['number'])==denominator and m['unit']==denom_unit and re.search(r'(?:有|共|固定|总计|全部)$',prefix):
                total_evidence.append(ev(p,m.start(),m.end(),'同批总计交叉核对'))
            else:raise shared.Refuse('unassigned_count_or_retry_count')
    return {'question_first_attempt':q_first,'explicit_first_attempt':explicit_first,
        'retry_separation_quotes':[ev(p,m.start(),m.end(),'统计阶段界限') for p in passages for m in re.finditer(r'每项只计初次结果|只计首次结果|人工重试另列|后续复跑不能剔除[^。]+',shared.first_sentence(p))],
        'total_count_crosscheck':total_evidence}

def percent(numerator,denominator,question,passages):
    policies=[]
    for text in [question]+[shared.first_sentence(p) for p in passages]:
        for m in re.finditer(r'保留(?P<places>[0-9]+)位小数[，,]?四舍五入|四舍五入[，,]?保留(?P<other>[0-9]+)位小数',text):
            policies.append(int(m['places'] or m['other']))
    require(len(set(policies))<=1,'rounding_policies_conflict')
    if any(re.search(r'保留.*小数|四舍五入|舍入|取整|截断',text) for text in [question]+[shared.first_sentence(p) for p in passages]):
        require(policies,'rounding_instruction_not_reliably_parsed')
    rational=Fraction(numerator)/Fraction(denominator)*100
    residue=rational.denominator;twos=fives=0
    while residue%2==0:residue//=2;twos+=1
    while residue%5==0:residue//=5;fives+=1
    require(residue==1 or policies,'nonterminating_percentage_rounding_not_defined')
    if policies:require(0<=policies[0]<=12,'rounding_precision_not_supported')
    with localcontext() as context:
        context.prec=max(80,len(str(rational.numerator))+len(str(rational.denominator))+max(twos,fives)+20)
        value=numerator/denominator*Decimal(100)
        if policies:value=value.quantize(Decimal(1).scaleb(-policies[0]),rounding=ROUND_HALF_UP)
        rendered=format(value,'f')
        if not policies:rendered=rendered.rstrip('0').rstrip('.') if '.' in rendered else rendered
    return rendered+'%',{'mode':'ROUND_HALF_UP','places':policies[0]} if policies else {'mode':'exact_terminating_decimal_no_rounding_needed'}

def propose(question,passages,raw_answer_json,universe=None):
    original=copy.deepcopy((question,passages,raw_answer_json,universe))
    result={'run_kind':'offline_ratio_calculation_proposal','judgment_source':'local_rule','applicable':False,
        'proof_established':False,'status':'not_applicable','trace':[],'proposed_response':None,
        'answer_changed':False,'not_original_model_response':True}
    try:
        targets=list(QUESTION.finditer(question))
        if not targets:result['reason']='question_does_not_request_supported_ratio';return result
        result.update(applicable=True,status='unknown');require(len(targets)==1,'multiple_requested_metrics')
        metric=targets[0]['metric'];result['requested_metric']=metric+'率'
        raw=json.loads(raw_answer_json);require(isinstance(raw,dict) and isinstance(raw.get('answer'),str),'invalid_original_answer')
        original_pool=copy.deepcopy(passages if universe is None else universe)
        main,extra,link=shared.linked_pairs(question,passages,original_pool,result['trace'])
        fact_passages=[main,extra]
        definition=definitions(metric,fact_passages);result['definition']=definition
        remainder='\n'.join(shared.first_sentence(p) for p in fact_passages).replace(definition['source']['quote'],'')
        require(not re.search(r'其中|重叠|重复|交叉|同时属于|可同时|多标签|包括|包含',remainder),'explicit_overlap_or_inclusion_outside_count_block')
        denominator,unit,denom_rows=denominators(fact_passages)
        result['denominator']={'value':str(denominator),'unit':unit,'sources':denom_rows}
        counts=partition(fact_passages);result['category_counts']=counts
        labels={r['category']:r for r in counts['rows']}
        require(set(definition['included'])<=labels.keys(),'defined_category_count_missing')
        require(not(metric in labels and definition['included']!=[metric]),'aggregate_and_component_categories_overlap')
        require(all(r['unit']==unit for r in counts['rows']),'count_unit_mismatch')
        require(sum((Decimal(r['value']) for r in counts['rows']),Decimal(0))==denominator,'closed_partition_total_does_not_equal_denominator')
        excluded_status=[]
        if not definition['closed_definition']:
            # “列为”本身不代表穷尽。未纳入项还须有明确相斥的正常结果描述。
            require(bool(re.search(r'失败|错误',metric)),'nonexclusive_definition_remaining_categories_unknown')
            for name,row in labels.items():
                if name in definition['included']:continue
                require(not re.search(r'不|未|失败|错误|异常|超时',name) and bool(re.search(r'成功|合法|通过|正常',name)),
                    'nonexclusive_definition_remaining_category_not_explicitly_normal')
                excluded_status.append({'category':name,'source':row['source'],'basis':'同批单次结果并列分类中的明示正常/合法状态；分子仍仅使用原文列为目标指标的类别，不以分母减此项代算。'})
        scope=statistical_scope(question,fact_passages,counts,denominator,unit,denom_rows);result['statistical_scope']=scope
        result['category_assignment']={'included':definition['included'],'excluded':[name for name in labels if name not in definition['included']],
            'basis':'实际原文的只计/列为定义形成封闭分子；不从术语常识补分类。',
            'excluded_status_sources':excluded_status,
            'partition_limit':'限同批并列复核结果、分类名不嵌套、无明示交叉/重复且总和吻合；不保证排除隐含的语义重叠，需独立原文复核。'}
        chosen=[labels[name] for name in definition['included']]
        numerator=sum((Decimal(r['value']) for r in chosen),Decimal(0))
        result['numerator']={'value':str(numerator),'unit':unit,'sources':chosen}
        result['expression']='('+ '+'.join(r['value'] for r in chosen)+')/'+str(denominator)+'*100'
        answer,rounding=percent(numerator,denominator,question,fact_passages)
        result['rounding']=rounding
        ids={definition['source']['passage_id']}|{r['source']['passage_id'] for r in denom_rows}|{r['source']['passage_id'] for r in counts['rows']}
        citations=[p['id'] for p in passages if p['id'] in ids]
        require(ids<={p['id'] for p in passages},'fact_or_citation_outside_final_model_input')
        result.update(proof_established=True,status='established',reason='explicit_metric_definition_partition_denominator_and_attempt_scope_confirmed',
            proposed_response={'answer':answer,'citations':citations},answer_changed=answer!=raw['answer'],
            proposed_response_kind='local_rule_calculated_new_answer_not_model_output',original_answer=raw['answer'])
    except shared.Refuse as error:result.update(status='refused',reason=str(error),proposed_response=None)
    finally:assert (question,passages,raw_answer_json,universe)==original
    return result
