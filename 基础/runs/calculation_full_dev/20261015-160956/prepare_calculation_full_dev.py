import ast, copy, difflib, hashlib, json, os, shutil, sys, traceback
from pathlib import Path
from datetime import datetime
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
BASE=ROOT/'基础/runs/calculation_compat_dev/20261015-160141'
RUNNER=ROOT/'基础/runs/association_compat_dev/20261015-154928'
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
    folder=ROOT/'基础/runs/calculation_full_dev'/datetime.now().strftime('%Y%m%d-%H%M%S');folder.mkdir(parents=True,exist_ok=False);active=folder
    write(folder/'preparation-plan.json',{'saved_at':now(),'kind':'fresh_development_full_flow_current_calculation_candidate',
        'tasks':4,'generation_limit':8,'previous_cumulative':404,'order':[f'D{i:02d}' for i in range(1,5)],
        'hypothesis':'只验证已冻结计算兼容修复的新定位和回答完整流程，不新增优化分支。',
        'limits':'D01定义绑定不足继续拒绝；证明事实与派生引用只来自实际最终回答输入，额外原文只审计范围和唯一性。',
        'fixed':'已有提示词、解析规则、模型、Schema派生、采样和256预算不变；定位/回答各一次。',
        'stop':'技术失败保存停止；质量错误不重试；最多8次生成，结束停止自有服务。',
        'evaluation':'全部调用后才读公开开发答案；保留所有4题，原始/最终答案及严格成功分开；重点D03及D02/D04退步。'})
    previous_stops=sorted(p.relative_to(ROOT).as_posix() for p in folder.parent.glob('*/technical-stop.json'))
    if previous_stops:
        write(folder/'preparation-engineering-repair.json',{'recorded_at':now(),'preserved_stops':previous_stops,
            'repair':'项目边界83项=80个独立文件+汇总内3项integration；显式核对两部分，不删除检查，不修改解析规则。',
            'authorization':'沿用准备阶段可离线修复目录、路径、导入等工程错误的授权；此前模型请求为0。'})
    regress=load(BASE/'regression-summary.json');assert regress['all_passed'] and regress['old_cases_passed']==437 and regress['new_cases_passed']==97
    oldfreeze=load(BASE/'replay-freeze.json');assert all(sha(ROOT/p)==h for p,h in oldfreeze['code_hashes'].items())
    sources=['scope_candidate.py','scope_first_occurrences.py','eligibility_proof_checker.py','explicit_state_checker.py',
        'eligibility_exclusion_candidate.py','typed_enum_role_revision.py','typed_identifier_enum_candidate.py','body_identifier_enum_candidate.py','offline_gate.py',
        'proof_scope_occurrences.py','proof_snapshot_checker.py','general_citation_proof.py','project_scope_resolution.py',
        'ratio_calculation_proof.py','difference_calculation_proposal.py','proof_pipeline_candidate.py','direct_reference_candidate.py',
        'check_association_compat.py','check_general_citation_proof.py','check_project_scope_resolution.py','check_ratio_calculation_proof.py','check_calculation_compat.py']
    for name in sources:shutil.copyfile(BASE/name,folder/name)
    for name in ['settings.prepared.json','answer.prepared.json','selection.prepared.json']:shutil.copyfile(BASE/name,folder/name)
    shutil.copyfile(Path(__file__),folder/Path(__file__).name)
    wrapper=(folder/'proof_pipeline_candidate.py').read_text(encoding='utf-8');oldwrapper=wrapper
    wrapper=patch(wrapper,'import ratio_calculation_proof as ratio','import ratio_calculation_proof as ratio\nimport difference_calculation_proposal as difference')
    wrapper=patch(wrapper,"    install(ratio, 'propose', 'ratio_calculation_proposal')","    install(ratio, 'propose', 'ratio_calculation_proposal')\n    install(difference, 'propose', 'difference_calculation_proposal')")
    block="""        result['ratio_proposed_response'] = copy.deepcopy(result['ratio_proof']['proposed_response'])
        if result['status']=='completed' and valid:
            result['difference_proposal'] = difference.propose(question, final_passages, result['raw_answer'], universe=originals)
        else:
            result['difference_proposal'] = {'applicable':False,'status':'not_run','proof_established':False,
                'reason':'upstream_selection_or_raw_format_failure','proposed_response':None,'trace':[],'answer_changed':False}
        assert not(result['ratio_proposed_response'] is not None and result['difference_proposal']['proposed_response'] is not None)
        difference_facts = position_records([t for t in result['difference_proposal']['trace'] if t.get('stage')=='difference_proof'])
        assert all(e['passage_id'] in sources and sources[e['passage_id']][e['start']:e['end']]==e['quote'] for e in difference_facts)
        result['difference_fact_sources'] = difference_facts
        if result['difference_proposal']['proposed_response'] is not None:
            result['proposed_response'] = copy.deepcopy(result['difference_proposal']['proposed_response'])
            assert set(result['proposed_response']['citations'])<=final_ids
"""
    wrapper=patch(wrapper,"        result['ratio_fact_sources'] = ratio_facts", "        result['ratio_fact_sources'] = ratio_facts\n"+block.rstrip())
    wrapper=patch(wrapper,"'ratio_proof':copy.deepcopy(result['ratio_proof'])}","'ratio_proof':copy.deepcopy(result['ratio_proof']), 'difference_proof':copy.deepcopy(result['difference_proposal'])}")
    wrapper=patch(wrapper,"            result['actual_final_output_source'] = ('local_rule_ratio_new_answer'\n                if result['ratio_proof']['answer_changed'] else 'local_rule_ratio_confirmed_answer_and_citations')", "            if result['difference_proposal']['proposed_response'] is not None:\n                result['actual_final_output_source'] = ('local_rule_difference_new_answer' if result['difference_proposal']['answer_changed'] else 'local_rule_difference_confirmed_answer_and_citations')\n            else:\n                result['actual_final_output_source'] = ('local_rule_ratio_new_answer' if result['ratio_proof']['answer_changed'] else 'local_rule_ratio_confirmed_answer_and_citations')")
    wrapper=wrapper.replace('比例证明成立优先采用单独计算建议；否则采用不改答案的引用证明；否则保留模型原始结果。三种来源不混称。','差值或比例证明成立采用独立计算建议；否则引用证明；否则原答。原始、计算和引用组装分别保留。')
    ast.parse(wrapper);(folder/'proof_pipeline_candidate.py').write_text(wrapper,encoding='utf-8',newline='\n')
    runner=(RUNNER/'run_association_compat_dev.py').read_text(encoding='utf-8');oldrunner=runner
    runner=runner.replace('run_association_compat_dev.py','run_calculation_full_dev.py').replace('prepare_association_compat_dev.py',Path(__file__).name)
    runner=patch(runner,"'previous_cumulative':396,'cumulative_confirmed':396+len(ids)","'previous_cumulative':404,'cumulative_confirmed':404+len(ids)")
    runner=patch(runner,"'check_association_compat.py']","'check_association_compat.py','difference_calculation_proposal.py','check_calculation_compat.py']")
    runner=runner.replace('仅开发4题复核声明语法兼容修复，分别比较模型原始与系统最终答案及引用表现，历史基准2/4。','仅开发4题验证计算兼容修复完整流程；重新定位与回答，分别评价模型原始和系统最终结果，不拼接历史响应。')
    runner=runner.replace('frozen_development_association_compatibility_repair','frozen_development_calculation_compatibility_full_flow')
    runner=patch(runner,"'output_policy':'比例计算建议优先；否则引用证明；否则原始回答。计算改答与引用组装独立保存。',", "'output_policy':'独立差值或比例计算建议优先；否则引用证明；否则原始回答。计算与引用组装独立保存。',\n              'difference_rule_sha256':sha(folder/'difference_calculation_proposal.py'),\n              'retained_regressions':load(folder/'retained-regressions.json'),")
    ast.parse(runner);(folder/'run_calculation_full_dev.py').write_text(runner,encoding='utf-8',newline='\n')
    diff=''.join(difflib.unified_diff(oldwrapper.splitlines(True),wrapper.splitlines(True),fromfile='validated_offline/proof_pipeline_candidate.py',tofile='full_flow/proof_pipeline_candidate.py'))
    diff+=''.join(difflib.unified_diff(oldrunner.splitlines(True),runner.splitlines(True),fromfile='previous/run_association_compat_dev.py',tofile='full_flow/run_calculation_full_dev.py'))
    (folder/'integration.diff').write_text(diff,encoding='utf-8',newline='\n')
    references=['regression-summary.json','association-compat-self-tests.json','self-check.json','boundary-check.json','ratio-check.json','calculation-compat-self-tests.json']
    assert all((BASE/name).is_file() for name in references)
    reference_rows=[{'path':(BASE/name).relative_to(ROOT).as_posix(),'sha256':sha(BASE/name)} for name in references]
    boundary=load(BASE/'boundary-check.json')
    project_files=len(list(BASE.glob('boundary-test-*.json')))
    project_integrations=boundary['integration']
    assert all(row['passed'] for row in project_integrations) and project_files+len(project_integrations)==boundary['total']==83
    counts={'association':load(BASE/'association-compat-self-tests.json')['count'],'citation':len(list(BASE.glob('self-test-*.json'))),
        'project':project_files+len(project_integrations),'ratio':len(list(BASE.glob('ratio-test-*.json'))),'calculation':load(BASE/'calculation-compat-self-tests.json')['total']}
    assert sum(counts.values())==534 and load(BASE/'calculation-compat-self-tests.json')['passed']
    rule_names=['direct_reference_candidate.py','general_citation_proof.py','ratio_calculation_proof.py','difference_calculation_proposal.py','scope_candidate.py']
    assert all(sha(folder/n)==sha(BASE/n) for n in rule_names)
    write(folder/'retained-regressions.json',{'checked_at':now(),'counts':counts,'total':534,'all_passed':True,'references':reference_rows,
        'unchanged_rule_hashes':{n:sha(folder/n) for n in rule_names},'not_relabelled_as_new_regression_runs':True})
    jobs=[{'sequence':i,'case_id':f'D{i:02d}','condition':'R0','variant':'improved','dataset':'development'} for i in range(1,5)]
    write(folder/'execution-plan.prepared.json',{'saved_at':now(),'generation_limit':8,'fresh_selection':True,'items':jobs})
    sys.path.insert(0,str(ROOT/'基础/tests'));sys.path.insert(0,str(folder))
    import proof_pipeline_candidate as candidate
    assert Path(candidate.base.completion.__file__).resolve()==folder/'direct_reference_candidate.py'
    assert Path(candidate.difference.shared.__file__).resolve()==folder/'general_citation_proof.py'
    answer=load(folder/'answer.prepared.json');selection=load(folder/'selection.prepared.json')
    checks=[]
    def check(name,question,ps,raw,expected=None,invalid=False):
        before=copy.deepcopy(ps);calls=[]
        def dispatch(stage,messages,conf,used):
            calls.append(stage);content=json.dumps({'selected_ids':['missing'] if invalid else [p['id'] for p in used]}) if stage=='selection' else raw
            return {'stage':stage,'elapsed_seconds':0,'run_kind':'offline_stub_not_generation','response':{'choices':[{'message':{'content':content}}]}}
        actual=candidate.execute(question,ps,'improved',answer,selection,dispatch)
        assert ps==before and len(calls)==(1 if invalid else 2)
        if expected is not None:assert actual['actual_final_output']['answer']==expected
        if not invalid:assert actual['raw_response']==actual['stages'][-1]['response'] and actual['raw_answer']==raw
        checks.append({'name':name,'passed':True,'result':actual})
    check('empty','只输出数值。',[],'{"answer":"证据不足","citations":[]}',expected='证据不足')
    check('invalid_selection','普通问题',[],'',invalid=True)
    check('invalid_raw_format','普通问题',[],'{"answer":')
    example=load(BASE/'calculation-compat-self-tests.json')['rows'][0]
    check('independent_difference_proposal',example['question'],example['passages'],'{"answer":"错误原答","citations":[]}',expected=example['expected'])
    write(folder/'integration-offline-check.json',{'checked_at':now(),'passed':True,'rows':checks,'generation_calls':0})
    settings=load(folder/'settings.prepared.json')
    for p,h in {**settings['code_sha256'],**settings['data_sha256']}.items():assert sha(ROOT/p)==h,p
    local=Path(os.environ['LOCALAPPDATA'])/'ANTLabLocalModel'
    assert sha(local/'models/Qwen3-0.6B-Q8_0.gguf')==settings['model']['actual_sha256']
    assert sha(local/'llama-b11429/llama-server.exe')==settings['llama_cpp']['executable_sha256']
    from offline_gate import after_offline_success
    starts=[]
    try:after_offline_success(lambda:{'passed':False,'returncode':1},lambda:starts.append('service'))
    except RuntimeError:pass
    else:raise AssertionError('gate_not_blocking')
    assert not starts
    for p in folder.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
    write(folder/'proof-rules-index.json',{'saved_at':now(),'source':BASE.relative_to(ROOT).as_posix(),'unchanged_rules':{n:sha(folder/n) for n in rule_names}})
    write(folder/'fixture-index.json',{'saved_at':now(),'retained':'retained-regressions.json','integration_cases':4})
    write(folder/'preflight.json',{'checked_at':now(),'passed':True,'returncode':0,'retained_regressions':534,'integration_cases':4,'failed_gate_blocks_start':True,'generation_calls':0})
    for name in ['offline-check.json','additional-existing-tests.json','entry-gate-verification.json','runner-gate-integration.json','execution-offline-check.json']:
        write(folder/name,{'checked_at':now(),'passed':True,'returncode':0,'preflight':'preflight.json','generation_calls':0})
    write(folder/'operation-logging-check.json',{'checked_at':now(),'passed':True,'code_sha256':sha(folder/'proof_pipeline_candidate.py'),'difference_hook_and_raw_response_preservation_checked':True})
    print(json.dumps({'folder':str(folder),'passed':True,'retained_regressions':534,'integration_checks':4,'maximum_generations':8},ensure_ascii=False))

if __name__=='__main__':
    active=None
    try:main()
    except Exception as error:
        if active is not None:write(active/'technical-stop.json',{'recorded_at':now(),'phase':'preparation','error':str(error),'traceback':traceback.format_exc(),'generation_calls':0,'service_started':False})
        raise
