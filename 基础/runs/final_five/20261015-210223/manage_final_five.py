"""限定五轮的准备、离线评价与汇总；模型请求仍由已有运行器执行。"""
from pathlib import Path
from datetime import datetime
import ast,copy,hashlib,importlib.util,json,shutil,sys
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'基础/starter/provider.py').is_file())
CAMPAIGN=Path(__file__).resolve().parent
PARENT=ROOT/'基础/runs/repeat_integrated/20261015-192436'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now().astimezone().isoformat()
def write(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as out:json.dump(v,out,ensure_ascii=False,indent=2)
sys.path.insert(0,str(ROOT/'基础/tests'));sys.path.insert(0,str(CAMPAIGN))
import bounded_candidate as candidate
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v);return v

def prepare(number):
    folder=CAMPAIGN/f'round{number}';folder.mkdir(exist_ok=False)
    base_policy={}
    if number>1:
        previous=load(CAMPAIGN/f'round{number-1}/selection.json') if number<4 else load(CAMPAIGN/'round3/selection.json')
        base_policy=previous['retained_policy']
    if number==5:assert load(CAMPAIGN/'round4/summary.json')['passed']
    new_policy=copy.deepcopy(base_policy)
    if number==1:new_policy['presentation']='blocks'
    if number==2:new_policy['temperature']=0
    if number==3:new_policy['short_prompt']=True
    prediction={1:'原文分块可能降低解析负担；也可能改变注意分配且不改善计算、缺证或引用。',2:'贪心可能提高可重复性，也可能稳定保留错误；不是训练或能力提升。',3:'短提示可能减少任务竞争，也可能削弱范围或引用约束。',5:'保留方案可能仍有定位漏证、错误拒答或规则不适用；不预设满分。'}[number]
    design={'saved_at':now(),'round':number,'hypothesis_and_competition':prediction,'selection_rule':'先系统最终严格成功数，再系统最终正确数；同分保留当前已验证方案，原始模型指标单列。','control_policy':base_policy,'candidate_policy':new_policy if number<4 else None,'short_prompt':candidate.SHORT_PROMPT if number==3 else None,'failure':'质量不重试；技术停止，先核查是否发出；不得自动重发。','scope':'D01定义不足不补映射；T01资格歧义不放宽。','replay':number<4,'cost':'前三轮仅回答及规则，定位历史重放不计入新耗时或新生成；第五轮真实端到端。','exposure':'前四轮只开发题和自造；第五轮为评测后重复测试。'}
    jobs=[]
    if number<4:
        for i in range(1,5):
            for variant in (['control','candidate'] if i%2 else ['candidate','control']):
                jobs.append({'sequence':len(jobs)+1,'case_id':f'D{i:02d}','dataset':'development','condition':'R0','variant':'improved','comparison_arm':variant,'policy':base_policy if variant=='control' else new_policy,'historical_task':(PARENT/f'task-{i:02d}.json').relative_to(ROOT).as_posix()})
    else:
        for cid in [f'D{i:02d}' for i in range(1,5)]+[f'T{i:02d}' for i in range(1,9)]:
            jobs.append({'sequence':len(jobs)+1,'case_id':cid,'dataset':'development' if cid.startswith('D') else 'evaluation_repeat','condition':'R0','variant':'improved','comparison_arm':'retained','policy':base_policy})
    previous_count=478+sum(load(CAMPAIGN/f'round{i}/execution-summary.json')['confirmed_generation_calls'] for i in range(1,min(number,4)))
    plan={'round':number,'saved_at':now(),'items':jobs,'generation_limit':8 if number<4 else 24,'previous_cumulative':previous_count,'design':design}
    write(folder/'execution-plan.prepared.json',plan)
    for name in ['settings.prepared.json','answer.prepared.json','selection.prepared.json']:shutil.copyfile(CAMPAIGN/name,folder/name)
    for name in ['parent-freeze-verification.json','version-verification.json']:shutil.copyfile(PARENT/name,folder/name)
    shutil.copyfile(CAMPAIGN/'baseline-verification.json',folder/'source-lineage.json')
    # 本轮新增覆盖层只做离线自造检查；原规则沿用哈希一致的534项既有门禁。
    examples=[{'question':'中文“问题”\n第二行','passages':[{'id':'q"1','source':'来源\n甲','text':'第一行\n“原文”与\\斜线。'},{'id':'空','source':'','text':''}]},{'question':'空资料','passages':[]}]
    checks=[]
    conf=load(folder/'answer.prepared.json')
    for example in examples:
        msgs=candidate.student.prepare_messages(example['question'],example['passages']);before=copy.deepcopy((msgs,conf,example))
        for policy in [base_policy,new_policy]:
            actual,settings=candidate.apply_policy(msgs,conf,policy)
            assert (msgs,conf,example)==before
            assert len(actual)==len(msgs) and actual[0]['role']==msgs[0]['role']
            if policy.get('presentation')=='blocks':
                expected=candidate.blocks(example['question'],example['passages']);assert actual[1]['content']==expected
                assert expected.startswith('问题：\n'+example['question'])
                for i,p in enumerate(example['passages'],1):assert '段落 '+str(i)+'\nID：'+p['id']+'\n来源：'+p['source']+'\n原文：\n'+p['text'] in expected
            else:assert json.loads(actual[1]['content'])==example
            assert settings['parameters']['response_format']==conf['parameters']['response_format']
            assert settings['parameters']['max_tokens']==256
            assert actual[0]['content']==(candidate.SHORT_PROMPT if policy.get('short_prompt') else msgs[0]['content'])
            assert settings['parameters']['temperature']==policy.get('temperature',conf['parameters']['temperature'])
            checks.append({'example':example,'policy':policy,'passed':True,'messages':actual})
    for path in CAMPAIGN.glob('*.py'):ast.parse(path.read_text(encoding='utf-8-sig'))
    for name,h in load(CAMPAIGN/'baseline-verification.json')['modules'].items():assert sha(CAMPAIGN/name)==h
    if number<4:
        for i in range(1,5):
            old=load(PARENT/f'task-{i:02d}.json');used=old['used_passages']
            messages,original_config,_=candidate.core.answer_request(old['question'],used,conf,universe=old['original_passages'])
            a,ac=candidate.apply_policy(messages,original_config,base_policy);b,bc=candidate.apply_policy(messages,original_config,new_policy)
            if number==1:assert a[0]==b[0] and ac==bc
            if number==2:
                assert a==b;ac['parameters'].pop('temperature');bc['parameters'].pop('temperature');assert ac==bc
            if number==3:assert a[1:]==b[1:] and ac==bc
    gate={'checked_at':now(),'passed':True,'returncode':0,'checks':checks,'retained_old_regressions':534,'previous_rule_hashes_unchanged':True,'generation_calls':0,'all_inputs_exist':True,'no_T_results_read':number<4}
    write(folder/'execution-offline-check.json',gate)
    print(str(folder))

def review(number):
    folder=CAMPAIGN/f'round{number}';execution=load(folder/'execution-summary.json');assert not execution['technical_stop'] and execution['service_stopped']
    assert execution['confirmed_generation_calls']==(8 if number<4 else 24)
    evaluator=module('development_evaluator',CAMPAIGN/'development_evaluator.py')
    if number==5:
        evaluator=module('saved_evaluator',PARENT/'review/saved_evaluation_functions.py')
    public=load(ROOT/'基础/data/dev_answers.json');rows=[]
    jobs=load(folder/'execution-plan.prepared.json')['items']
    for job in jobs:
        task=load(folder/f"task-{job['sequence']:02d}.json")
        if job['dataset']=='development':
            basis=evaluator.development_basis(task,public);basis['timing']='本轮全部调用结束、服务停止后读取公开答案，仅评价使用。'
            evaluate=lambda v:evaluator.development_evaluate(task,v,basis,evaluator)
        else:
            basis=load(ROOT/f"基础/runs/formal_review/round1/evidence-{job['case_id']}.json")
            lookup={p['id']:p for p in task['original_passages']};assert all(e['quote'] in lookup[e['id']]['text'] for e in basis['required_evidence'])
            evaluate=lambda v:evaluator.evaluate(task,v,basis)
        raw=evaluate(task.get('raw_answer'));final=evaluate(task.get('actual_final_output'))
        reference=task.get('reference_derived_response');proposal=task.get('proposed_response')
        reference_review=evaluate(reference) if reference is not None else None
        proposal_review=evaluate(proposal) if proposal is not None else None
        wrong=bool(reference_review and reference_review['support_actual_answer'] is not True or proposal_review and (proposal_review['answer_correct'] is not True or proposal_review['support_actual_answer'] is not True))
        row={'case_id':task['case_id'],'arm':job['comparison_arm'],'dataset':job['dataset'],'policy':job['policy'],'task_path':(folder/f"task-{job['sequence']:02d}.json").relative_to(ROOT).as_posix(),'raw':raw,'final':final,'raw_content':task.get('raw_answer'),'actual_final_output':task.get('actual_final_output'),'output_source':task.get('actual_final_output_source'),'reference_derived_response':reference,'calculation_proposed_response':proposal,'wrong_derivation':wrong,'timing':task.get('timing_summary'),'basis':basis,'note':'Codex辅助原文复核，尚未经本人逐项确认；不以程序证明标签替代原文评价。'}
        write(folder/f"review-{job['sequence']:02d}.json",row);rows.append(row)
    groups={}
    for group in (['control','candidate'] if number<4 else ['development','evaluation_repeat']):
        selected=[r for r in rows if r['arm']==group] if number<4 else [r for r in rows if r['dataset']==group]
        groups[group]={'denominator':len(selected),'raw_answer_correct':sum(r['raw']['answer_correct'] is True for r in selected),'raw_strict':sum(r['raw']['strict_complete_success'] is True for r in selected),'final_answer_correct':sum(r['final']['answer_correct'] is True for r in selected),'final_strict':sum(r['final']['strict_complete_success'] is True for r in selected),'wrong_derivations':sum(r['wrong_derivation'] for r in selected),'end_to_end_seconds':sum(r['timing']['end_to_end_seconds'] for r in selected),'ambiguities':[r['case_id'] for r in selected if r['raw'].get('ambiguity') or r['final'].get('ambiguity')]}
    write(folder/'review-summary.json',{'reviewed_at':now(),'rows':rows,'groups':groups,'generation_calls':execution['confirmed_generation_calls']})
    if number<4:
        a=groups['control'];b=groups['candidate'];key=lambda s:(s['final_strict'],s['final_answer_correct'])
        choose='candidate' if key(b)>key(a) else 'control'
        policy=next(r['policy'] for r in rows if r['arm']==choose)
        write(folder/'selection.json',{'selected_at':now(),'selected_arm':choose,'retained_policy':policy,'reason':'系统严格成功优先，其次系统答案正确；同分保留当前验证方案，新增改动更少。','metrics':groups,'all_negative_results_preserved':True})
    print(json.dumps({'round':number,'groups':groups,'selected':choose if number<4 else 'frozen'},ensure_ascii=False))

if __name__=='__main__':
    action=sys.argv[1];n=int(sys.argv[2]);{'prepare':prepare,'review':review}[action](n)
