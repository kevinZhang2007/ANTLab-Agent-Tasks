"""有限原文明示状态；输入位置关联，未知保留，不做资格选择。"""
import re

SIGNAL = re.compile(r'缺失|缺少|缺(?!陷)|失败|偏移|未关闭(?:的问题|问题)?|通过')
COUNT = re.compile(r'(?<![0-9.＋+\-负])(?P<n>[0-9]+|[零〇一二两三四五六七八九十]+)\s*项\s*$')
NEGATION = re.compile(r'(?:不存在|没有|未发现|未见|无|不|未)\s*$')
UNCERTAIN = re.compile(r'如果|假如|若|是否|可能|或许|未说明|不确定|尚未确认|无法确认|不一定|不能确认|不是\s*[0-9零〇一二两三四五六七八九十]+|超过|至少|至多')
OTHER_OWNER = re.compile(r'其他候选|另一候选|另一个候选|前者|后者')
DIGITS = dict(zip('零〇一二两三四五六七八九','001223456789'))

def parse_integer(text):
    if text.isascii() and text.isdigit():
        return int(text)
    if len(text)==1 and text in DIGITS:
        return int(DIGITS[text])
    if re.fullmatch(r'[一二三四五六七八九]?十[一二三四五六七八九]?',text):
        left,right=text.split('十')
        return (int(DIGITS[left]) if left else 1)*10+(int(DIGITS[right]) if right else 0)
    return None

def clause_bounds(text,start,end):
    left=max(text.rfind(c,0,start) for c in '；。;')+1
    right=min((p for c in '；。;' if (p:=text.find(c,end))>=0),default=len(text))
    return left,right+1 if right<len(text) else right

def inspect_explicit_states(passages,candidates):
    occurrences=[]
    for candidate in candidates:
        for source in candidate['sources']:
            index=source['passage_index'];passage=passages[index]
            start,end=source['start'],source['end']
            if passage['id']!=source['passage_id'] or not (0<=start<end<=len(passage['text'])) or passage['text'][start:end]!=candidate['snapshot']:
                raise ValueError('候选位置或来源不一致')
            left,right=clause_bounds(passage['text'],start,end)
            occurrences.append({'snapshot':candidate['snapshot'],'passage_index':index,'passage_id':passage['id'],
                                'candidate_start':start,'candidate_end':end,'start':left,'end':right})
    result=[]
    for occurrence in occurrences:
        p=passages[occurrence['passage_index']];text=p['text'];left,right=occurrence['start'],occurrence['end']
        owners=[o for o in occurrences if o['passage_index']==occurrence['passage_index'] and o['start']==left and o['end']==right]
        description_start=occurrence['candidate_end'];description=text[description_start:right]
        row={**occurrence,'quote':text[left:right],'events':[],'unparsed_content':[],
             'qualification_not_checked':True,'unclosed_count_not_defaulted_to_zero':True}
        if len(owners)!=1 or OTHER_OWNER.search(description):
            row.update(observed_state='unknown',association_reason='multiple_or_other_candidate_in_clause')
            row['unparsed_content']=[{'start':description_start,'end':right,'quote':description,'reason':'归属不可靠'}]
            result.append(row);continue
        for atom in re.finditer(r'[^，,、；。;]+',description):
            phrase=atom.group(0);absolute=description_start+atom.start();events=[]
            for signal in SIGNAL.finditer(phrase):
                token=signal.group(0);prefix=phrase[:signal.start()]
                count=COUNT.search(prefix);number=parse_integer(count['n']) if count else None
                anchor=count.start() if count else signal.start();negative=bool(NEGATION.search(phrase[:anchor]))
                suffix=phrase[signal.end():]
                status='unknown';reason='unparsed_signal'
                if UNCERTAIN.search(phrase) or (token=='失败' and re.match(r'率|概率|风险|定义|规则|要求',suffix)):
                    reason='conditional_or_uncertain_or_metric_mention'
                elif count and negative:
                    reason='negated_exact_quantity_ambiguous'
                elif negative:
                    status='unknown' if token=='通过' else 'explicit_absence'
                    reason='negative_pass_not_assumed_failure' if token=='通过' else 'explicit_negation'
                elif count and number==0:
                    status='explicit_absence' if token!='通过' else 'unknown';reason='explicit_zero_count'
                elif token=='通过':
                    status='explicit_pass';reason='literal_pass'
                elif token.startswith('缺') or token=='失败':
                    if count and number is None:reason='unparsed_integer'
                    else:status='explicit_defect';reason='literal_missing_or_failure'
                elif token=='偏移' or token.startswith('未关闭'):
                    if count and number is not None and number>0:
                        status='explicit_defect';reason='explicit_nonzero_integer_count'
                    else:reason='count_not_explicit_or_unparsed'
                event={'status':status,'trigger':token,'trigger_start':absolute+signal.start(),'trigger_end':absolute+signal.end(),
                       'rule':reason,'quantity_text':count['n'] if count else None,'quantity':number,
                       'quote':text[left:right],'start':left,'end':right,'description_quote':phrase,
                       'description_start':absolute,'description_end':absolute+len(phrase),'condition_context_not_semantically_parsed':True}
                events.append(event)
            row['events'].extend(events)
            if not events or any(e['status']=='unknown' for e in events):
                row['unparsed_content'].append({'start':absolute,'end':absolute+len(phrase),'quote':phrase,
                                               'reason':'没有受支持的明示信号或信号不确定'})
        statuses={e['status'] for e in row['events']}
        row['observed_state']=('explicit_defect' if 'explicit_defect' in statuses else
                               'unknown' if 'unknown' in statuses or not statuses else
                               'explicit_pass_only' if 'explicit_pass' in statuses else 'explicit_absence_only')
        result.append(row)
    return result
