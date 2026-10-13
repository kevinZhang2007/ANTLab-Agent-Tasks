"""不调用模型的排序、内容保留和等价变体检查。"""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json
import random
import sys

repo=Path(__file__).resolve().parents[2]
base=repo/'基础'
folder=base/'runs/improve/dev_r0'
sys.path.insert(0,str(base/'starter'))
import student
compile((base/'starter/student.py').read_text(encoding='utf-8'),str(base/'starter/student.py'),'exec')
assert student.improve('任意问题',[])==[]
assert student.relevance_score('',{'text':'任意正文'})==0
assert student.relevance_score('核验率',{'text':'核验率'})==1
assert student.relevance_score('核验率',{'text':'核验'})==0.5
assert student.relevance_score('ALPHA R4',{'text':'alpha r4'})==1
sample=[{'id':'z','source':'B','text':'不相关'}, {'id':'a','source':'A','text':'alpha r4'}]
assert student.improve('alpha r4',sample)[0] is sample[1]
ties=[{'id':'z','source':'B','text':'同分'}, {'id':'a','source':'A','text':'同分'}]
assert [p['source'] for p in student.improve('',ties)]==['A','B']
capacity=json.loads((base/'runs/capacity/stage3/inputs.json').read_text(encoding='utf-8'))
rows=[]
def content_order(passages): return [(p['source'],p['text']) for p in passages]
for index,cid in enumerate(('D01','D02','D03','D04')):
    row=next(r for r in capacity['rows'] if r['case_id']==cid and r['condition']=='R0')
    payload=json.loads(row['messages'][1]['content'])
    question,passages=payload['question'],payload['passages']
    before=copy.deepcopy(passages)
    ranked=student.improve(question,passages)
    assert len(ranked)==len(passages)==7
    assert all(ranked.count(p)==passages.count(p) for p in passages)
    assert passages==before
    assert student.prepare_messages(question,passages)==row['messages']
    for seed in range(10):
        shuffled=copy.deepcopy(passages)
        random.Random(1000+index*10+seed).shuffle(shuffled)
        assert content_order(student.improve(question,shuffled))==content_order(ranked)
        remapped=copy.deepcopy(shuffled)
        for number,p in enumerate(remapped): p['id']=f'alias-{100-number}'
        assert content_order(student.improve(question,remapped))==content_order(ranked)
    scores=[]
    for p in passages:
        query=student.text_features(question)
        matched=query & student.text_features(p['text'])
        scores.append({'id':p['id'],'source':p['source'],'score':student.relevance_score(question,p),
                       'matched_features':sorted(matched),'query_feature_count':len(query)})
    rows.append({'case_id':cid,'question':question,'original_passages':before,'ranked_passages':ranked,
                 'original_ids':[p['id'] for p in passages],'ranked_ids':[p['id'] for p in ranked],
                 'scores':scores,'content_and_count_preserved':True,'input_unchanged':True,
                 'shuffle_and_id_remapping_trials':10})
    print(cid,'BEFORE',rows[-1]['original_ids'],'AFTER',rows[-1]['ranked_ids'],flush=True)
out=folder/'offline-check.json'
assert not out.exists()
out.write_text(json.dumps({'record_kind':'offline_sorting_check','counts_as_generation':False,
               'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'checks_passed':True,
               'student_sha256':hashlib.sha256((base/'starter/student.py').read_bytes()).hexdigest(),
               'score_is_semantic_support':False,'rows':rows},ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS counts, content, no mutation, empty input, exact score samples, ties, 40 shuffles and ID remappings')
