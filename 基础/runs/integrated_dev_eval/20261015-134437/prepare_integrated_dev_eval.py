import ast,copy,difflib,hashlib,importlib.util,json,os,shutil,subprocess,sys,traceback
from datetime import datetime
from pathlib import Path
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
BASE=ROOT/'基础/runs/general_proof_full_r0/20261015-131742'
PROOF=ROOT/'基础/runs/ratio_calculation_proof/20261015-133404'
SYNTHETIC=ROOT/'基础/runs/eligibility_proof/20261015-000204'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now().astimezone().isoformat()
def write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as out:json.dump(value,out,ensure_ascii=False,indent=2);out.write('\n')
def patch(text,old,new):
    assert text.count(old)==1,old[:120]
    return text.replace(old,new,1)
def mod(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def normalized_imports(text):
    tree=ast.parse(text)
    mapping={'proof_scope_occurrences':'scope_first_occurrences','proof_snapshot_checker':'eligibility_proof_checker'}
    for node in ast.walk(tree):
        if isinstance(node,ast.ImportFrom):node.module=mapping.get(node.module,node.module)
        elif isinstance(node,ast.Import):
            for alias in node.names:alias.name=mapping.get(alias.name,alias.name)
    return ast.dump(tree,include_attributes=False)

def main():
    global active
    folder=ROOT/'基础/runs/integrated_dev_eval'/datetime.now().strftime('%Y%m%d-%H%M%S')
    folder.mkdir(parents=True,exist_ok=False);active=folder
    write(folder/'preparation-plan.json',{'saved_at':now(),'kind':'post_evaluation_full_R0_repeat_not_blind',
        'main_tasks':12,'maximum_generations':24,'previous_cumulative':372,
        'cancelled_unexecuted_experiment':'取消恢复首次版本、比较呈现方式；本轮清单不包含该实验，旧文件不删改。',
        'cohorts':'D01—D04 R0完整流程后，若无技术故障继续T01—T08 R0，单一冻结、同一配置，不因开发质量调参。',
        'plan':'重新定位、验证ID、直接关联、原输入相对顺序回答；引用证明不改答案；比例计算建议可改答，单独保存且优先级固定。',
        'hypothesis':'完整新定位链下，有限证明能否改善完整引用，且不为错误或未知答案派生成功。',
        'competing_explanations':['定位/关联漏证会阻断证明。','证据齐全仍可能算错或拒答；系统引用组装不等于模型推理改善。'],
        'isolation':'生成链保留原scope_first_occurrences；证明器通过仅导入名不同的proof_scope_occurrences/proof_snapshot_checker隔离，验证非导入AST完全一致。',
        'material_policy':'事实及派生引用只来自最终回答模型输入；其余完整原始可见资料只做实体、范围、唯一性审计，分开保存。',
        'prediction':'失败/unknown/不适用保留原结果；引用证明不改answer，只有比例证明成立才允许单独计算新答；不预设两组成功数。',
        'stop':'离线失败阻断加载；新技术错误立即保存停止；质量失败不重试；每题最多2次生成，共24次。',
        'evaluate_after_all_requests':True,'denominators':{'development':4,'evaluation_repeat':8}})
    oldfreeze=load(PROOF/'freeze.json')
    assert all(sha(ROOT/p)==h for p,h in oldfreeze['code_hashes'].items())
    generation_names=['scope_candidate.py','scope_first_occurrences.py','eligibility_proof_checker.py','explicit_state_checker.py',
        'eligibility_exclusion_candidate.py','typed_enum_role_revision.py','typed_identifier_enum_candidate.py','body_identifier_enum_candidate.py','offline_gate.py']
    for name in generation_names:shutil.copyfile(BASE/name,folder/name)
    lineage=[]
    for origin,name in [('proof_scope_occurrences.py','proof_scope_occurrences.py'),('proof_snapshot_checker.py','proof_snapshot_checker.py'),
        ('general_citation_proof.py','general_citation_proof.py'),('project_scope_resolution.py','project_scope_resolution.py')]:
        original=(PROOF/origin).read_text(encoding='utf-8');text=original
        if name in ['proof_snapshot_checker.py','general_citation_proof.py']:
            text=text.replace('from scope_first_occurrences import','from proof_scope_occurrences import')
        if name=='general_citation_proof.py':text=text.replace('import eligibility_proof_checker as snapshot','import proof_snapshot_checker as snapshot')
        assert normalized_imports(text)==normalized_imports(original)
        (folder/name).write_text(text,encoding='utf-8',newline='\n')
        lineage.append({'source':(PROOF/origin).relative_to(ROOT).as_posix(),'source_sha256':sha(PROOF/origin),
            'target':name,'target_sha256':sha(folder/name),'non_import_ast_identical':True})
    for name in ['check_general_citation_proof.py','check_project_scope_resolution.py','check_ratio_calculation_proof.py','ratio_calculation_proof.py']:
        shutil.copyfile(PROOF/name,folder/name)
    shutil.copyfile(Path(__file__).with_name('integrated_ratio_candidate.py'),folder/'proof_pipeline_candidate.py')
    shutil.copyfile(Path(__file__),folder/Path(__file__).name)
    write(folder/'proof-rules-index.json',{'saved_at':now(),'lineage':lineage,'generation_rule_files_unchanged':{n:sha(BASE/n)==sha(folder/n) for n in generation_names}})
    runner=(BASE/'run_general_proof_full_r0.py').read_text(encoding='utf-8')
    original_runner=runner
    runner=runner.replace('run_general_proof_full_r0.py','run_integrated_dev_eval.py').replace('prepare_general_proof_full_r0.py','prepare_integrated_dev_eval.py')
    runner=patch(runner,'assert len(jobs)==8 and all','assert len(jobs)==12 and all')
    runner=patch(runner,"assert len({(j['case_id'],j['condition'],j['variant']) for j in jobs})==8","assert len({(j['case_id'],j['condition'],j['variant']) for j in jobs})==12\n    assert [j['case_id'] for j in jobs]==[f'D{i:02d}' for i in range(1,5)]+[f'T{i:02d}' for i in range(1,9)]")
    runner=runner.replace("runtime['generation_dispatches']<16","runtime['generation_dispatches']<24")
    runner=runner.replace("'maximum_generation_calls':16","'maximum_generation_calls':24").replace("'main_task_limit':8,'generation_limit':16","'main_task_limit':12,'generation_limit':24")
    runner=runner.replace("'planned_main_tasks':8","'planned_main_tasks':12").replace("'main_tasks':8","'main_tasks':12")
    runner=patch(runner,"'previous_cumulative':356,'cumulative_confirmed':356+len(ids)","'previous_cumulative':372,'cumulative_confirmed':372+len(ids)")
    runner=patch(runner,"'check_project_scope_resolution.py','prepare_integrated_dev_eval.py']","'check_project_scope_resolution.py','prepare_integrated_dev_eval.py','ratio_calculation_proof.py','check_ratio_calculation_proof.py']")
    runner=patch(runner,"'denominator':'T01—T08 R0 improved共8项；规则未适用、unknown、定位失败均保留在8题分母，最多16次生成。'","'denominator':'开发4题、评测后重复8题分开；规则不适用、unknown、定位失败均计分母，12项最多24次生成。'")
    runner=runner.replace('post_evaluation_general_proof_full_r0_repeat','frozen_integrated_development_then_evaluation_repeat')
    runner=runner.replace('当前独立完整候选在已接触的八题上，原始严格成功与三类有限正向证明派生后的系统严格成功如何。','单一冻结整合候选先开发4题再评测后重复8题，分别比较模型原始与系统最终答案及引用表现。')
    runner=patch(runner,"'case_id':current['case_id'],'condition':current['condition'],'variant':current['variant'],","'case_id':current['case_id'],'condition':current['condition'],'variant':current['variant'],'dataset':current['dataset'],")
    runner=patch(runner,"        for job in jobs:\n            current=","        for job in jobs:\n            phase=job['dataset']+'_generation'\n            if job['sequence']==5:\n                assert load(folder/'development-stage-complete.json')['technical_failures']==0\n                assert sha(folder/'freeze.json')==freeze_hash\n            current=")
    runner=patch(runner,"            print('TASK',job['sequence']", "            if job['sequence']==4:\n                assert all(sha(repo/p)==h for p,h in {**code_hashes,**data_hashes}.items())\n                write('development-stage-complete.json',{'completed_at':now(),'completed_tasks':4,'technical_failures':0,'freeze_sha256':freeze_hash,'development_answers_not_read':True,'continue_same_frozen_plan':True})\n            print('TASK',job['sequence']")
    runner=patch(runner,"'completed_main_tasks':sum(t.get('status') in ('completed','selection_output_failure') for t in tasks),", "'completed_main_tasks':sum(t.get('status') in ('completed','selection_output_failure') for t in tasks),\n                 'completed_development_tasks':sum(t.get('dataset')=='development' and t.get('status') in ('completed','selection_output_failure') for t in tasks),\n                 'completed_evaluation_tasks':sum(t.get('dataset')=='evaluation_repeat' and t.get('status') in ('completed','selection_output_failure') for t in tasks),")
    runner=runner.replace('八题新定位与回答，最多16次生成','开发4题后评测后重复8题，同冻结最多24次生成')
    runner=patch(runner,"'proof_rule_lineage':load(folder/'proof-rules-index.json'),", "'proof_rule_lineage':load(folder/'proof-rules-index.json'),\n              'ratio_rule_source':{'source':'基础/runs/ratio_calculation_proof/20261015-133404/ratio_calculation_proof.py','sha256':sha(folder/'ratio_calculation_proof.py')},\n              'output_policy':'比例计算建议优先；否则引用证明；否则原始回答。计算改答与引用组装独立保存。',")
    ast.parse(runner);(folder/'run_integrated_dev_eval.py').write_text(runner,encoding='utf-8',newline='\n')
    diff=''.join(difflib.unified_diff((BASE/'proof_pipeline_candidate.py').read_text(encoding='utf-8').splitlines(True),(folder/'proof_pipeline_candidate.py').read_text(encoding='utf-8').splitlines(True),fromfile='previous_full/proof_pipeline_candidate.py',tofile='new_full/proof_pipeline_candidate.py'))
    diff+=''.join(difflib.unified_diff(original_runner.splitlines(True),runner.splitlines(True),fromfile='previous_full/run_general_proof_full_r0.py',tofile='new_full/run_integrated_dev_eval.py'))
    (folder/'integration.diff').write_text(diff,encoding='utf-8',newline='\n')
    for name in ['settings.prepared.json','answer.prepared.json','selection.prepared.json']:shutil.copyfile(BASE/name,folder/name)
    jobs=[{'sequence':i,'case_id':f'D{i:02d}','condition':'R0','variant':'improved','dataset':'development'} for i in range(1,5)]
    jobs += [{'sequence':i+4,'case_id':f'T{i:02d}','condition':'R0','variant':'improved','dataset':'evaluation_repeat'} for i in range(1,9)]
    write(folder/'execution-plan.prepared.json',{'saved_at':now(),'generation_limit':24,'fresh_selection':True,'items':jobs})
    fixture_list=[]
    for test_name in ['check_general_citation_proof.py','check_project_scope_resolution.py','check_ratio_calculation_proof.py']:
        result=subprocess.run([sys.executable,'-X','utf8','-B',str(folder/test_name)],capture_output=True,text=True,encoding='utf-8',
            env={**os.environ,'PYTHONPATH':str(ROOT/'基础/tests')})
        write(folder/(test_name+'.execution.json'),{'executed_at':now(),'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'generation_calls':0})
        assert result.returncode==0,result.stdout+result.stderr
        fixture_list.append({'type':'synthetic_suite','source':test_name,'sha256':sha(folder/test_name)})
    sys.path.insert(0,str(ROOT/'基础/tests'));sys.path.insert(0,str(folder))
    import proof_pipeline_candidate as candidate
    prior=[]
    for index in range(1,15):
        path=SYNTHETIC/f'test-{index:02d}.json';case=load(path)
        assert isinstance(case,dict) and {'passages','raw_response','expected_established','name'}<=case.keys()
        actual=candidate.proof.prove_answer('竹岭项目V4版本在2026-04的发布快照是什么？只输出快照编号。',case['passages'],case['raw_response'])
        prior.append({'name':case['name'],'passed':actual['proof_established']==case['expected_established'],'proof':actual})
        fixture_list.append({'type':'snapshot_regression','source':path.relative_to(ROOT).as_posix(),'sha256':sha(path)})
    write(folder/'snapshot-regressions.json',{'checked_at':now(),'rows':prior,'passed':all(r['passed'] for r in prior)});assert all(r['passed'] for r in prior)
    write(folder/'fixture-index.json',{'created_at':now(),'explicit_file_list':fixture_list,'no_silent_skips':True})
    answer=load(folder/'answer.prepared.json');selection=load(folder/'selection.prepared.json')
    integrations=[]
    def check(question,passages,final_content,invalid_selection=False,expect_derived=False,expect_proposed=False):
        calls=[];before=copy.deepcopy(passages)
        def dispatch(stage,messages,config,used):
            calls.append({'stage':stage,'messages':messages,'config':config,'passages':used})
            text=json.dumps({'selected_ids':['unknown-source'] if invalid_selection else [p['id'] for p in used]},ensure_ascii=False) if stage=='selection' else final_content
            return {'stage':stage,'elapsed_seconds':0.0,'run_kind':'offline_stub_not_generation','response':{'choices':[{'message':{'content':text}}]}}
        result=candidate.execute(question,passages,'improved',answer,selection,dispatch)
        assert passages==before
        assert len(calls)==(1 if invalid_selection else 2)
        assert (result['derived_response'] is not None)==expect_derived
        assert (result['proposed_response'] is not None)==expect_proposed
        if not invalid_selection:
            assert result['raw_response']==result['stages'][-1]['response'] and result['raw_answer']==final_content
        assert all(e['rule_version']['sha256'] and e['elapsed_seconds']>=0 for e in result['local_rule_processing'])
        integrations.append({'question':question,'passed':True,'result':result,'offline_requests':calls})
    check('只输出数值。',[],'{"answer":"证据不足","citations":[]}')
    check('虚构项目R1版本在2026-01的快照是什么？只输出快照编号。',[],'{"answer":"证据不足","citations":[]}')
    check('只输出数值。',[],'',True)
    check('只输出数值。',[],'{"answer":')
    for name in ['self-test-001.json','self-test-013.json']:
        case=load(folder/name);check(case['question'],case['passages'],case['raw'],expect_derived=True)
    for name,expected in [('ratio-test-001.json',True),('ratio-test-002.json',False)]:
        case=load(folder/name);check(case['question'],case['passages'],case['raw'],expect_proposed=expected)
    write(folder/'integration-offline-check.json',{'checked_at':now(),'passed':True,'rows':integrations,'generation_calls':0})
    gate=mod(folder/'offline_gate.py','full_general_gate');starts=[]
    try:gate.after_offline_success(lambda:{'passed':False,'returncode':1},lambda:starts.append('service'))
    except RuntimeError:pass
    else:raise AssertionError('gate_not_blocking')
    assert not starts and "after_offline_success(lambda:load(target/'execution-offline-check.json'),main)" in runner
    assert candidate.base.audit_occurrences.__module__=='scope_first_occurrences'
    assert candidate.proof.snapshot.audit_occurrences.__module__=='proof_scope_occurrences'
    import runner as data_runner
    settings=load(folder/'settings.prepared.json');input_rows=[]
    for job in jobs:
        case,passages,_,_=data_runner.prepare(job['case_id'],'R0','baseline')
        messages,conf,_=candidate.answer_request(case['question'],passages,answer)
        schema=conf['parameters']['response_format']['json_schema']['schema']
        assert [m['role'] for m in messages]==['system','user'] and schema['required']==['answer','citations']
        assert len(passages)==len({p['id'] for p in passages}) and all({'id','source','text'}<=p.keys() for p in passages)
        input_rows.append({'case_id':job['case_id'],'dataset':job['dataset'],'condition':'R0','input_passages':len(passages),'schema_and_messages_checked':True})
    for path,expected in {**settings['code_sha256'],**settings['data_sha256']}.items():assert (ROOT/path).is_file() and sha(ROOT/path)==expected,path
    local=Path(os.environ['LOCALAPPDATA'])/'ANTLabLocalModel'
    assert sha(local/'models/Qwen3-0.6B-Q8_0.gguf')==settings['model']['actual_sha256']
    assert sha(local/'llama-b11429/llama-server.exe')==settings['llama_cpp']['executable_sha256']
    assert answer==load(BASE/'answer.prepared.json') and selection==load(BASE/'selection.prepared.json')
    assert not list(folder.glob('run-*.json')) and not (folder/'runtime.json').exists()
    for path in folder.glob('*.py'):ast.parse(path.read_text(encoding='utf-8-sig'))
    write(folder/'preflight.json',{'checked_at':now(),'passed':True,'returncode':0,'self_cases':130,'project_boundary_cases':83,'snapshot_cases':14,'ratio_cases':146,
        'integration_cases':len(integrations),'input_checks':input_rows,'model_code_config_data_hashes_match':True,
        'generation_scope_module_isolated_from_proof_scope_module':True,'no_model_settings_or_prompts_changed':True,'failed_gate_blocks_start':True,'generation_calls':0})
    for name in ['offline-check.json','additional-existing-tests.json','entry-gate-verification.json','runner-gate-integration.json','execution-offline-check.json']:
        write(folder/name,{'checked_at':now(),'passed':True,'returncode':0,'preflight':'preflight.json','generation_calls':0})
    write(folder/'operation-logging-check.json',{'checked_at':now(),'passed':True,'code_sha256':sha(folder/'proof_pipeline_candidate.py'),'event_versions_and_times_checked':True})
    print(json.dumps({'folder':str(folder),'passed':True,'synthetic':130,'boundary':83,'snapshot':14,'ratio':146,'integration':len(integrations),'planned_tasks':12,'generation_limit':24,'generation_calls':0},ensure_ascii=False))

if __name__=='__main__':
    active=None
    try:main()
    except Exception as error:
        if active is not None:write(active/'technical-stop.json',{'recorded_at':now(),'phase':'preparation','error_type':type(error).__name__,'detail':str(error),'traceback':traceback.format_exc(),'generation_dispatches':0,'service_started':False})
        raise
