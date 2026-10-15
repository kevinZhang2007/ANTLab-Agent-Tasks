import ast
import copy
import difflib
import importlib.util
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
OLD=ROOT/'基础/runs/eligibility_r0_repeat/20261014-231852/full'
EXCLUSION=ROOT/'基础/runs/eligibility_exclusion/20261014-230758'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
now=lambda:datetime.now().astimezone().isoformat()

def write(p,value):
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def replace(text,old,new):
    assert text.count(old)==1,old[:80]
    return text.replace(old,new,1)

def main():
    folder=ROOT/'基础/runs/scope_first_pairs'/datetime.now().strftime('%Y%m%d-%H%M%S')
    folder.mkdir(parents=True,exist_ok=False)
    write(folder/'repair-plan.json',{'saved_at':now(),'old_implementation':(OLD/'eligibility_general_candidate.py').relative_to(ROOT).as_posix(),
        'previous_offline_failure_preserved':'基础/runs/scope_first_pairs/20261014-233749/technical-stop.json',
        'additional_offline_repair':'在项目/版本语境识别任意英数版本标签，修正继承提取器仅R版本造成的漏识别；原失败样例与预期不改。',
        'mechanism':'显式范围冲突仅保留审计，不参与目标竞争；未知范围仍阻断排除。目标范围重复只有单一可靠业务声明与全文相同的资料复本可合并。其余保守保留。',
        'identity_limit':'仅文本声明身份，不声称外部物理快照唯一；非全文相同的重复可能仍unknown。',
        'stops':'离线失败门禁阻断启动；技术失败停止，质量错误不重试。',
        'order':['old_fresh_selection_and_answer','new_fresh_selection_and_answer'],'generation_limit':4,
        'kind':'post_evaluation_fault_repair_not_independent_evaluation','previous_cumulative':334})
    for name in ['explicit_state_checker.py','eligibility_exclusion_candidate.py','typed_enum_role_revision.py','typed_identifier_enum_candidate.py','body_identifier_enum_candidate.py','offline_gate.py']:
        shutil.copyfile(OLD/name,folder/name)
    shutil.copyfile(OLD/'eligibility_general_candidate.py',folder/'old_eligibility_general_candidate.py')
    shutil.copyfile(Path(__file__).with_name('scope_first_occurrences.py'),folder/'scope_first_occurrences.py')
    source=(OLD/'eligibility_general_candidate.py').read_text(encoding='utf-8')
    revised=replace(source,'import eligibility_exclusion_candidate as exclusion','import eligibility_exclusion_candidate as exclusion\nfrom scope_first_occurrences import audit_occurrences')
    revised=replace(revised,'    candidates = []\n    occurrences = {}',"    original_universe = copy.deepcopy(full)\n    full, occurrence_audit, scope_audit = audit_occurrences(question, full, schema['properties']['answer']['enum'], {p['id'] for p in passages})\n    record.update(scope_audit=scope_audit, occurrence_audit=occurrence_audit, original_universe=original_universe)\n    candidates = []\n    occurrences = {}")
    revised=replace(revised,"        if len(occurrences[value]) != 1:\n            skipped.append({'candidate': value, 'reason': 'multiple_occurrences_or_scopes_unknown'})\n            continue", "        identity_audit = occurrence_audit[value]\n        if not identity_audit['eligible_for_exclusion_check']:\n            skipped.append({'candidate': value, 'reason': identity_audit['reason'], 'scope_and_identity_audit': identity_audit})\n            continue")
    ast.parse(revised)
    (folder/'eligibility_general_candidate.py').write_text(revised,encoding='utf-8',newline='\n')
    (folder/'repair.diff').write_text(''.join(difflib.unified_diff(source.splitlines(True),revised.splitlines(True),fromfile='old/eligibility_general_candidate.py',tofile='new/eligibility_general_candidate.py')),encoding='utf-8',newline='\n')
    sys.path.insert(0,str(ROOT/'基础/tests'));sys.path.insert(0,str(folder))
    candidate=module(folder/'eligibility_general_candidate.py','scope_first_candidate')
    old=module(folder/'old_eligibility_general_candidate.py','scope_old_candidate')
    config=load(OLD/'answer.prepared.json')
    tests=[]
    # 复用此前10项原始自造样例，不删除任何失败边界。
    for p in sorted(EXCLUSION.glob('synthetic-*.json')):
        case=load(p);snapshot=case['states'][0]['snapshot']
        _,conf,audit=candidate.answer_request('澄海项目V2版本在2026-01的发布快照是什么？只输出快照编号。',case['passages'],config)
        actual=snapshot not in conf['parameters']['response_format']['json_schema']['schema']['properties']['answer'].get('enum',[])
        tests.append({'name':'previous_'+case['name'],'passed':actual==case['expected_excluded'],'audit':audit})
    question='澄海项目V2版本在2026-01的发布快照是什么？只输出快照编号。'
    data={'id':'main','source':'self','text':'澄海项目V2版本在2026-01的记录：复核表BX37显示Snap11区域定位2项失败；Snap12区域定位通过。'}
    rule={'id':'rule','source':'other','text':'批次BX37的复核补页：BX37的发布规则要求区域定位检查全部通过。'}
    variants=[
        ('cross_version_same_identifier',{'id':'old','source':'other','text':'澄海项目V1版本在2026-01的记录：签署快照为Snap11。'},True),
        ('identical_same_version_copy',{**data,'id':'copy','source':'different'},True),
        ('same_scope_status_conflict',{'id':'conflict','source':'other','text':'澄海项目V2版本在2026-01的记录：复核表BX37显示Snap11区域定位通过。'},False),
        ('missing_scope',{'id':'missing','source':'other','text':'复核表BX37显示Snap11区域定位2项失败。'},False),
        ('other_project',{'id':'other','source':'other','text':'远山项目V2版本在2026-01的记录：签署快照为Snap11。'},True),
        ('same_scope_different_object',{'id':'different-object','source':'other','text':'澄海项目V2版本在2026-01的记录：复核表CX48显示Snap11区域定位2项失败。'},False),
        ('same_scope_unknown_description',{'id':'unknown','source':'other','text':'澄海项目V2版本在2026-01的记录：签署快照为Snap11。'},False),
    ]
    for name,extra,expected in variants:
        universe=[extra,copy.deepcopy(data),copy.deepcopy(rule)];used=[copy.deepcopy(data),copy.deepcopy(rule)]
        untouched=copy.deepcopy((used,universe))
        _,conf,audit=candidate.answer_request(question,used,config,universe)
        values=conf['parameters']['response_format']['json_schema']['schema']['properties']['answer']['enum']
        actual='Snap11' not in values
        mapped=copy.deepcopy(universe)
        for i,p in enumerate(mapped):p['id']='Remap'+str(i)
        mapped_used=[copy.deepcopy(p) for p in mapped if p['text'] in {data['text'],rule['text']}]
        # 完全相同复本只选当前代表主段，保持测试输入数量一致。
        mapped_used=[mapped[-2],mapped[-1]]
        _,remap_conf,remap_audit=candidate.answer_request(question,mapped_used,config,mapped)
        remap_values=remap_conf['parameters']['response_format']['json_schema']['schema']['properties']['answer']['enum']
        tests.append({'name':name,'passed':actual==expected and values==remap_values and (used,universe)==untouched,
            'expected_exclude':expected,'actual_exclude':actual,'enum':values,'id_remapping_passed':values==remap_values,
            'audit':audit,'remapped_audit':remap_audit,'universe':universe})
    write(folder/'regression-results.json',{'checked_at':now(),'total':len(tests),'passed':sum(t['passed'] for t in tests),
         'failed':sum(not t['passed'] for t in tests),'failed_cases':[t['name'] for t in tests if not t['passed']],'tests':tests})
    passed=all(t['passed'] for t in tests)
    gate=module(folder/'offline_gate.py','scope_gate');starts=[]
    try:gate.after_offline_success(lambda:{'passed':False,'returncode':1},lambda:starts.append('model'));blocked=False
    except RuntimeError:blocked=True
    passed=passed and blocked and not starts
    write(folder/'offline-check.json',{'checked_at':now(),'passed':passed,'returncode':0 if passed else 1})
    write(folder/'runner-gate-integration.json',{'checked_at':now(),'passed':blocked and not starts,'failure_blocks_main':True,'model_start_calls':len(starts)})
    if not passed:
        write(folder/'technical-stop.json',{'stopped_at':now(),'stage':'offline_regression','generated':0,'failed':[t['name'] for t in tests if not t['passed']]})
        print(json.dumps({'folder':str(folder),'passed':False,'failed':[t['name'] for t in tests if not t['passed']]},ensure_ascii=False));return 1
    original=load(OLD/'task-08.json')
    replay=[]
    for scheme,engine in [('old',old),('new',candidate)]:
        _,conf,audit=engine.answer_request(original['question'],original['used_passages'],config,original['original_passages'])
        replay.append({'scheme':scheme,'rule_audit':audit,'enum':conf['parameters']['response_format']['json_schema']['schema']['properties']['answer']['enum']})
    write(folder/'preflight-full-universe-audit.json',{'checked_at':now(),'question':original['question'],'original_passages':original['original_passages'],'diagnostic_only_not_fresh_selection':True,'arms':replay})
    for name in ['settings.prepared.json','answer.prepared.json','selection.prepared.json']:shutil.copyfile(OLD/name,folder/name)
    jobs=[{'sequence':1,'case_id':'T08','condition':'R0','variant':'improved','scheme':'old'},
          {'sequence':2,'case_id':'T08','condition':'R0','variant':'improved','scheme':'new'}]
    write(folder/'execution-plan.prepared.json',{'saved_at':now(),'items':jobs,'generation_limit':4,'main_task_limit':2,'paired_question_count':1})
    runner=(OLD/'run_full_r0.py').read_text(encoding='utf-8')
    runner=replace(runner,'import eligibility_general_candidate as candidate','import eligibility_general_candidate as candidate\nimport old_eligibility_general_candidate as old_candidate')
    runner=replace(runner,'assert len(jobs)==8 and all', 'assert len(jobs)==2 and all')
    runner=replace(runner,"assert len({(j['case_id'],j['condition'],j['variant']) for j in jobs})==8","assert len({(j['case_id'],j['scheme']) for j in jobs})==2")
    begin=runner.index("    assert load(folder.parent/'small/execution-summary.json')")
    end=runner.index('    differences=[]',begin)
    runner=runner[:begin]+runner[end:]
    runner=runner.replace('run_full_r0.py','run_scope_first_pairs.py')
    runner=replace(runner,"'execution-plan.prepared.json']]","'execution-plan.prepared.json','old_eligibility_general_candidate.py','scope_first_occurrences.py']]")
    runner=runner.replace("runtime['generation_dispatches']<16","runtime['generation_dispatches']<4")
    runner=runner.replace("'maximum_generation_calls':16","'maximum_generation_calls':4")
    runner=runner.replace("'main_task_limit':8,'generation_limit':16","'main_task_limit':2,'generation_limit':4")
    runner=runner.replace("'planned_main_tasks':8","'planned_main_tasks':2")
    runner=runner.replace("'main_tasks':8","'main_tasks':2")
    runner=replace(runner,"'previous_cumulative':318,'cumulative_confirmed':318+len(ids)","'previous_cumulative':334,'cumulative_confirmed':334+len(ids)")
    runner=replace(runner,"save(candidate.execute(question,original,job['variant'],answer,selection,dispatch,save))","engine=old_candidate if job['scheme']=='old' else candidate\n            save(engine.execute(question,original,job['variant'],answer,selection,dispatch,save))")
    runner=replace(runner,"messages,conf,_=candidate.answer_request(case['question'],original,answer)","engine=old_candidate if job['scheme']=='old' else candidate\n            messages,conf,_=engine.answer_request(case['question'],original,answer)")
    runner=runner.replace("'denominator':'本轮仅R0 improved，8道主任务；最多16次生成，失败仍计8题分母。'","'denominator':'同一题旧/新两个完整流程，每侧一次定位+回答，最多4次生成，不是独立两题。'")
    runner=runner.replace('第二轮评测后重复评测：40个主任务、最多48次生成；不覆盖首次记录。','评测后范围顺序修复：同一题旧/新完整流程，最多4次生成。')
    ast.parse(runner)
    (folder/'run_scope_first_pairs.py').write_text(runner,encoding='utf-8',newline='\n')
    shutil.copyfile(Path(__file__),folder/'prepare_scope_first_pairs.py')
    print(json.dumps({'folder':str(folder),'passed':True,'regression_total':len(tests),'preflight_enums':[{k:r[k] for k in ['scheme','enum']} for r in replay]},ensure_ascii=False));return 0

if __name__=='__main__':raise SystemExit(main())
