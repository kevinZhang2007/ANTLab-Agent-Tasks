from pathlib import Path
import copy
import importlib.util
import json
import subprocess
import sys

repo = Path(__file__).resolve().parents[2]
base = repo / '基础'
student_path = base / 'starter/student.py'
compile(student_path.read_text(encoding='utf-8'), str(student_path), 'exec')
print('PASS student.py syntax')
spec = importlib.util.spec_from_file_location('student', student_path)
student = importlib.util.module_from_spec(spec)
spec.loader.exec_module(student)
question = '中文问题："哪一段？"\n第二行\\路径'
passages = [
    {'id': '样例乙', 'source': '来源"乙"\n下一行', 'text': '中文正文\n"引号"与\\反斜杠'},
    {'id': '样例甲', 'source': '', 'text': ''},
]
before = copy.deepcopy(passages)
for supplied in (passages, []):
    messages = student.prepare_messages(question, supplied)
    assert [m['role'] for m in messages] == ['system', 'user']
    assert all(set(m) == {'role', 'content'} for m in messages)
    payload = json.loads(messages[1]['content'])
    assert payload == {'question': question, 'passages': supplied}
    assert messages[0]['content'] == student.prepare_messages('另一个问题', [])[0]['content']
    assert '证据不足' in messages[0]['content']
    assert 'answer' not in payload
assert passages == before
assert student.improve(question, passages) is passages
print('PASS custom samples: Chinese, quotes, newline, backslash, empty text, empty list, no input mutation')
command = [sys.executable, '-X', 'utf8', '-B', 'starter/runner.py', '--case', 'D01', '--condition', 'E', '--dry-run', '--config', 'config.example.json']
result = subprocess.run(command, cwd=base, capture_output=True, text=True, encoding='utf-8')
print('COMMAND: python -X utf8 -B starter/runner.py --case D01 --condition E --dry-run --config config.example.json')
print(result.stdout, end='')
print(result.stderr, end='')
assert result.returncode == 0, result.returncode
run_id = result.stdout.split()[0]
record_path = base / 'runs' / (run_id + '.json')
record = json.loads(record_path.read_text(encoding='utf-8'))
# 只核对D01，不输出或执行其他题目的内容。
case = next(c for c in json.loads((base / 'data/cases.json').read_text(encoding='utf-8')) if c['id'] == 'D01')
by_id = {p['id']: p for p in case['passages']}
expected = [by_id[i] for i in case['conditions']['E']]
payload = json.loads(record['messages'][1]['content'])
assert payload == {'question': case['question'], 'passages': expected}
assert record['selected_passage_ids'] == case['conditions']['E']
assert record['original_passage_ids'] == case['conditions']['E']
assert record['mode'] == 'dry' and record['status'] == 'dry_run'
assert record['response'] is None and record['elapsed_seconds'] is None
assert record['messages'][0]['content'] == student.prepare_messages(question, [])[0]['content']
print('PASS D01: question and complete passages (id/source/text/order) match actual input')
print('D01 passage IDs:', record['selected_passage_ids'])
print('D01 message roles:', [m['role'] for m in record['messages']])
print('RECORD:', record_path.relative_to(repo))
print('PASS dry-run response=None, no model call')
