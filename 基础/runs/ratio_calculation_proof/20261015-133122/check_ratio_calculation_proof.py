"""比例证明自造正反例；不读取题库，不调用模型。"""
import copy,json,re
from pathlib import Path
from datetime import datetime
import ratio_calculation_proof as candidate

def main():
    folder=Path(__file__).resolve().parent;cases=[]
    def p(text,index):return {'id':'doc-'+str(index),'source':'自造比例资料','text':text}
    scope='竹岭项目V4版本在2026-04'
    q=scope+'冻结清单的完整支持率是多少？只输出百分数。'
    main=p(scope+'的记录：冻结评测集Trace82固定80条主张为分母，后续复跑不能剔除无引用和格式异常主张。',1)
    extra=p('批次Trace82的复核补页：Trace82人工复核显示52条完全支持、13条部分支持、9条矛盾、6条无引用；完整支持只计完全支持。',2)
    def add(name,question,passages,expected_answer):
        cases.append({'name':name,'question':question,'passages':copy.deepcopy(passages),
            'raw':json.dumps({'answer':'证据不足','citations':[]},ensure_ascii=False),'expected_answer':expected_answer})
    add('complete_support_excludes_partial',q,[main,extra],'65%')
    add('definition_missing',q,[main,p(extra['text'].replace('；完整支持只计完全支持',''),2)],None)
    add('requested_metric_mismatch',q.replace('完整支持率','合法返回率'),[main,extra],None)
    add('partial_not_silently_added',q,[main,p(extra['text'].replace('只计完全支持','只计完全支持和部分支持'),2)],'81.25%')
    add('definition_included_count_missing',q,[main,p(extra['text'].replace('只计完全支持','只计完全支持和已签署'),2)],None)
    add('count_units_differ',q,[main,p(extra['text'].replace('13条部分支持','13项部分支持'),2)],None)
    add('cross_batch',q,[main,p(extra['text'].replace('Trace82','Batch93'),2)],None)
    add('cross_version',q,[p(main['text'].replace('V4版本','V5版本'),1),extra],None)
    add('duplicate_category',q,[main,p(extra['text'].replace('13条部分支持','13条完全支持'),2)],None)
    add('explicit_overlap',q,[main,p(extra['text'].replace('；完整支持','；部分支持与完全支持可同时属于同一条目；完整支持'),2)],None)
    add('nested_category_labels',q,[main,p(extra['text'].replace('13条部分支持','13条完全支持且已签署'),2)],None)
    add('partition_total_mismatch',q,[main,p(extra['text'].replace('52条','53条'),2)],None)
    add('denominator_zero',q,[p(main['text'].replace('80条','0条'),1),extra],None)
    add('denominator_conflict',q,[main,p(extra['text']+'',2),p('批次Trace82的补充记录：分母为全部79条。',3)],None)
    add('duplicate_count_block',q,[main,p(extra['text'].replace('；完整支持','；另有52条完全支持、13条部分支持、9条矛盾、6条无引用；完整支持'),2)],None)
    add('positive_denominator_adjustment',q,[p(main['text'].replace('不能剔除','剔除'),1),extra],None)
    add('equal_numbers_different_categories_valid',q,[main,p(extra['text'].replace('52条完全支持、13条部分支持、9条矛盾、6条无引用','20条完全支持、20条部分支持、20条矛盾、20条无引用'),2)],'25%')
    add('zero_numerator',q,[main,p(extra['text'].replace('52条完全支持、13条部分支持','0条完全支持、65条部分支持'),2)],'0%')
    add('negative_category_count',q,[main,p(extra['text'].replace('52条完全支持、13条部分支持','-1条完全支持、66条部分支持'),2)],None)
    add('fractional_category_count',q,[main,p(extra['text'].replace('52条完全支持、13条部分支持','51.5条完全支持、13.5条部分支持'),2)],None)
    add('unsupported_rounding_instruction',q.replace('只输出百分数。','保留适当小数位。只输出百分数。'),[main,extra],None)
    third_main=p(main['text'].replace('80条','3条'),1)
    third_extra=p(extra['text'].replace('52条完全支持、13条部分支持、9条矛盾、6条无引用','1条完全支持、2条部分支持'),2)
    add('nonterminating_without_rounding',q,[third_main,third_extra],None)
    add('nonterminating_with_rounding',q.replace('只输出百分数。','保留2位小数，四舍五入。只输出百分数。'),[third_main,third_extra],'33.33%')
    tq=scope+'首次执行清单的技术失败率是多少？只输出百分数。'
    tm=p(scope+'的记录：首次执行清单Batch73有80项任务；61项返回合法结果、11项超时、8项格式不合法；每项只计初次结果。',1)
    te=p('批次Batch73的复核补页：Batch73质量口径把超时和格式不合法均列为技术失败，分母为全部80项；人工重试另列。',2)
    add('technical_definition_explicit',tq,[tm,te],'23.75%')
    add('technical_definition_missing',tq,[tm,p('批次Batch73的复核补页：Batch73分母为全部80项；人工重试另列。',2)],None)
    add('technical_unknown_remaining_category',tq,[p(tm['text'].replace('返回合法结果','尚未核验'),1),te],None)
    add('failure_cannot_be_legal_return_rate',tq.replace('技术失败率','合法返回率'),[tm,te],None)
    add('first_definition_missing',tq,[p(tm['text'].replace('；每项只计初次结果',''),1),te],None)
    add('retry_count_mixed',tq,[p(tm['text'].replace('；每项只计初次结果','；重试另有5项超时；每项只计初次结果'),1),te],None)
    add('retry_category_mixed',tq,[p(tm['text'].replace('8项格式不合法','8项重试格式不合法'),1),te],None)
    add('question_includes_retries_but_data_first',tq.replace('首次执行','含重试的全部执行'),[tm,te],None)
    add('aggregate_and_components_overlap',tq,[p(tm['text'].replace('61项返回合法结果','61项技术失败'),1),te],None)
    add('unsupported_nonratio','选择哪项方案？只输出名称。',[main,extra],None)
    # 最终回答输入缺少定义补页，即使原始可见资料里存在也不能借来算。
    missing={'name':'audit_only_definition_cannot_be_fact','question':tq,'passages':[tm],
        'universe':[tm,te],'raw':'{"answer":"证据不足","citations":[]}','expected_answer':None}
    cases.append(missing)
    originals=copy.deepcopy(cases)
    for old in originals:
        for mode in ['ids','identifiers','order']:
            case=copy.deepcopy(old);case['name']+='_'+mode
            if mode=='ids':
                for collection in ['passages','universe']:
                    for passage in case.get(collection,[]):passage['id']='Remap'+passage['id']
            elif mode=='identifiers':
                case['question']=case['question'].replace('V4','Edition92')
                for collection in ['passages','universe']:
                    for passage in case.get(collection,[]):passage['text']=passage['text'].replace('V4','Edition92').replace('V5','Edition93').replace('Trace82','Record851').replace('Batch73','Record852')
            else:
                case['passages'].reverse()
                if 'universe' in case:case['universe'].reverse()
            cases.append(case)
    # 数值按同一比例缩放，目标比例不变，防止绑定具体计数。
    for scale in [2,3,9]:
        for source in [originals[0],next(c for c in originals if c['name']=='technical_definition_explicit')]:
            case=copy.deepcopy(source);case['name']+='_numeric_remap_'+str(scale)
            for passage in case['passages']:
                passage['text']=re.sub(r'(?<![A-Za-z0-9])([0-9]+)(?=条|项)',lambda m:str(int(m[1])*scale),passage['text'])
            cases.append(case)
    rows=[]
    for index,case in enumerate(cases,1):
        before=copy.deepcopy(case)
        result=candidate.propose(case['question'],case['passages'],case['raw'],case.get('universe'))
        response=result['proposed_response'];expected=case['expected_answer']
        passed=case==before and ((response is None) if expected is None else response is not None and response['answer']==expected)
        if response is not None:passed=passed and set(response['citations'])<={p['id'] for p in case['passages']}
        with (folder/f'ratio-test-{index:03d}.json').open('x',encoding='utf-8') as out:json.dump({**case,'actual':result,'passed':passed},out,ensure_ascii=False,indent=2)
        rows.append({'name':case['name'],'passed':passed,'expected':expected,'actual':response,'reason':result.get('reason')})
    summary={'checked_at':datetime.now().astimezone().isoformat(),'total':len(rows),'passed_count':sum(r['passed'] for r in rows),
        'passed':all(r['passed'] for r in rows),'failed':[r for r in rows if not r['passed']],'generation_calls':0}
    summary['returncode']=0 if summary['passed'] else 1
    with (folder/'ratio-check.json').open('x',encoding='utf-8') as out:json.dump(summary,out,ensure_ascii=False,indent=2)
    print(json.dumps(summary,ensure_ascii=False));return summary['returncode']

if __name__=='__main__':raise SystemExit(main())
