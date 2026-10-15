"""修复独立状态检查器并接回已保存的4项计划；只做离线准备。"""
import ast
import copy
import difflib
import hashlib
import importlib.util
import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
OLD = ROOT/'基础/runs/local_rule_state_pairs/20261014-224810'
PREVIOUS_CHECK = ROOT/'基础/runs/explicit_state_checker_revision/20261014-190839'
now = lambda: datetime.now().astimezone().isoformat()
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.write('\n')


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def replace_once(text, old, new):
    assert text.count(old) == 1, '补丁匹配必须唯一：'+old[:80]
    return text.replace(old, new, 1)


def main():
    folder = ROOT/'基础/runs/local_rule_state_pairs'/datetime.now().strftime('%Y%m%d-%H%M%S')
    folder.mkdir(parents=True, exist_ok=False)
    snapshots = folder/'code-snapshot'
    snapshots.mkdir()
    original = PREVIOUS_CHECK/'explicit_state_checker.py'
    prior_plan = load(OLD/'design-plan.json')
    assert load(OLD/'execution-summary.json')['generation_dispatches'] == 0
    preserved_paths = list(OLD.rglob('*')) + list(PREVIOUS_CHECK.rglob('*'))
    preserved_paths += [ROOT/p for p in ['report.md', 'README.md', '基础/开发记录.md', '基础/starter/student.py', '基础/starter/provider.py']]
    protected = {p.relative_to(ROOT).as_posix(): sha(p) for p in preserved_paths if p.is_file()}
    write(folder/'repair-plan.json', {'saved_at': now(), 'previous_plan': OLD.relative_to(ROOT).as_posix()+'/design-plan.json',
          'old_checker_sha256': sha(original), 'old_generation_calls': 0,
          'authorized_scope': '区分通过检查数量和缺陷数量，保留局部、部分和未知限制；通过后续跑原定4项，顺序与设置不变。',
          'prediction': '三项检查通过可识别为局部明示通过；部分通过、未全部通过、零项通过及数量归属不明不变为全部合格。',
          'stop_rule': '全部离线及原文检查通过后才可启动运行器；失败保持阻断，不生成。',
          'protected_hashes': protected})
    text = original.read_text(encoding='utf-8')
    revised = replace_once(text, 'AFTER_ITEMS =', "PASS_COUNT = re.compile(r'(?<![0-9.＋+\\-负])(?P<n>'+NUMBER+r')\\s*项\\s*(?:检查)?\\s*$')\nPASS_LIMIT = re.compile(r'部分|未全部|未全|不全|尚未全部|其中|项中')\nAFTER_ITEMS =")
    revised = replace_once(revised, 'before = BEFORE_COUNT.search(prefix)', "before = (PASS_COUNT if token == '通过' else BEFORE_COUNT).search(prefix)")
    revised = replace_once(revised, "'ownership': 'current_check_item',", "'ownership': 'current_check_item',\n                                   'quantity_kind': 'passed_check_count' if token == '通过' else 'defect_count',")
    revised = replace_once(revised, 'elif len(quantities) > 1 or (quantity and value is None) or malformed_quantity or unowned_prefix_quantity:', "elif token == '通过' and PASS_LIMIT.search(phrase):\n            reason = 'partial_or_not_all_pass_not_generalized'\n        elif len(quantities) > 1 or (quantity and value is None) or malformed_quantity or unowned_prefix_quantity:")
    revised = replace_once(revised, "'quantity_text': quantity['raw'] if quantity else None, 'quantity': value,", "'quantity_text': quantity['raw'] if quantity else None, 'quantity': value,\n                       'pass_scope': 'stated_local_checks_only' if status == 'explicit_pass' else None,\n                       'overall_eligibility_not_inferred': True,")
    ast.parse(revised)
    (folder/'explicit_state_checker.py').write_text(revised, encoding='utf-8', newline='\n')
    shutil.copyfile(original, snapshots/'previous_explicit_state_checker.py')
    shutil.copyfile(OLD/'local_rule_state_candidate.py', folder/'local_rule_state_candidate.py')
    shutil.copyfile(PREVIOUS_CHECK/'offline_gate.py', folder/'offline_gate.py')
    shutil.copyfile(Path(__file__), folder/'prepare_rule_pass_fix.py')
    (folder/'repair.diff').write_text(''.join(difflib.unified_diff(text.splitlines(True), revised.splitlines(True),
          fromfile='previous/explicit_state_checker.py', tofile='repair/explicit_state_checker.py')), encoding='utf-8', newline='\n')
    mod = module(folder/'explicit_state_checker.py', 'pass_fix_checker')
    test_mod = module(PREVIOUS_CHECK/'check_revision.py', 'old_check_helpers')
    cases = [{k:r[k] for k in ['name', 'text', 'values', 'expected', 'source']} | ({'event_statuses': r['event_statuses']} if 'event_statuses' in r else {}) for r in load(PREVIOUS_CHECK/'results.json')['results']]
    assert len(cases) == 74
    new_cases = [
        ('counted_checks_pass', 'A71三项检查通过。', 'explicit_pass_only'),
        ('partial_count_pass', 'A71三项中两项通过。', 'unknown'),
        ('not_all_count_pass', 'A71三项未全部通过。', 'unknown'),
        ('zero_checks_pass', 'A71零项通过。', 'unknown'),
        ('post_pass_count_mixed', 'A71通过3项但恢复失败。', 'explicit_defect', ['explicit_pass', 'explicit_defect']),
        ('quantity_ownership_unknown', 'A71编号3的检查通过。', 'unknown'),
        ('arabic_counted_checks', 'A71有3项检查通过。', 'explicit_pass_only'),
        ('arabic_partial_checks', 'A71共3项检查，其中2项通过。', 'unknown'),
        ('partial_without_count', 'A71部分检查通过。', 'unknown'),
        ('negative_without_count', 'A71未全部通过。', 'unknown'),
        ('arabic_zero_pass', 'A71通过0项。', 'unknown'),
        ('pass_unknown_quantity', 'A71通过数量不明。', 'unknown'),
    ]
    for entry in new_cases:
        name, text, state = entry[:3]
        case = {'name': name, 'text': text, 'values': ['A71'], 'expected': [state], 'source': 'pass_count_fix'}
        if len(entry) == 4:
            case['event_statuses'] = entry[3]
        cases.append(case)
    results = []
    for i, case in enumerate(cases):
        try:
            result = test_mod.run_case(mod, case)
        except Exception as error:
            result = {**case, 'passed': False, 'error': repr(error)}
        write(folder/('regression-'+str(i+1).zfill(2)+'.json'), {'checked_at': now(), **result})
        results.append(result)
    regression_passed = all(r['passed'] for r in results)
    write(folder/'regression-results.json', {'checked_at': now(), 'total': len(results),
          'passed': sum(r['passed'] for r in results), 'failed': sum(not r['passed'] for r in results),
          'old_74_preserved': True, 'failed_cases': [r['name'] for r in results if not r['passed']], 'results': results})
    source = load(ROOT/prior_plan['source_path'])
    previous_review = load(OLD/'state-original-text-review.json')
    expected = {r['snapshot']: r for r in previous_review['items']}
    reviews, state_items = [], []
    for row in source['items']:
        states = mod.inspect_explicit_states(row['passages'], row['candidates'])
        state_items.append({'case_id': row['case_id'], 'items': states})
        for state in states:
            wanted = expected[state['snapshot']]
            reviews.append({**wanted, 'actual_state': state['observed_state'],
                            'matches_original_text': state['observed_state'] == wanted['expected_explicit_state'],
                            'event_rules': [e['rule'] for e in state['events']], 'current_events': state['events']})
    write(folder/'six-state-recompute.json', {'checked_at': now(), 'checker_sha256': sha(folder/'explicit_state_checker.py'),
          'source_path': prior_plan['source_path'], 'items': state_items, 'source_question_and_passages': source['items']})
    write(folder/'six-state-original-text-review.json', {'reviewed_at': now(), 'items': reviews,
          'passed': all(r['matches_original_text'] for r in reviews)})
    candidate = module(folder/'local_rule_state_candidate.py', 'repaired_state_candidate')
    pairs = []
    old_pairs = load(OLD/'request-pairs.json')['items']
    for old_pair in old_pairs:
        states = next(s['items'] for s in state_items if s['case_id'] == old_pair['case_id'])
        new_request = candidate.attach_rule_states(old_pair['control'], states, sha(folder/'explicit_state_checker.py'))
        pairs.append({**old_pair, 'local_rule': new_request})
    write(folder/'request-pairs.json', {'saved_at': now(), 'items': pairs, 'not_dispatched': True})
    passed = regression_passed and all(r['matches_original_text'] for r in reviews)
    gate = module(folder/'offline_gate.py', 'pass_fix_gate')
    sentinel = []
    gate_checks = []
    for bad in [{'passed': False, 'returncode': 1}, {'passed': False, 'returncode': 0}, {'passed': True, 'returncode': 1}]:
        try:
            gate.after_offline_success(lambda: bad, lambda: sentinel.append('service_start'))
            blocked = False
        except RuntimeError:
            blocked = True
        gate_checks.append({'input': bad, 'blocked': blocked})
    gate_passed = not sentinel and all(c['blocked'] for c in gate_checks)
    write(folder/'gate-check.json', {'checked_at': now(), 'passed': gate_passed, 'tests': gate_checks,
          'start_sentinel_calls': len(sentinel), 'runner_integration': 'run_local_rule_pairs.py调用同一after_offline_success后才进入包含Popen的main；文件与AST接入检查在生成前执行。'})
    passed = passed and gate_passed
    write(folder/'offline-check.json', {'checked_at': now(), 'passed': passed, 'returncode': 0 if passed else 1,
          'regression_passed': regression_passed, 'six_states_match_text': all(r['matches_original_text'] for r in reviews),
          'gate_passed': gate_passed, 'checker_sha256': sha(folder/'explicit_state_checker.py')})
    write(folder/'design-plan.json', {**prior_plan, 'saved_at': now(), 'continued_from': OLD.relative_to(ROOT).as_posix(),
          'original_plan_time_preserved_in': OLD.relative_to(ROOT).as_posix()+'/design-plan.json',
          'checker_path': (folder/'explicit_state_checker.py').relative_to(ROOT).as_posix(),
          'checker_sha256': sha(folder/'explicit_state_checker.py'), 'protected_hashes': protected})
    assert all(sha(ROOT/p) == h for p, h in protected.items())
    if not passed:
        write(folder/'technical-stop.json', {'stopped_at': now(), 'stage': 'offline_regression', 'generation_dispatches': 0,
              'failed_cases': [r['name'] for r in results if not r['passed']], 'six_states': reviews, 'runner_start_blocked': True})
    print(json.dumps({'folder': str(folder), 'offline_passed': passed, 'total': len(results),
                     'passed': sum(r['passed'] for r in results), 'failed': sum(not r['passed'] for r in results),
                     'failed_cases': [r['name'] for r in results if not r['passed']],
                     'six_states': [{k:r[k] for k in ('snapshot', 'actual_state', 'matches_original_text')} for r in reviews]}, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
