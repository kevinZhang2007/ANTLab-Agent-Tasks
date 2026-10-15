"""项目边界机制正反例；不访问正式材料，不调用模型。"""
import copy,json,sys
from pathlib import Path
from datetime import datetime
import general_citation_proof as candidate
from project_scope_resolution import resolve_question_scope
from scope_first_occurrences import explicit_scope

def main():
    folder=Path(__file__).resolve().parent
    cases=[]
    def data(name='竹岭项目',version='V4版本',date='2026-04',pid='main'):
        return {'id':pid,'source':'自造边界材料','text':name+version+'在'+date+'的记录：核验表Trace42记录流程春召回13条证据、引入4条错误证据；流程夏召回11条、错误1条。'}
    def q(name):return name+'V4版本2026-04核验表应选择哪条流程？只输出流程名称。'
    def add(name,question,passages,expected,entity=None):
        cases.append({'name':name,'question':question,'passages':passages,'expected_status':expected,'expected_entity':entity})
    add('literal',q('竹岭项目'),[data()],'resolved','竹岭项目')
    for guide in ['按','根据','依据','按照']:
        add('guide_'+guide,q(guide+'竹岭项目'),[data()],'resolved','竹岭项目')
    add('real_entity_starts_an',q('按竹岭项目'),[data('按竹岭项目')],'resolved','按竹岭项目')
    add('guide_before_real_entity_starts_an',q('按按竹岭项目'),[data('按竹岭项目')],'resolved','按竹岭项目')
    add('guide_word_inside_name',q('南按北项目'),[data('南按北项目')],'resolved','南按北项目')
    add('guide_word_at_real_name_start',q('根据地项目'),[data('根据地项目')],'resolved','根据地项目')
    add('real_name_starts_anzhao',q('按照竹岭项目'),[data('按照竹岭项目')],'resolved','按照竹岭项目')
    add('two_declared_interpretations',q('按竹岭项目'),[data(),data('按竹岭项目',pid='other')],'unknown')
    add('overlapping_guides_two_entities',q('按照竹岭项目'),[data(),data('照竹岭项目',pid='other')],'unknown')
    add('question_body_version_conflict',q('按竹岭项目'),[data(version='V5版本')],'unknown')
    add('question_body_date_conflict',q('按竹岭项目'),[data(date='2026-05')],'unknown')
    add('entity_boundary_not_declared',q('按竹岭项目'),[{'id':'x','source':'自造','text':'资料提到竹岭项目V4版本在2026-04，但没有实体范围声明。'}],'unknown')
    add('unsupported_question_prefix',q('请就竹岭项目'),[data()],'unknown')
    add('version_boundary_missing',q('按竹岭项目 ').replace(' V4',' V4'),[data()],'unknown')
    add('other_declared_entity_not_candidate',q('按竹岭项目'),[data(),data('独立项目',pid='other')],'resolved','竹岭项目')
    add('two_interpretations_even_if_one_version_conflicts',q('按竹岭项目'),[data(),data('按竹岭项目',version='V5版本',pid='other')],'unknown')
    add('mere_mention_does_not_override_real_name',q('按竹岭项目'),[data('按竹岭项目'),{'id':'mention','source':'自造','text':'另页参考竹岭项目V4版本，未作实体声明。'}],'resolved','按竹岭项目')
    originals=copy.deepcopy(cases)
    for old in originals:
        for mode in ['id_remap','order','identifier_remap']:
            changed=copy.deepcopy(old);changed['name']+='_'+mode
            if mode=='id_remap':
                for i,p in enumerate(changed['passages']):p['id']='Remapped'+str(i)
            elif mode=='order':changed['passages'].reverse()
            else:
                changed['question']=changed['question'].replace('V4','Edition91')
                for p in changed['passages']:p['text']=p['text'].replace('V4','Edition91').replace('V5','Edition92').replace('Trace42','Object85')
            cases.append(changed)
    rows=[]
    for index,test in enumerate(cases,1):
        before=copy.deepcopy(test)
        scope,audit=resolve_question_scope(test['question'],test['passages'],explicit_scope(test['question']))
        passed=audit['status']==test['expected_status'] and test==before
        if test['expected_status']=='resolved':passed=passed and scope['project']==[test['expected_entity']]
        row={**test,'scope':scope,'audit':audit,'passed':passed}
        with (folder/f'boundary-test-{index:03d}.json').open('x',encoding='utf-8') as out:json.dump(row,out,ensure_ascii=False,indent=2)
        rows.append(row)
    # 端到端资格证明必须再次执行门槛及决策；修复范围不等于自动通过。
    main=data();extra={'id':'rule','source':'自造','text':'批次Trace42的复核补页：Trace42规则先要求错误证据不超过2条，再最大化召回。'}
    integration=[]
    for question,answer,expected in [(q('按竹岭项目'),'流程夏',True),(q('按竹岭项目'),'流程春',False),
        (q('按竹岭项目'), '流程夏',True)]:
        passages=[main,extra]
        if len(integration)==2:
            passages=copy.deepcopy(passages);passages[0]['text']=passages[0]['text'].replace('错误1条','错误3条');expected=False
        result=candidate.prove_answer(question,passages,json.dumps({'answer':answer,'citations':[]},ensure_ascii=False))
        integration.append({'question':question,'passages':passages,'answer':answer,'expected':expected,'actual':result,'passed':result['proof_established']==expected})
    summary={'checked_at':datetime.now().astimezone().isoformat(),'passed':all(r['passed'] for r in rows+integration),'total':len(rows)+len(integration),
        'passed_count':sum(r['passed'] for r in rows+integration),'failed':[r['name'] for r in rows if not r['passed']],
        'integration':integration,'generation_calls':0}
    summary['returncode']=0 if summary['passed'] else 1
    with (folder/'boundary-check.json').open('x',encoding='utf-8') as out:json.dump(summary,out,ensure_ascii=False,indent=2)
    print(json.dumps({k:v for k,v in summary.items() if k!='integration'},ensure_ascii=False));return summary['returncode']

if __name__=='__main__':raise SystemExit(main())
