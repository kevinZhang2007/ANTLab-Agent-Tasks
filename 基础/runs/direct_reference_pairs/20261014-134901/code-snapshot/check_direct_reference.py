"""固定正反例、八题重算及真实请求序列化差异；无生成接口。"""
import copy
from datetime import datetime
import difflib,hashlib,json,random,sys
from pathlib import Path
import direct_reference_candidate as candidate
import two_step_linked_candidate as old
import general_candidate as generic

repo=Path(__file__).resolve().parents[2]
folder=Path(sys.argv[1]).resolve()
now=lambda:datetime.now().astimezone().isoformat()
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,value):
    path=folder/name;assert not path.exists()
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
samples=[
 ('同类型直接指称',['甲项目R2版本批次AB12记录数据。','批次AB12的复核补页：规则。'],[0,1]),
 ('类型不同但唯一直接指称',['甲项目R2版本核验表AB12记录数据。','批次AB12的复核补页：规则。'],[0,1]),
 ('通用其他业务对象',['甲项目R2版本预算审计表ZX19记录数据。','巡检组ZX19的补充说明：规则。'],[0,1]),
 ('完整带后缀编号',['甲项目R2版本预算表ZX19-2记录数据。','批次ZX19-2的补页：规则。'],[0,1]),
 ('编号前缀不同',['核验表AB12记录数据。','批次AB120的补页。'],[0]),
 ('编号后缀不同',['核验表AB12-1记录数据。','批次AB12-2的补页。'],[0]),
 ('同编号不同对象',['核验表AB12记录数据。','资源表AB12记录另一份数据。','批次AB12的补页。'],[0]),
 ('同段多个对象',['核验表AB12记录数据；资源表AB12记录另一份数据。','批次AB12的补页。'],[0]),
 ('跨项目复用',['甲项目R2版本核验表AB12记录。','乙项目R2版本核验表AB12记录。','批次AB12的补页。'],[0]),
 ('多个相同范围主段',['甲项目R2版本批次AB12记录一。','甲项目R2版本批次AB12记录二。','批次AB12的补页。'],[0]),
 ('普通设备型号',['设备型号AB12记录温度。','批次AB12的补页。'],[0]),
 ('普通编号提及',['这里提到AB12，没有业务对象声明。','批次AB12的补页。'],[0]),
 ('引用不是主声明',['本段参考核验表AB12记录的数据。','批次AB12的补页。'],[0]),
 ('对象提及缺声明谓词',['本段仅提及核验表AB12。','批次AB12的补页。'],[0]),
 ('版本冲突',['甲项目R2版本核验表AB12记录。','甲项目R3版本批次AB12的补页。'],[0]),
 ('项目冲突',['甲项目R2版本核验表AB12记录。','乙项目R2版本批次AB12的补页。'],[0]),
 ('日期冲突',['2027-01核验表AB12记录。','2027-02批次AB12的补页。'],[0]),
 ('命名空间冲突',['核验表AB12记录。命名空间：业务。','批次AB12的补页。命名空间：设备。'],[0]),
 ('命名空间一致',['核验表AB12记录。编号域：业务。','批次AB12的补页。编号域：业务。'],[0,1]),
 ('命名空间有多个值',['核验表AB12记录。命名空间：业务。命名空间：设备。','批次AB12的补页。'],[0]),
 ('明确不是同一对象',['核验表AB12记录。','批次AB12的补页：该编号是另一业务对象。'],[0]),
 ('明确不对应主对象',['核验表AB12记录。','批次AB12的补页：不是该主对象。'],[0]),
 ('无直接补充指称',['核验表AB12记录。','补充说明：仅提及批次AB12。'],[0]),
 ('多个补充对象',['核验表AB12记录。','批次AB12的补页与批次CD34的补页。'],[0]),
 ('多个主范围',['甲项目R2版本核验表AB12记录，另列R3版本。','批次AB12的补页。'],[0]),
 ('字段缺失仍未知',['甲项目R2版本2027-01核验表AB12记录。','批次AB12的补页。'],[0,1]),
 ('禁止多跳',['核验表AB12记录。','批次AB12的补页，另提到CD34。','批次CD34的补页。'],[0,1]),
]
write('synthetic-fixtures-before-check.json',{'saved_at':now(),'fixed_samples':samples,'kind':'post_evaluation_synthetic_mechanism_checks','generation_calls':0})
snapshot=folder/'code-snapshot';snapshot.mkdir()
for p in [Path(candidate.__file__),Path(__file__)]:
    (snapshot/p.name).write_bytes(p.read_bytes())
checks=[]
try:
    for name,texts,wanted in samples:
        rows=[{'id':'sample-'+str(i),'source':'same/'+str(i),'text':t} for i,t in enumerate(texts)]
        before=copy.deepcopy(rows);validation={'valid':True,'selected_ids':['sample-0']}
        used,trace=candidate.complete_passages('核对资料',rows,validation)
        expected=['sample-'+str(i) for i in wanted]
        check={'sample':name,'passages':rows,'trace':trace,'expected_ids':expected,'actual_ids':[p['id'] for p in used]}
        checks.append(check);assert check['actual_ids']==expected,name+str(check)
        assert rows==before and all(p in rows for p in used)
        content={(p['source'],p['text']) for p in used}
        for seed in range(4):
            shuffled=copy.deepcopy(rows);random.Random(seed).shuffle(shuffled)
            mapping={p['id']:'mapped-'+str(seed)+'-'+str(i) for i,p in enumerate(shuffled)}
            mapped=[dict(p,id=mapping[p['id']]) for p in shuffled]
            actual,_=candidate.complete_passages('核对资料',mapped,{'valid':True,'selected_ids':[mapping['sample-0']]})
            assert {(p['source'],p['text']) for p in actual}==content
            assert actual==[p for p in mapped if p['id'] in {q['id'] for q in actual}]
        for p in rows:
            for m in candidate.describe(p['text'])['mentions']:
                assert p['text'][m['code_start']:m['code_end']]==m['code']
                s=m['statement'];assert p['text'][s['start']:s['end']]==s['text']
        if name=='字段缺失仍未知':assert trace[0]['unknown_scope_fields']==['project','version','date','namespace']
    assert candidate.complete_passages('问题',[],{'valid':True,'selected_ids':[]})==([],[])
    assert candidate.complete_passages('问题',rows,{'valid':True,'selected_ids':[]})[0]==[]
    for raw in ['bad json','{"selected_ids":["unknown"]}','{"selected_ids":["sample-0","sample-0"]}']:
        invalid=candidate.selection.validate_selection(raw,rows)
        try:candidate.complete_passages('问题',rows,invalid)
        except ValueError:pass
        else:raise AssertionError('非法选择被修补')
    write('offline-check.json',{'checked_at':now(),'passed':True,'items':checks,'shuffle_remap_trials':108,'generation_calls':0,'misassociation_found':False})
    round2=repo/'基础/runs/formal/round2-20261014-133000'
    config=load(round2/'freeze.json')['answer_config']
    reuse_source=repo/'基础/runs/association_repair_pairs/20261014-133536'
    prior_runs=[load(p) for p in reuse_source.glob('run-*.json')]
    items=[];changed=[];reuse=[]
    for path in sorted(round2.glob('task-*.json')):
        task=load(path)
        if task['variant']!='improved':continue
        question=task['question'];original=task['original_passages'];validation=task['selection_validation']
        old_used,old_trace=old.complete_passages(question,original,validation)
        new_used,new_trace=candidate.complete_passages(question,original,validation)
        assert old_used==task['used_passages']
        seed=validation['selected_ids'][0]
        possible=[r for r in new_trace if r['added']]
        assert all(r['target_id']==seed for r in possible),'新增关系无法解释'
        bodies={};serial={};messages={}
        for variant,used in [('old',old_used),('new',new_used)]:
            msgs,conf,rule=generic.answer_request(question,used,config)
            bodies[variant]={'model':conf['model'],'messages':msgs,'stream':False,**conf['parameters']}
            serial[variant]=json.dumps(bodies[variant],ensure_ascii=False)
            messages[variant]=msgs
        assert {k:v for k,v in bodies['old'].items() if k!='messages'}=={k:v for k,v in bodies['new'].items() if k!='messages'}
        assert messages['old'][0]==messages['new'][0]
        differs=serial['old']!=serial['new']
        if differs:changed.append(task['case_id'])
        else:
            previous=next(r for r in prior_runs if r['case_id']==task['case_id'] and r['variant']=='old')
            assert previous['raw_http_request_body']==serial['old']
            reuse.append({'case_id':task['case_id'],'run_id':previous['run_id'],
                'record_path':(reuse_source/('run-'+previous['run_id']+'.json')).relative_to(repo).as_posix(),
                'record_sha256':sha(reuse_source/('run-'+previous['run_id']+'.json')),
                'actual_serialized_request_exact_match':True,'reuse_for':['old','new'],'new_generation_calls':0})
        items.append({'case_id':task['case_id'],'source_path':path.relative_to(repo).as_posix(),'source_sha256':sha(path),
            'question':question,'original_passages':original,'selection_validation':validation,
            'old_used_passages':old_used,'new_used_passages':new_used,'old_trace':old_trace,'new_trace':new_trace,
            'request_changed':differs,'request_bodies':bodies,'raw_serialized_requests':serial,
            'request_sha256':{v:hashlib.sha256(s.encode()).hexdigest() for v,s in serial.items()},
            'user_message_diff':''.join(difflib.unified_diff(messages['old'][1]['content'].splitlines(keepends=True),messages['new'][1]['content'].splitlines(keepends=True),fromfile='old-user-content',tofile='new-user-content')),
            'misassociation_found':False,'change_explanation':'唯一可靠主声明+完整编号直接补充指称+无明示冲突；类型标签差异不独立决定关系。'})
    write('eight-case-association-recompute.json',{'checked_at':now(),'passed':True,'items':sorted(items,key=lambda r:r['case_id']),'changed_cases':sorted(changed),'generation_calls':0})
    write('reused-results.json',{'checked_at':now(),'items':reuse,'new_generation_calls':0})
    order=[]
    for i,cid in enumerate(sorted(changed)):
        for variant in (['old','new'] if i%2==0 else ['new','old']):
            order.append({'sequence':len(order)+1,'case_id':cid,'variant':variant})
    write('execution-plan.json',{'saved_at':now(),'order':order,'planned_generation_calls':len(order),'generation_limit':16,
        'changed_cases':sorted(changed),'unchanged_cases':[r['case_id'] for r in reuse],
        'prediction':'变化只在关联补页导致的完整原段落输入。可能改善覆盖，不能保证计算、答案形式或最终引用成功。',
        'selection_rule':'严格完整成功优先，其次指定答法正确；同分保留旧方案；误关联单列。',
        'stop':'技术失败或容量/哈希不符保存后停止，不重试质量错误。',
        'evaluation_source':'第二轮既有原文依据及评价口径；生成全部结束后核对。'})
    print('PASS 27 fixed synthetic cases / 108 remaps; changed:',sorted(changed),'reuse:',[r['case_id'] for r in reuse],'planned calls:',len(order))
except Exception as error:
    write('offline-stop.json',{'stopped_at':now(),'error':repr(error),'checks':checks,'generation_calls':0,'limitation':'检查失败后停止，不为评测题改反例标准。'})
    raise
