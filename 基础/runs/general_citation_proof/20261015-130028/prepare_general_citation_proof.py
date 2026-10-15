import ast
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
SOURCE=ROOT/'基础/runs/proof_full_r0_repeat/20261015-124627'
PROOF=ROOT/'基础/runs/eligibility_proof/20261015-000204'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now().astimezone().isoformat()
def write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as out:json.dump(value,out,ensure_ascii=False,indent=2);out.write('\n')
def main():
    folder=ROOT/'基础/runs/general_citation_proof'/datetime.now().strftime('%Y%m%d-%H%M%S')
    folder.mkdir(parents=True,exist_ok=False)
    protected={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'基础/runs').rglob('*') if p.is_file() and folder not in p.parents}
    for name in ['report.md','README.md','基础/开发记录.md','基础/config.local.json']:
        if (ROOT/name).exists():protected[name]=sha(ROOT/name)
    for directory in ['基础/starter','基础/tests']:
        for p in (ROOT/directory).rglob('*.py'):protected[p.relative_to(ROOT).as_posix()]=sha(p)
    write(folder/'protected-hashes.json',protected)
    write(folder/'design-plan.json',{'saved_at':now(),'kind':'post_evaluation_offline_proof_extension_no_model_generation',
        'scope':'保留既有快照证明；新增有限差值与资格选择原文语法，只证明已有answer并派生引用。',
        'difference':'先从问题确定对象、指标、单位、方向；唯一直接同批主文/补页、同样样本集合及一致统计量，Decimal计算后才比较原answer。',
        'selection':'先解析完整资格门槛与字段，再筛选；有多个合格项才按明确最大化/最小化的次序比较，未解并列拒绝。唯一合格项不需要未触发的后续排名。',
        'field_inheritance':'表状分号行只有首行明示字段、相同列数/单位且显式字段不冲突，才允许后续行承接字段；不任意猜同义词。',
        'range':'复用已验证唯一直接关联；主文与问题范围须完整匹配，补页缺字段仍标未知，只能通过唯一直接指称承接，不视为显式相同。',
        'risks':['有限正则和表状字段继承不是通用语义理解；不能证明未解析的隐藏条件。','数量通过承接检查集合沿用旧有限解释，T01歧义保持。','新的规则是在已接触评测资料后设计，不是盲测。'],
        'gate':'所有自造检查与旧快照回归通过后才冻结；冻结后遍历最新完整8条，不挑预期成功题；失败阻断实际材料处理。',
        'generation_calls':0,'denominator':8,'previous_cumulative':356})
    names=['scope_candidate.py','scope_first_occurrences.py','eligibility_proof_checker.py','explicit_state_checker.py',
        'eligibility_exclusion_candidate.py','typed_enum_role_revision.py','typed_identifier_enum_candidate.py','body_identifier_enum_candidate.py','offline_gate.py']
    for name in names:shutil.copyfile(SOURCE/name,folder/name)
    for name in ['general_citation_proof.py','check_general_citation_proof.py','prepare_general_citation_proof.py']:
        shutil.copyfile(Path(__file__).with_name(name),folder/name)
    command=[sys.executable,'-X','utf8','-B',str(folder/'check_general_citation_proof.py')]
    result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',env={**__import__('os').environ,'PYTHONPATH':str(ROOT/'基础/tests')})
    write(folder/'self-check-command.json',{'executed_at':now(),'command':[str(p).replace(str(ROOT),'<repo>') for p in command],
        'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'generation_calls':0})
    if result.returncode!=0:
        write(folder/'stop.json',{'recorded_at':now(),'stage':'synthetic_regression','reason':'自造检查未全通过，未冻结、未处理八题。','generation_calls':0})
        print(json.dumps({'folder':str(folder),'passed':False,'stage':'synthetic_regression','output':result.stdout,'error':result.stderr},ensure_ascii=False));return 1
    sys.path.insert(0,str(ROOT/'基础/tests'));sys.path.insert(0,str(folder))
    import general_citation_proof as candidate
    prior=[]
    for index in range(1,15):
        path=PROOF/f'test-{index:02d}.json';case=load(path)
        actual=candidate.prove_answer('竹岭项目V4版本在2026-04的发布快照是什么？只输出快照编号。',case['passages'],case['raw_response'])
        passed=actual['proof_established']==case['expected_established']
        prior.append({'source':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'passed':passed,'result':actual})
    gate=__import__('offline_gate');starts=[]
    try:gate.after_offline_success(lambda:{'passed':False,'returncode':1},lambda:starts.append('actual_material'))
    except RuntimeError:blocked=True
    else:blocked=False
    unchanged={name:sha(folder/name)==sha(SOURCE/name) for name in names}
    assert all(r['passed'] for r in prior) and blocked and not starts and all(unchanged.values())
    write(folder/'snapshot-regressions.json',{'checked_at':now(),'total':len(prior),'passed':all(r['passed'] for r in prior),'rows':prior,'unchanged_inherited_files':unchanged})
    write(folder/'offline-gate.json',{'checked_at':now(),'passed':True,'returncode':0,'failed_check_blocks_material_processing':True,'generation_calls':0})
    for path in folder.glob('*.py'):ast.parse(path.read_text(encoding='utf-8-sig'))
    oldfreeze=load(SOURCE/'freeze.json')
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in folder.glob('*.py')}
    hashes.update({p:sha(ROOT/p) for p in oldfreeze['code_hashes'] if p.startswith('基础/tests/') or p.startswith('基础/starter/')})
    source_paths=[SOURCE/f'task-{i:02d}.json' for i in range(1,9)]
    assert all(p.is_file() for p in source_paths)
    write(folder/'freeze.json',{'frozen_at':now(),'kind':'offline_rules_frozen_before_eight_response_replay','frozen':True,
        'not_blind_or_new_model_evaluation':True,'code_hashes':hashes,'data_hashes':oldfreeze['data_hashes'],
        'source_task_hashes':{p.relative_to(ROOT).as_posix():sha(p) for p in source_paths},
        'model_metadata_only_not_loaded':oldfreeze['model'],'source_frozen_config':SOURCE.relative_to(ROOT).as_posix()+'/freeze.json',
        'source_config_sha256':sha(SOURCE/'freeze.json'),'rule_order':['snapshot','difference','qualification_selection','not_applicable_keep_raw'],
        'answer_never_changed':True,'generation_calls':0,'denominator':8})
    print(json.dumps({'folder':str(folder),'passed':True,'self_checks':load(folder/'self-check.json')['total'],'snapshot_checks':14,'frozen':True,'generation_calls':0},ensure_ascii=False));return 0

if __name__=='__main__':raise SystemExit(main())
