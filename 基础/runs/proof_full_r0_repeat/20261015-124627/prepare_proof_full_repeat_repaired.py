import ast
import copy
import difflib
import hashlib
import importlib.util
import json
import shutil
import sys
import os
import traceback
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
    global active_folder
    folder=ROOT/'基础/runs/proof_full_r0_repeat'/datetime.now().strftime('%Y%m%d-%H%M%S')
    folder.mkdir(parents=True,exist_ok=False)
    active_folder=folder
    write(folder/'preparation-plan.json',{'saved_at':now(),'kind':'post_evaluation_repeated_test_not_blind',
        'lineage':SOURCE.relative_to(ROOT).as_posix(),'maximum_main_tasks':8,'maximum_generation_calls':16,
        'hypothesis':'当前独立完整候选在八题上能否保持原始回答，并仅在可靠快照正向证明成立时派生有依据的引用。',
        'competing_explanations':['定位漏证、范围及补页关系拒绝可能阻断证明。','输入覆盖齐全仍可能回答错误；引用组装收益不等于模型推理提高。'],
        'routing_only_change':'取消外层仅快照入口限制；非快照仍运行既有通用链路，跳过资格证明并保留原结果。所有规则文件不变。',
        'prediction':'快照分支不应改变原始answer；未知、非适用或定位失败不得强行派生。八题质量不预设。',
        'selection':'全部重新定位，不选历史最佳；质量错误不重试，技术失败立即停止。',
        'denominator':8,'review_after_all_calls':True,'previous_cumulative':340})
    # 原汇总未提供逐文件路径，因此建立明确清单；缺字段直接失败，不跳过。
    variant_names=['variant-01.json','variant-02.json','variant-03.json','variant-04.json','variant-05.json','variant-06.json','variant-07.json','variant-08.json','variant-09.json']
    regression_names=['test-01.json','test-02.json','test-03.json','test-04.json','test-05.json','test-06.json','test-07.json','test-08.json','test-09.json','test-10.json','test-11.json','test-12.json','test-13.json','test-14.json']
    assert load(SOURCE/'variant-results.json')['total']==len(variant_names)
    assert load(PROOF/'offline-check.json')['total']==len(regression_names)
    fixtures=[]
    for kind,directory,nameset in [('mechanism_variant',SOURCE,variant_names),('prior_regression',PROOF,regression_names)]:
        for name in nameset:
            path=directory/name
            assert path.is_file() and path.suffix=='.json',str(path)
            value=load(path);assert isinstance(value,dict),str(path)
            required={'name','payload','expected_proof','expected_citations'} if kind=='mechanism_variant' else {'name','passages','raw_response','expected_established'}
            assert required<=value.keys(),(name,required-value.keys())
            if kind=='mechanism_variant':
                payload=value['payload'];assert isinstance(payload,dict) and {'question','passages','raw','universe'}<=payload.keys()
                assert isinstance(payload['question'],str) and isinstance(payload['raw'],str) and isinstance(value['expected_proof'],bool)
                for key in ['passages','universe']:
                    assert isinstance(payload[key],list)
                    assert all(isinstance(p,dict) and all(isinstance(p.get(k),str) for k in ['id','source','text']) for p in payload[key])
            else:
                assert isinstance(value['passages'],list) and isinstance(value['raw_response'],str) and isinstance(value['expected_established'],bool)
            fixtures.append({'kind':kind,'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'required_fields':sorted(required),'structure_checked':True})
    write(folder/'fixture-index.json',{'created_at':now(),'explicit_file_list':fixtures,'summary_files_excluded':['variant-results.json','offline-check.json'],'no_silent_skipping':True})
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
    for path in [SOURCE/name for name in variant_names]:
        oldcase=load(path);p=copy.deepcopy(oldcase['payload']);before=copy.deepcopy(p)
        result=proof.prove_answer(p['question'],p['passages'],p['raw'],p['universe']);helpers.positions(result,p['universe'])
        passed=result['proof_established']==oldcase['expected_proof'] and p==before
        if oldcase['expected_proof']:passed=passed and set(result['final_response']['citations'])==set(oldcase['expected_citations']) and result['final_response']['answer']==json.loads(p['raw'])['answer']
        else:passed=passed and result['final_response'] is None
        checks.append({'name':oldcase['name'],'passed':passed,'source':path.relative_to(ROOT).as_posix(),'source_sha256':sha(path),'result':result})
    for path in [PROOF/name for name in regression_names]:
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
    # 启动前一次性核查依赖、配置、输入、输出保护与Schema结构；不发送请求。
    import runner as data_runner
    settings=load(folder/'settings.prepared.json')
    jobs=load(folder/'execution-plan.prepared.json')['items']
    assert len(jobs)==8 and [j['case_id'] for j in jobs]==[f'T{i:02d}' for i in range(1,9)]
    assert all(j['condition']=='R0' and j['variant']=='improved' for j in jobs)
    inputs=[]
    for job in jobs:
        case,passages,_,_=data_runner.prepare(job['case_id'],'R0','baseline')
        assert isinstance(case['question'],str) and isinstance(passages,list) and passages
        assert all(all(isinstance(p.get(k),str) for k in ['id','source','text']) for p in passages)
        messages,conf,rule=pipeline.answer_request(case['question'],passages,answer)
        schema=conf['parameters']['response_format']['json_schema']['schema']
        assert schema['type']=='object' and schema['required']==['answer','citations']
        assert schema['properties']['answer']['type']=='string' and schema['properties']['citations']['items']['type']=='string'
        assert [m['role'] for m in messages]==['system','user']
        inputs.append({'case_id':job['case_id'],'condition':'R0','passage_count':len(passages),'message_structure_checked':True,'schema_structure_checked':True})
    path_checks=[]
    for name,expected in {**settings['data_sha256'],**settings['code_sha256']}.items():
        path=ROOT/name;assert path.is_file() and sha(path)==expected,name
        path_checks.append({'path':name,'exists':True,'sha256_matches':True})
    model_root=Path(os.environ['LOCALAPPDATA'])/'ANTLabLocalModel'
    for path,expected in [(model_root/'models/Qwen3-0.6B-Q8_0.gguf',settings['model']['actual_sha256']),
        (model_root/'llama-b11429/llama-server.exe',settings['llama_cpp']['executable_sha256'])]:
        assert path.is_file() and sha(path)==expected,str(path)
        path_checks.append({'path':str(path).replace(str(model_root),'%LOCALAPPDATA%/ANTLabLocalModel'),'exists':True,'sha256_matches':True})
    assert answer==load(SOURCE/'answer.prepared.json') and selection==load(SOURCE/'selection.prepared.json')
    assert selection['parameters']['response_format']['json_schema']['schema']==pipeline.selection.SELECTION_SCHEMA
    for code in folder.glob('*.py'):ast.parse(code.read_text(encoding='utf-8-sig'))
    assert not list(folder.glob('run-*.json')) and not (folder/'freeze.json').exists() and not (folder/'runtime.json').exists()
    parsed=ast.parse(Path(__file__).read_text(encoding='utf-8'))
    fixture_globs=[node for node in ast.walk(parsed) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)
        and node.func.attr=='glob' and any(isinstance(arg,ast.Constant) and arg.value=='variant-'+'*.json' for arg in node.args)]
    assert not fixture_globs and len(fixtures)==23
    write(folder/'preflight.json',{'checked_at':now(),'passed':True,'returncode':0,'fixture_index':'fixture-index.json','fixture_count':len(fixtures),
        'input_checks':inputs,'path_hash_checks':path_checks,'configuration_unchanged':True,'schema_structure_and_original_source_checked':True,
        'native_schema_support':'沿用已验证的相同本机b11429、相同Schema派生实现；此处是结构和来源核查，不冒充新原生语法正反例测试。',
        'imports_checked':True,'output_directory_new_and_empty_of_runs':True,'offline_failure_gate_exercised':True,
        'patch_landed':"variant_names显式列表；逐项类型/必需字段断言；不扫描variant通配符，不缺字段跳过。",'generation_calls':0})
    # 门禁本身读取完整预检结果；失败与运行器之间没有自动继续路径。
    entry=(folder/'run_proof_full_repeat.py').read_text(encoding='utf-8')
    entry=patch(entry,"    assert load(folder/'offline-check.json')['passed']","    assert load(folder/'preflight.json')['passed'] and load(folder/'preflight.json')['returncode']==0\n    assert load(folder/'offline-check.json')['passed']")
    entry=patch(entry,"'execution-plan.prepared.json','scope_candidate.py'","'execution-plan.prepared.json','fixture-index.json','preflight.json','scope_candidate.py'")
    (folder/'run_proof_full_repeat.py').write_text(entry,encoding='utf-8',newline='\n')
    shutil.copyfile(Path(__file__),folder/Path(__file__).name)
    failed_helper=ROOT/'基础/runs/proof_full_r0_repeat/20261015-124043/prepare_proof_full_repeat.py'
    repair=''.join(difflib.unified_diff(failed_helper.read_text(encoding='utf-8').splitlines(True),Path(__file__).read_text(encoding='utf-8').splitlines(True),
        fromfile='preserved_failed/prepare_proof_full_repeat.py',tofile='repaired/prepare_proof_full_repeat_repaired.py'))
    (folder/'preparation-repair.diff').write_text(repair,encoding='utf-8',newline='\n')
    print(json.dumps({'folder':str(folder),'passed':passed,'mechanism_cases':len(checks),'integration_cases':len(integration),'rule_files_identical':len(identical),'generation_calls':0},ensure_ascii=False))

if __name__=='__main__':
    active_folder=None
    try:main()
    except Exception as error:
        if active_folder is not None:
            write(active_folder/'technical-stop.json',{'recorded_at':now(),'phase':'preparation','error_type':type(error).__name__,
                'detail':str(error),'traceback':traceback.format_exc(),'generation_dispatches':0,'service_started':False})
        raise
