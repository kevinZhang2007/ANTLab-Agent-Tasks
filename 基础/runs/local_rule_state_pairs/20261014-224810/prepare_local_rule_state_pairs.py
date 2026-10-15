import copy
import hashlib
import importlib.util
import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
CHECKER = ROOT/'基础/runs/explicit_state_checker_revision/20261014-190839/explicit_state_checker.py'
SOURCE = ROOT/'基础/runs/snapshot_qualification_diagnostic/20261014-175307/source-inputs.json'
OLD_PAIRS = ROOT/'基础/runs/revised_identifier_enum_pairs/20261014-174818'
TIME = lambda: datetime.now().astimezone().isoformat()
SHA = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.write('\n')


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    folder = ROOT/'基础/runs/local_rule_state_pairs'/datetime.now().strftime('%Y%m%d-%H%M%S')
    folder.mkdir(parents=True, exist_ok=False)
    (folder/'code-snapshot').mkdir(exist_ok=False)
    sources = load(SOURCE)
    service_reference = load(ROOT/'基础/runs/formal/round2-20261014-133000/freeze.json')
    assert service_reference['service_arguments'][service_reference['service_arguments'].index('--reasoning')+1] == 'off'
    histories = [load(p) | {'record_path': p.relative_to(ROOT).as_posix()} for p in OLD_PAIRS.glob('run-*.json')]
    controls = {r['case_id']: r for r in histories if r['variant'] == 'new'}
    assert set(controls) == {'T01', 'T08'}
    protected_paths = [ROOT/'report.md', ROOT/'README.md', ROOT/'基础/开发记录.md', ROOT/'基础/starter/student.py']
    protected_paths += list(CHECKER.parent.rglob('*')) + list(OLD_PAIRS.rglob('*'))
    protected = {p.relative_to(ROOT).as_posix(): SHA(p) for p in protected_paths if p.is_file()}
    plan = {'saved_at': TIME(), 'experiment_kind': 'post_evaluation_local_rule_state_pairs',
            'historical_selection_replay': True, 'no_new_selection': True,
            'hypothesis': '明确标注的局部规则状态可能帮助模型避免选取明示缺陷候选，但不证明整体资格。',
            'competing_explanation': '模型仍可能忽略规则状态、误用unknown或漏引发布条件；收益包含外部规则工具，不代表模型自身推理能力提高。',
            'checker_path': CHECKER.relative_to(ROOT).as_posix(), 'checker_sha256': SHA(CHECKER),
            'service_arguments': service_reference['service_arguments'],
            'source_path': SOURCE.relative_to(ROOT).as_posix(), 'source_sha256': SHA(SOURCE),
            'planned_calls': 4, 'order': [{'sequence': 1, 'case_id': 'T01', 'variant': 'control'},
                                         {'sequence': 2, 'case_id': 'T01', 'variant': 'local_rule'},
                                         {'sequence': 3, 'case_id': 'T08', 'variant': 'local_rule'},
                                         {'sequence': 4, 'case_id': 'T08', 'variant': 'control'}],
            'single_difference': '仅向user JSON增加local_rule_states；其他messages、完整资料、类型enum和全部请求参数不变。',
            'settings': 'Qwen3-0.6B-Q8_0，关闭思考，4096上下文，CPU单槽4线程，沿用原采样、类型enum和max_tokens=256。',
            'memory_gate': '沿用2 GiB加载门槛和此前1 GiB低内存停止规则；不结束其他程序。',
            'stops': ['原文复算不符即停止，不能启动服务', '离线失败阻断运行器', '实际模板容量失败不截断', '技术失败保存后停止，质量错误不重试'],
            'evaluation': ['规则状态原文核对', '最终选择符合规则（保留T01资格歧义）', '数据和发布条件引用覆盖', '引用支持', '严格完整成功'],
            'protected_hashes': protected,
            'generation_calls_so_far': 0}
    write(folder/'design-plan.json', plan)
    shutil.copyfile(CHECKER, folder/'code-snapshot/explicit_state_checker.py')
    shutil.copyfile(CHECKER.parent/'offline_gate.py', folder/'code-snapshot/offline_gate.py')
    shutil.copyfile(Path(__file__).with_name('local_rule_state_candidate.py'), folder/'local_rule_state_candidate.py')
    shutil.copyfile(Path(__file__), folder/'prepare_local_rule_state_pairs.py')
    checker = module(CHECKER, 'checker_for_state_pairs')
    candidate = module(folder/'local_rule_state_candidate.py', 'state_pair_candidate')
    expected_reviews = {
        'S23': ('explicit_defect', '缺坐标映射', '正文明确缺坐标映射；问答完成不消除该缺陷。'),
        'S24': ('unknown', '完成问答、引用定位及冷启动恢复', '正文说明完成检查，不明示未关闭定位问题为零；不从完成推断整体资格。'),
        'S25': ('explicit_defect', '三项未关闭问题', '正文明确非零未关闭问题。'),
        'K16': ('explicit_defect', '4项偏移', '问答通过与定位偏移分别记录；4项偏移为明示缺陷。'),
        'K17': ('explicit_pass_only', '三项检查通过', '该句直接明示三项检查通过；这里只核对明示通过，不代替整体资格判断。'),
        'K18': ('explicit_defect', '2项失败', '会话恢复2项失败为明示缺陷，解析较快不消除失败。'),
    }
    results, reviews, request_pairs = [], [], []
    for row in sources['items']:
        original = copy.deepcopy(row)
        states = checker.inspect_explicit_states(row['passages'], row['candidates'])
        assert row == original
        write(folder/('state-recompute-'+row['case_id']+'.json'), {'checked_at': TIME(),
              'checker_sha256': SHA(CHECKER), 'question': row['question'], 'passages': row['passages'],
              'snapshot_candidates': row['candidates'], 'items': states, 'input_unchanged': True})
        for state in states:
            text = row['passages'][state['passage_index']]['text']
            assert text[state['start']:state['end']] == state['quote']
            for event in state['events']:
                assert text[event['trigger_start']:event['trigger_end']] == event['trigger']
            expected, excerpt, reason = expected_reviews[state['snapshot']]
            assert excerpt in state['quote']
            review = {'snapshot': state['snapshot'], 'passage_id': state['passage_id'],
                      'start': state['start'], 'end': state['end'], 'quote': state['quote'],
                      'actual_state': state['observed_state'], 'expected_explicit_state': expected,
                      'matches_original_text': state['observed_state'] == expected,
                      'basis': reason, 'event_rules': [e['rule'] for e in state['events']],
                      'source': 'Codex辅助原文核对，尚待本人确认；不是整体资格或标准答案标签。'}
            reviews.append(review)
        control_record = controls[row['case_id']]
        body = control_record['actual_http_request_body']
        decoded = json.loads(body['messages'][1]['content'])
        assert decoded['question'] == row['question'] and decoded['passages'] == row['passages']
        assert body['max_tokens'] == 256
        schema = body['response_format']['json_schema']['schema']
        assert 'enum' in schema['properties']['answer']
        new_body = candidate.attach_rule_states(body, states, SHA(CHECKER))
        request_pairs.append({'case_id': row['case_id'], 'control_source': control_record['record_path'],
                              'control_source_sha256': SHA(ROOT/control_record['record_path']),
                              'control': body, 'local_rule': new_body,
                              'only_user_local_rule_states_added': True,
                              'answer_enum': schema['properties']['answer']['enum']})
        results.extend(states)
    write(folder/'request-pairs.json', {'saved_at': TIME(), 'items': request_pairs, 'not_dispatched': True})
    write(folder/'state-original-text-review.json', {'reviewed_at': TIME(), 'items': reviews,
          'passed': all(r['matches_original_text'] for r in reviews),
          'review_is_not_final_answer_evaluation': True})
    all_passed = all(r['matches_original_text'] for r in reviews)
    write(folder/'offline-check.json', {'checked_at': TIME(), 'passed': all_passed,
          'returncode': 0 if all_passed else 1, 'states_total': len(results),
          'states_match_text': sum(r['matches_original_text'] for r in reviews),
          'only_user_field_added': True, 'complete_original_passages_preserved': True,
          'no_candidate_deletion_or_forced_answer': True,
          'checker_sha256_unchanged': SHA(CHECKER) == plan['checker_sha256']})
    gate = module(folder/'code-snapshot/offline_gate.py', 'state_candidate_gate')
    next_steps = []
    blocked = False
    if not all_passed:
        try:
            gate.after_offline_success(lambda: {'passed': False, 'returncode': 1}, lambda: next_steps.append('runner'))
        except RuntimeError:
            blocked = True
        write(folder/'technical-stop.json', {'stopped_at': TIME(), 'stage': 'offline_original_text_review',
              'reason': '明示状态复算与原文不一致；按计划停止，不修复或掩盖未知状态。',
              'differences': [r for r in reviews if not r['matches_original_text']],
              'generation_dispatches': 0, 'model_service_started': False,
              'template_capacity_check': 'not_run_due_to_offline_gate',
              'planned_calls_not_run': 4, 'failed_offline_check_blocked_runner': blocked,
              'next_step_calls': len(next_steps)})
    assert all(SHA(ROOT/path) == value for path, value in protected.items())
    write(folder/'execution-summary.json', {'saved_at': TIME(), 'planned_calls': 4,
          'generation_dispatches': 0, 'completed_answers': 0, 'not_run': 4,
          'model_service_started': False, 'offline_passed': all_passed,
          'protected_files_unchanged': True, 'checker_not_modified': True,
          'cumulative_confirmed': 312, 'cumulative_source': '基础/runs/local_checks_full_answer/20261014-183922/execution-summary.json'})
    print(json.dumps({'folder': str(folder), 'offline_passed': all_passed,
                     'items': [{k:r[k] for k in ('snapshot', 'actual_state', 'expected_explicit_state', 'matches_original_text')} for r in reviews],
                     'generation_calls': 0, 'runner_blocked': blocked}, ensure_ascii=False))
    return 0 if all_passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
