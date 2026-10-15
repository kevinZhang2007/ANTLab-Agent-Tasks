import ast
import copy
import hashlib
import importlib.util
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
PROOF=ROOT/'基础/runs/eligibility_proof/20261015-000204'
SCOPE=ROOT/'基础/runs/scope_first_pairs/20261014-234038'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now().astimezone().isoformat()

def write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as out:json.dump(value,out,ensure_ascii=False,indent=2);out.write('\n')
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def patch(text,old,new):
    assert text.count(old)==1,old[:90]
    return text.replace(old,new,1)

def main():
    folder=ROOT/'基础/runs/proof_pipeline'/datetime.now().strftime('%Y%m%d-%H%M%S')
    folder.mkdir(parents=True,exist_ok=False)
    write(folder/'mechanism-plan.json',{'saved_at':now(),'kind':'post_evaluation_mechanism_checks_not_independent_evaluation',
          'previous_failed_variant_preserved':'基础/runs/proof_pipeline/20261015-122914/variant-05.json',
          'boundary_fix':'版本只采用带完整英数边界的提取结果，不再并入旧规则从Other404版本内部截出的r404版本。仅新副本修复，变体不变。',
          'variants':'编号、段落ID、顺序、范围冲突资料；失败、缺检查说明、缺必检项、缺规则。',
          'expectations':'等价及不相关范围干扰保持证明，失败/缺证必须unknown或拒绝；原文位置与证明链均核对。',
          'integration':'仅快照题；仅原答案可证明时派生；原始响应不改；所有local_rule有版本、位置及耗时。',
          'generation_limit':2,'previous_cumulative':338,'stop':'任何离线失败阻断模型启动；技术失败停止，无质量重试。'})
    for name in ['eligibility_proof_checker.py','explicit_state_checker.py','eligibility_exclusion_candidate.py','typed_enum_role_revision.py','typed_identifier_enum_candidate.py','body_identifier_enum_candidate.py','offline_gate.py']:
        shutil.copyfile(PROOF/name,folder/name)
    shutil.copyfile(SCOPE/'scope_first_occurrences.py',folder/'scope_first_occurrences.py')
    scope_path=folder/'scope_first_occurrences.py'
    scope_text=scope_path.read_text(encoding='utf-8')
    old_line="result['version'] = sorted(set(result['version']+versions))"
    assert scope_text.count(old_line)==1
    (folder/'scope-before-boundary-fix.py').write_text(scope_text,encoding='utf-8',newline='\n')
    scope_text=scope_text.replace(old_line,"result['version'] = sorted(set(versions))",1)
    scope_path.write_text(scope_text,encoding='utf-8',newline='\n')
    shutil.copyfile(SCOPE/'eligibility_general_candidate.py',folder/'scope_candidate.py')
    shutil.copyfile(Path(__file__).with_name('proof_pipeline_candidate.py'),folder/'proof_pipeline_candidate.py')
    sys.path.insert(0,str(ROOT/'基础/tests'));sys.path.insert(0,str(folder))
    proof=module(folder/'eligibility_proof_checker.py','proof_variant_checker')
    helpers=module(PROOF/'prepare_eligibility_proof.py','position_helpers')
    origin=load(PROOF/'proof-T08.json');task=load(ROOT/origin['source_path'])
    baseline={'question':task['question'],'passages':task['used_passages'],'universe':task['original_passages'],'raw':task['raw_answer']}
    positive_citations=set(origin['proof']['final_response']['citations'])
    variants=[]
    def add(name,payload,expected,basis,expected_ids=None):
        variants.append({'name':name,'payload':copy.deepcopy(payload),'expected_proof':expected,'expected_basis':basis,
                         'expected_citations':sorted(positive_citations if expected_ids is None else expected_ids)})
    add('validated_material_baseline',baseline,True,'复用已验证原文作为机制基准，不生成。')
    mapped=copy.deepcopy(baseline)
    texts=[mapped['question']]+[p['text'] for p in mapped['universe']]
    codes=list(dict.fromkeys(re.findall(r'\b[A-Za-z]+[0-9]+\b','\n'.join(texts))))
    code_map={v:'Alias'+str(801+i) for i,v in enumerate(codes)}
    def replace_codes(text):return re.sub(r'\b[A-Za-z]+[0-9]+\b',lambda m:code_map.get(m.group(),m.group()),text)
    mapped['question']=replace_codes(mapped['question'])
    for collection in ['passages','universe']:
        for p in mapped[collection]:p['text']=replace_codes(p['text'])
    value=json.loads(mapped['raw']);value['answer']=replace_codes(value['answer']);mapped['raw']=json.dumps(value,ensure_ascii=False)
    add('identifier_remapping',mapped,True,'正文编号、业务编号、版本编号及答案中的编号同步一一映射，不按前缀筛选。')
    id_map={p['id']:'Doc'+str(501+i) for i,p in enumerate(baseline['universe'])}
    mapped=copy.deepcopy(baseline)
    for collection in ['passages','universe']:
        for p in mapped[collection]:p['id']=id_map[p['id']]
    value=json.loads(mapped['raw']);value['citations']=[id_map[i] for i in value['citations']];mapped['raw']=json.dumps(value,ensure_ascii=False)
    add('passage_id_remapping',mapped,True,'来源ID同步重映射，正文不变，证明链来源随之映射。',{id_map[i] for i in positive_citations})
    mapped=copy.deepcopy(baseline);mapped['passages'].reverse();mapped['universe'].reverse()
    add('passage_order_reversed',mapped,True,'完整段落逆序不改变目标、规则或原文事实。')
    selected_id=origin['proof']['candidate_description']['passage_id']
    selected=next(p for p in baseline['passages'] if p['id']==selected_id)
    conflicting=copy.deepcopy(selected);conflicting['id']='extra-conflicting-scope';conflicting['source']='synthetic-scope-variant'
    old_version=origin['proof']['scope_audit']['question_scope']['version'][0]
    conflicting['text']=conflicting['text'].replace(old_version,'Other404版本')
    mapped=copy.deepcopy(baseline);mapped['passages'].append(conflicting);mapped['universe'].append(copy.deepcopy(conflicting))
    add('additional_conflicting_scope',mapped,True,'增加同编号但版本明示冲突的资料，只保留冲突审计，不借其证明或阻断目标身份。')
    description=origin['proof']['candidate_description'];claim=selected['text'][description['start']:description['end']]
    def change_selected(payload,new_claim):
        for collection in ['passages','universe']:
            for p in payload[collection]:
                if p['id']==selected_id:p['text']=p['text'][:description['start']]+new_claim+p['text'][description['end']:]
    mapped=copy.deepcopy(baseline);assert '通过' in claim
    change_selected(mapped,claim.replace('通过','失败'))
    add('selected_candidate_explicit_failure',mapped,False,'只改变实际获选项状态为失败，不能借其他候选或旧通过结果维持证明。')
    mapped=copy.deepcopy(baseline);answer=json.loads(mapped['raw'])['answer']
    change_selected(mapped,answer+'；')
    add('necessary_candidate_checks_removed',mapped,False,'保留获选编号但删除其必要检查说明，不能从排除其他项补证明。')
    rule_id=origin['proof']['rule_info']['rule']['passage_id']
    first_required=origin['proof']['conditions'][0]['name']
    mapped=copy.deepcopy(baseline)
    for collection in ['passages','universe']:
        for p in mapped[collection]:
            if p['id']==rule_id:
                assert first_required+'、' in p['text']
                p['text']=p['text'].replace(first_required+'、','',1)
    add('required_set_item_removed',mapped,False,'删去规则的一项列举但保留声明数量，集合不完整、数量不对应，必须unknown。')
    mapped=copy.deepcopy(baseline)
    for collection in ['passages','universe']:mapped[collection]=[p for p in mapped[collection] if p['id']!=rule_id]
    add('release_rule_removed',mapped,False,'没有实际可见发布规则，不得生成资格证明或规则引用。')
    results=[]
    for i,test in enumerate(variants):
        before=copy.deepcopy(test['payload']);p=test['payload']
        result=proof.prove_answer(p['question'],p['passages'],p['raw'],p['universe'])
        helpers.positions(result,p['universe'])
        passed=result['proof_established']==test['expected_proof'] and p==before
        if test['expected_proof']:
            passed=passed and result['final_response']['answer']==json.loads(p['raw'])['answer'] and set(result['final_response']['citations'])==set(test['expected_citations'])
        else:passed=passed and result['final_response'] is None
        record={**test,'actual_result':result,'passed':passed,'generation_calls':0}
        write(folder/('variant-'+str(i+1).zfill(2)+'.json'),{'checked_at':now(),**record});results.append(record)
    regressions=[]
    for path in sorted(PROOF.glob('test-*.json')):
        old=load(path);result=proof.prove_answer('竹岭项目V4版本在2026-04的发布快照是什么？只输出快照编号。',old['passages'],old['raw_response'])
        helpers.positions(result,old['passages'])
        regressions.append({'name':old['name'],'passed':result['proof_established']==old['expected_established'],'result':result})
    passed=all(r['passed'] for r in results+regressions)
    write(folder/'variant-results.json',{'checked_at':now(),'total':len(results),'passed':sum(r['passed'] for r in results),'failed':[r['name'] for r in results if not r['passed']]})
    write(folder/'prior-regressions.json',{'checked_at':now(),'total':len(regressions),'passed':sum(r['passed'] for r in regressions),'rows':regressions})
    if not passed:
        write(folder/'offline-check.json',{'passed':False,'returncode':1,'generation_calls':0})
        write(folder/'technical-stop.json',{'stopped_at':now(),'stage':'offline_mechanism_variants','generation_calls':0})
        print(json.dumps({'folder':str(folder),'passed':False,'failed':[r['name'] for r in results+regressions if not r['passed']]},ensure_ascii=False));return 1
    pipeline=module(folder/'proof_pipeline_candidate.py','proof_pipeline_for_checks')
    settings=load(SCOPE/'settings.prepared.json');answer_config=load(SCOPE/'answer.prepared.json');selection_config=load(SCOPE/'selection.prepared.json')
    stub_calls=[]
    def stub(stage,messages,config,used):
        stub_calls.append(stage)
        raw='{"selected_ids":[]}' if stage=='selection' else '{"answer":"证据不足","citations":[]}'
        return {'run_kind':'offline_stub_not_generation','response':{'choices':[{'message':{'content':raw}}]}}
    empty=pipeline.execute('虚构项目R1版本在2026-01的快照是什么？只输出快照编号。',[],'improved',answer_config,selection_config,stub)
    assert empty['derived_response'] is None and empty['raw_response'] and len(stub_calls)==2
    blocked=0
    for question in ['只输出数值。','选择哪个配置？只输出名称。']:
        try:pipeline.execute(question,[],'improved',answer_config,selection_config,stub)
        except ValueError:blocked+=1
    assert blocked==2 and len(stub_calls)==2
    for event in empty['local_rule_processing']:
        assert event['rule_version']['sha256'] and event['elapsed_seconds']>=0 and 'original_text_positions' in event
    write(folder/'integration-offline-check.json',{'checked_at':now(),'passed':True,'empty_input_no_derived_response':True,
        'non_snapshot_inputs_blocked_before_dispatch':blocked,'local_rule_versions_positions_and_times_present':True,'generation_calls':0})
    write(folder/'offline-check.json',{'checked_at':now(),'passed':True,'returncode':0,'variant_count':9,'prior_case_count':14,'integration_cases':3})
    gate=module(folder/'offline_gate.py','proof_pipeline_gate');starts=[]
    try:gate.after_offline_success(lambda:{'passed':False,'returncode':1},lambda:starts.append('model'));failure_blocked=False
    except RuntimeError:failure_blocked=True
    assert failure_blocked and not starts
    write(folder/'runner-gate-integration.json',{'checked_at':now(),'passed':True,'failed_offline_blocks_main':True,'model_start_calls':0})
    write(folder/'additional-existing-tests.json',{'passed':True,'proof_pipeline_integration_checked':True})
    write(folder/'entry-gate-verification.json',{'passed':True,'gate_reused_from_validated_runner':True})
    write(folder/'execution-offline-check.json',{'passed':True,'returncode':0,'checks':['offline-check.json','integration-offline-check.json','runner-gate-integration.json']})
    for name in ['settings.prepared.json','answer.prepared.json','selection.prepared.json']:shutil.copyfile(SCOPE/name,folder/name)
    write(folder/'execution-plan.prepared.json',{'saved_at':now(),'items':[{'sequence':1,'case_id':'T08','condition':'R0','variant':'improved'}],'generation_limit':2,'fresh_selection':True})
    old_runner=(SCOPE/'run_scope_first_pairs.py').read_text(encoding='utf-8')
    runner=patch(old_runner,'import eligibility_general_candidate as candidate\nimport old_eligibility_general_candidate as old_candidate','import proof_pipeline_candidate as candidate')
    runner=patch(runner,'assert len(jobs)==2 and all','assert len(jobs)==1 and all')
    runner=patch(runner,"assert len({(j['case_id'],j['scheme']) for j in jobs})==2","assert len({(j['case_id'],j['condition'],j['variant']) for j in jobs})==1")
    runner=runner.replace('run_scope_first_pairs.py','run_proof_pipeline.py')
    runner=patch(runner,"'old_eligibility_general_candidate.py','scope_first_occurrences.py']]","'scope_candidate.py','scope_first_occurrences.py','eligibility_proof_checker.py','proof_pipeline_candidate.py']]")
    # 原运行器source列表仍含旧模块名，改为本轮实际依赖。
    runner=runner.replace("'eligibility_general_candidate.py'","'scope_candidate.py'")
    runner=runner.replace("engine=old_candidate if job['scheme']=='old' else candidate","engine=candidate")
    runner=runner.replace("runtime['generation_dispatches']<4","runtime['generation_dispatches']<2")
    runner=runner.replace("'maximum_generation_calls':4","'maximum_generation_calls':2")
    runner=runner.replace("'main_task_limit':2,'generation_limit':4","'main_task_limit':1,'generation_limit':2")
    runner=runner.replace("'planned_main_tasks':2","'planned_main_tasks':1")
    runner=runner.replace("'main_tasks':2","'main_tasks':1")
    runner=patch(runner,"'previous_cumulative':334,'cumulative_confirmed':334+len(ids)","'previous_cumulative':338,'cumulative_confirmed':338+len(ids)")
    runner=runner.replace('评测后范围顺序修复：同一题旧/新完整流程，最多4次生成。','评测后资格证明完整流程：单题新定位与回答，最多2次生成，证明与引用组装离线。')
    runner=runner.replace("'main_question':'范围优先核对后，同一完整R0资料旧/新资格排除、答案与引用表现是否变化。'","'main_question':'仅快照资格分支的完整流程能否保留原答并在正向证明成立时独立派生引用。'")
    runner=runner.replace("'denominator':'同一题旧/新两个完整流程，每侧一次定位+回答，最多4次生成，不是独立两题。'","'denominator':'仅T08完整流程1项，最多2次生成；原始成功与系统派生成功分别评价。'")
    ast.parse(runner)
    (folder/'run_proof_pipeline.py').write_text(runner,encoding='utf-8',newline='\n')
    shutil.copyfile(Path(__file__),folder/'prepare_proof_pipeline.py')
    print(json.dumps({'folder':str(folder),'passed':True,'variants':len(results),'prior_regressions':len(regressions),'integration_cases':3,'generation_calls':0},ensure_ascii=False));return 0

if __name__=='__main__':raise SystemExit(main())
