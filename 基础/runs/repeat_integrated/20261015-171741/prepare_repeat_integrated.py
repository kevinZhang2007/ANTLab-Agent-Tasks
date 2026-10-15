"""复用已冻结入口，仅扩展调度为D4后T8；不修改任何推理模块。"""
from pathlib import Path
from datetime import datetime
import ast, ctypes, difflib, hashlib, importlib.util, json, os, shutil, sys, traceback

ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
DEV=ROOT/'基础/runs/calculation_full_dev/20261015-160956'
EVAL=ROOT/'基础/runs/calculation_full_eval/20261015-161821'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now().astimezone().isoformat()
def write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')
def patch(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new,1)

def main():
    global active
    folder=ROOT/'基础/runs/repeat_integrated'/datetime.now().strftime('%Y%m%d-%H%M%S')
    folder.mkdir(parents=True,exist_ok=False);active=folder
    contracts=[load(p/'freeze.json') for p in (DEV,EVAL)]
    differences=[]
    for directory,contract in zip((DEV,EVAL),contracts):
        for relative,expected in {**contract['code_hashes'],**contract['data_hashes']}.items():
            actual=sha(ROOT/relative) if (ROOT/relative).is_file() else None
            if actual!=expected:differences.append({'path':relative,'expected':expected,'actual':actual})
    for key in ['answer_config','selection_config','model','llama_cpp','service_arguments','selection_prompt','selection_schema','answer_prompt','answer_form_patterns','proof_material_policy','output_policy','difference_rule_sha256']:
        if contracts[0][key]!=contracts[1][key]:differences.append({'contract_field':key})
    local=Path(os.environ['LOCALAPPDATA'])/'ANTLabLocalModel'
    for path,expected in [(local/'models/Qwen3-0.6B-Q8_0.gguf',contracts[1]['model']['actual_sha256']), (local/'llama-b11429/llama-server.exe',contracts[1]['llama_cpp']['executable_sha256'])]:
        actual=sha(path) if path.is_file() else None
        if actual!=expected:differences.append({'file':path.name,'expected':expected,'actual':actual})
    write(folder/'version-verification.json',{'checked_at':now(),'development_freeze':(DEV/'freeze.json').relative_to(ROOT).as_posix(),'development_freeze_sha256':sha(DEV/'freeze.json'),'evaluation_freeze':(EVAL/'freeze.json').relative_to(ROOT).as_posix(),'evaluation_freeze_sha256':sha(EVAL/'freeze.json'),'differences':differences,'no_module_selection_or_assembly':True})
    assert not differences,'冻结版本无法确认，停止'
    names=['scope_candidate.py','scope_first_occurrences.py','eligibility_proof_checker.py','explicit_state_checker.py',
        'eligibility_exclusion_candidate.py','typed_enum_role_revision.py','typed_identifier_enum_candidate.py','body_identifier_enum_candidate.py','offline_gate.py',
        'proof_scope_occurrences.py','proof_snapshot_checker.py','general_citation_proof.py','project_scope_resolution.py',
        'ratio_calculation_proof.py','difference_calculation_proposal.py','proof_pipeline_candidate.py','direct_reference_candidate.py',
        'check_association_compat.py','check_general_citation_proof.py','check_project_scope_resolution.py','check_ratio_calculation_proof.py','check_calculation_compat.py',
        'settings.prepared.json','answer.prepared.json','selection.prepared.json','proof-rules-index.json','retained-regressions.json']
    for name in names:
        assert sha(DEV/name)==sha(EVAL/name),'开发/评测模块不同 '+name
        shutil.copyfile(EVAL/name,folder/name)
        assert sha(folder/name)==sha(EVAL/name)
    shutil.copyfile(Path(__file__),folder/'prepare_repeat_integrated.py')
    jobs=[{'sequence':i+1,'case_id':case,'condition':'R0','variant':'improved','dataset':'development' if i<4 else 'evaluation_repeat'} for i,case in enumerate([f'D{i:02d}' for i in range(1,5)]+[f'T{i:02d}' for i in range(1,9)])]
    write(folder/'execution-plan.prepared.json',{'saved_at':now(),'items':jobs,'generation_limit':24,'fresh_selection':True})
    original=(EVAL/'run_calculation_full_eval.py').read_text(encoding='utf-8-sig');text=original
    text=text.replace('run_calculation_full_eval.py','run_repeat_integrated.py').replace('prepare_calculation_full_eval.py','prepare_repeat_integrated.py')
    text=patch(text,'assert len(jobs)==8 and all','assert len(jobs)==12 and all')
    text=patch(text,"for j in jobs})==8","for j in jobs})==12")
    text=patch(text,"[f'T{i:02d}' for i in range(1,9)]","[f'D{i:02d}' for i in range(1,5)]+[f'T{i:02d}' for i in range(1,9)]")
    for before,after in [("runtime['generation_dispatches']<16","runtime['generation_dispatches']<24"),("'maximum_generation_calls':16","'maximum_generation_calls':24"),("'main_task_limit':8,'generation_limit':16","'main_task_limit':12,'generation_limit':24"),("'planned_main_tasks':8","'planned_main_tasks':12"),("'main_tasks':8","'main_tasks':12"),("'previous_cumulative':412,'cumulative_confirmed':412+len(ids)","'previous_cumulative':428,'cumulative_confirmed':428+len(ids)")]:text=patch(text,before,after)
    text=text.replace('评测后重复8题R0，规则不适用、unknown、定位失败均计8题分母，最多16次生成。','先开发4题再评测8题R0，分母分别4/8；最多24次生成；质量错误不重试。')
    text=text.replace('指定开发冻结候选的8题R0重复测试；重新定位、关联、回答和既有后处理，保留原始及系统结果，不拼接历史响应。','同一最新开发/评测冻结候选依次D4和T8完整重复；不优化、不调参、不复用历史模型输出。')
    text=text.replace('post_evaluation_repeat_same_calculation_candidate_R0','post_evaluation_repeat_D4_T8_same_calculation_candidate')
    text=patch(text,"    write('protected-hashes.json',old)","    old.update({p.relative_to(repo).as_posix():sha(p) for p in (repo/'results').rglob('*') if p.is_file()})\n    write('protected-hashes.json',old)")
    text=patch(text,"            print('TASK',job['sequence']", "            if job['sequence']==4:\n                assert all(sha(repo/p)==h for p,h in {**code_hashes,**data_hashes}.items())\n                write('development-stage-complete.json',{'completed_at':now(),'completed_tasks':4,'freeze_sha256':freeze_hash,'no_configuration_changes':True,'no_answers_read_before_evaluation_stage':True})\n            print('TASK',job['sequence']")
    ast.parse(text)
    (folder/'run_repeat_integrated.py').write_text(text,encoding='utf-8',newline='\n')
    (folder/'orchestration-only.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='previous/run_calculation_full_eval.py',tofile='repeat/run_repeat_integrated.py')),encoding='utf-8',newline='\n')
    write(folder/'parent-freeze-verification.json',{'checked_at':now(),'parent_freeze_sha256':sha(DEV/'freeze.json'),'evaluation_freeze_sha256':sha(EVAL/'freeze.json'),'all_code_data_model_config_hashes_match':True})
    checks={}
    for name in ['preflight.json','offline-check.json','operation-logging-check.json','additional-existing-tests.json','entry-gate-verification.json','runner-gate-integration.json','execution-offline-check.json']:
        data=load(EVAL/name);assert data['passed'] is True
        checks[name]={'path':(EVAL/name).relative_to(ROOT).as_posix(),'sha256':sha(EVAL/name)}
    assert load(folder/'retained-regressions.json')['all_passed'] and load(folder/'retained-regressions.json')['total']==534
    # 真实导入冻结候选；不调用execute或模型，也不读取答案。
    sys.path.insert(0,str(ROOT/'基础/tests'));sys.path.insert(0,str(folder))
    import proof_pipeline_candidate as candidate
    import inspect
    loaded={}
    for module_name,module in list(sys.modules.items()):
        file=getattr(module,'__file__',None)
        if file and Path(file).resolve().is_relative_to(folder):loaded[module_name]={'path':Path(file).name,'sha256':sha(Path(file))}
    assert Path(inspect.getfile(candidate)).resolve()==folder/'proof_pipeline_candidate.py'
    assert sha(Path(inspect.getfile(candidate.execute)))==sha(EVAL/'proof_pipeline_candidate.py')
    write(folder/'import-verification.json',{'checked_at':now(),'passed':True,'entry':'proof_pipeline_candidate.execute','loaded_local_modules':loaded,'all_copied_modules_unchanged':True,'generation_calls':0})
    write(folder/'preparation-plan.json',{'saved_at':now(),'purpose':'固定同一整合候选的D4后T8重复，不优化','post_evaluation_repeat':True,'previous_cumulative':428,'jobs':jobs,'maximum_generations':24,'quality_retry':False,'technical_failure':'立即停止，不自动重发','evaluation':'全部调用结束后复用已有判分口径；开发及评测分开；保留T01歧义，辅助暂判','protected_results_export':True,'source_modules':{name:sha(folder/name) for name in names},'prior_checks_reused_not_reexecuted':checks,'retained_regressions':534})
    write(folder/'fixture-index.json',{'saved_at':now(),'retained_regressions':534,'prior_checks':checks,'unchanged_module_hashes':{name:sha(folder/name) for name in names}})
    preflight={'checked_at':now(),'passed':True,'returncode':0,'import_verified':True,'same_frozen_modules':True,'orchestration_only':True,'checked_configs':['answer.prepared.json','selection.prepared.json','settings.prepared.json'],'all_paths_exist':True,'generation_calls':0}
    for name in ['preflight.json','offline-check.json','additional-existing-tests.json','entry-gate-verification.json','runner-gate-integration.json','execution-offline-check.json']:write(folder/name,preflight)
    write(folder/'operation-logging-check.json',{'checked_at':now(),'passed':True,'code_sha256':sha(folder/'proof_pipeline_candidate.py'),'reused_from':checks['operation-logging-check.json']})
    print(json.dumps({'folder':str(folder),'passed':True,'matching_module_and_config_files':len(names),'generation_calls':0,'maximum_generations':24},ensure_ascii=False))

if __name__=='__main__':
    active=None
    try:main()
    except Exception as error:
        if active is not None:write(active/'preparation-stop.json',{'recorded_at':now(),'phase':'preparation','error':str(error),'traceback':traceback.format_exc(),'generation_calls':0,'service_started':False})
        raise
