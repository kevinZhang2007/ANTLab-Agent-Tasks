"""措辞兼容与保守拒绝回归；纯自造输入，不访问题库或答案。"""
import copy, json
from pathlib import Path
import general_citation_proof as proof
import difference_calculation_proposal as diff
import ratio_calculation_proof as ratio

def run():
    rows=[]
    scope='松镜项目V8版本在2026-02'
    q=scope+'同机实验中，新流程的完整响应耗时中位数比旧流程少多少秒？只输出数值。'
    main={'id':'alpha','source':'自造/一','text':scope+'的记录：顺序批次Record29的旧流程处理17个固定问题，客户端完整响应耗时中位数为9.7秒。'}
    extra={'id':'beta','source':'自造/二','text':'批次Record29的复核补页：Record29新流程处理相同17个问题，中位数为6.4秒；两组设置相同。'}
    cases=[]
    def add(name,question,ps,expected):cases.append({'name':name,'question':question,'passages':copy.deepcopy(ps),'expected':expected})
    add('different_word_same_population',q,[main,extra],'3.3')
    add('legacy_same_word',q,[main,{**extra,'text':extra['text'].replace('相同17','同样17')}],'3.3')
    for punct in ['，',',','；',';']:
        add('punctuation_'+punct,q,[main,{**extra,'text':extra['text'].replace('，中位数',punct+'中位数')}],'3.3')
    add('whitespace_population',q,[main,{**extra,'text':extra['text'].replace('相同17','相同 17')}],'3.3')
    add('direction_reversal',q.replace('少多少','多多少'),[main,extra],'-3.3')
    add('different_batch',q,[main,{**extra,'text':extra['text'].replace('Record29','Other42')}],None)
    add('different_scope',q,[main,{**extra,'text':'遥星项目V8版本在2026-02的记录：'+extra['text']}],None)
    add('units_conflict',q,[main,{**extra,'text':extra['text'].replace('6.4秒','6.4毫秒')}],None)
    add('metric_definition_missing',q,[{**main,'text':main['text'].replace('完整响应耗时中位数','另一指标中位数')},extra],None)
    add('statistic_conflict',q,[main,{**extra,'text':extra['text'].replace('中位数','平均值')}],None)
    add('ambiguous_operands',q,[main,{**extra,'text':extra['text'].replace('中位数为6.4秒','中位数为6.4秒，中位数为6.1秒')}],None)
    add('population_mismatch',q,[main,{**extra,'text':extra['text'].replace('相同17','相同18')}],None)
    add('population_not_explicit',q,[main,{**extra,'text':extra['text'].replace('相同17个问题','若干问题')}],None)
    add('population_negated',q,[main,{**extra,'text':extra['text'].replace('相同17','并非相同17')}],None)
    add('population_zero_ambiguity',q,[{**main,'text':main['text'].replace('17个','0个')},{**extra,'text':extra['text'].replace('17个','0个')}],None)
    # 旧函数过去没有禁止零规模；新兼容不能藉空集合证明可比中位数。
    add('multiple_main_targets',q,[main,extra,{**main,'id':'third'}],None)
    originals=copy.deepcopy(cases)
    for case in originals:
        for mode in ['ids','identifiers','order','numeric']:
            c=copy.deepcopy(case);c['name']+='_'+mode
            if mode=='ids':
                for p in c['passages']:p['id']='changed-'+p['id']
            elif mode=='identifiers':
                c['question']=c['question'].replace('V8','Edition65')
                for p in c['passages']:p['text']=p['text'].replace('V8','Edition65').replace('Record29','Code803').replace('Other42','Code804')
            elif mode=='order':c['passages'].reverse()
            else:
                for p in c['passages']:p['text']=p['text'].replace('9.7秒','19.4秒').replace('6.4秒','12.8秒')
                if c['expected']=='3.3':c['expected']='6.6'
                elif c['expected']=='-3.3':c['expected']='-6.6'
            cases.append(c)
    raw=json.dumps({'answer':'错误原答','citations':[]},ensure_ascii=False)
    for case in cases:
        before=copy.deepcopy(case);actual=diff.propose(case['question'],case['passages'],raw)
        response=actual['proposed_response'];passed=case==before and (response is None if case['expected'] is None else response is not None and response['answer']==case['expected'])
        if response is not None:
            raw_proof=proof.prove_answer(case['question'],case['passages'],raw)
            passed=passed and not raw_proof['proof_established'] and raw_proof['reason']=='original_answer_not_equal_to_proven_difference'
        rows.append({**case,'actual':actual,'passed':passed})
    # 指标无定义仍拒绝；不能从“支持”常识映射任意指标，不能把零分母吞掉。
    rq=scope+'登记清单的审定率是多少？只输出百分数。'
    rm={'id':'m','source':'自造','text':scope+'的记录：登记批次Ratio41固定20条记录为分母。'}
    re={'id':'n','source':'自造','text':'批次Ratio41的复核补页：Ratio41显示15条完整支持、5条未支持。'}
    for name,m,e in [('missing_metric_definition',rm,re),('zero_denominator',{**rm,'text':rm['text'].replace('20条','0条')},{**re,'text':re['text']+'；审定只计完整支持。'})]:
        result=ratio.propose(rq,[m,e],raw)
        rows.append({'name':name,'passed':result['proposed_response'] is None,'actual':result,'expected':None})
    return {'passed':all(r['passed'] for r in rows),'total':len(rows),'passed_count':sum(r['passed'] for r in rows),'failed':[r['name'] for r in rows if not r['passed']],'rows':rows,'generation_calls':0}

if __name__=='__main__':
    result=run();Path(__file__).with_name('calculation-compat-self-tests.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},ensure_ascii=False));raise SystemExit(0 if result['passed'] else 1)
