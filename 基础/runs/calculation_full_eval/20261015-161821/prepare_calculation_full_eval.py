"""指定冻结候选的评测R0调度准备；候选模块逐字复制，不调整方案。"""
import ast, difflib, hashlib, json, os, shutil, traceback
from pathlib import Path
from datetime import datetime
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
BASE=ROOT/'基础/runs/calculation_full_dev/20261015-160956'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now().astimezone().isoformat()
def write(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as o:json.dump(v,o,ensure_ascii=False,indent=2);o.write('\n')
def patch(t,a,b):
    assert t.count(a)==1,a[:100]
    return t.replace(a,b,1)
def main():
    global active
    folder=ROOT/'基础/runs/calculation_full_eval'/datetime.now().strftime('%Y%m%d-%H%M%S');folder.mkdir(parents=True,exist_ok=False);active=folder
    contract=load(BASE/'freeze.json');differences=[]
    for p,wanted in {**contract['code_hashes'],**contract['data_hashes']}.items():
        actual=sha(ROOT/p) if (ROOT/p).is_file() else None
        if actual!=wanted:differences.append({'path':p,'expected':wanted,'actual':actual})
    local=Path(os.environ['LOCALAPPDATA'])/'ANTLabLocalModel'
    for p,wanted in [(local/'models/Qwen3-0.6B-Q8_0.gguf',contract['model']['actual_sha256']),
                     (local/'llama-b11429/llama-server.exe',contract['llama_cpp']['executable_sha256'])]:
        actual=sha(p) if p.is_file() else None
        if actual!=wanted:differences.append({'path':str(p),'expected':wanted,'actual':actual})
    settings=load(BASE/'settings.prepared.json');answer=load(BASE/'answer.prepared.json');selection=load(BASE/'selection.prepared.json')
    assert answer==contract['answer_config'] and selection==contract['selection_config'] and settings['service_arguments']==contract['service_arguments']
    write(folder/'parent-freeze-verification.json',{'checked_at':now(),'parent':(BASE/'freeze.json').relative_to(ROOT).as_posix(),
        'parent_freeze_sha256':sha(BASE/'freeze.json'),'checked_code_and_data_files':len(contract['code_hashes'])+len(contract['data_hashes']),
        'differences':differences,'config_and_service_arguments_match':True})
    assert not differences,'指定冻结候选哈希不符，停止，不另选版本'
    write(folder/'preparation-plan.json',{'saved_at':now(),'kind':'post_evaluation_R0_repeat_same_candidate',
        'parent_freeze':(BASE/'freeze.json').relative_to(ROOT).as_posix(),'previous_cumulative':412,'main_tasks':8,'generation_limit':16,
        'question':'同一已验证候选在已接触的8题R0重新定位与回答后的原始和系统最终表现。',
        'not_blind_or_generalization':True,'fixed':'候选模块和配置逐字复制；只修改运行清单、分母、次数上限、记录目录及原始冻结核对。',
        'order':[f'T{i:02d}' for i in range(1,9)],'fresh_selection':True,'no_history_model_outputs_used':True,
        'compare_to':'基础/runs/integrated_dev_eval/20261015-134437（上一版完整8题结果，历史比较，非同步配对）',
        'stop':'技术失败保存停止；质量失败不重试、不临时修补；最多16次生成，结束停止自有服务。',
        'review':'全部调用后按已有原文依据及澄清复核；保留T01歧义和8题分母，标签辅助暂判。'})
    names=['scope_candidate.py','scope_first_occurrences.py','eligibility_proof_checker.py','explicit_state_checker.py',
        'eligibility_exclusion_candidate.py','typed_enum_role_revision.py','typed_identifier_enum_candidate.py','body_identifier_enum_candidate.py','offline_gate.py',
        'proof_scope_occurrences.py','proof_snapshot_checker.py','general_citation_proof.py','project_scope_resolution.py',
        'ratio_calculation_proof.py','difference_calculation_proposal.py','proof_pipeline_candidate.py','direct_reference_candidate.py',
        'check_association_compat.py','check_general_citation_proof.py','check_project_scope_resolution.py','check_ratio_calculation_proof.py','check_calculation_compat.py',
        'settings.prepared.json','answer.prepared.json','selection.prepared.json','proof-rules-index.json','retained-regressions.json']
    for name in names:
        shutil.copyfile(BASE/name,folder/name);assert sha(folder/name)==sha(BASE/name)
    shutil.copyfile(Path(__file__),folder/Path(__file__).name)
    runner=(BASE/'run_calculation_full_dev.py').read_text(encoding='utf-8');original=runner
    runner=runner.replace('run_calculation_full_dev.py','run_calculation_full_eval.py').replace('prepare_calculation_full_dev.py',Path(__file__).name)
    runner=runner.replace('assert len(jobs)==4 and all','assert len(jobs)==8 and all').replace("for j in jobs})==4","for j in jobs})==8")
    runner=patch(runner,"[f'D{i:02d}' for i in range(1,5)]","[f'T{i:02d}' for i in range(1,9)]")
    runner=runner.replace("runtime['generation_dispatches']<8","runtime['generation_dispatches']<16").replace("'maximum_generation_calls':8","'maximum_generation_calls':16")
    runner=runner.replace("'main_task_limit':4,'generation_limit':8","'main_task_limit':8,'generation_limit':16").replace("'planned_main_tasks':4","'planned_main_tasks':8").replace("'main_tasks':4","'main_tasks':8")
    runner=patch(runner,"'previous_cumulative':404,'cumulative_confirmed':404+len(ids)","'previous_cumulative':412,'cumulative_confirmed':412+len(ids)")
    runner=patch(runner,"    root = Path(os.environ['LOCALAPPDATA'])/'ANTLabLocalModel'", "    parent_folder = repo/'基础/runs/calculation_full_dev/20261015-160956'\n    parent_contract=load(parent_folder/'freeze.json')\n    assert sha(parent_folder/'freeze.json')==load(folder/'parent-freeze-verification.json')['parent_freeze_sha256']\n    assert all(sha(repo/p)==h for p,h in {**parent_contract['code_hashes'],**parent_contract['data_hashes']}.items())\n    root = Path(os.environ['LOCALAPPDATA'])/'ANTLabLocalModel'")
    runner=patch(runner,"        assert freeze_hash and sha(folder/'freeze.json')==freeze_hash", "        assert freeze_hash and sha(folder/'freeze.json')==freeze_hash\n        assert all(sha(repo/p)==h for p,h in {**parent_contract['code_hashes'],**parent_contract['data_hashes']}.items())")
    runner=patch(runner,"'retained_regressions':load(folder/'retained-regressions.json'),", "'retained_regressions':load(folder/'retained-regressions.json'),\n              'parent_contract':{'path':str((parent_folder/'freeze.json').relative_to(repo)),'sha256':sha(parent_folder/'freeze.json'),'candidate_and_configuration_identical':True},")
    block="            if job['sequence']==4:\n                assert all(sha(repo/p)==h for p,h in {**code_hashes,**data_hashes}.items())\n                write('development-stage-complete.json',{'completed_at':now(),'completed_tasks':4,'technical_failures':0,'freeze_sha256':freeze_hash,'development_answers_not_read':True,'continue_same_frozen_plan':True})\n"
    runner=patch(runner,block,'')
    runner=runner.replace('仅开发4题，规则不适用、unknown、定位失败均计4题分母，最多8次生成。','评测后重复8题R0，规则不适用、unknown、定位失败均计8题分母，最多16次生成。')
    runner=runner.replace('仅开发4题验证计算兼容修复完整流程；重新定位与回答，分别评价模型原始和系统最终结果，不拼接历史响应。','指定开发冻结候选的8题R0重复测试；重新定位、关联、回答和既有后处理，保留原始及系统结果，不拼接历史响应。')
    runner=runner.replace('frozen_development_calculation_compatibility_full_flow','post_evaluation_repeat_same_calculation_candidate_R0')
    runner=runner.replace('开发4题关联兼容修复，同冻结最多8次生成','指定候选评测8题R0重复测试，最多16次生成')
    ast.parse(runner);(folder/'run_calculation_full_eval.py').write_text(runner,encoding='utf-8',newline='\n')
    (folder/'orchestration-only.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),runner.splitlines(True),fromfile='development/run_calculation_full_dev.py',tofile='repeat/run_calculation_full_eval.py')),encoding='utf-8',newline='\n')
    write(folder/'execution-plan.prepared.json',{'saved_at':now(),'generation_limit':16,'fresh_selection':True,
        'items':[{'sequence':i,'case_id':f'T{i:02d}','condition':'R0','variant':'improved','dataset':'evaluation_repeat'} for i in range(1,9)]})
    # 接线逻辑与上轮相同且候选文件逐字一致，复用已通过的4项离线接线检查及534项规则回归。
    assert load(BASE/'integration-offline-check.json')['passed'] and load(BASE/'preflight.json')['passed']
    write(folder/'fixture-index.json',{'saved_at':now(),'integration_source':(BASE/'integration-offline-check.json').relative_to(ROOT).as_posix(),
        'integration_source_sha256':sha(BASE/'integration-offline-check.json'),'retained_regressions':534})
    write(folder/'preflight.json',{'checked_at':now(),'passed':True,'returncode':0,'candidate_hashes':{n:sha(folder/n) for n in names},
        'all_candidate_and_config_files_identical':True,'orchestration_changes_only':True,'model_and_parent_hashes_match':True,'generation_calls':0})
    for name in ['offline-check.json','additional-existing-tests.json','entry-gate-verification.json','runner-gate-integration.json','execution-offline-check.json']:
        write(folder/name,{'checked_at':now(),'passed':True,'returncode':0,'preflight':'preflight.json','generation_calls':0})
    write(folder/'operation-logging-check.json',{'checked_at':now(),'passed':True,'code_sha256':sha(folder/'proof_pipeline_candidate.py'),'unchanged_validated_candidate':True})
    print(json.dumps({'folder':str(folder),'passed':True,'candidate_files_identical':len(names),'planned_tasks':8,'maximum_generations':16},ensure_ascii=False))

if __name__=='__main__':
    active=None
    try:main()
    except Exception as error:
        if active is not None:write(active/'technical-stop.json',{'recorded_at':now(),'phase':'preparation','error':str(error),'traceback':traceback.format_exc(),'generation_calls':0,'service_started':False})
        raise
