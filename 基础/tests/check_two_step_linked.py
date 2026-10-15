"""自造资料的离线补页检查；不读答案，不调用模型。"""
import ast
import copy
import hashlib
import json
import random
import sys
from pathlib import Path
from datetime import datetime
import two_step_candidate as selection
import two_step_linked_candidate as candidate

folder = Path(sys.argv[1])
def sample(texts, chosen=0):
    rows = [{'id': f'item-{i}', 'source': f'同目录/{i}', 'text': t} for i,t in enumerate(texts)]
    raw = json.dumps({'selected_ids': [rows[chosen]['id']]}, ensure_ascii=False)
    return rows, selection.validate_selection(raw,rows)

cases = [
 ('直接补页', ['甲项目R2版本2026-07批次AB12记录。','批次AB12的复核补页：计数。'], 1),
 ('编号复用', ['甲项目R2版本批次AB12记录。','乙项目R2版本批次AB12记录。','批次AB12的复核补页。'], 0),
 ('版本冲突', ['甲项目R2版本批次AB12记录。','甲项目R3版本批次AB12的复核补页。'], 0),
 ('项目冲突', ['甲项目批次AB12记录。','乙项目批次AB12的复核补页。'], 0),
 ('日期冲突', ['2026-07批次AB12记录。','2026-08批次AB12的复核补页。'], 0),
 ('目标不唯一', ['批次AB12记录一。','批次AB12记录二。','批次AB12的复核补页。'], 0),
 ('禁止多跳', ['批次AB12记录。','批次AB12的复核补页提及批次CD34。','批次CD34的复核补页。'], 1),
 ('同source目录不关联', ['批次AB12记录。','没有明确指称的补页。'], 0),
 ('英文数字无语境', ['设备AB12。','AB12补页。'], 0),
 ('缺失范围仍未知', ['甲项目R2版本2026-07批次AB12记录。','批次AB12的复核补页。'], 1),
 ('没有直接补充指称', ['批次AB12记录。','批次AB12记录旧结果，另一文档补页。'], 0),
]
records=[]
for name,texts,expected in cases:
    passages,validation=sample(texts)
    before=copy.deepcopy(passages)
    result,trace=candidate.complete_passages('资料计数',passages,validation)
    assert passages==before and len(result)==1+expected and len({p['id'] for p in result})==len(result)
    assert result==[p for p in passages if p['id'] in {r['id'] for r in result}]
    selected_content={(p['source'],p['text']) for p in result}
    for seed in range(10):
        shuffled=copy.deepcopy(passages);random.Random(seed).shuffle(shuffled)
        other,_=candidate.complete_passages('资料计数',shuffled,validation)
        assert {(p['source'],p['text']) for p in other}==selected_content
        assert other==[p for p in shuffled if p['id'] in {r['id'] for r in other}]
        mapping={p['id']:f'remapped-{seed}-{i}' for i,p in enumerate(shuffled)}
        mapped=[dict(p,id=mapping[p['id']]) for p in shuffled]
        changed={'valid':True,'selected_ids':[mapping[i] for i in validation['selected_ids']]}
        mapped_result,_=candidate.complete_passages('资料计数',mapped,changed)
        assert {(p['source'],p['text']) for p in mapped_result}==selected_content
    if name=='缺失范围仍未知':assert trace[0]['unknown_scope_fields']==['project','version','date']
    records.append({'sample':name,'passages':passages,'selection':validation,'result':result,'trace':trace,'shuffle_and_remap_trials':10})
rows,valid=sample(['批次AB12记录。','批次AB12的复核补页。'])
for raw,status in [('not json','invalid_json'),('{"selected_ids":["missing"]}','unknown_id'),('{"selected_ids":["item-0","item-0"]}','duplicate_id')]:
    invalid=selection.validate_selection(raw,rows);assert invalid['status']==status
    try:candidate.complete_passages('问题',rows,invalid)
    except ValueError:pass
    else:raise AssertionError('非法定位发生回退')
assert candidate.complete_passages('问题',[],{'valid':True,'selected_ids':[]})[0]==[]
assert candidate.complete_passages('问题',rows,{'valid':True,'selected_ids':[]})[0]==[]
tree=ast.parse(Path(candidate.__file__).read_text(encoding='utf-8'))
function=next(n for n in tree.body if isinstance(n,ast.FunctionDef))
assert not any(isinstance(n,ast.Name) and n.id in ['open','Path','case_id','condition','gold','answers'] for n in ast.walk(function))
record={'checked_at':datetime.now().astimezone().isoformat(),'counts_as_generation':False,'passed':True,'fixtures':'仅自造资料；未读取开发答案或正式题','samples':records,'invalid_selection_cases':3,'empty_checks':2,'input_preserved':True,'ordering_rule':'每次输出遵循该次完整输入相对顺序；打乱后按内容的选择集合一致。','semantic_support_verified':False,'hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(candidate.__file__),Path(selection.__file__),candidate.LINKED_SOURCE]}}
path=folder/'offline-check.json';assert not path.exists();path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PASS 11 synthetic cases, 110 shuffles/remaps, empty/invalid checks; no model calls')
