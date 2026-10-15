"""自造机制正反例及八题关联重算；不调用模型，不读取答案。"""
import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import random
import sys
import association_repair_candidate as candidate
import two_step_linked_candidate as old

repo=Path(__file__).resolve().parents[2]
folder=Path(sys.argv[1]).resolve()
now=lambda:datetime.now().astimezone().isoformat()
def write(name,value):
    path=folder/name;assert not path.exists()
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
samples=[
 ('批次直接指称',['甲项目R2版本批次AB12记录。','批次AB12的复核补页：数据。'],[0,1]),
 ('非题目词汇的表声明',['甲项目R2版本预算审计表ZX19保存支出。','预算审计表ZX19的补充说明：规则。'],[0,1]),
 ('通用清单声明',['甲项目R2版本巡检清单LM27列明检查项。','巡检清单LM27的续页：附数据。'],[0,1]),
 ('通用集合声明',['甲项目R2版本训练数据集MN31收录样本。','训练数据集MN31的补充记录：定义。'],[0,1]),
 ('通用评审声明',['甲项目R2版本例会评审HK11给出检查结果。','例会评审HK11的复核补页：规则。'],[0,1]),
 ('通用组声明',['甲项目R2版本远程组NM22执行请求。','远程组NM22的补充页：计数。'],[0,1]),
 ('跨类型有明示桥接',['甲项目R2版本核验表AB12记录计数。','批次AB12的复核补页：对应核验表AB12，补充其规则。'],[0,1]),
 ('跨类型仅同号',['甲项目R2版本核验表AB12记录计数。','批次AB12的复核补页：计数。'],[0]),
 ('同类型不同名称',['甲项目R2版本核验表AB12记录计数。','资源表AB12的复核补页：规则。'],[0]),
 ('任意设备英文编号',['设备AB12开机。','批次AB12的复核补页。'],[0]),
 ('对象提及无声明谓词',['这里提到预算表AB12，但不说明其内容。','预算表AB12的补页。'],[0]),
 ('编号跨项目复用',['甲项目R2版本批次AB12记录。','乙项目R2版本批次AB12记录。','批次AB12的补页。'],[0]),
 ('同范围多个主段',['甲项目R2版本批次AB12记录一。','甲项目R2版本批次AB12记录二。','批次AB12的补页。'],[0]),
 ('版本冲突',['甲项目R2版本批次AB12记录。','甲项目R3版本批次AB12的补页。'],[0]),
 ('项目冲突',['甲项目R2版本批次AB12记录。','乙项目R2版本批次AB12的补页。'],[0]),
 ('日期冲突',['2027-01批次AB12记录。','2027-02批次AB12的补页。'],[0]),
 ('多个版本',['甲项目R2版本批次AB12记录，并引用R3版本。','批次AB12的补页。'],[0]),
 ('主段多个业务对象',['核验表AB12记录数据，巡检清单CD34列出规则。','核验表AB12的补页。'],[0]),
 ('补页多个指称',['批次AB12记录。','批次AB12的补页和批次CD34的补页。'],[0]),
 ('缺失范围保持未知',['甲项目R2版本2027-01批次AB12记录。','批次AB12的补页。'],[0,1]),
 ('有编号无明确补充指称',['批次AB12记录。','补页：仅提及批次AB12。'],[0]),
 ('无可靠关联',['记录没有编号。','另页补充说明：一些数据。'],[0]),
 ('禁止多跳',['批次AB12记录。','批次AB12的补页，另提到CD34。','批次CD34的补页。'],[0,1]),
]
write('synthetic-fixtures-before-check.json',{'saved_at':now(),'samples':samples,'generation_calls':0,'independent_evaluation_set':False})
snapshot=folder/'code-snapshot';snapshot.mkdir()
for p in [Path(candidate.__file__),Path(__file__)]:
    (snapshot/p.name).write_bytes(p.read_bytes())
write('offline-code-hashes.json',{p.relative_to(repo).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(candidate.__file__),Path(__file__)]})
checks=[]
try:
    for name,texts,expected in samples:
        rows=[{'id':'item-'+str(i),'source':'same/'+str(i),'text':text} for i,text in enumerate(texts)]
        before=copy.deepcopy(rows);validation={'valid':True,'selected_ids':['item-0']}
        result,trace=candidate.complete_passages('检查资料',rows,validation)
        actual=[p['id'] for p in result];expected_ids=['item-'+str(i) for i in expected]
        record={'sample':name,'input':rows,'trace':trace,'actual_ids':actual,'expected_ids':expected_ids,'passed':actual==expected_ids}
        checks.append(record)
        assert actual==expected_ids,name+': '+str(actual)
        assert rows==before and all(p in before for p in result)
        wanted={(p['source'],p['text']) for p in result}
        for seed in range(4):
            shuffled=copy.deepcopy(rows);random.Random(seed).shuffle(shuffled)
            mapping={p['id']:'renamed-'+str(seed)+'-'+str(i) for i,p in enumerate(shuffled)}
            remapped=[dict(p,id=mapping[p['id']]) for p in shuffled]
            selected={'valid':True,'selected_ids':[mapping['item-0']]}
            other,_=candidate.complete_passages('检查资料',remapped,selected)
            assert {(p['source'],p['text']) for p in other}==wanted
            assert other==[p for p in remapped if p['id'] in {q['id'] for q in other}]
        for p in rows:
            for mention in candidate.describe(p['text'])['mentions']:
                assert p['text'][mention['code_start']:mention['code_end']]==mention['code']
                s=mention['statement'];assert p['text'][s['start']:s['end']]==s['text']
        if name=='缺失范围保持未知':assert trace[0]['unknown_scope_fields']==['project','version','date']
    assert candidate.complete_passages('问题',[],{'valid':True,'selected_ids':[]})==([],[])
    empty,_=candidate.complete_passages('问题',rows,{'valid':True,'selected_ids':[]});assert empty==[]
    for raw in ['bad json','{"selected_ids":["unknown"]}','{"selected_ids":["item-0","item-0"]}']:
        invalid=candidate.selection.validate_selection(raw,rows)
        try:candidate.complete_passages('问题',rows,invalid)
        except ValueError:pass
        else:raise AssertionError('非法选择被修补')
    write('offline-check.json',{'checked_at':now(),'passed':True,'generation_calls':0,'items':checks,'shuffle_remap_trials':92,'empty_and_invalid_passed':True})
    rerun=[]
    original=repo/'基础/runs/formal/round2-20261014-133000'
    for path in sorted(original.glob('task-*.json')):
        task=json.loads(path.read_text(encoding='utf-8'))
        if task['variant']!='improved':continue
        old_used,old_trace=old.complete_passages(task['question'],task['original_passages'],task['selection_validation'])
        new_used,new_trace=candidate.complete_passages(task['question'],task['original_passages'],task['selection_validation'])
        assert old_used==task['used_passages'],'旧关联重算不一致'
        assert new_used==old_used,'本轮出现未预期关联变化，停止'
        rerun.append({'case_id':task['case_id'],'source_path':path.relative_to(repo).as_posix(),
            'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'question':task['question'],
            'original_passages':task['original_passages'],'selection_validation':task['selection_validation'],
            'old_used_passages':old_used,'new_used_passages':new_used,'old_trace':old_trace,'new_trace':new_trace,
            'extracted_contexts':[{'id':p['id'],**candidate.describe(p['text'])} for p in task['original_passages']],
            'change_explained':'声明提取扩大；跨类型无明示桥接仍拒绝。T03同类型批次关系保留。','misassociation_found':False})
    write('eight-case-association-recompute.json',{'checked_at':now(),'passed':True,'items':sorted(rerun,key=lambda r:r['case_id']),'generation_calls':0})
    print('PASS 23 synthetic samples / 92 shuffle-remaps; 8 recomputations; no new association or model call')
except Exception as error:
    write('offline-stop.json',{'stopped_at':now(),'error':repr(error),'checks_completed':checks,'generation_calls':0})
    raise
