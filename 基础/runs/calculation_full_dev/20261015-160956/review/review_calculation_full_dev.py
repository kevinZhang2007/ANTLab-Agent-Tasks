"""四道开发题全部结束后独立复核；不读取T题记录。"""
import hashlib, importlib.util, inspect, json, shutil, statistics
from pathlib import Path
from datetime import datetime
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
FOLDER=ROOT/'基础/runs/calculation_full_dev/20261015-160956'
BASE=ROOT/'基础/runs/association_compat_dev/20261015-154928'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now().astimezone().isoformat()
NOTE='Codex辅助原文复核，尚未经本人逐项确认；仅本轮开发题，不是独立泛化成绩。'
def write(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as o:json.dump(v,o,ensure_ascii=False,indent=2);o.write('\n')
def parse(raw):
    try:
        v=json.loads(raw) if isinstance(raw,str) else raw
        good=isinstance(v,dict) and set(v)=={'answer','citations'} and isinstance(v['answer'],str) and isinstance(v['citations'],list) and all(isinstance(i,str) for i in v['citations'])
        return (v if good else {}),good
    except (ValueError,TypeError):return {},False
def positions(v,passages):
    sources={p['id']:p['text'] for p in passages}
    if isinstance(v,dict):
        if all(k in v for k in ['passage_id','start','end','quote']):
            assert v['passage_id'] in sources and sources[v['passage_id']][v['start']:v['end']]==v['quote']
        for x in v.values():positions(x,passages)
    elif isinstance(v,list):
        for x in v:positions(x,passages)
def main():
    execution=load(FOLDER/'execution-summary.json');assert not execution['technical_stop'] and execution['service_stopped'] and execution['completed_main_tasks']==4
    frozen=load(FOLDER/'freeze.json');assert all(sha(ROOT/p)==h for p,h in {**frozen['code_hashes'],**frozen['data_hashes']}.items())
    out=FOLDER/'review';out.mkdir(exist_ok=False)
    # 只复用上轮开发评价函数；不调用其main，也不加载T题依据、响应或汇总。
    workspace=Path(__file__).resolve().parent
    spec=importlib.util.spec_from_file_location('previous_development_evaluator',workspace/'review_integrated_dev_eval.py')
    reviewer=importlib.util.module_from_spec(spec);spec.loader.exec_module(reviewer)
    (out/'development-evaluator.py').write_text(inspect.getsource(reviewer.development_basis)+'\n'+inspect.getsource(reviewer.development_evaluate),encoding='utf-8',newline='\n')
    public=load(ROOT/'基础/data/dev_answers.json');rows=[];association_reviews=[]
    for i in range(1,5):
        task=load(FOLDER/f'task-{i:02d}.json');old=load(BASE/f'task-{i:02d}.json');cid=task['case_id'];assert cid==f'D{i:02d}'
        assert task['question']==old['question'] and task['original_passages']==old['original_passages']
        basis=reviewer.development_basis(task,public)
        evaluate=lambda response:reviewer.development_evaluate(task,response,basis,__import__(__name__))
        raw=evaluate(task['raw_answer']);final=evaluate(task['actual_final_output'])
        old_basis=reviewer.development_basis(old,public)
        old_raw=reviewer.development_evaluate(old,old['raw_answer'],old_basis,__import__(__name__))
        old_final=reviewer.development_evaluate(old,old['actual_final_output'],old_basis,__import__(__name__))
        assert task['selection_is_fresh'] and len(task['stages'])==2
        assert task['raw_response']==task['stages'][-1]['response']
        for stage in task['stages']:
            assert stage['started_at']>frozen['frozen_at'] and stage['actual_http_request_body']['max_tokens']==256
            assert stage['freeze_sha256']==sha(FOLDER/'freeze.json') and all(stage['parameter_checks'].values()) and stage['truncated'] is False
        reference=task['reference_derived_response'];proposal=task['proposed_response']
        positions(task['proof_fact_sources'],task['used_passages']);positions(task['ratio_fact_sources'],task['used_passages']);positions(task['difference_fact_sources'],task['used_passages'])
        ids={p['id'] for p in task['used_passages']}
        if reference is not None:assert reference['answer']==raw['answer'] and set(reference['citations'])<=ids
        if proposal is not None:assert set(proposal['citations'])<=ids
        assert task['actual_final_output']==(proposal if proposal is not None else reference if reference is not None else parse(task['raw_answer'])[0])
        reference_review=evaluate(reference) if reference else None;proposal_review=evaluate(proposal) if proposal else None
        wrong_derivation=bool((reference_review and reference_review['support_actual_answer'] is not True) or (proposal_review and (proposal_review['answer_correct'] is not True or proposal_review['support_actual_answer'] is not True)))
        related={p['id'] for p in basis['related_original_sources']}
        links=[r for r in task['association_trace'] if r['added']]
        association=[]
        for link in links:
            main=next(p for p in task['original_passages'] if p['id']==link['target_id']);supp=next(p for p in task['original_passages'] if p['id']==link['supplement_id'])
            correct=main['id'] in related and supp['id'] in related
            association.append({'main_id':main['id'],'supplement_id':supp['id'],'main_text':main['text'],'supplement_text':supp['text'],
                'independent_provisional_correct':correct,'reason':basis['derivation']+' 补页正文直接指向主记录编号，当前资料无竞争声明或明确范围冲突；缺失范围仍为未知。'})
        row={'reviewed_at':now(),'reviewer_note':NOTE,'case_id':cid,'raw_response':task['raw_response'],'raw_review':raw,
            'reference_derived_response':reference,'proposed_response':proposal,'system_final_response':task['actual_final_output'],
            'system_final_review':final,'output_source':task['actual_final_output_source'],'proof':task['proof_record'],'ratio_proof':task['ratio_proof'],'difference_proposal':task['difference_proposal'],
            'erroneous_derivation':wrong_derivation,'erroneous_association':any(not r['independent_provisional_correct'] for r in association),
            'association_review':association,'stage_run_ids':[s['run_id'] for s in task['stages']],'timing':task['timing_summary'],
            'raw_strict_regression':old_raw['strict_complete_success'] and not raw['strict_complete_success'],
            'system_strict_regression':old_final['strict_complete_success'] and not final['strict_complete_success'],
            'system_strict_improved':not old_final['strict_complete_success'] and final['strict_complete_success'],
            'historical_comparison':'上轮开发4题2/4，历史复用；本轮新定位新回答，未拼接旧回答。',
            'material_policy':'证明事实及派生引用只来自used_passages；全部原始资料仅范围、实体和唯一性审计，不补标准答案。'}
        write(out/f'review-{cid}.json',{'basis':basis,'row':row,'previous_raw_review':old_raw,'previous_final_review':old_final});rows.append(row)
    metrics={}
    for side in ['raw_review','system_final_review']:
        metrics[side]={k:{'numerator':sum(r[side][k] is True for r in rows),'denominator':4,'percent':sum(r[side][k] is True for r in rows)*25} for k in ['answer_correct','strict_complete_success']}
    summary={'reviewed_at':now(),'reviewer_note':NOTE,'denominator':4,'metrics':metrics,
        'erroneous_associations':sum(r['erroneous_association'] for r in rows),'erroneous_derivations':sum(r['erroneous_derivation'] for r in rows),
        'system_regressions':sum(r['system_strict_regression'] for r in rows),'system_improvements':sum(r['system_strict_improved'] for r in rows),
        'previous_system_strict':{'numerator':2,'denominator':4},'only_development_reviewed':True,'this_round_generations':execution['confirmed_generation_calls']}
    write(out/'summary.json',summary);write(out/'effective-reviews.json',{'reviewed_at':now(),'reviewer_note':NOTE,'rows':rows})
    # 全库只提取run ID和usage用于去重计数，不展示或分析T题内容和结果。
    ids=set()
    for p in (ROOT/'基础/runs').rglob('*.json'):
        v=load(p)
        if not isinstance(v,dict):continue
        usage=v.get('usage')
        if not isinstance(usage,dict) and isinstance(v.get('response'),dict):usage=v['response'].get('usage')
        if v.get('run_id') and isinstance(usage,dict) and usage.get('completion_tokens',0)>0:ids.add(v['run_id'])
    assert len(ids)==404+execution['confirmed_generation_calls']
    write(FOLDER/'generation-count.json',{'checked_at':now(),'previous':404,'this_round':execution['confirmed_generation_calls'],'cumulative_unique':len(ids),'run_ids':sorted(ids),'no_T_semantic_analysis':True})
    protected=load(FOLDER/'protected-hashes.json');changed=[p for p,h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h];assert not changed
    shutil.copyfile(Path(__file__),out/Path(__file__).name)
    write(FOLDER/'final-audit.json',{'checked_at':now(),'protected_count':len(protected),'changed':changed,'service_stopped':True,
        'only_development_generated':True,'this_round':execution['confirmed_generation_calls'],'cumulative':len(ids),
        'new_files':sorted(p.relative_to(ROOT).as_posix() for p in FOLDER.rglob('*') if p.is_file())})
    print(json.dumps({'rows':[{'case_id':r['case_id'],'raw':{'answer':r['raw_review']['answer'],'citations':r['raw_review']['citations']},
        'reference_derived':r['reference_derived_response'],'calculation_proposed':r['proposed_response'],'final':r['system_final_response'],
        'raw_correct':r['raw_review']['answer_correct'],'final_correct':r['system_final_review']['answer_correct'],
        'raw_strict':r['raw_review']['strict_complete_success'],'final_strict':r['system_final_review']['strict_complete_success'],
        'seconds':round(r['timing']['end_to_end_seconds'],3),'proof_reason':r['proof'].get('reason'),'ratio_reason':r['ratio_proof'].get('reason'),'difference_reason':r['difference_proposal'].get('reason')} for r in rows],
        'summary':summary,'cumulative':len(ids)},ensure_ascii=False))

if __name__=='__main__':main()
