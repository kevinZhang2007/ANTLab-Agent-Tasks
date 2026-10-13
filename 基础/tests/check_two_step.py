"""自造资料的独立定位/原文选择检查，不调用模型。"""
from pathlib import Path
from datetime import datetime
import ast
import copy
import json
import hashlib
import two_step_candidate as candidate

repo = Path(__file__).resolve().parents[2]
folder = repo / '基础/runs/two_step/dev_r0'
passages = [
    {'id':'x', 'source':'自造/主记录', 'text':'中文“引号”与\n换行，数量资料。'},
    {'id':'y', 'source':'自造/规则', 'text':'资格规则与比较口径。'},
    {'id':'z', 'source':'自造/检查', 'text':'缺失信息的检查来源。'},
]
original = copy.deepcopy(passages)
tests = []
messages = candidate.prepare_selection_messages('问题包含\n换行和"引号"', passages)
assert json.loads(messages[1]['content']) == {'question':'问题包含\n换行和"引号"','passages':passages}
assert passages == original
tests.append('消息完整保留问题和原文，输入不变')
valid = candidate.validate_selection('{"selected_ids":["z","x"]}', passages)
selected = candidate.select_original_passages(passages, valid)
assert selected == [original[0], original[2]]
assert selected[0] is not passages[0]
assert passages == original
tests.append('按输入相对顺序选完整深拷贝，忽略返回ID顺序')
for raw, status in [('{"selected_ids":[]}','empty_selection'),
    ('{"selected_ids":["missing"]}','unknown_id'),
    ('{"selected_ids":["x","x"]}','duplicate_id'),
    ('not json','invalid_json'),
    ('{"selected_ids":[],"answer":"fake"}','invalid_fields'),
    ('{"selected_ids":"x"}','invalid_type'),
    ('{"selected_ids":[1]}','invalid_type'),
    ('{"selected_ids":[],"selected_ids":["x"]}','invalid_json')]:
    result=candidate.validate_selection(raw,passages)
    assert result['status']==status
    if result['valid']:
        assert candidate.select_original_passages(passages,result)==[]
    else:
        try:candidate.select_original_passages(passages,result)
        except ValueError:pass
        else:raise AssertionError('非法选择发生回退')
    tests.append(status)
mapped=[dict(p,id={'x':'new-c','y':'new-a','z':'new-b'}[p['id']]) for p in passages]
mapped_selection=candidate.select_original_passages(mapped,candidate.validate_selection('{"selected_ids":["new-b","new-c"]}',mapped))
assert [(p['source'],p['text']) for p in mapped_selection]==[(p['source'],p['text']) for p in selected]
assert candidate.select_original_passages([],candidate.validate_selection('{"selected_ids":[]}',[]))==[]
assert passages==original
tests.append('ID重映射及空输入通过')
source=(Path(__file__).parent/'two_step_candidate.py').read_text(encoding='utf-8')
tree=ast.parse(source)
assert all(n.module=='copy' or n.module=='json' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom))
assert {a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names}<={'copy','json'}
assert not any(isinstance(n,ast.Name) and n.id in {'open','Path','eval','exec','case_id','condition'} for n in ast.walk(tree))
tests.append('定位模块仅copy/json，无文件读取、题号或条件输入')
record={'checked_at':datetime.now().astimezone().isoformat(),'counts_as_generation':False,'fixtures':'自造资料，不读开发答案或正式题','tests':tests,'passed':True,'module_sha256':hashlib.sha256((Path(__file__).parent/'two_step_candidate.py').read_bytes()).hexdigest()}
path=folder/'offline-check.json'
assert not path.exists()
path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS',len(tests),'checks; no model calls')
