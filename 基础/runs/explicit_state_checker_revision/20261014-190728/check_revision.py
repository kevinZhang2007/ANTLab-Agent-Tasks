import copy
import difflib
import hashlib
import importlib.util
import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
OLD = ROOT / '基础/runs/explicit_state_checker/20261014-185340'
NOW = lambda: datetime.now().astimezone().isoformat()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.write('\n')


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_input(text, values, passage_id='self-id'):
    passages = [{'id': passage_id, 'source': 'self', 'text': text}]
    candidates = [{'snapshot': value, 'sources': [{'passage_id': passage_id,
                   'passage_index': 0, 'start': text.index(value), 'end': text.index(value)+len(value)}]}
                  for value in values]
    return passages, candidates


def check_positions(rows, passages):
    for row in rows:
        text = passages[row['passage_index']]['text']
        spans = [row, *row['unparsed_content']]
        for event in row['events']:
            assert text[event['trigger_start']:event['trigger_end']] == event['trigger']
            assert text[event['description_start']:event['description_end']] == event['description_quote']
            if event['negation_scope']:
                spans.extend([event['negation_scope'], *event['negation_scope']['markers']])
            for quantity in event['quantity_scope']:
                spans.extend([quantity, quantity['item_scope']])
                assert text[quantity['number_start']:quantity['number_end']] == quantity['raw']
        for span in spans:
            assert text[span['start']:span['end']] == span['quote']


def run_case(module, case):
    passages, candidates = make_input(case['text'], case['values'])
    original = copy.deepcopy((passages, candidates))
    rows = module.inspect_explicit_states(passages, candidates)
    actual = [row['observed_state'] for row in rows]
    check_positions(rows, passages)
    assert (passages, candidates) == original
    remapped = case['text']
    new_values = []
    for index, value in enumerate(case['values']):
        replacement = 'Other'+str(701+index)
        remapped = remapped.replace(value, replacement)
        new_values.append(replacement)
    new_passages, new_candidates = make_input(remapped, new_values, 'remapped-source-id')
    new_rows = module.inspect_explicit_states(new_passages, new_candidates)
    check_positions(new_rows, new_passages)
    signature = lambda output: [(r['observed_state'], [(e['status'], e['expression_class'], e['trigger'], e['quantity']) for e in r['events']]) for r in output]
    remap_ok = signature(rows) == signature(new_rows)
    passed = actual == case['expected'] and remap_ok
    if case.get('event_statuses'):
        passed = passed and [e['status'] for e in rows[0]['events']] == case['event_statuses']
    return {**case, 'actual': actual, 'rows': rows, 'remapped_rows': new_rows,
            'input_unchanged': True, 'positions_match_original': True,
            'remapping_passed': remap_ok, 'passed': passed}


def main():
    destination = ROOT / '基础/runs/explicit_state_checker_revision' / datetime.now().strftime('%Y%m%d-%H%M%S')
    destination.mkdir(parents=True, exist_ok=False)
    protected_paths = list(OLD.rglob('*')) + [ROOT/'report.md', ROOT/'README.md', ROOT/'基础/开发记录.md', ROOT/'基础/starter/student.py']
    before = {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p) for p in protected_paths if p.is_file()}
    base = read(OLD/'synthetic-check.json')['tests']
    boundary = read(OLD/'additional-negation-zero-boundary-audit.json')['tests']
    cases = [{'name': t['name'], 'text': t['text'], 'values': [r['snapshot'] for r in t['rows']],
              'expected': t['expected'], 'source': 'original_24'} for t in base]
    cases += [{'name': 'old_boundary_'+str(i+1), 'text': t['text'], 'values': [t['result']['snapshot']],
               'expected': ['explicit_absence_only'], 'previous_expectation': t['expected'],
               'previous_passed': t['passed'], 'source': 'original_extra_6'} for i, t in enumerate(boundary)]
    variants = [
        ('front_negation_with_subject', 'Z91并非解析失败。', 'explicit_absence_only'),
        ('post_negative_with_subject', 'Z91恢复失败不存在。', 'explicit_absence_only'),
        ('post_negative_context', 'Z91解析失败情况未发生。', 'explicit_absence_only'),
        ('front_absence_with_subject', 'Z91不存在定位偏移。', 'explicit_absence_only'),
        ('arabic_post_count', 'Z91恢复失败2项。', 'explicit_defect'),
        ('chinese_post_zero', 'Z91恢复失败次数为零。', 'explicit_absence_only'),
        ('ideographic_post_zero', 'Z91缺失数量为〇。', 'explicit_absence_only'),
        ('chinese_pre_zero', 'Z91有零项偏移。', 'explicit_absence_only'),
        ('colon_quantity', 'Z91定位偏移：0。', 'explicit_absence_only'),
        ('equal_quantity', 'Z91定位偏移=0。', 'explicit_absence_only'),
        ('spaces_quantity', 'Z91恢复失败次数 为 0 次。', 'explicit_absence_only'),
        ('bare_count', 'Z91失败0项。', 'explicit_absence_only'),
        ('comma_mixed_negation', 'Z91并非解析失败，但恢复失败。', 'explicit_defect', ['explicit_absence', 'explicit_defect']),
        ('comma_mixed_zero', 'Z91定位偏移为0，恢复失败2项。', 'explicit_defect', ['explicit_absence', 'explicit_defect']),
        ('contrast_no_comma', 'Z91并非解析失败但恢复失败。', 'explicit_defect', ['explicit_absence', 'explicit_defect']),
        ('ascii_comma_mixed', 'Z91恢复失败不存在,定位4项偏移。', 'explicit_defect', ['explicit_absence', 'explicit_defect']),
        ('zero_and_true_missing', 'Z91定位偏移为零、缺少坐标。', 'explicit_defect', ['explicit_absence', 'explicit_defect']),
        ('pass_and_fail', 'Z91问答通过，但恢复失败。', 'explicit_defect', ['explicit_pass', 'explicit_defect']),
        ('separate_uncertainty', 'Z91无法确认解析是否失败，但恢复失败。', 'explicit_defect', ['unknown', 'explicit_defect']),
        ('zero_multiple_items', 'Z91定位偏移为0，恢复失败次数为零。', 'explicit_absence_only', ['explicit_absence', 'explicit_absence']),
        ('mixed_negated_count', 'Z91不是0项偏移，但恢复失败2项。', 'explicit_defect', ['unknown', 'explicit_defect']),
        ('no_count_offset', 'Z91定位偏移。', 'unknown'),
        ('unclosed_unknown', 'Z91未关闭问题数量不明。', 'unknown'),
        ('approximate_zero', 'Z91恢复失败次数约为0。', 'unknown'),
        ('unsupported_unit', 'Z91恢复失败3秒。', 'unknown'),
        ('bare_unknown_number', 'Z91恢复失败2。', 'unknown'),
        ('fraction_count', 'Z91恢复失败数量为0.5项。', 'unknown'),
        ('negative_count', 'Z91恢复负2项失败。', 'unknown'),
        ('percentage_not_count', 'Z91失败数量为1%。', 'unknown'),
        ('metric_zero', 'Z91失败率为0。', 'unknown'),
        ('nested_negation', 'Z91并非没有失败。', 'unknown'),
        ('negated_positive_count', 'Z91没有2项偏移。', 'unknown'),
        ('range_count', 'Z91失败数量为0-2项。', 'unknown'),
        ('multi_predicate_no_boundary', 'Z91没有解析失败和定位偏移。', 'unknown'),
        ('chinese_positive', 'Z91恢复失败次数为三。', 'explicit_defect'),
        ('post_zero_unclosed', 'Z91未关闭问题数量为零。', 'explicit_absence_only'),
    ]
    for item in variants:
        name, text, state = item[:3]
        case = {'name': name, 'text': text, 'values': ['Z91'], 'expected': [state], 'source': 'new_variant'}
        if len(item) == 4:
            case['event_statuses'] = item[3]
        cases.append(case)
    save(destination/'design-plan.json', {'saved_at': NOW(), 'status': 'offline_only',
         'original_implementation': str(OLD.relative_to(ROOT)).replace('\\', '/'),
         'protected_hashes': before, 'classes': ['positive_presence', 'explicit_negation', 'explicit_zero_quantity', 'unparsed'],
         'mechanism': '先按标点及并列/转折边界分检查项，再解析前后否定及前后计数。作用范围限于本项。复合谓词、精确数量否定、条件或数量无法可靠归属时unknown。',
         'limits': ['有限语法，不是通用语义判断', '多个候选同句仍unknown', '不推断整体资格、不选择编号', '局部通过或无缺陷不代表合格'],
         'samples': cases, 'stop_rule': '任何检查失败，ready-to-run=false；禁止进入运行器。本轮无服务或生成。',
         'generation_calls': 0})
    shutil.copyfile(OLD/'explicit_state_checker.py', destination/'original-state-checker.py')
    implementation = Path(__file__).with_name('explicit_state_revision.py')
    if not implementation.exists():
        implementation = Path(__file__).with_name('explicit_state_checker.py')
    shutil.copyfile(implementation, destination/'explicit_state_checker.py')
    shutil.copyfile(Path(__file__), destination/'check_revision.py')
    shutil.copyfile(OLD/'offline_gate.py', destination/'offline_gate.py')
    diff = ''.join(difflib.unified_diff((OLD/'explicit_state_checker.py').read_text(encoding='utf-8').splitlines(True),
                    (destination/'explicit_state_checker.py').read_text(encoding='utf-8').splitlines(True),
                    fromfile='original/explicit_state_checker.py', tofile='revision/explicit_state_checker.py'))
    (destination/'code.diff').write_text(diff, encoding='utf-8', newline='\n')
    save(destination/'code-hashes.json', {'saved_at': NOW(), 'original_sha256': digest(OLD/'explicit_state_checker.py'),
         'revision_sha256': digest(destination/'explicit_state_checker.py'), 'diff_file': 'code.diff'})
    module = load_module(destination/'explicit_state_checker.py', 'state_revision')
    results = []
    for index, case in enumerate(cases):
        try:
            result = run_case(module, case)
        except Exception as error:
            result = {**case, 'passed': False, 'error': repr(error)}
        save(destination/('case-'+str(index+1).zfill(2)+'.json'), {'checked_at': NOW(), **result})
        results.append(result)
    gate = load_module(destination/'offline_gate.py', 'offline_gate')
    called = []
    gate_results = []
    for bad in [{'returncode': 1, 'passed': False}, {'returncode': 0, 'passed': False}, {'returncode': 1, 'passed': True}, {}, []]:
        try:
            gate.after_offline_success(lambda: bad, lambda: called.append('unexpected'))
            blocked = False
        except RuntimeError:
            blocked = True
        gate_results.append({'input': bad, 'blocked': blocked})
    def raises():
        raise ValueError('synthetic offline check exception')
    try:
        gate.after_offline_success(raises, lambda: called.append('unexpected'))
        exception_blocked = False
    except ValueError:
        exception_blocked = True
    gate_passed = all(g['blocked'] for g in gate_results) and exception_blocked and not called
    save(destination/'gate-check.json', {'checked_at': NOW(), 'cases': gate_results,
         'exception_blocked': exception_blocked, 'next_step_calls': len(called), 'passed': gate_passed,
         'note': '仅调用内存哨兵；没有启动运行器或任何模型进程。'})
    passed = sum(r['passed'] for r in results)
    preserved = all(digest(ROOT/p) == h for p, h in before.items())
    ready = passed == len(cases) and gate_passed and preserved
    save(destination/'results.json', {'checked_at': NOW(), 'total': len(cases), 'passed': passed,
         'failed': len(cases)-passed, 'original_30': {'total': 30, 'passed': sum(r['passed'] for r in results[:30])},
         'new_variants': {'total': len(cases)-30, 'passed': sum(r['passed'] for r in results[30:])},
         'failed_cases': [r['name'] for r in results if not r['passed']],
         'remapping_checks': {'total': len(cases), 'passed': sum(r.get('remapping_passed', False) for r in results)},
         'old_files_and_protected_documents_unchanged': preserved, 'gate_passed': gate_passed,
         'generation_calls': 0, 'results': results})
    save(destination/'ready-to-run.json', {'checked_at': NOW(), 'passed': ready, 'returncode': 0 if ready else 1,
         'runner_start_allowed': False, 'reason': '本轮仅离线；失败持续阻断后续运行。即使离线通过也未授权启动。',
         'generation_calls': 0})
    print(json.dumps({'directory': str(destination), 'total': len(cases), 'passed': passed,
                      'failed': len(cases)-passed, 'failed_cases': [r['name'] for r in results if not r['passed']],
                      'protected_unchanged': preserved, 'gate_passed': gate_passed}, ensure_ascii=False))
    return 0 if ready else 1


if __name__ == '__main__':
    raise SystemExit(main())
