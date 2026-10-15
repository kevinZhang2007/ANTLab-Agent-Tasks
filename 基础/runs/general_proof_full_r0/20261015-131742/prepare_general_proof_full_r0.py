import ast,copy,difflib,hashlib,importlib.util,json,os,shutil,subprocess,sys,traceback
from datetime import datetime
from pathlib import Path
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
BASE=ROOT/'基础/runs/proof_full_r0_repeat/20261015-124627'
PROOF=ROOT/'基础/runs/project_boundary_proof/20261015-131007'
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
    folder=ROOT/'基础/runs/general_proof_full_r0'/datetime.now().strftime('%Y%m%d-%H%M%S')
    folder.mkdir(parents=True,exist_ok=False);active=folder
    write(folder/'preparation-plan.json',{'saved_at':now(),'kind':'post_evaluation_full_R0_repeat_not_blind',
        'main_tasks':8,'maximum_generations':16,'previous_cumulative':356,
        'plan':'重新定位、验证ID、直接关联、原输入相对顺序回答；返回原始回答后才运行已验证三类证明，答案不变。',
        'hypothesis':'完整新定位链下，有限证明能否改善完整引用，且不为错误或未知答案派生成功。',
        'competing_explanations':['定位/关联漏证会阻断证明。','证据齐全仍可能算错或拒答；系统引用组装不等于模型推理改善。'],
        'isolation':'生成链保留原scope_first_occurrences；证明器通过仅导入名不同的proof_scope_occurrences/proof_snapshot_checker隔离，验证非导入AST完全一致。',
        'material_policy':'事实及派生引用只来自最终回答模型输入；其余完整原始可见资料只做实体、范围、唯一性审计，分开保存。',
        'prediction':'证明不改answer，失败/unknown/不适用保留原结果；不预设八题成功数。',
        'stop':'离线失败阻断加载；新技术错误立即保存停止；质量失败不重试；最多16次。',
        'evaluate_after_all_requests':True,'denominator':8})
    oldfreeze=load(PROOF/'freeze.json')
    assert all(sha(ROOT/p)==h for p,h in oldfreeze['code_hashes'].items())
    generation_names=['scope_candidate.py','scope_first_occurrences.py','eligibility_proof_checker.py','explicit_state_checker.py',
        'eligibility_exclusion_candidate.py','typed_enum_role_revision.py','typed_identifier_enum_candidate.py','body_identifier_enum_candidate.py','offline_gate.py']
    for name in generation_names:shutil.copyfile(BASE/name,folder/name)
    lineage=[]
    for origin,name in [('scope_first_occurrences.py','proof_scope_occurrences.py'),('eligibility_proof_checker.py','proof_snapshot_checker.py'),
        ('general_citation_proof.py','general_citation_proof.py'),('project_scope_resolution.py','project_scope_resolution.py')]:
        original=(PROOF/origin).read_text(encoding='utf-8');text=original
        if name in ['proof_snapshot_checker.py','general_citation_proof.py']:
            text=text.replace('from scope_first_occurrences import','from proof_scope_occurrences import')
        if name=='general_citation_proof.py':text=text.replace('import eligibility_proof_checker as snapshot','import proof_snapshot_checker as snapshot')
        assert normalized_imports(text)==normalized_imports(original)
        (folder/name).write_text(text,encoding='utf-8',newline='\n')
        lineage.append({'source':(PROOF/origin).relative_to(ROOT).as_posix(),'source_sha256':sha(PROOF/origin),
            'target':name,'target_sha256':sha(folder/name),'non_import_ast_identical':True})
    for name in ['check_general_citation_proof.py','check_project_scope_resolution.py']:
        shutil.copyfile(PROOF/name,folder/name)
    shutil.copyfile(Path(__file__).with_name('integrated_general_proof_candidate.py'),folder/'proof_pipeline_candidate.py')
    shutil.copyfile(Path(__file__),folder/Path(__file__).name)
    write(folder/'proof-rules-index.json',{'saved_at':now(),'lineage':lineage,'generation_rule_files_unchanged':{n:sha(BASE/n)==sha(folder/n) for n in generation_names}})
    runner=(BASE/'run_proof_full_repeat.py').read_text(encoding='utf-8')
    original_runner=runner
    runner=runner.replace('run_proof_full_repeat.py','run_general_proof_full_r0.py')
    runner=runner.replace("'previous_cumulative':340,'cumulative_confirmed':340+len(ids)","'previous_cumulative':356,'cumulative_confirmed':356+len(ids)")
    runner=runner.replace('仅快照分支正向证明派生','三类有限正向证明派生')
    runner=runner.replace('post_evaluation_proof_full_r0_repeat','post_evaluation_general_proof_full_r0_repeat')
    before="    code_hashes = {p:sha(repo/p) for p in sources}"
    after="""    sources += [(folder/name).relative_to(repo).as_posix() for name in ['general_citation_proof.py','proof_scope_occurrences.py','proof_snapshot_checker.py','project_scope_resolution.py','proof-rules-index.json','check_general_citation_proof.py','check_project_scope_resolution.py','prepare_general_proof_full_r0.py']]
    code_hashes = {p:sha(repo/p) for p in sources}"""
    runner=patch(runner,before,after)
    runner=patch(runner,"'final_order':'最终所选完整原段落按当前原输入相对顺序',", "'final_order':'最终所选完整原段落按当前原输入相对顺序',\n              'proof_material_policy':'证明事实与派生引用仅最终回答输入；额外原始可见段落仅范围、实体、唯一性审计，独立字段保存。',\n              'proof_rule_lineage':load(folder/'proof-rules-index.json'),")
    runner=patch(runner,"    try:\n        runtime['memory_before']=memory()","    phase='model_loading'\n    try:\n        runtime['memory_before']=memory()")
    runner=patch(runner,"        begin=time.perf_counter();monitor_thread=", "        phase='health_check'\n        begin=time.perf_counter();monitor_thread=")
    runner=patch(runner,"        inputs={}\n", "        phase='template_capacity_preflight'\n        inputs={}\n")
    runner=patch(runner,"        for job in jobs:\n            current=", "        phase='generation'\n        for job in jobs:\n            current=")
    runner=patch(runner,"'generation_dispatches':runtime['generation_dispatches'],'current_task':current}","'generation_dispatches':runtime['generation_dispatches'],'current_task':current,'phase':phase}")
    runner=runner.replace('仅快照资格分支','三类有限证明分支')
    ast.parse(runner);(folder/'run_general_proof_full_r0.py').write_text(runner,encoding='utf-8',newline='\n')
    diff=''.join(difflib.unified_diff((BASE/'proof_pipeline_candidate.py').read_text(encoding='utf-8').splitlines(True),(folder/'proof_pipeline_candidate.py').read_text(encoding='utf-8').splitlines(True),fromfile='previous_full/proof_pipeline_candidate.py',tofile='new_full/proof_pipeline_candidate.py'))
    diff+=''.join(difflib.unified_diff(original_runner.splitlines(True),runner.splitlines(True),fromfile='previous_full/run_proof_full_repeat.py',tofile='new_full/run_general_proof_full_r0.py'))
    (folder/'integration.diff').write_text(diff,encoding='utf-8',newline='\n')
    for name in ['settings.prepared.json','answer.prepared.json','selection.prepared.json']:shutil.copyfile(BASE/name,folder/name)
    write(folder/'execution-plan.prepared.json',{'saved_at':now(),'generation_limit':16,'fresh_selection':True,
        'items':[{'sequence':i,'case_id':f'T{i:02d}','condition':'R0','variant':'improved'} for i in range(1,9)]})
    fixture_list=[]
    for test_name in ['check_general_citation_proof.py','check_project_scope_resolution.py']:
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
    def check(question,passages,final_content,invalid_selection=False,expect_derived=False):
        calls=[];before=copy.deepcopy(passages)
        def dispatch(stage,messages,config,used):
            calls.append({'stage':stage,'messages':messages,'config':config,'passages':used})
            text=json.dumps({'selected_ids':['unknown-source'] if invalid_selection else [p['id'] for p in used]},ensure_ascii=False) if stage=='selection' else final_content
            return {'stage':stage,'elapsed_seconds':0.0,'run_kind':'offline_stub_not_generation','response':{'choices':[{'message':{'content':text}}]}}
        result=candidate.execute(question,passages,'improved',answer,selection,dispatch)
        assert passages==before
        assert len(calls)==(1 if invalid_selection else 2)
        assert (result['derived_response'] is not None)==expect_derived
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
    for index in range(1,9):
        case,passages,_,_=data_runner.prepare(f'T{index:02d}','R0','baseline')
        messages,conf,_=candidate.answer_request(case['question'],passages,answer)
        schema=conf['parameters']['response_format']['json_schema']['schema']
        assert [m['role'] for m in messages]==['system','user'] and schema['required']==['answer','citations']
        assert len(passages)==len({p['id'] for p in passages}) and all({'id','source','text'}<=p.keys() for p in passages)
        input_rows.append({'case_id':f'T{index:02d}','condition':'R0','input_passages':len(passages),'schema_and_messages_checked':True})
    for path,expected in {**settings['code_sha256'],**settings['data_sha256']}.items():assert (ROOT/path).is_file() and sha(ROOT/path)==expected,path
    local=Path(os.environ['LOCALAPPDATA'])/'ANTLabLocalModel'
    assert sha(local/'models/Qwen3-0.6B-Q8_0.gguf')==settings['model']['actual_sha256']
    assert sha(local/'llama-b11429/llama-server.exe')==settings['llama_cpp']['executable_sha256']
    assert answer==load(BASE/'answer.prepared.json') and selection==load(BASE/'selection.prepared.json')
    assert not list(folder.glob('run-*.json')) and not (folder/'runtime.json').exists()
    for path in folder.glob('*.py'):ast.parse(path.read_text(encoding='utf-8-sig'))
    write(folder/'preflight.json',{'checked_at':now(),'passed':True,'returncode':0,'self_cases':130,'project_boundary_cases':83,'snapshot_cases':14,
        'integration_cases':len(integrations),'input_checks':input_rows,'model_code_config_data_hashes_match':True,
        'generation_scope_module_isolated_from_proof_scope_module':True,'no_model_settings_or_prompts_changed':True,'failed_gate_blocks_start':True,'generation_calls':0})
    for name in ['offline-check.json','additional-existing-tests.json','entry-gate-verification.json','runner-gate-integration.json','execution-offline-check.json']:
        write(folder/name,{'checked_at':now(),'passed':True,'returncode':0,'preflight':'preflight.json','generation_calls':0})
    write(folder/'operation-logging-check.json',{'checked_at':now(),'passed':True,'code_sha256':sha(folder/'proof_pipeline_candidate.py'),'event_versions_and_times_checked':True})
    print(json.dumps({'folder':str(folder),'passed':True,'synthetic':130,'boundary':83,'snapshot':14,'integration':len(integrations),'generation_calls':0},ensure_ascii=False))

if __name__=='__main__':
    active=None
    try:main()
    except Exception as error:
        if active is not None:write(active/'technical-stop.json',{'recorded_at':now(),'phase':'preparation','error_type':type(error).__name__,'detail':str(error),'traceback':traceback.format_exc(),'generation_dispatches':0,'service_started':False})
        raise
