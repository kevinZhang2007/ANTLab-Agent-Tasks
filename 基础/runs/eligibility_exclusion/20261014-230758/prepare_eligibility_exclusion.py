import copy
import hashlib
import importlib.util
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
PREVIOUS = ROOT/'基础/runs/local_rule_state_pairs/20261014-225350'
NOW = lambda: datetime.now().astimezone().isoformat()
SHA = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as out:
        json.dump(value, out, ensure_ascii=False, indent=2)
        out.write('\n')


def main():
    folder = ROOT/'基础/runs/eligibility_exclusion'/datetime.now().strftime('%Y%m%d-%H%M%S')
    folder.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(ROOT/'基础/tests'))
    sys.path.insert(0, str(ROOT/'基础/runs/revised_identifier_enum_pairs/20261014-174818'))
    inputs = load(PREVIOUS/'six-state-recompute.json')['source_question_and_passages']
    protected_files = [p for p in PREVIOUS.rglob('*') if p.is_file()]
    protected_files += [ROOT/p for p in ['report.md','README.md','基础/开发记录.md','基础/starter/student.py']]
    protected = {p.relative_to(ROOT).as_posix():SHA(p) for p in protected_files}
    write(folder/'design-plan.json', {'saved_at':NOW(),'kind':'post_evaluation_rule_candidate',
          'scope':'有限语法发布规则、逐字检查名或禁止状态，以及原唯一直接补页关系；不加入题号/前缀/答案分支。',
          'hypothesis':'若存在可靠逐字对应，排除明确违例候选可能改善对象选择；不保证引用或整体资格。',
          'competition':'规则指代、同义词和范围关系可能无法解析；未知仍保留。枚举缩小不证明剩余项合格。',
          'stop':'任何离线失败或须人工建立对应时，保存后停止。本轮最多4次，仅变更题前后配对。',
          'checker_path':(PREVIOUS/'explicit_state_checker.py').relative_to(ROOT).as_posix(),
          'checker_sha256':SHA(PREVIOUS/'explicit_state_checker.py'),
          'protected_hashes':protected, 'planned_max_generation':4})
    shutil.copyfile(Path(__file__).with_name('eligibility_exclusion_candidate.py'),folder/'eligibility_exclusion_candidate.py')
    shutil.copyfile(Path(__file__),folder/'prepare_eligibility_exclusion.py')
    checker = module(PREVIOUS/'explicit_state_checker.py','eligibility_state_checker')
    candidate = module(folder/'eligibility_exclusion_candidate.py','eligibility_candidate')
    from typed_enum_role_revision import constrain_revised_roles
    specs = [
        ('required_failure','区域定位2项失败','区域定位检查全部通过',True),
        ('unrelated_failure','导出2项失败','区域定位检查全部通过',False),
        ('negative','不存在区域定位失败','区域定位检查全部通过',False),
        ('zero','区域定位0项偏移','区域定位检查全部通过',False),
        ('incomplete_rule','区域定位2项失败','上述两项检查全部通过',False),
        ('scope_conflict','区域定位2项失败','区域定位检查全部通过',False),
        ('all_excluded','区域定位2项失败','区域定位检查全部通过',True),
        ('unknown_candidate','区域定位数量未说明','区域定位检查全部通过',False),
        ('pass_not_general_qualification','区域定位通过','区域定位检查全部通过',False),
        ('check_name_overlap_not_same','导出区域定位2项失败','区域定位检查全部通过',False),
    ]
    results = []
    for i,(name,description,rule,wanted) in enumerate(specs):
        text = '澄海项目V2版本在2026-01的记录：复核表BX37显示Snap11'+description+'。'
        extra_range = '远山项目V3版本在2026-02。' if name == 'scope_conflict' else ''
        passages = [{'id':'data','source':'self','text':text},
                    {'id':'rule','source':'different-directory','text':extra_range+'批次BX37的复核补页：BX37的发布规则要求'+rule+'。'}]
        start=text.index('Snap11')
        candidates=[{'snapshot':'Snap11','sources':[{'passage_id':'data','passage_index':0,'start':start,'end':start+6}]}]
        states=checker.inspect_explicit_states(passages,candidates)
        audit=candidate.constrain_eligibility('澄海项目V2版本的发布快照是什么？只输出快照编号。',passages,['Snap11','证据不足'],states)
        actual=audit['decisions'][0]['excluded']
        passed=actual==wanted and '证据不足' in audit['answer_enum']
        if name=='all_excluded':passed=passed and audit['answer_enum']==['证据不足']
        result={'name':name,'passages':passages,'states':states,'expected_excluded':wanted,'actual_excluded':actual,'passed':passed,'audit':audit}
        write(folder/('synthetic-'+str(i+1).zfill(2)+'.json'), {'checked_at':NOW(),**result})
        results.append(result)
    offline_passed=all(r['passed'] for r in results)
    write(folder/'offline-check.json',{'checked_at':NOW(),'passed':offline_passed,'returncode':0 if offline_passed else 1,
          'total':len(results),'passed_count':sum(r['passed'] for r in results),'failed_cases':[r['name'] for r in results if not r['passed']]})
    pairs=load(PREVIOUS/'request-pairs.json')['items']
    audits=[]
    for row in inputs:
        original=next(p['control'] for p in pairs if p['case_id']==row['case_id'])
        schema=original['response_format']['json_schema']['schema']
        actual_schema, type_audit=constrain_revised_roles(row['question'],row['passages'],schema)
        assert actual_schema['properties']['answer']['enum']==schema['properties']['answer']['enum']
        states=checker.inspect_explicit_states(row['passages'],row['candidates'])
        audit=candidate.constrain_eligibility(row['question'],row['passages'],schema['properties']['answer']['enum'],states)
        revised=copy.deepcopy(original)
        revised['response_format']['json_schema']['schema']['properties']['answer']['enum']=audit['answer_enum']
        removed=copy.deepcopy(revised)
        removed['response_format']['json_schema']['schema']['properties']['answer']['enum']=schema['properties']['answer']['enum']
        assert removed==original
        item={'case_id':row['case_id'],'question':row['question'],'passages':row['passages'],'states':states,
              'type_audit':type_audit, 'audit':audit,'original_request':original,'proposed_request':revised,
              'only_answer_enum_changed':True,'not_dispatched':True}
        write(folder/('original-evidence-audit-'+row['case_id']+'.json'),{'checked_at':NOW(),**item})
        audits.append(item)
    needs_manual=any(a['audit']['needs_manual_correspondence'] for a in audits)
    gate=module(PREVIOUS/'offline_gate.py','exclusion_gate')
    started=[]
    try:
        gate.after_offline_success(lambda:{'passed':False,'returncode':1},lambda:started.append('runner'))
        blocked=False
    except RuntimeError:
        blocked=True
    write(folder/'gate-check.json',{'checked_at':NOW(),'passed':blocked and not started,'runner_start_calls':len(started)})
    if not offline_passed or needs_manual:
        write(folder/'stop.json', {'stopped_at':NOW(),'stage':'offline_rule_correspondence',
              'reason':'原发布规则存在未解析的检查指代，自动对应不完整；不写入人工同义关系。' if needs_manual else '自造离线检查失败',
              'offline_passed':offline_passed,'manual_correspondence_required':needs_manual,
              'generation_calls':0,'service_started':False,'no_automatic_repair_or_labels':True})
    assert all(SHA(ROOT/p)==h for p,h in protected.items())
    write(folder/'summary.json',{'saved_at':NOW(),'generation_calls':0,'previous_cumulative':316,
          'service_started':False,'protected_unchanged':True,'offline_passed':offline_passed,
          'stopped_for_unreliable_correspondence':needs_manual,
          'items':[{'case_id':a['case_id'],'remaining':a['audit']['answer_enum'],
                   'excluded':[d['candidate'] for d in a['audit']['decisions'] if d['excluded']],
                   'changed':a['audit']['changed']} for a in audits]})
    print(json.dumps({'folder':str(folder),'offline_passed':offline_passed,'failed_cases':[r['name'] for r in results if not r['passed']],
                     'needs_manual_stop':needs_manual,'audits':[{'case_id':a['case_id'],'remaining':a['audit']['answer_enum'],'excluded':[d['candidate'] for d in a['audit']['decisions'] if d['excluded']]} for a in audits]},ensure_ascii=False))
    return 1 if not offline_passed or needs_manual else 0


if __name__=='__main__':
    raise SystemExit(main())
