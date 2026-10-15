import ast, hashlib, importlib.util, inspect, json, shutil, sys
from pathlib import Path
from datetime import datetime
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
BASE=ROOT/'基础/runs/association_compat_dev/20261015-154928'
FOLDER=ROOT/'基础/runs/calculation_compat_dev/20261015-160141'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now().astimezone().isoformat()
def write(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as o:json.dump(v,o,ensure_ascii=False,indent=2);o.write('\n')
def parse(raw):
    try:
        v=json.loads(raw) if isinstance(raw,str) else raw
        good=isinstance(v,dict) and set(v)=={'answer','citations'} and isinstance(v['answer'],str) and isinstance(v['citations'],list) and all(isinstance(i,str) for i in v['citations'])
        return (v if good else {}),good
    except (ValueError,TypeError):return {},False
def main():
    gate=load(FOLDER/'regression-summary.json');assert gate['all_passed'] and gate['old_cases_passed']==437 and gate['new_cases_passed']==97
    freeze=load(FOLDER/'freeze.json');assert all(sha(ROOT/p)==v for p,v in freeze['code_hashes'].items())
    shutil.copyfile(Path(__file__).with_name('calculation_replay_entry.py'),FOLDER/'calculation_replay_entry.py')
    shutil.copyfile(Path(__file__),FOLDER/Path(__file__).name)
    for p in FOLDER.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
    sys.path.insert(0,str(ROOT/'基础/tests'));sys.path.insert(0,str(FOLDER))
    import calculation_replay_entry as entry
    assert Path(entry.reference.__file__).resolve()==FOLDER/'general_citation_proof.py'
    # 重放入口也在第一次数据重放前落盘并冻结，保留原规则冻结记录。
    write(FOLDER/'replay-freeze.json',{'frozen_at':now(),'rule_freeze_sha256':sha(FOLDER/'freeze.json'),
        'code_hashes':{p.relative_to(ROOT).as_posix():sha(p) for p in FOLDER.glob('*.py')},
        'generation_calls':0,'mode':'offline_only','inputs':freeze['input_record_hashes'],'sequence':[f'D{i:02d}' for i in range(1,5)]})
    tasks=[];replayed=[]
    for i in range(1,5):
        p=BASE/f'task-{i:02d}.json';assert sha(p)==freeze['input_record_hashes'][p.name]
        task=load(p);assert task['case_id']==f'D{i:02d}'
        result=entry.replay(task);write(FOLDER/f'replay-{task["case_id"]}.json',{'replayed_at':now(),'source_record':p.relative_to(ROOT).as_posix(),'source_sha256':sha(p),'result':result})
        tasks.append(task);replayed.append(result)
    # 四条重放结束后才加载公开开发答案；只复用开发评价函数，不读取T题结果。
    spec=importlib.util.spec_from_file_location('saved_dev_evaluation',Path(__file__).with_name('review_integrated_dev_eval.py'))
    evaluator=importlib.util.module_from_spec(spec);spec.loader.exec_module(evaluator)
    public=load(ROOT/'基础/data/dev_answers.json');out=FOLDER/'review';out.mkdir(exist_ok=False)
    (out/'development-evaluator.py').write_text(inspect.getsource(evaluator.development_basis)+'\n'+inspect.getsource(evaluator.development_evaluate),encoding='utf-8',newline='\n')
    note='Codex辅助原文复核，尚未经本人逐项确认；本轮是离线重放，没有新增模型生成。'
    rows=[]
    for task,result in zip(tasks,replayed):
        cid=task['case_id'];basis=evaluator.development_basis(task,public)
        evaluate=lambda response:evaluator.development_evaluate(task,response,basis,__import__(__name__))
        raw=evaluate(task['raw_answer']);before=evaluate(task['actual_final_output']);after=evaluate(result['actual_final_output'])
        independent='沿用开发原文推导，不用程序proof_established当作评分。'
        if cid=='D03':independent+=' 原文方案甲7.6秒、乙5.8秒，同一批次相同40问题；问乙比甲少，7.6−5.8=1.8秒，只输出数值。'
        if cid=='D01':independent+=' 公开开发答案为80%，原文85有效问题与68完整支持支持其推导；但现有自动规则未能可靠绑定所求核验指标定义，因此仍拒绝，不将公开答案用于补规则。'
        proposed=result['proposed_response'];wrong=proposed is not None and (after['answer_correct'] is not True or after['support_actual_answer'] is not True)
        row={'reviewed_at':now(),'reviewer_note':note,'case_id':cid,'raw_review':raw,'before_system_review':before,'after_system_review':after,
            'raw_response_preserved':task['raw_response']==result['raw_response'],'computed_proposal':proposed,
            'reference_derived_response':result['reference_derived_response'],'actual_final_output':result['actual_final_output'],
            'output_source':result['output_source'],'independent_source_judgment':independent,'erroneous_calculation_or_derivation':wrong,
            'association_unchanged':task['association_trace']==load(BASE/f'task-{task["sequence"]:02d}.json')['association_trace'],
            'refusal':{'reference':result['reference_proof'].get('reason'),'ratio':result['ratio_proof'].get('reason'),'difference':result['difference_proposal'].get('reason')},
            'strict_regression':before['strict_complete_success'] and not after['strict_complete_success']}
        write(out/f'review-{cid}.json',{'basis':basis,'row':row});rows.append(row)
    assert all(r['raw_response_preserved'] and r['association_unchanged'] for r in rows)
    assert all(r['after_system_review']==r['before_system_review'] for r in rows if r['case_id'] in ['D02','D04'])
    metrics={side:{k:{'numerator':sum(r[side][k] is True for r in rows),'denominator':4,'percent':sum(r[side][k] is True for r in rows)*25} for k in ['answer_correct','strict_complete_success']} for side in ['raw_review','before_system_review','after_system_review']}
    summary={'reviewed_at':now(),'reviewer_note':note,'metrics':metrics,'misderivations':sum(r['erroneous_calculation_or_derivation'] for r in rows),
        'misassociations_added':0,'regressions':sum(r['strict_regression'] for r in rows),'D02_D04_unchanged':True,
        'old_regressions':437,'new_regressions':97,'all_regressions_passed':True,'generations':0,'cumulative':404}
    write(out/'summary.json',summary);write(out/'effective-reviews.json',{'reviewed_at':now(),'reviewer_note':note,'rows':rows})
    protected=load(FOLDER/'protected-hashes.json');changed=[p for p,h in protected.items() if not (ROOT/p).exists() or sha(ROOT/p)!=h];assert not changed
    frozen=load(FOLDER/'replay-freeze.json');assert all(sha(ROOT/p)==h for p,h in frozen['code_hashes'].items())
    write(FOLDER/'final-audit.json',{'checked_at':now(),'protected_count':len(protected),'changed':changed,'generation_calls':0,'cumulative':404,
        'service_started':False,'no_T_inputs_or_results_for_rule_adjustments':True,'source_cumulative_reference':str(BASE.relative_to(ROOT)/'generation-count.json'),
        'source_cumulative_file_sha256':sha(BASE/'generation-count.json'),'final_proof_facts_and_citations_final_model_input_only':True,
        'new_files':sorted(p.relative_to(ROOT).as_posix() for p in FOLDER.rglob('*') if p.is_file())})
    print(json.dumps({'rows':[{'case_id':r['case_id'],'raw':r['raw_review']['answer'],'before':r['before_system_review']['answer'],
        'after':r['after_system_review']['answer'],'new_strict':r['after_system_review']['strict_complete_success'],'proposal':r['computed_proposal'],'refusal':r['refusal']} for r in rows],
        'summary':summary},ensure_ascii=False))

if __name__=='__main__':main()
