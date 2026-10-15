"""自造后处理检查并提取八题历史原回答；不调用模型。"""
from pathlib import Path
from datetime import datetime
import copy,hashlib,json,sys
import citation_review_candidate as candidate

repo=Path(__file__).resolve().parents[2]
folder=Path(sys.argv[1]).resolve()
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now().astimezone().isoformat()
def write(name,value):
    path=folder/name;assert not path.exists();path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
passages=[{'id':'alpha','source':'自造来源','text':'中文“引号”\n换行。'},
          {'id':'beta','source':'另一自造来源','text':'补充资料。'}]
original={'answer':'保留 "引号"\n中文、空格  ','citations':['alpha']}
fixtures=[
 ('supported合法','{"verdict":"supported","citations":["alpha","beta"],"reason":"自造检查"}',True,['alpha','beta']),
 ('未知ID','{"verdict":"supported","citations":["unknown"],"reason":"自造检查"}',False,['alpha']),
 ('重复ID','{"verdict":"supported","citations":["alpha","alpha"],"reason":"自造检查"}',False,['alpha']),
 ('非法verdict','{"verdict":"correct","citations":["alpha"],"reason":"自造检查"}',False,['alpha']),
 ('空引用supported','{"verdict":"supported","citations":[],"reason":"自造检查"}',True,[]),
 ('contradicted保留原回答','{"verdict":"contradicted","citations":["beta"],"reason":"自造检查"}',False,['alpha']),
 ('insufficient保留原回答','{"verdict":"insufficient","citations":[],"reason":"自造检查"}',False,['alpha']),
 ('不得另写答案','{"verdict":"supported","citations":["beta"],"reason":"自造检查","answer":"改写"}',False,['alpha']),
 ('非法JSON','bad json',False,['alpha']),
 ('重复JSON字段','{"verdict":"supported","verdict":"insufficient","citations":[],"reason":"自造检查"}',False,['alpha']),
 ('空理由','{"verdict":"supported","citations":["beta"],"reason":""}',False,['alpha']),
]
write('synthetic-fixtures-before-check.json',{'saved_at':now(),'fixtures':fixtures,'original_response':original,
    'passages':passages,'generation_calls':0,'fixtures_are_not_model_responses':True})
write('schema.review.json',candidate.REVIEW_SCHEMA)
(folder/'system.review.txt').write_text(candidate.REVIEW_PROMPT,encoding='utf-8')
snapshot=folder/'code-snapshot';snapshot.mkdir()
for p in [Path(candidate.__file__),Path(__file__)]:
    (snapshot/p.name).write_bytes(p.read_bytes())
checks=[]
for name,raw,applied,citations in fixtures:
    prior=copy.deepcopy(original);data=copy.deepcopy(passages)
    result=candidate.derive_candidate(original,raw,passages)
    assert original==prior and passages==data
    assert result['candidate_response']['answer']==original['answer']
    assert result['citation_replacement_applied']==applied and result['candidate_response']['citations']==citations
    checks.append({'sample':name,'raw_fixture':raw,'result':result,'passed':True})
messages=candidate.prepare_review_messages('中文问题？',passages,original)
assert json.loads(messages[1]['content'])=={'question':'中文问题？','passages':passages,'original_response':original}
empty=candidate.derive_candidate(original,'{"verdict":"supported","citations":[],"reason":"自造检查"}',[])
assert empty['candidate_response']['answer']==original['answer'] and empty['candidate_response']['citations']==[]
mapping={'alpha':'changed-0','beta':'changed-1'}
changed=[dict(p,id=mapping[p['id']]) for p in passages]
mapped=candidate.derive_candidate(dict(original,citations=['changed-0']),
    '{"verdict":"supported","citations":["changed-1"],"reason":"自造检查"}',changed)
assert mapped['candidate_response']['citations']==['changed-1']
write('offline-check.json',{'checked_at':now(),'passed':True,'checks':checks,'empty_input_and_id_remap_passed':True,
    'generation_calls':0,'empty_citations_are_not_semantic_success':True})

previous=repo/'基础/runs/direct_reference_pairs/20261014-134901'
association=load(previous/'eight-case-association-recompute.json')['items']
old_runs=[load(p) for p in previous.glob('run-*.json')]
reused=load(previous/'reused-results.json')['items']
inputs=[]
for item in association:
    matches=[r for r in old_runs if r['case_id']==item['case_id'] and r['variant']=='new']
    if matches:
        assert len(matches)==1;record=matches[0]
        path=previous/('run-'+record['run_id']+'.json');provenance='previous_new_variant_actual_answer'
    else:
        r=next(r for r in reused if r['case_id']==item['case_id'])
        path=repo/r['record_path'];assert sha(path)==r['record_sha256']
        record=load(path);provenance='previous_new_variant_same_request_historical_reuse'
    raw=record['raw_content'];response=json.loads(raw,object_pairs_hook=candidate.unique_fields)
    assert set(response)=={'answer','citations'} and isinstance(response['answer'],str)
    payload=json.loads(record['messages'][1]['content'])
    assert payload=={'question':item['question'],'passages':item['new_used_passages']}
    assert record['raw_http_request_body']==item['raw_serialized_requests']['new']
    inputs.append({'case_id':item['case_id'],'question':payload['question'],'passages':payload['passages'],
        'original_response':response,'original_raw_content':raw,'source_run_id':record['run_id'],
        'source_path':path.relative_to(repo).as_posix(),'source_sha256':sha(path),'source_provenance':provenance})
write('source-inputs.json',{'saved_at':now(),'items':sorted(inputs,key=lambda r:r['case_id']),
    'source_side':'historical_reuse_not_synchronous_answer_control','new_initial_answer_calls':0})
config=load(repo/'基础/runs/formal/round2-20261014-133000/freeze.json')['answer_config']
config=copy.deepcopy(config)
config['parameters']['response_format']={'type':'json_schema','json_schema':{'schema':copy.deepcopy(candidate.REVIEW_SCHEMA)}}
write('config.review.json',config)
plan=load(folder/'design-plan.json')
write('execution-plan.json',{'saved_at':now(),'order':[{**j,'variant':'citation_review'} for j in plan['order']],
    'planned_generation_calls':8,'generation_limit':8,'selection_rule':'严格优先，同分保留原方案；supported误报单列。'})
print('PASS 11 synthetic fixtures, empty/input/remap and unchanged-answer checks; 8 historical source inputs locked; 0 model calls')
