import ast,hashlib,importlib.util,json,os,shutil,subprocess,sys,traceback
from pathlib import Path
from datetime import datetime
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
SOURCE=ROOT/'基础/runs/general_proof_full_r0/20261015-131742'
SYNTHETIC=ROOT/'基础/runs/eligibility_proof/20261015-000204'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now().astimezone().isoformat()
def write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as out:json.dump(value,out,ensure_ascii=False,indent=2);out.write('\n')
def mod(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main():
    global active
    folder=ROOT/'基础/runs/ratio_calculation_proof'/datetime.now().strftime('%Y%m%d-%H%M%S')
    folder.mkdir(parents=True,exist_ok=False);active=folder
    protected={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'基础/runs').rglob('*') if p.is_file() and folder not in p.parents}
    for name in ['report.md','README.md','基础/开发记录.md','基础/config.local.json']:
        if (ROOT/name).exists():protected[name]=sha(ROOT/name)
    for directory in ['基础/starter','基础/tests']:
        for p in (ROOT/directory).rglob('*.py'):protected[p.relative_to(ROOT).as_posix()]=sha(p)
    write(folder/'protected-hashes.json',protected)
    write(folder/'design-plan.json',{'saved_at':now(),'kind':'post_evaluation_independent_offline_ratio_proposal',
        'source_complete_round':SOURCE.relative_to(ROOT).as_posix(),'generation_calls':0,'services_started':False,'denominator':8,
        'rules':['先按问题识别指标，要求只计/列为的原文分类定义，再读同范围唯一并列计数和明确分母。',
            '分子只按明确类别计数相加；不由合法返回数反推技术失败，不将部分支持默认为完全支持。',
            '仅支持同计数单位、分类不嵌套、无明示重复交叉且总和等于分母的单次并列结果。列为不是穷尽定义，其他类别还须明示正常结果。',
            '首次必须有只计初次等范围证据；任何无法归属的额外计数/重试计数拒绝。',
            'Decimal计算百分比；精确有限十进制无须舍入，无限小数需明确四舍五入位数，未解析舍入要求拒绝。'],
        'proposal':'单独proposed_response，记录answer_changed；模型raw_response、已有proof/derived_response/最终输出都另存不改。',
        'material_policy':'事实与引文仅最终模型输入；其他原始可见资料只供范围、实体和唯一性审计。',
        'limits':['有限句式与明示正常状态检查不是通用语义分类。','并列分类及计数闭合不能保证没有未写出的隐含交叉；最终需独立原文复核。'],
        'gate':'比例正反例及130/83/14旧证明检查全部通过才冻结，并离线处理全8条；无模型调用。',
        'prior_cumulative':372})
    previous=load(SOURCE/'freeze.json')
    assert all(sha(ROOT/p)==h for p,h in previous['code_hashes'].items())
    files=['scope_candidate.py','scope_first_occurrences.py','eligibility_proof_checker.py','explicit_state_checker.py','eligibility_exclusion_candidate.py',
        'typed_enum_role_revision.py','typed_identifier_enum_candidate.py','body_identifier_enum_candidate.py','offline_gate.py',
        'general_citation_proof.py','proof_scope_occurrences.py','proof_snapshot_checker.py','project_scope_resolution.py',
        'check_general_citation_proof.py','check_project_scope_resolution.py']
    for name in files:shutil.copyfile(SOURCE/name,folder/name)
    for name in ['ratio_calculation_proof.py','check_ratio_calculation_proof.py','prepare_ratio_calculation_proof.py']:
        shutil.copyfile(Path(__file__).with_name(name),folder/name)
    for script in ['check_general_citation_proof.py','check_project_scope_resolution.py','check_ratio_calculation_proof.py']:
        command=[sys.executable,'-X','utf8','-B',str(folder/script)]
        result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',env={**os.environ,'PYTHONPATH':str(ROOT/'基础/tests')})
        write(folder/(script+'.execution.json'),{'executed_at':now(),'command':command,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'generation_calls':0})
        if result.returncode!=0:
            write(folder/'stop.json',{'recorded_at':now(),'stage':script,'reason':'离线检查失败，未冻结、未处理八题。','generation_calls':0})
            print(json.dumps({'folder':str(folder),'passed':False,'stage':script,'stdout':result.stdout,'stderr':result.stderr},ensure_ascii=False));return 1
    sys.path.insert(0,str(ROOT/'基础/tests'));sys.path.insert(0,str(folder))
    import general_citation_proof as old_proof
    regressions=[]
    for index in range(1,15):
        p=SYNTHETIC/f'test-{index:02d}.json';case=load(p)
        result=old_proof.prove_answer('竹岭项目V4版本在2026-04的发布快照是什么？只输出快照编号。',case['passages'],case['raw_response'])
        regressions.append({'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'passed':result['proof_established']==case['expected_established'],'proof':result})
    assert all(r['passed'] for r in regressions)
    write(folder/'snapshot-regressions.json',{'checked_at':now(),'passed':True,'total':14,'rows':regressions})
    gate=mod(folder/'offline_gate.py','ratio_gate');starts=[]
    try:gate.after_offline_success(lambda:{'passed':False,'returncode':1},lambda:starts.append('replay'))
    except RuntimeError:pass
    else:raise AssertionError('gate_not_blocking')
    assert not starts
    assert all(sha(SOURCE/name)==sha(folder/name) for name in files)
    write(folder/'offline-gate.json',{'checked_at':now(),'passed':True,'returncode':0,'failure_blocks_replay':True,'old_rule_files_identical':True,'generation_calls':0})
    for p in folder.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in folder.glob('*.py')}
    hashes.update({p:sha(ROOT/p) for p in previous['code_hashes'] if p.startswith('基础/tests/') or p.startswith('基础/starter/')})
    source_paths=[SOURCE/f'task-{i:02d}.json' for i in range(1,9)]
    write(folder/'freeze.json',{'frozen_at':now(),'kind':'offline_ratio_rules_frozen_before_all_eight_replays','frozen':True,
        'code_hashes':hashes,'data_hashes':previous['data_hashes'],'source_task_hashes':{p.relative_to(ROOT).as_posix():sha(p) for p in source_paths},
        'model_metadata_only_not_loaded':previous['model'],'source_freeze':(SOURCE/'freeze.json').relative_to(ROOT).as_posix(),
        'source_freeze_sha256':sha(SOURCE/'freeze.json'),'original_answer_never_modified':True,'proposed_new_answer_separate':True,
        'generation_calls':0,'denominator':8})
    print(json.dumps({'folder':str(folder),'passed':True,'ratio_cases':load(folder/'ratio-check.json')['total'],'prior_cases':130+83+14,'frozen':True,'generation_calls':0},ensure_ascii=False));return 0

if __name__=='__main__':
    active=None
    try:raise SystemExit(main())
    except Exception as error:
        if active is not None:write(active/'technical-stop.json',{'recorded_at':now(),'stage':'offline_preparation','error_type':type(error).__name__,'detail':str(error),'traceback':traceback.format_exc(),'generation_calls':0})
        raise
