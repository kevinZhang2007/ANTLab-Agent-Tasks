"""仅开发题和自造样例的离线关联检查，不调用模型。"""
from pathlib import Path
from datetime import datetime
import copy
import hashlib
import importlib.util
import json
import random
import sys

base = Path(__file__).resolve().parents[1]
folder = base / 'runs/improve/linked_r0'
spec = importlib.util.spec_from_file_location('linked_candidate', folder / 'student-v2.py')
student = importlib.util.module_from_spec(spec)
spec.loader.exec_module(student)

def passage(text, source='样例', identifier='x'):
    return {'id': identifier, 'source': source, 'text': text}

def order(rows):
    return [(p['source'], p['text']) for p in rows]

def check(question, passages):
    before = copy.deepcopy(passages)
    result, decisions = student.organize_passages(question, passages)
    assert passages == before
    assert len(result) == len(passages)
    assert all(result.count(p) == passages.count(p) for p in passages)
    for seed in range(10):
        shuffled = copy.deepcopy(passages)
        random.Random(seed).shuffle(shuffled)
        assert order(student.improve(question, shuffled)) == order(result)
        for index, p in enumerate(shuffled):
            p['id'] = f'remapped-{index}'
        assert order(student.improve(question, shuffled)) == order(result)
    return result, decisions

samples = [
    ('明确关联', ['甲项目R2版本2026-07正式批次AB12。', '批次AB12的复核补页：计数。'], True),
    ('编号复用', ['甲项目R2版本批次AB12。', '乙项目R2版本批次AB12。', '批次AB12的复核补页：计数。'], False),
    ('版本冲突', ['甲项目R2版本批次AB12。', '甲项目R3版本批次AB12的复核补页：计数。'], False),
    ('项目冲突', ['甲项目批次AB12。', '乙项目批次AB12的复核补页：计数。'], False),
    ('日期冲突', ['批次AB12记录2026-07。', '2026-08批次AB12的复核补页：计数。'], False),
    ('缺失范围', ['甲项目R2版本2026-07批次AB12。', '批次AB12的复核补页：计数。'], True),
    ('多个主段', ['批次AB12记录一。', '批次AB12记录二。', '批次AB12的复核补页：计数。'], False),
    ('无关联', ['甲项目批次AB12。', '独立资料无补充指称。'], False),
    ('任意英文数字词', ['设备AB12返回成功。', 'AB12补页：计数。'], False),
    ('非直接补充指称', ['批次AB12记录。', '批次AB12记录旧结果，另一文档补页计数。'], False),
    ('禁止多跳', ['批次AB12记录。', '批次AB12的复核补页提及批次CD34。', '批次CD34的复核补页：计数。'], True),
]
records = []
assert student.improve('任意问题', []) == []
for name, texts, expected in samples:
    ps = [passage(t, str(i), str(i)) for i, t in enumerate(texts)]
    result, decisions = check('甲项目计数', ps)
    assert any(d['target_id'] is not None for d in decisions) == expected, (name, decisions)
    if name == '缺失范围':
        assert decisions[0]['unknown_scope_fields'] == ['project', 'version', 'date']
    if name == '禁止多跳':
        assert sum(d['target_id'] is not None for d in decisions) == 1
    records.append({'sample': name, 'input': ps, 'output': result, 'decisions': decisions})
capacity = json.loads((base / 'runs/capacity/stage3/inputs.json').read_text(encoding='utf-8'))
rows = []
for cid in ('D01', 'D02', 'D03', 'D04'):
    row = next(r for r in capacity['rows'] if r['case_id'] == cid and r['condition'] == 'R0')
    payload = json.loads(row['messages'][1]['content'])
    result, decisions = check(payload['question'], payload['passages'])
    assert student.prepare_messages(payload['question'], payload['passages']) == row['messages']
    rows.append({'case_id': cid, 'original_passages': payload['passages'], 'selected_passages': result,
                 'decisions': decisions, 'scores': [{'id': p['id'], 'score': student.relevance_score(payload['question'], p)} for p in payload['passages']]})
    print(cid, [p['id'] for p in result], decisions, flush=True)
if '--no-save' in sys.argv:
    print('PASS offline recheck of frozen candidate; no files written')
    sys.exit(0)
output = folder / 'offline-check-final.json'
assert not output.exists(), '保留原记录，禁止覆盖'
output.write_text(json.dumps({'recorded_at': datetime.now().astimezone().isoformat(),
    'counts_as_generation': False, 'checks_passed': True, 'semantic_support_verified': False,
    'student_sha256': hashlib.sha256((folder / 'student-v2.py').read_bytes()).hexdigest(),
    'samples': records, 'rows': rows}, ensure_ascii=False, indent=2), encoding='utf-8')
print('PASS contents/counts/input unchanged/empty/shuffles/ID remapping/11 synthetic cases')
