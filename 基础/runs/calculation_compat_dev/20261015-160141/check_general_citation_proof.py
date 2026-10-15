"""自造机制回归；没有题库访问或模型调用。失败返回非零。"""
import copy
import json
import re
import sys
from pathlib import Path
from datetime import datetime
import general_citation_proof as candidate

def main():
    folder=Path(__file__).resolve().parent
    cases=[]
    def add(name,question,passages,answer,expected):
        cases.append({'name':name,'question':question,'passages':passages,'raw':json.dumps({'answer':answer,'citations':[]},ensure_ascii=False),'expected':expected})
    def p(text,index):return {'id':'source-'+str(index),'source':'自造资料/'+str(index),'text':text}
    scope='竹岭项目V4版本在2026-04'
    q=scope+'同机实验中，新链路的完整响应耗时中位数比旧链路少多少秒？只输出数值。'
    data=p(scope+'的记录：同机顺序批次Trace82的旧链路处理40个固定问题，客户端完整响应耗时中位数为12.5秒。',1)
    extra=p('批次Trace82的复核补页：Trace82新链路处理同样40个问题，中位数为8.2秒；两次保持输入顺序。',2)
    add('difference_complete',q,[data,extra],'4.3',True)
    add('difference_direction_reversed_wrong_answer',q.replace('少多少','多多少'),[data,extra],'4.3',False)
    add('difference_direction_reversed_correct_signed_answer',q.replace('少多少','多多少'),[data,extra],'-4.3',True)
    add('difference_units_differ',q,[data,p(extra['text'].replace('8.2秒','8.2毫秒'),2)],'4.3',False)
    add('difference_other_batch',q,[data,p(extra['text'].replace('Trace82','Pair93'),2)],'4.3',False)
    add('difference_answer_mismatch',q,[data,extra],'4.4',False)
    add('difference_population_mismatch',q,[data,p(extra['text'].replace('同样40个','同样41个'),2)],'4.3',False)
    add('difference_scope_conflict',q,[p(data['text'].replace('V4版本','V5版本'),1),extra],'4.3',False)
    add('difference_short_metric_wrong_modifier',q,[data,p(extra['text'].replace('，中位数','，另一个指标中位数'),2)],'4.3',False)
    add('difference_statistic_different',q,[data,p(extra['text'].replace('中位数','平均值'),2)],'4.3',False)
    add('difference_zero',q,[data,p(extra['text'].replace('8.2','12.5'),2)],'0',True)
    add('difference_negative_decimal',q,[p(data['text'].replace('12.5','-3.1'),1),p(extra['text'].replace('8.2','-7.4'),2)],'4.3',True)
    sq=scope+'核验表应选择哪条流程？只输出流程名称。'
    sd=p(scope+'的记录：核验表Check64记录流程春召回13条证据、引入5条错误证据；流程夏召回11条、错误1条；流程秋召回15条、错误4条。',1)
    sr=p('批次Check64的复核补页：Check64的正式规则先要求错误证据不超过2条，再最大化召回；流程名称不参与第一轮筛选。',2)
    add('selection_unique_eligible',sq,[sd,sr],'流程夏',True)
    add('selection_chosen_fails_threshold',sq,[sd,sr],'流程春',False)
    add('selection_missing_rule',sq,[sd],'流程夏',False)
    add('selection_unknown_condition',sq,[sd,p(sr['text'].replace('错误证据不超过2条','错误证据不超过2条且签署状态已确认'),2)],'流程夏',False)
    add('selection_conflicting_scope',sq,[p(sd['text'].replace('V4版本','V5版本'),1),sr],'流程夏',False)
    add('selection_units_mismatch',sq,[sd,p(sr['text'].replace('不超过2条','不超过2秒'),2)],'流程夏',False)
    multi=p(sd['text'].replace('5条错误证据','1条错误证据').replace('错误4条','错误1条'),1)
    add('selection_maximize_order',sq,[multi,sr],'流程秋',True)
    add('selection_minimize_order',sq,[multi,p(sr['text'].replace('最大化','最小化'),2)],'流程夏',True)
    add('selection_changed_order_old_answer_rejected',sq,[multi,p(sr['text'].replace('最大化','最小化'),2)],'流程秋',False)
    tied=p(multi['text'].replace('召回13条','召回11条').replace('召回15条','召回11条'),1)
    add('selection_unresolved_tie',sq,[tied,sr],'流程夏',False)
    add('selection_direction_unknown_with_competitors',sq,[multi,p(sr['text'].replace('最大化召回','比较召回'),2)],'流程秋',False)
    add('selection_no_eligible',sq,[sd,p(sr['text'].replace('不超过2条','不超过0条'),2)],'流程夏',False)
    pq=scope+'资源表应选择哪项方案？只输出方案名称。'
    pd=p(scope+'的记录：资源表Review73记录青完整支持81%、P50为5.2秒、2次调用；蓝88%、8.1秒、3次；紫89%、6.4秒、2次。',1)
    pr=p('批次Review73的复核补页：Review73决策先要求完整支持率至少86%且P50不高于7秒，再比较平均调用次数和完整耗时。',2)
    add('selection_two_conditions_implicit_columns',pq,[pd,pr],'紫',True)
    add('selection_other_qualified_but_order_unresolved',pq,[p(pd['text'].replace('8.1秒','6.1秒'),1),pr],'紫',False)
    add('selection_missing_data_field',pq,[p(pd['text'].replace('、P50为5.2秒',''),1),pr],'紫',False)
    add('selection_explicit_metric_conflict',pq,[p(pd['text'].replace('蓝88%','蓝其他支持88%'),1),pr],'紫',False)
    add('selection_all_fields_equal_tie',pq,[p(pd['text'].replace('81%','89%').replace('5.2秒','6.4秒').replace('88%','89%').replace('8.1秒','6.4秒'),1),pr],'紫',False)
    add('selection_multichar_unseparated_name_unknown',pq,[p(pd['text'].replace('青完整支持','青山完整支持'),1),pr],'紫',False)
    add('unsupported_no_derivation','普通问题',[p('无相关资料。',1)],'证据不足',False)
    # 显式构造重映射：不是使用正确答案反向选数或改证明规则。
    originals=list(cases)
    for old in originals:
        for kind in ['ids','identifiers','order']:
            case=copy.deepcopy(old);case['name']=old['name']+'_'+kind
            if kind=='ids':
                for i,passage in enumerate(case['passages']):passage['id']='Remapped'+str(901+i)
            elif kind=='identifiers':
                mapping={'Trace82':'Code701','Pair93':'Code702','Check64':'Code703','Review73':'Code704','V4':'Edition705','V5':'Edition706'}
                def rename(text):
                    for old_code,new_code in mapping.items():text=text.replace(old_code,new_code)
                    return text
                case['question']=rename(case['question'])
                for passage in case['passages']:passage['text']=rename(passage['text'])
            else:case['passages'].reverse()
            cases.append(case)
    # 数值整体对应变化，差值与阈值随自造输入生成，验证规则不绑定具体数值。
    for scale in [2,3,7]:
        case=copy.deepcopy(originals[0]);case['name']='difference_numeric_remap_'+str(scale)
        case['passages'][0]['text']=case['passages'][0]['text'].replace('12.5秒',str(125*scale/10)+'秒')
        case['passages'][1]['text']=case['passages'][1]['text'].replace('8.2秒',str(82*scale/10)+'秒')
        case['raw']=json.dumps({'answer':str(43*scale/10),'citations':[]},ensure_ascii=False);cases.append(case)
        case=copy.deepcopy(originals[12]);case['name']='selection_numeric_remap_'+str(scale)
        for passage in case['passages']:
            passage['text']=re.sub(r'(?<![A-Za-z0-9])([0-9]+)(?=条)',lambda m:str(int(m[1])*scale),passage['text'])
        cases.append(case)
    results=[]
    for index,case in enumerate(cases,1):
        before=copy.deepcopy(case)
        result=candidate.prove_answer(case['question'],case['passages'],case['raw'])
        passed=result['proof_established']==case['expected'] and case==before
        if result['derived_response'] is not None:
            passed=passed and result['derived_response']['answer']==json.loads(case['raw'])['answer']
            passed=passed and all(i in {p['id'] for p in case['passages']} for i in result['derived_response']['citations'])
        row={**case,'actual':result,'passed':passed,'checked_at':datetime.now().astimezone().isoformat()}
        with (folder/f'self-test-{index:03d}.json').open('x',encoding='utf-8') as out:json.dump(row,out,ensure_ascii=False,indent=2)
        results.append({'name':case['name'],'passed':passed,'expected':case['expected'],'actual':result['proof_established'],'reason':result.get('reason')})
    summary={'checked_at':datetime.now().astimezone().isoformat(),'passed':all(r['passed'] for r in results),'returncode':0 if all(r['passed'] for r in results) else 1,
        'total':len(results),'passed_count':sum(r['passed'] for r in results),'failed':[r for r in results if not r['passed']],'generation_calls':0}
    with (folder/'self-check.json').open('x',encoding='utf-8') as out:json.dump(summary,out,ensure_ascii=False,indent=2)
    print(json.dumps(summary,ensure_ascii=False));return summary['returncode']

if __name__=='__main__':raise SystemExit(main())
