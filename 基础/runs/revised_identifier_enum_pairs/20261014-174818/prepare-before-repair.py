from pathlib import Path
from datetime import datetime
import json,hashlib,copy,sys,ast,difflib
repo=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');base=repo/'基础'
previous=base/'runs/typed_identifier_enum_pairs/20261014-173249'
revision=base/'runs/typed_identifier_enum_revision/20261014-174223'
folder=base/'runs/revised_identifier_enum_pairs'/datetime.now().astimezone().strftime('%Y%m%d-%H%M%S')
folder.mkdir(parents=True,exist_ok=False)
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(n,v):
    p=folder/n;assert not p.exists();p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
save('protected-hashes.json',{p.relative_to(repo).as_posix():sha(p) for p in repo.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts and p.name!='config.local.json' and folder not in p.parents})
save('initial-memory-check.json',{'measured_at':'2026-10-14T17:43:43.801524+08:00','available_bytes':2235219968,'available_gib':2.0817108154296875,'threshold_gib':2,'meets_gate':True,'source':'本轮GlobalMemoryStatusEx实际测量；启动前运行器还将重新测量，不降低门槛。'})
assert load(revision/'synthetic-check.json')['passed']
for name in ['typed_enum_role_revision.py','body_identifier_enum_candidate.py','typed_identifier_enum_candidate.py']:(folder/name).write_bytes((revision/name).read_bytes())
for name in ['config.answer.json','system.original.txt','execution-plan.json','reused-results.json']:(folder/name).write_bytes((previous/name).read_bytes())
sys.path.insert(0,str(base/'tests'));sys.path.insert(0,str(base/'starter'));sys.path.insert(0,str(folder))
from general_candidate import answer_request
import body_identifier_enum_candidate as control
from typed_enum_role_revision import constrain_revised_roles
config=load(folder/'config.answer.json');plain=config['parameters']['response_format']['json_schema']['schema']
old_rows=load(previous/'eight-case-association-recompute.json')['items'];rows=[];rules=[];schemas={};cases=[]
verified={r['case_id']:r for r in load(revision/'candidate-list.json')['items']}
for row in old_rows:
    messages,conf,form=answer_request(row['question'],row['old_used_passages'],config)
    old,oldrule=control.constrain_body_identifiers(row['question'],row['old_used_passages'],plain)
    new,newrule=constrain_revised_roles(row['question'],row['old_used_passages'],plain)
    assert new==verified[row['case_id']]['schema'] and newrule['decisions']==verified[row['case_id']]['decisions']
    a={'model':conf['model'],'messages':messages,'stream':False,**conf['parameters']};a=copy.deepcopy(a);a['response_format']['json_schema']['schema']=old
    b=copy.deepcopy(a);b['response_format']['json_schema']['schema']=new
    assert a['messages']==b['messages'] and a!=b
    newrow=copy.deepcopy(row);newrow['raw_serialized_requests']={'old':json.dumps(a,ensure_ascii=False),'new':json.dumps(b,ensure_ascii=False)};rows.append(newrow)
    rules.append({'case_id':row['case_id'],**newrule})
    for variant,schema in [('old',old),('new',new)]:
        key=row['case_id']+'-'+variant;schemas[key]=schema
        for value in oldrule['values']+['证据不足']:
            cases.append([key,{'answer':value,'citations':[]},value in schema['properties']['answer']['enum']])
        for passage in row['old_used_passages']:cases.append([key,{'answer':passage['id'],'citations':[]},False])
save('candidate-list.json',{'checked_at':datetime.now().astimezone().isoformat(),'items':rules,'verified_revision_source':revision.relative_to(repo).as_posix(),'revision_source_sha256':sha(revision/'candidate-list.json')})
save('native-cases.json',{'schemas':schemas,'cases':cases})
save('eight-case-association-recompute.json',{'passed':True,'items':rows,'input_kind':'historical_completed_evidence_replay_no_new_selection'})
save('offline-check.json',{'checked_at':datetime.now().astimezone().isoformat(),'passed':True,'candidate_matches_verified_revision':True,'only_answer_enum_changed':True,'same_prompt_passages_parameters_and_budget':True,'native_validation_required_before_generation':True})
save('design-plan.json',{'saved_at':datetime.now().astimezone().isoformat(),'kind':'post_evaluation_revised_typed_enum_pairs','hypothesis':'排除所有可靠非目标类型，可能减少业务编号答案，但不保证在快照候选中选对。','competing_explanation':'错误快照、漏规则或错误拒答仍可能存在；类型合法与答案正确分开。','only_change':'对照正文全部编号enum，候选复用20261014-174223已验证角色规则。','evaluation':'对象类型、原文答案依据、必要引用覆盖、实际答案支持、严格成功独立记录；T01条件推导和严格字面边界保留。','stop':'启动前至少2GiB；沿用0.6B运行器资源监测。最多4次生成，技术失败保存停止，质量错误不重试。','previous_unique_generations':292,'adoption':'不自动采用，不改变生产方案。'})
source=previous/'run_typed_enum_pair.py';runner=source.read_text(encoding='utf-8')
def replace(a,b):
    global runner
    assert runner.count(a)==1,(a,runner.count(a));runner=runner.replace(a,b)
replace("['run_typed_enum_pair.py','typed_identifier_enum_candidate.py','body_identifier_enum_candidate.py','config.answer.json','eight-case-association-recompute.json']","['run_revised_enum_pair.py','typed_enum_role_revision.py','typed_identifier_enum_candidate.py','body_identifier_enum_candidate.py','config.answer.json','eight-case-association-recompute.json']")
replace('from typed_identifier_enum_candidate import constrain_typed_identifiers as constrain','from typed_enum_role_revision import constrain_revised_roles as constrain')
replace("'experiment_kind':'post_evaluation_typed_identifier_enum_pairs'","'experiment_kind':'post_evaluation_revised_typed_identifier_enum_pairs'")
ast.parse(runner);(folder/'run_revised_enum_pair.py').write_text(runner,encoding='utf-8')
(folder/'runner-adaptation.diff').write_text(''.join(difflib.unified_diff(source.read_text(encoding='utf-8').splitlines(True),runner.splitlines(True),fromfile=source.relative_to(repo).as_posix(),tofile=(folder/'run_revised_enum_pair.py').relative_to(repo).as_posix())),encoding='utf-8')
(folder/'check-native-enum.py').write_bytes((previous/'check-native-enum.py').read_bytes())
save('native-tool-reuse.json',{'source':(previous/'check-native-enum.py').relative_to(repo).as_posix(),'source_sha256':sha(previous/'check-native-enum.py'),'same_native_tool':True})
print(folder)
