import copy
import hashlib
import importlib.util
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
SCOPE=ROOT/'基础/runs/scope_first_pairs/20261014-234038'
T01SOURCE=ROOT/'基础/runs/eligibility_r0_repeat/20261014-231852/full/task-01.json'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now().astimezone().isoformat()

def write(p,value):
    with p.open('x',encoding='utf-8',newline='\n') as out:json.dump(value,out,ensure_ascii=False,indent=2);out.write('\n')
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def positions(result,passages):
    by_id={p['id']:p['text'] for p in passages}
    def visit(value):
        if isinstance(value,dict):
            if all(k in value for k in ['passage_id','start','end','quote']) and value['passage_id'] in by_id:
                assert by_id[value['passage_id']][value['start']:value['end']]==value['quote']
            for item in value.values():visit(item)
        elif isinstance(value,list):
            for item in value:visit(item)
    visit(result)

def main():
    folder=ROOT/'基础/runs/eligibility_proof'/datetime.now().strftime('%Y%m%d-%H%M%S')
    folder.mkdir(parents=True,exist_ok=False)
    protected={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'基础/runs').rglob('*') if p.is_file() and folder not in p.parents}
    for name in ['report.md','README.md','基础/开发记录.md','基础/starter/student.py']:
        protected[name]=sha(ROOT/name)
    write(folder/'design-plan.json',{'saved_at':now(),'kind':'post_evaluation_offline_proof_not_model_generation',
        'scope':'获选项正向资格逐条件证明，不使用排除其他项作为通过依据。仅唯一直接发布规则、显式范围与可靠描述。',
        'aggregate_rule':'数量表达仅在候选自身明确完整数量通过、唯一同记录规则定义同数量完整检查集合且明示集合无冲突时承接；不凭数量相等单独判断。',
        'unknown':'未列、部分通过、未解析规则、额外禁止条件无证据均unknown；不推断T01未知条件通过。',
        'derivation':'成立时answer逐字不变，引用仅收集实际证明条件的数据与规则，独立标为local_rule引用组装。',
        'limits':'有限语法与同记录指称解释，不保证发现所有隐含集合；系统proof不是独立语义核验，另存辅助原文复核。',
        'protected_hashes':protected,'generation_calls':0,'model_loading':False})
    for name in ['scope_first_occurrences.py','explicit_state_checker.py','eligibility_exclusion_candidate.py','typed_enum_role_revision.py','typed_identifier_enum_candidate.py','body_identifier_enum_candidate.py','offline_gate.py']:
        shutil.copyfile(SCOPE/name,folder/name)
    shutil.copyfile(Path(__file__).with_name('eligibility_proof_checker.py'),folder/'eligibility_proof_checker.py')
    shutil.copyfile(Path(__file__),folder/'prepare_eligibility_proof.py')
    sys.path.insert(0,str(ROOT/'基础/tests'));sys.path.insert(0,str(folder))
    proof=module(folder/'eligibility_proof_checker.py','independent_proof')
    cases=[
        ('complete_named_pass','文本问答通过、区域定位通过、会话恢复通过','文本问答、区域定位和会话恢复三项检查全部通过',True),
        ('complete_aggregate_pass','三项检查通过','文本问答、区域定位和会话恢复三项检查全部通过',True),
        ('partial_pass','文本问答通过、区域定位通过','文本问答、区域定位和会话恢复三项检查全部通过',False),
        ('partial_count_pass','三项中两项通过','文本问答、区域定位和会话恢复三项检查全部通过',False),
        ('count_mismatch','三项检查通过','文本问答、区域定位、会话恢复和结果导出四项检查全部通过',False),
        ('missing_rule','三项检查通过',None,False),
        ('rule_scope_conflict','三项检查通过','文本问答、区域定位和会话恢复三项检查全部通过',False),
        ('only_others_excluded','记录未说明','文本问答、区域定位和会话恢复三项检查全部通过',False),
        ('selected_defect','文本问答通过、区域定位2项偏移、会话恢复通过','文本问答、区域定位和会话恢复三项检查全部通过',False),
        ('forbidden_count_missing','三项检查通过','文本问答、区域定位和会话恢复三项检查全部通过，且不存在未关闭问题',False),
        ('forbidden_zero_proved','文本问答通过、区域定位通过、会话恢复通过、未关闭问题数量为零','文本问答、区域定位和会话恢复三项检查全部通过，且不存在未关闭问题',True),
        ('same_count_other_set','三项检查通过','文本问答、区域定位和会话恢复三项检查全部通过',False),
        ('unparsed_requirements','三项检查通过','同一快照完成上述三项检查，且不存在未关闭问题',False),
        ('contradictory_status','文本问答通过、区域定位通过、区域定位2项偏移、会话恢复通过','文本问答、区域定位和会话恢复三项检查全部通过',False),
    ]
    results=[]
    for i,(name,description,rule,expected) in enumerate(cases):
        text='竹岭项目V4版本在2026-04的记录：'
        if name=='same_count_other_set':text+='检查集合为构建、部署和发布。'
        text+='复核表ZL39显示Choice11'+description+'；Choice12区域定位3项偏移。'
        passages=[{'id':'data-source','source':'self','text':text}]
        if rule is not None:
            prefix='其他项目V5版本在2026-05。' if name=='rule_scope_conflict' else ''
            passages.append({'id':'release-source','source':'another-directory','text':prefix+'批次ZL39的复核补页：ZL39的发布规则要求'+rule+'。'})
        passages.append({'id':'unrelated-source','source':'self','text':'其他记录只登记导出时间，不提供该候选检查结果。'})
        question='竹岭项目V4版本在2026-04的发布快照是什么？只输出快照编号。'
        raw='{"answer":"Choice11","citations":["data-source"]}'
        before=copy.deepcopy(passages)
        result=proof.prove_answer(question,passages,raw)
        positions(result,passages)
        mapped=copy.deepcopy(passages)
        for j,p in enumerate(mapped):p['id']='Remap'+str(j)
        remap=proof.prove_answer(question,mapped,raw)
        positions(remap,mapped)
        passed=result['proof_established']==expected and remap['proof_established']==expected and passages==before
        if expected:
            passed=passed and result['final_response']['answer']=='Choice11' and set(result['final_response']['citations'])=={'data-source','release-source'}
            passed=passed and set(remap['final_response']['citations'])=={'Remap0','Remap1'}
        else:passed=passed and result['final_response'] is None
        entry={'name':name,'expected_established':expected,'passed':passed,'passages':passages,'raw_response':raw,'proof':result,'remapped_proof':remap}
        write(folder/('test-'+str(i+1).zfill(2)+'.json'),{'checked_at':now(),**entry});results.append(entry)
    passed=all(r['passed'] for r in results)
    write(folder/'offline-check.json',{'checked_at':now(),'passed':passed,'returncode':0 if passed else 1,
        'total':len(results),'passed_count':sum(r['passed'] for r in results),'failed_cases':[r['name'] for r in results if not r['passed']]})
    if not passed:
        write(folder/'stop.json',{'stopped_at':now(),'stage':'synthetic_regression','generation_calls':0,'real_material_recheck_not_run':True})
        print(json.dumps({'folder':str(folder),'passed':False,'failed':[r['name'] for r in results if not r['passed']]},ensure_ascii=False));return 1
    gate=module(folder/'offline_gate.py','proof_gate')
    def recheck_real():
        outputs=[]
        for label,path in [('T08',SCOPE/'task-02.json'),('T01',T01SOURCE)]:
            task=load(path);result=proof.prove_answer(task['question'],task['used_passages'],task['raw_answer'],task['original_passages'])
            positions(result,task['original_passages'])
            output={'checked_at':now(),'case_id':label,'source_path':path.relative_to(ROOT).as_posix(),'source_sha256':sha(path),
                'raw_response':task['stages'][-1]['response'],'raw_content':task['raw_answer'],
                'actual_final_passages':task['used_passages'],'full_original_passages':task['original_passages'],'proof':result,
                'original_response_and_evaluation_not_modified':True}
            write(folder/('proof-'+label+'.json'),output);outputs.append(output)
        return outputs
    outputs=gate.after_offline_success(lambda:load(folder/'offline-check.json'),recheck_real)
    assert all(sha(ROOT/p)==h for p,h in protected.items())
    write(folder/'code-hashes.json',{'checked_at':now(),'files':{p.name:sha(p) for p in folder.glob('*.py')}})
    write(folder/'preservation-audit.json',{'checked_at':now(),'all_old_files_unchanged':True,'generation_calls':0,'services_started':False})
    print(json.dumps({'folder':str(folder),'passed':True,'total':len(results),'items':[{'case_id':o['case_id'],'status':o['proof']['proof_status'],
        'final_response':o['proof']['final_response'],'conditions':[(c['name'],c['status']) for c in o['proof']['conditions']]} for o in outputs]},ensure_ascii=False))
    return 0

if __name__=='__main__':raise SystemExit(main())
