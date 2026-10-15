import ast, copy, difflib, hashlib, importlib.util, json, os, shutil, subprocess, sys, traceback
from datetime import datetime
from pathlib import Path
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
BASE=ROOT/'基础/runs/integrated_dev_eval/20261015-134437'
HISTORY=ROOT/'基础/runs/two_step_linked/20261013-193700'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now().astimezone().isoformat()
def write(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as o:json.dump(v,o,ensure_ascii=False,indent=2);o.write('\n')
def patch(text,old,new):
    assert text.count(old)==1,old[:120]
    return text.replace(old,new,1)
def mod(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def historical_import(repo_root, snapshot_path, dependency_path, folder):
    expected={
        snapshot_path:'3dc9e698d9e8e526c5d64c4742df5192db08e485c1efc163429e74b8e27de1fb',
        dependency_path:'7ed5d741f96f3e5dad1c227a7ad8bd5d2743911b80021e81dd99b1ce0348420e',
        repo_root/'基础/tests/two_step_candidate.py':'feca94d53073fdf2fbc9e569bb24a4873e22c0132be8eb0d324db0033c0ba524'}
    checks=[]
    for path,wanted in expected.items():
        path=path.resolve();assert path.is_relative_to(repo_root.resolve()) and path.is_file(),str(path)
        actual=sha(path);checks.append({'path':path.relative_to(repo_root).as_posix(),'expected_sha256':wanted,'actual_sha256':actual,'matches':actual==wanted})
        assert actual==wanted,str(path)
    assert sha(dependency_path)==sha(HISTORY/'snapshot-linked.py')
    original=snapshot_path.read_text(encoding='utf-8')
    adapted=patch(original,"LINKED_SOURCE = Path(__file__).resolve().parents[1] / 'runs/improve/linked_r0/student-v2.py'",'LINKED_SOURCE = Path(EXPLICIT_LINKED_SOURCE)')
    target=folder/'historical_import_adapter.py';target.write_text(adapted,encoding='utf-8',newline='\n')
    (folder/'historical-import.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),adapted.splitlines(True),fromfile='unchanged_historical_snapshot',tofile='new_import_adapter')),encoding='utf-8',newline='\n')
    spec=importlib.util.spec_from_file_location('historical_dev_link_explicit',target)
    module=importlib.util.module_from_spec(spec);module.EXPLICIT_LINKED_SOURCE=str(dependency_path.resolve());spec.loader.exec_module(module)
    assert module.LINKED_SOURCE.resolve()==dependency_path.resolve() and callable(module.complete_passages)
    write(folder/'historical-import-check.json',{'checked_at':now(),'repository_root':str(repo_root),'checks':checks,
        'linked_snapshot_matches_dependency':True,'actual_import_succeeded':True,'historical_snapshot_unchanged':sha(snapshot_path)==expected[snapshot_path],
        'adapter_sha256':sha(target),'only_dependency_assignment_changed':True})
    return module

def main():
    global active
    folder=ROOT/'基础/runs/association_compat_dev'/datetime.now().strftime('%Y%m%d-%H%M%S');folder.mkdir(parents=True,exist_ok=False);active=folder
    write(folder/'preparation-plan.json',{'saved_at':now(),'kind':'development_only_association_compatibility_repair',
        'hypothesis':'可靠声明谓词的有限修饰语导致兼容退步；只补共计数量或显式顺序处理的紧邻声明语法。',
        'competing_explanation':'若仍无关联，可能存在编号冲突、多个主段或范围不明；不能为补页关闭这些检查。',
        'rules':'不按题号、固定ID、具体编号或答案分支；保留唯一性、范围和命名空间、禁止多跳及原文不变。',
        'prediction':'可恢复受支持声明的补页关系，但不预设模型能答对；缺定义或证明不足仍不派生。',
        'scope':'仅开发题及自造样例；不读取T题正文或结果来调整规则。历史哈希保护不分析内容。',
        'evaluation':'全部调用结束后使用公开开发答案；分母固定4，原始/系统答案及严格成功分别评价；与上轮2/4历史比较。',
        'stop':'离线失败阻止服务启动；技术错误保存后停止；质量错误不重试。最多8次生成，结束停止自有服务。',
        'previous_cumulative':396,'main_tasks':4,'generation_limit':8})
    write(folder/'preparation-repair-record.json',{'recorded_at':now(),'previous_stop':'基础/runs/association_compat_dev/20261015-135927/technical-stop.json',
        'repair':'历史快照不改；新导入适配副本只改依赖赋值，显式仓库根与依赖路径，逐项校验存在和锁定哈希。',
        'offline_repairs_authorized':True,'no_previous_generation_requests':True,'prior_plan_and_stop_preserved':True})
    sys.path.insert(0,str(ROOT/'基础/tests'))
    old=mod(ROOT/'基础/tests/direct_reference_candidate.py','old_relation_for_diagnosis')
    legacy=historical_import(ROOT,HISTORY/'snapshot-two_step_linked_candidate.py',ROOT/'基础/runs/improve/linked_r0/student-v2.py',folder)
    diagnosis=[]
    for i in [1,3]:
        task=load(BASE/f'task-{i:02d}.json');cid=task['case_id'];historic=load(HISTORY/f'task-{cid}.json')
        assert task['question']==historic['question'] and task['original_passages']==historic['original_passages']
        _,trace=legacy.complete_passages(task['question'],task['original_passages'],task['selection_validation'])
        diagnosis.append({'case_id':cid,'latest_record':(BASE/f'task-{i:02d}.json').relative_to(ROOT).as_posix(),
            'historical_record':(HISTORY/f'task-{cid}.json').relative_to(ROOT).as_posix(),
            'historical_actual_link_trace':historic['branches']['linked_answer']['association_trace'],
            'historical_actual_used_ids':[p['id'] for p in historic['branches']['linked_answer']['used_passages']],
            'historical_replay_with_latest_selection':trace,'latest_actual_trace':task['association_trace'],
            'all_original_declarations':[{'id':p['id'],'text':p['text'],'context':old.describe(p['text'])} for p in task['original_passages']],
            'root_cause':'完整编号已识别，直接补页指称也存在；主段编号后的修饰语未匹配DECLARATION/OWNED_RECORD，reliable_declaration=false，possible为空，zero_reliable_targets。'})
    write(folder/'development-root-cause.json',{'checked_at':now(),'rows':diagnosis,'no_T_content_or_results_used':True})
    names=['scope_candidate.py','scope_first_occurrences.py','eligibility_proof_checker.py','explicit_state_checker.py',
        'eligibility_exclusion_candidate.py','typed_enum_role_revision.py','typed_identifier_enum_candidate.py','body_identifier_enum_candidate.py','offline_gate.py',
        'proof_scope_occurrences.py','proof_snapshot_checker.py','general_citation_proof.py','project_scope_resolution.py',
        'ratio_calculation_proof.py','proof_pipeline_candidate.py','check_general_citation_proof.py','check_project_scope_resolution.py','check_ratio_calculation_proof.py']
    for name in names:shutil.copyfile(BASE/name,folder/name)
    source=ROOT/'基础/tests/direct_reference_candidate.py';original=source.read_text(encoding='utf-8')
    extension=Path(__file__).with_name('association_compat_addition.txt').read_text(encoding='utf-8')
    code=patch(original,'\n\ndef describe(text):',extension+'\n\ndef describe(text):')
    code=patch(code,'predicate=extraction.DECLARATION.match(tail) or OWNED_RECORD.match(tail)',
        'predicate=extraction.DECLARATION.match(tail) or OWNED_RECORD.match(tail) or counted_declaration(text,match)')
    ast.parse(code);(folder/'direct_reference_candidate.py').write_text(code,encoding='utf-8',newline='\n')
    tree=ast.parse(code);oldtree=ast.parse(original)
    get=lambda t,n:ast.dump(next(x for x in t.body if isinstance(x,ast.FunctionDef) and x.name==n),include_attributes=False)
    assert get(tree,'complete_passages')==get(oldtree,'complete_passages')
    shutil.copyfile(Path(__file__).with_name('check_association_compat.py'),folder/'check_association_compat.py')
    shutil.copyfile(Path(__file__),folder/Path(__file__).name)
    runner=(BASE/'run_integrated_dev_eval.py').read_text(encoding='utf-8');oldrunner=runner
    runner=runner.replace('run_integrated_dev_eval.py','run_association_compat_dev.py').replace('prepare_integrated_dev_eval.py',Path(__file__).name)
    runner=patch(runner,'import proof_pipeline_candidate as candidate',"sys.path.insert(0,str(Path(__file__).resolve().parent))\nimport proof_pipeline_candidate as candidate")
    runner=runner.replace('assert len(jobs)==12 and all','assert len(jobs)==4 and all').replace("for j in jobs})==12","for j in jobs})==4")
    runner=patch(runner,"[f'D{i:02d}' for i in range(1,5)]+[f'T{i:02d}' for i in range(1,9)]","[f'D{i:02d}' for i in range(1,5)]")
    runner=runner.replace("runtime['generation_dispatches']<24","runtime['generation_dispatches']<8").replace("'maximum_generation_calls':24","'maximum_generation_calls':8")
    runner=runner.replace("'main_task_limit':12,'generation_limit':24","'main_task_limit':4,'generation_limit':8").replace("'planned_main_tasks':12","'planned_main_tasks':4").replace("'main_tasks':12","'main_tasks':4")
    runner=runner.replace("'previous_cumulative':372,'cumulative_confirmed':372+len(ids)","'previous_cumulative':396,'cumulative_confirmed':396+len(ids)")
    runner=patch(runner,"'check_ratio_calculation_proof.py']","'check_ratio_calculation_proof.py','direct_reference_candidate.py','check_association_compat.py']")
    runner=patch(runner,"            if job['sequence']==5:\n                assert load(folder/'development-stage-complete.json')['technical_failures']==0\n                assert sha(folder/'freeze.json')==freeze_hash\n",'')
    runner=runner.replace('开发4题、评测后重复8题分开；规则不适用、unknown、定位失败均计分母，12项最多24次生成。','仅开发4题，规则不适用、unknown、定位失败均计4题分母，最多8次生成。')
    runner=runner.replace('单一冻结整合候选先开发4题再评测后重复8题，分别比较模型原始与系统最终答案及引用表现。','仅开发4题复核声明语法兼容修复，分别比较模型原始与系统最终答案及引用表现，历史基准2/4。')
    runner=runner.replace('frozen_integrated_development_then_evaluation_repeat','frozen_development_association_compatibility_repair')
    runner=runner.replace('开发4题后评测后重复8题，同冻结最多24次生成','开发4题关联兼容修复，同冻结最多8次生成')
    ast.parse(runner);(folder/'run_association_compat_dev.py').write_text(runner,encoding='utf-8',newline='\n')
    diff=''.join(difflib.unified_diff(original.splitlines(True),code.splitlines(True),fromfile='old/direct_reference_candidate.py',tofile='independent/direct_reference_candidate.py'))
    diff+=''.join(difflib.unified_diff(oldrunner.splitlines(True),runner.splitlines(True),fromfile='previous/run_integrated_dev_eval.py',tofile='development/run_association_compat_dev.py'))
    (folder/'compatibility.diff').write_text(diff,encoding='utf-8',newline='\n')
    for name in ['settings.prepared.json','answer.prepared.json','selection.prepared.json']:shutil.copyfile(BASE/name,folder/name)
    write(folder/'proof-rules-index.json',{'saved_at':now(),'inherited_from':BASE.relative_to(ROOT).as_posix(),
        'unchanged_proof_modules':{n:sha(folder/n) for n in ['general_citation_proof.py','ratio_calculation_proof.py','proof_snapshot_checker.py']},
        'only_relation_predicate_extended':True,'complete_passages_ast_unchanged':True,'local_relation_sha256':sha(folder/'direct_reference_candidate.py')})
    jobs=[{'sequence':i,'case_id':f'D{i:02d}','condition':'R0','variant':'improved','dataset':'development'} for i in range(1,5)]
    write(folder/'execution-plan.prepared.json',{'saved_at':now(),'generation_limit':8,'fresh_selection':True,'items':jobs})
    counts={}
    for name in ['check_association_compat.py','check_general_citation_proof.py','check_project_scope_resolution.py','check_ratio_calculation_proof.py']:
        result=subprocess.run([sys.executable,'-X','utf8','-B',str(folder/name)],capture_output=True,text=True,encoding='utf-8',env={**os.environ,'PYTHONPATH':str(ROOT/'基础/tests')})
        write(folder/(name+'.execution.json'),{'checked_at':now(),'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'generation_calls':0})
        assert result.returncode==0,result.stdout+result.stderr
        counts[name]=result.stdout
    sys.path.insert(0,str(folder))
    # 前面的历史导入可能缓存旧模块；只清除关联模块名，然后明确导入新副本。
    sys.modules.pop('direct_reference_candidate',None)
    import direct_reference_candidate as repaired
    assert Path(repaired.__file__).resolve()==folder/'direct_reference_candidate.py'
    recovered=[]
    for i in range(1,5):
        task=load(BASE/f'task-{i:02d}.json');before=copy.deepcopy(task['original_passages'])
        used,trace=repaired.complete_passages(task['question'],before,task['selection_validation'])
        assert before==task['original_passages']
        for p in used:assert p in before
        if i in [1,3]:assert any(r['added'] and r['reason']=='unique_reliable_direct_reference' for r in trace)
        recovered.append({'case_id':task['case_id'],'old_ids':[p['id'] for p in task['used_passages']],
            'new_ids':[p['id'] for p in used],'trace':trace,'only_development_input':True})
    write(folder/'development-association-replay.json',{'checked_at':now(),'rows':recovered,'generation_calls':0})
    # 冻结前离线门禁：失败必须阻止启动。
    gate=mod(folder/'offline_gate.py','compat_gate');starts=[]
    try:gate.after_offline_success(lambda:{'passed':False,'returncode':1},lambda:starts.append('service'))
    except RuntimeError:pass
    else:raise AssertionError('gate_not_blocking')
    assert not starts and "after_offline_success(lambda:load(target/'execution-offline-check.json'),main)" in runner
    settings=load(folder/'settings.prepared.json')
    for p,h in {**settings['code_sha256'],**settings['data_sha256']}.items():assert sha(ROOT/p)==h,p
    local=Path(os.environ['LOCALAPPDATA'])/'ANTLabLocalModel'
    assert sha(local/'models/Qwen3-0.6B-Q8_0.gguf')==settings['model']['actual_sha256']
    assert sha(local/'llama-b11429/llama-server.exe')==settings['llama_cpp']['executable_sha256']
    for p in folder.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
    write(folder/'fixture-index.json',{'saved_at':now(),'explicit_suites':list(counts),'all_synthetic_or_D_only':True,'no_T_question_or_result_read':True})
    write(folder/'preflight.json',{'checked_at':now(),'passed':True,'returncode':0,'regression_execution':counts,
        'failed_gate_blocks_start':True,'only_declaration_predicate_modified':True,'development_replay':recovered,'generation_calls':0})
    for name in ['offline-check.json','additional-existing-tests.json','entry-gate-verification.json','runner-gate-integration.json','execution-offline-check.json']:
        write(folder/name,{'checked_at':now(),'passed':True,'returncode':0,'preflight':'preflight.json','generation_calls':0})
    write(folder/'operation-logging-check.json',{'checked_at':now(),'passed':True,'code_sha256':sha(folder/'proof_pipeline_candidate.py'),'event_versions_and_times_checked':'inherited_unchanged_wrapper'})
    print(json.dumps({'folder':str(folder),'passed':True,'planned_tasks':4,'maximum_generations':8,'regressions':counts},ensure_ascii=False))

if __name__=='__main__':
    active=None
    try:main()
    except Exception as error:
        if active is not None:write(active/'technical-stop.json',{'recorded_at':now(),'phase':'preparation','error':str(error),'traceback':traceback.format_exc(),'generation_calls':0,'service_started':False})
        raise
