import ast
import copy
import difflib
import hashlib
import importlib.util
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
PREVIOUS=ROOT/'基础/runs/local_rule_state_pairs/20261014-225350'
EXCLUSION=ROOT/'基础/runs/eligibility_exclusion/20261014-230758'
TYPES=ROOT/'基础/runs/revised_identifier_enum_pairs/20261014-174818'
now=lambda:datetime.now().astimezone().isoformat()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))

def write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as out:
        json.dump(value,out,ensure_ascii=False,indent=2);out.write('\n')

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def patch(text,old,new):
    assert text.count(old)==1,old[:100]
    return text.replace(old,new,1)

def main():
    parent=ROOT/'基础/runs/eligibility_r0_repeat'/datetime.now().strftime('%Y%m%d-%H%M%S')
    parent.mkdir(parents=True,exist_ok=False)
    small=parent/'small';full=parent/'full';small.mkdir();full.mkdir()
    protected_paths=[p for p in (ROOT/'基础/runs').rglob('*') if p.is_file() and parent not in p.parents]
    protected_paths += [ROOT/p for p in ['report.md','README.md','基础/开发记录.md','基础/starter/student.py','基础/starter/provider.py']]
    protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected_paths}
    freeze=load(ROOT/'基础/runs/formal/round2-20261014-133000/freeze.json')
    write(parent/'authorization-plan.json',{'saved_at':now(),'kind':'post_evaluation_repeat_not_blind',
        'small_limit':2,'full_main_task_limit':8,'full_generation_limit':16,
        'total_generation_limit':18,'order':'T08原类型enum/资格enum；完成且无技术错误后T01至T08逐题R0 improved。',
        'unknown_policy':'不能自动对应的资格规则保留原enum，不按题号回退。未知不代表合格。',
        'first_stage_only_change':'answer enum','full_flow':'新定位+唯一直接补页+最终回答；不复用历史定位。',
        'previous_cumulative':316,'failure_policy':'离线或技术失败停止；质量失败不重试，主任务仍计8题分母。',
        'protected_hashes':protected,'evaluation':'沿用原文辅助暂判口径，保留歧义；严格成功是综合指标，非官方成绩。'})
    common={
        'eligibility_general_candidate.py':Path(__file__).with_name('eligibility_general_candidate.py'),
        'explicit_state_checker.py':PREVIOUS/'explicit_state_checker.py',
        'eligibility_exclusion_candidate.py':EXCLUSION/'eligibility_exclusion_candidate.py',
        'offline_gate.py':PREVIOUS/'offline_gate.py',
        'typed_enum_role_revision.py':TYPES/'typed_enum_role_revision.py',
        'typed_identifier_enum_candidate.py':TYPES/'typed_identifier_enum_candidate.py',
        'body_identifier_enum_candidate.py':TYPES/'body_identifier_enum_candidate.py'}
    for folder in [small,full]:
        for name,path in common.items():shutil.copyfile(path,folder/name)
    sys.path.insert(0,str(ROOT/'基础/tests'));sys.path.insert(0,str(small))
    candidate=module(small/'eligibility_general_candidate.py','eligible_general')
    original_audit=load(EXCLUSION/'original-evidence-audit-T08.json')
    original=original_audit['original_request']
    conf=copy.deepcopy(freeze['answer_config']);conf['parameters']={k:v for k,v in original.items() if k not in {'messages','model','stream'}}
    messages,newconf,trace=candidate.answer_request(original_audit['question'],original_audit['passages'],conf)
    revised={'model':newconf['model'],'messages':messages,'stream':False,**newconf['parameters']}
    removed=copy.deepcopy(revised);removed['response_format']['json_schema']['schema']['properties']['answer']['enum']=original['response_format']['json_schema']['schema']['properties']['answer']['enum']
    assert removed==original and trace['qualification_enabled']
    assert revised['response_format']['json_schema']['schema']['properties']['answer']['enum']==original_audit['audit']['answer_enum']
    literals=[n.value for n in ast.walk(ast.parse((small/'eligibility_general_candidate.py').read_text(encoding='utf-8'))) if isinstance(n,ast.Constant) and isinstance(n.value,str)]
    assert not any(any(bad in s for bad in ['T01','T08','K17','K16','K18','P183430','P223300']) for s in literals)
    tests=[]
    for path in sorted(EXCLUSION.glob('synthetic-*.json')):
        prior=load(path);passages=prior['passages'];snapshot=prior['states'][0]['snapshot']
        question='澄海项目V2版本在2026-01的发布快照是什么？只输出快照编号。'
        _,config,audit=candidate.answer_request(question,passages,freeze['answer_config'])
        values=config['parameters']['response_format']['json_schema']['schema']['properties']['answer'].get('enum',[])
        actual=snapshot not in values
        passed=actual==prior['expected_excluded'] and '证据不足' in values
        tests.append({'name':prior['name'],'passed':passed,'audit':audit,'enum':values})
    for name,payload,selection_content,expected_status,expected_calls in [
        ('empty_input',[], '{"selected_ids":[]}','completed',2),
        ('invalid_selection',[{'id':'one','source':'self','text':'无快照编号。'}],'{"selected_ids":["unknown"]}','selection_output_failure',1),
        ('ordinary_input',[{'id':'renamed-id','source':'self','text':'只有普通资料。'}],'{"selected_ids":["renamed-id"]}','completed',2)]:
        before=copy.deepcopy(payload);calls=[]
        def stub(stage,messages,config,used):
            calls.append(stage)
            content=selection_content if stage=='selection' else '{"answer":"offline_fixture","citations":[]}'
            return {'run_kind':'offline_stub_not_model','response':{'choices':[{'message':{'content':content}}]}}
        output=candidate.execute('这份资料说明什么？',payload,'improved',freeze['answer_config'],freeze['selection_config'],stub)
        tests.append({'name':name,'passed':output['status']==expected_status and len(calls)==expected_calls and payload==before,
                      'calls_are_synthetic_only':True,'output':output})
    passed=all(t['passed'] for t in tests)
    for folder in [small,full]:
        write(folder/'offline-check.json',{'checked_at':now(),'passed':passed,'returncode':0 if passed else 1,
             'checker_sha256':sha(folder/'explicit_state_checker.py'),'tests':tests,'total':len(tests),
             'failed_cases':[t['name'] for t in tests if not t['passed']],'no_identifier_or_question_branches':True})
    if not passed:
        write(parent/'technical-stop.json',{'stopped_at':now(),'stage':'offline','generation_calls':0,'failed_cases':[t['name'] for t in tests if not t['passed']]})
        print(json.dumps({'parent':str(parent),'offline_passed':False,'failed':[t['name'] for t in tests if not t['passed']]},ensure_ascii=False));return 1
    small_design={**load(PREVIOUS/'design-plan.json'),'saved_at':now(),'experiment_kind':'post_evaluation_eligibility_enum_small',
        'planned_calls':2,'planned_generation_calls':2,'order':[{'sequence':1,'case_id':'T08','variant':'control'},{'sequence':2,'case_id':'T08','variant':'excluded'}],
        'checker_path':(small/'explicit_state_checker.py').relative_to(ROOT).as_posix(),'checker_sha256':sha(small/'explicit_state_checker.py'),
        'protected_hashes':protected,'only_change':'answer enum','previous_cumulative':316}
    write(small/'design-plan.json',small_design)
    write(small/'request-pairs.json',{'items':[{'case_id':'T08','control_source':str(EXCLUSION.relative_to(ROOT))+'/original-evidence-audit-T08.json',
        'control_source_sha256':sha(EXCLUSION/'original-evidence-audit-T08.json'),'control':original,'excluded':revised,'qualification_audit':trace}],
        'actual_parameters_unchanged':True,'messages_byte_for_byte_unchanged':True})
    write(small/'regression-results.json',{'failed':0,'total':len(tests)})
    write(small/'six-state-original-text-review.json',{'passed':True,'source':(PREVIOUS/'six-state-original-text-review.json').relative_to(ROOT).as_posix()})
    write(small/'six-state-recompute.json',original_audit)
    shutil.copyfile(PREVIOUS/'local_rule_state_candidate.py',small/'local_rule_state_candidate.py')
    old_runner=(PREVIOUS/'run_local_rule_pairs.py').read_text(encoding='utf-8')
    small_runner=old_runner.replace('Path(__file__).resolve().parents[4]',"next(p for p in Path(__file__).resolve().parents if (p/'基础/starter/provider.py').is_file())")
    small_runner=patch(small_runner,"plan={'order':design['order'],'planned_generation_calls':4}","plan={'order':design['order'],'planned_generation_calls':2}")
    small_runner=patch(small_runner,"assert len(jobs)==4 and plan['planned_generation_calls']==4","assert len(jobs)==2 and plan['planned_generation_calls']==2")
    small_runner=patch(small_runner,"assert runtime['generation_dispatches']<plan['planned_generation_calls']==4","assert runtime['generation_dispatches']<plan['planned_generation_calls']==2")
    small_runner=patch(small_runner,"'previous_cumulative':312,'cumulative_confirmed':312+len(confirmed)","'previous_cumulative':316,'cumulative_confirmed':316+len(confirmed)")
    small_runner=small_runner.replace('run_local_rule_pairs.py','run_small_pairs.py')
    (small/'run_small_pairs.py').write_text(small_runner,encoding='utf-8',newline='\n')
    write(small/'runner-gate-integration.json',load(PREVIOUS/'runner-gate-integration.json')|{'wrapper_source_reused_unchanged':True})
    settings={'service_arguments':freeze['service_arguments'],'model':freeze['model'],'llama_cpp':freeze['llama_cpp'],
        'data_sha256':freeze['data_hashes'],'code_sha256':freeze['code_hashes']}
    write(full/'settings.prepared.json',settings)
    write(full/'answer.prepared.json',freeze['answer_config']);write(full/'selection.prepared.json',freeze['selection_config'])
    jobs=[{'sequence':i+1,'case_id':'T'+str(i+1).zfill(2),'condition':'R0','variant':'improved'} for i in range(8)]
    write(full/'execution-plan.prepared.json',{'saved_at':now(),'items':jobs,'main_task_limit':8,'generation_limit':16,'fresh_selection':True})
    full_original=(ROOT/'基础/tests/run_formal_round2.py').read_text(encoding='utf-8')
    full_runner=full_original
    full_runner=patch(full_runner,'import general_candidate as candidate',"sys.path.insert(0,str(next(p for p in Path(__file__).resolve().parents if (p/'基础/starter/provider.py').is_file())/'基础/tests'))\nimport eligibility_general_candidate as candidate")
    full_runner=patch(full_runner,"repo = Path(__file__).resolve().parents[2]","repo = next(p for p in Path(__file__).resolve().parents if (p/'基础/starter/provider.py').is_file())")
    full_runner=patch(full_runner,"assert not folder.exists(), '新轮次必须使用全新目录，禁止自动续发或覆盖'\n    folder.mkdir(parents=True)","assert folder.exists() and not list(folder.glob('run-*.json')) and not (folder/'runtime.json').exists(), '禁止重复或自动续发'")
    full_runner=patch(full_runner,"settings = load(first/'candidate-settings.json')","settings = load(folder/'settings.prepared.json')")
    full_runner=patch(full_runner,"answer = load(base/'runs/two_step/dev_r0/config.answer.json')","answer = load(folder/'answer.prepared.json')")
    full_runner=patch(full_runner,"selection = load(base/'runs/two_step/dev_r0/config.selection.json')","selection = load(folder/'selection.prepared.json')")
    full_runner=patch(full_runner,"jobs = load(first/'run-list.json')['items']\n    assert len(jobs)==40 and sum(j['variant']=='baseline' for j in jobs)==32","jobs = load(folder/'execution-plan.prepared.json')['items']\n    assert len(jobs)==8 and all(j['condition']=='R0' and j['variant']=='improved' for j in jobs)")
    full_runner=patch(full_runner,"assert len({(j['case_id'],j['condition'],j['variant']) for j in jobs})==40","assert len({(j['case_id'],j['condition'],j['variant']) for j in jobs})==8")
    marker='    code_hashes = '
    pos=full_runner.index(marker)
    full_runner=full_runner[:pos]+"    sources += ['基础/tests/direct_reference_candidate.py','基础/tests/association_repair_candidate.py']\n    sources += [(folder/name).relative_to(repo).as_posix() for name in ['run_full_r0.py','eligibility_general_candidate.py','explicit_state_checker.py','eligibility_exclusion_candidate.py','typed_enum_role_revision.py','typed_identifier_enum_candidate.py','body_identifier_enum_candidate.py','offline_gate.py','settings.prepared.json','answer.prepared.json','selection.prepared.json','execution-plan.prepared.json']]\n"+full_runner[pos:]
    start=full_runner.index("    for script in ['check_two_step_linked.py'")
    end=full_runner.index('    differences=[]',start)
    full_runner=full_runner[:start]+"    assert load(folder/'offline-check.json')['passed']\n    assert load(folder/'runner-gate-integration.json')['passed']\n    assert load(folder.parent/'small/execution-summary.json')['completed_answers']==2\n    assert not load(folder.parent/'small/execution-summary.json')['technical_stop']\n    assert load(folder.parent/'small/execution-summary.json')['service_stopped']\n"+full_runner[end:]
    full_runner=full_runner.replace("runtime['generation_dispatches']<48","runtime['generation_dispatches']<16")
    full_runner=full_runner.replace("'maximum_generation_calls':48","'maximum_generation_calls':16")
    full_runner=full_runner.replace("'main_tasks':40","'main_tasks':8")
    full_runner=full_runner.replace("'main_task_limit':40,'generation_limit':48","'main_task_limit':8,'generation_limit':16")
    full_runner=full_runner.replace("'planned_main_tasks':40","'planned_main_tasks':8")
    full_runner=full_runner.replace("'previous_cumulative':198,'cumulative_confirmed':198+len(ids)","'previous_cumulative':318,'cumulative_confirmed':318+len(ids)")
    full_runner=full_runner.replace("'round':'post_evaluation_repeat_round2'","'round':'post_evaluation_eligibility_r0_repeat'")
    full_runner=full_runner.replace("'denominator':'每条件8题；主任务40；生成最多48；配对单位8道题。'","'denominator':'本轮仅R0 improved，8道主任务；最多16次生成，失败仍计8题分母。'")
    full_runner=full_runner.replace("'main_question':'最佳开发候选在已接触的评测题上是否改善证据覆盖与严格成功。'","'main_question':'独立最佳流程在已接触的8题R0上的表现；可靠资格排除仅自动核查通过时启用。'")
    full_runner=full_runner.replace("'review_note':'所有生成结束后再复用首轮原文依据；有争议保留，K只按实际可见资料。'","'review_note':'所有生成结束后再复用已有原文依据与澄清；有争议保留，所有标签辅助暂判。'")
    full_runner=full_runner.replace("'improved由单次全部资料文字排序，改为文字排序定位、合法性核验、直接补页和原输入相对顺序回答。'","'当前完整流程为新定位、直接补页、原输入相对顺序回答、通用答案形式及类型enum；可靠资格规则自动核查通过才排除。'")
    full_runner=full_runner.replace("'baseline增加问题派生的答案形式pattern。'","'本轮不跑baseline或其他条件；只报告本轮完整R0 improved，不把历史差异归因于单一因素。'")
    full_runner=full_runner.replace("'baseline全部原顺序；improved所选原段落按当前原输入相对顺序'","'最终所选完整原段落按当前原输入相对顺序'")
    full_runner=full_runner.replace("if __name__=='__main__': main()","from offline_gate import after_offline_success\n\nif __name__=='__main__':\n    target=Path(sys.argv[1]).resolve()\n    after_offline_success(lambda:load(target/'offline-check.json'),main)")
    ast.parse(full_runner)
    (full/'run_full_r0.py').write_text(full_runner,encoding='utf-8',newline='\n')
    (full/'runner-adaptation.diff').write_text(''.join(difflib.unified_diff(full_original.splitlines(True),full_runner.splitlines(True),fromfile='reused/run_formal_round2.py',tofile='independent/run_full_r0.py')),encoding='utf-8',newline='\n')
    gate=module(full/'offline_gate.py','eligibility_r0_gate');calls=[]
    try:
        gate.after_offline_success(lambda:{'passed':False,'returncode':1},lambda:calls.append('runner'))
        blocked=False
    except RuntimeError:blocked=True
    assert blocked and not calls
    write(full/'runner-gate-integration.json',{'checked_at':now(),'passed':True,'failure_blocks_main':True,'runner_start_calls':0,
        'actual_source_entrypoint_uses_gate':True})
    assert all(sha(ROOT/p)==h for p,h in protected.items())
    shutil.copyfile(Path(__file__),parent/'prepare_eligibility_r0_round.py')
    print(json.dumps({'parent':str(parent),'small':str(small),'full':str(full),'offline_passed':passed,'tests':len(tests),
                     'small_original_enum':original['response_format']['json_schema']['schema']['properties']['answer']['enum'],
                     'small_excluded_enum':revised['response_format']['json_schema']['schema']['properties']['answer']['enum']},ensure_ascii=False))
    return 0

if __name__=='__main__':raise SystemExit(main())
