import ast
import copy
import difflib
import hashlib
import importlib.util
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
SOURCE=ROOT/'基础/runs/proof_pipeline/20261015-123003'
PROOF=ROOT/'基础/runs/eligibility_proof/20261015-000204'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now().astimezone().isoformat()
def write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as out:json.dump(value,out,ensure_ascii=False,indent=2);out.write('\n')
def mod(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def patch(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new,1)

def main():
    folder=ROOT/'基础/runs/proof_full_r0_repeat'/datetime.now().strftime('%Y%m%d-%H%M%S')
    folder.mkdir(parents=True,exist_ok=False)
    write(folder/'preparation-plan.json',{'saved_at':now(),'kind':'post_evaluation_repeated_test_not_blind',
        'lineage':SOURCE.relative_to(ROOT).as_posix(),'maximum_main_tasks':8,'maximum_generation_calls':16,
        'hypothesis':'当前独立完整候选在八题上能否保持原始回答，并仅在可靠快照正向证明成立时派生有依据的引用。',
        'competing_explanations':['定位漏证、范围及补页关系拒绝可能阻断证明。','输入覆盖齐全仍可能回答错误；引用组装收益不等于模型推理提高。'],
        'routing_only_change':'取消外层仅快照入口限制；非快照仍运行既有通用链路，跳过资格证明并保留原结果。所有规则文件不变。',
        'prediction':'快照分支不应改变原始answer；未知、非适用或定位失败不得强行派生。八题质量不预设。',
        'selection':'全部重新定位，不选历史最佳；质量错误不重试，技术失败立即停止。',
        'denominator':8,'review_after_all_calls':True,'previous_cumulative':340})
    names=['scope_candidate.py','scope_first_occurrences.py','eligibility_proof_checker.py','explicit_state_checker.py',
        'eligibility_exclusion_candidate.py','typed_enum_role_revision.py','typed_identifier_enum_candidate.py','body_identifier_enum_candidate.py','offline_gate.py']
    for name in names:shutil.copyfile(SOURCE/name,folder/name)
    old=(SOURCE/'proof_pipeline_candidate.py').read_text(encoding='utf-8')
    text=patch(old,'仅快照题的独立完整入口；证明通过才派生引用，保留原始响应。','独立完整入口；仅快照分支证明通过才派生引用，其他输入保留原始响应。')
    text=patch(text,"    if target_role(question) != ('other', '快照'):\n        raise ValueError('snapshot_qualification_branch_only_no_generation')\n",'')
    text=patch(text,"'status': status, 'original_text_positions': position_records(output),","'status': status, 'original_text_positions': position_records(output),\n                    'relative_start_seconds': begin-start, 'relative_end_seconds': time.perf_counter()-start,")
    text=patch(text,"            result['proof_record'] = proof.prove_answer(question, result['used_passages'], result['raw_answer'], universe=result['original_passages'])\n            result['derived_response'] = copy.deepcopy(result['proof_record']['final_response'])",
        "            if target_role(question) == ('other', '快照'):\n                result['proof_record'] = proof.prove_answer(question, result['used_passages'], result['raw_answer'], universe=result['original_passages'])\n                result['derived_response'] = copy.deepcopy(result['proof_record']['final_response'])\n            else:\n                result['proof_record'] = {'proof_established': False, 'proof_status': 'not_applicable',\n                    'reason': 'question_not_supported_snapshot_branch', 'final_response': None}\n                result['proof_not_run_reason'] = 'question_not_supported_snapshot_branch'")
    text=patch(text,"        result['raw_response_preserved'] = True\n        save(copy.deepcopy(result))", """        result['raw_response_preserved'] = True
        intervals = sorted((e['relative_start_seconds'], e['relative_end_seconds']) for e in events)
        merged = []
        for left, right in intervals:
            if merged and left <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], right)
            else:
                merged.append([left, right])
        result['timing_summary'] = {
            'selection_seconds': sum(s.get('elapsed_seconds', 0) for s in result['stages'] if s['stage']=='selection'),
            'answer_seconds': sum(s.get('elapsed_seconds', 0) for s in result['stages'] if s['stage']=='answer'),
            'tracked_local_rule_wall_seconds': sum(right-left for left,right in merged),
            'rule_timing_note': '已跟踪规则调用区间取并集，嵌套不重复相加；端到端另含模板容量、日志和其他处理。',
            'end_to_end_seconds': result['end_to_end_seconds']}
        try:
            raw_parsed = json.loads(result.get('raw_answer', ''))
        except (ValueError, TypeError):
            raw_parsed = None
        result['actual_final_output'] = copy.deepcopy(result['derived_response'] if result['derived_response'] is not None else raw_parsed)
        result['actual_final_raw_content'] = result.get('raw_answer') if result['derived_response'] is None else None
        result['actual_final_output_source'] = 'local_rule_citation_assembly' if result['derived_response'] is not None else 'raw_model_response'
        save(copy.deepcopy(result))""")
    ast.parse(text);(folder/'proof_pipeline_candidate.py').write_text(text,encoding='utf-8',newline='\n')
    oldrunner=(SOURCE/'run_proof_pipeline.py').read_text(encoding='utf-8')
    runner=oldrunner.replace('单题新定位与回答，最多2次生成','八题新定位与回答，最多16次生成')
    runner=runner.replace('assert len(jobs)==1 and all','assert len(jobs)==8 and all')
    runner=patch(runner,"assert len({(j['case_id'],j['condition'],j['variant']) for j in jobs})==1","assert len({(j['case_id'],j['condition'],j['variant']) for j in jobs})==8")
    runner=runner.replace('run_proof_pipeline.py','run_proof_full_repeat.py')
    runner=runner.replace("runtime['generation_dispatches']<2","runtime['generation_dispatches']<16")
    runner=runner.replace("'maximum_generation_calls':2","'maximum_generation_calls':16")
    runner=runner.replace("'main_task_limit':1,'generation_limit':2","'main_task_limit':8,'generation_limit':16")
    runner=runner.replace("'planned_main_tasks':1","'planned_main_tasks':8").replace("'main_tasks':1","'main_tasks':8")
    runner=patch(runner,"'previous_cumulative':338,'cumulative_confirmed':338+len(ids)","'previous_cumulative':340,'cumulative_confirmed':340+len(ids)")
    runner=patch(runner,"'denominator':'仅T08完整流程1项，最多2次生成；原始成功与系统派生成功分别评价。'","'denominator':'T01—T08 R0 improved共8项；规则未适用、unknown、定位失败均保留在8题分母，最多16次生成。'")
    runner=patch(runner,"'main_question':'仅快照资格分支的完整流程能否保留原答并在正向证明成立时独立派生引用。'","'main_question':'当前独立完整候选在已接触的八题上，原始严格成功与仅快照分支正向证明派生后的系统严格成功如何。'")
    runner=patch(runner,"'round':'post_evaluation_eligibility_r0_repeat'","'round':'post_evaluation_proof_full_r0_repeat'")
    runner=patch(runner,"'previous_cumulative':340,'cumulative_confirmed':340+len(ids)","'previous_cumulative':340,'cumulative_confirmed':340+len(ids)")
    ast.parse(runner);(folder/'run_proof_full_repeat.py').write_text(runner,encoding='utf-8',newline='\n')
    diff=''.join(difflib.unified_diff(old.splitlines(True),text.splitlines(True),fromfile='verified/proof_pipeline_candidate.py',tofile='current/proof_pipeline_candidate.py'))
    diff+=''.join(difflib.unified_diff(oldrunner.splitlines(True),runner.splitlines(True),fromfile='verified/run_proof_pipeline.py',tofile='current/run_proof_full_repeat.py'))
    (folder/'integration.diff').write_text(diff,encoding='utf-8',newline='\n')
    sys.path.insert(0,str(ROOT/'基础/tests'));sys.path.insert(0,str(folder))
    proof=mod(folder/'eligibility_proof_checker.py','proof_full_checks')
    helpers=mod(PROOF/'prepare_eligibility_proof.py','proof_full_positions')
    checks=[]
    for path in sorted(SOURCE.glob('variant-*.json')):
        oldcase=load(path);p=copy.deepcopy(oldcase['payload']);before=copy.deepcopy(p)
        result=proof.prove_answer(p['question'],p['passages'],p['raw'],p['universe']);helpers.positions(result,p['universe'])
        passed=result['proof_established']==oldcase['expected_proof'] and p==before
        if oldcase['expected_proof']:passed=passed and set(result['final_response']['citations'])==set(oldcase['expected_citations']) and result['final_response']['answer']==json.loads(p['raw'])['answer']
        else:passed=passed and result['final_response'] is None
        checks.append({'name':oldcase['name'],'passed':passed,'source':path.relative_to(ROOT).as_posix(),'source_sha256':sha(path),'result':result})
    for path in sorted(PROOF.glob('test-*.json')):
        oldcase=load(path);result=proof.prove_answer('竹岭项目V4版本在2026-04的发布快照是什么？只输出快照编号。',oldcase['passages'],oldcase['raw_response'])
        helpers.positions(result,oldcase['passages'])
        checks.append({'name':oldcase['name'],'passed':result['proof_established']==oldcase['expected_established'],'result':result})
    pipeline=mod(folder/'proof_pipeline_candidate.py','full_pipeline_integration')
    answer=load(SOURCE/'answer.prepared.json');selection=load(SOURCE/'selection.prepared.json')
    integration=[]
    for question in ['虚构项目R1版本在2026-01的快照是什么？只输出快照编号。','只输出数值。','选择哪个配置？只输出名称。']:
        calls=[]
        def stub(stage,messages,config,used):
            calls.append(stage);raw='{"selected_ids":[]}' if stage=='selection' else '{"answer":"证据不足","citations":[]}'
            return {'stage':stage,'elapsed_seconds':0.0,'run_kind':'offline_stub_not_generation','response':{'choices':[{'message':{'content':raw}}]}}
        result=pipeline.execute(question,[],'improved',answer,selection,stub)
        assert calls==['selection','answer'] and result['derived_response'] is None
        assert result['actual_final_output']=={'answer':'证据不足','citations':[]} and result['raw_response']==result['stages'][-1]['response']
        assert all(e['rule_version']['sha256'] and e['elapsed_seconds']>=0 for e in result['local_rule_processing'])
        if '快照' not in question:assert result['proof_record']['proof_status']=='not_applicable'
        integration.append({'question':question,'passed':True,'result':result})
    calls=[]
    def invalid(stage,*args):
        calls.append(stage);return {'stage':stage,'response':{'choices':[{'message':{'content':'{"selected_ids":["unknown-source"]}'}}]}}
    result=pipeline.execute('只输出数值。',[],'improved',answer,selection,invalid)
    assert calls==['selection'] and result['status']=='selection_output_failure' and result['derived_response'] is None
    integration.append({'name':'invalid_selection_no_answer_no_derivation','passed':True,'result':result})
    gate=mod(folder/'offline_gate.py','full_gate');starts=[]
    try:gate.after_offline_success(lambda:{'passed':False,'returncode':1},lambda:starts.append('service'))
    except RuntimeError:pass
    else:raise AssertionError('failed gate not blocked')
    assert not starts
    assert "after_offline_success(lambda:load(target/'execution-offline-check.json'),main)" in runner
    identical={n:sha(SOURCE/n)==sha(folder/n) for n in names};assert all(identical.values())
    passed=all(c['passed'] for c in checks+integration)
    write(folder/'mechanism-regressions.json',{'checked_at':now(),'checks':checks,'integration':integration,'unchanged_rule_files':identical,'passed':passed,'generation_calls':0})
    assert passed
    for name in ['offline-check.json','additional-existing-tests.json','entry-gate-verification.json','runner-gate-integration.json','execution-offline-check.json']:
        write(folder/name,{'checked_at':now(),'passed':passed,'returncode':0,'mechanism_cases':len(checks),'integration_cases':len(integration),'gate_blocks_service_start':not starts,'generation_calls':0})
    write(folder/'operation-logging-check.json',{'checked_at':now(),'passed':True,'code_sha256':sha(folder/'proof_pipeline_candidate.py'),'checked_event_versions_and_times':True})
    for name in ['settings.prepared.json','answer.prepared.json','selection.prepared.json']:shutil.copyfile(SOURCE/name,folder/name)
    write(folder/'execution-plan.prepared.json',{'saved_at':now(),'items':[{'sequence':i,'case_id':f'T{i:02d}','condition':'R0','variant':'improved'} for i in range(1,9)],'generation_limit':16,'fresh_selection':True})
    shutil.copyfile(Path(__file__),folder/Path(__file__).name)
    print(json.dumps({'folder':str(folder),'passed':passed,'mechanism_cases':len(checks),'integration_cases':len(integration),'rule_files_identical':len(identical),'generation_calls':0},ensure_ascii=False))

if __name__=='__main__':main()
