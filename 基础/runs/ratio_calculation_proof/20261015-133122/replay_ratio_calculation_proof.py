import copy,hashlib,importlib.util,json,shutil,sys,time
from pathlib import Path
from datetime import datetime
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
FOLDER=ROOT/'基础/runs/ratio_calculation_proof/20261015-133122'
SOURCE=ROOT/'基础/runs/general_proof_full_r0/20261015-131742'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now().astimezone().isoformat()
def write(path,v):
    with path.open('x',encoding='utf-8',newline='\n') as out:json.dump(v,out,ensure_ascii=False,indent=2);out.write('\n')
def module(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def positions(value):
    result=[]
    if isinstance(value,dict):
        if all(k in value for k in ['passage_id','start','end','quote']):result.append(value)
        for item in value.values():result+=positions(item)
    elif isinstance(value,list):
        for item in value:result+=positions(item)
    return result

def main():
    frozen=load(FOLDER/'freeze.json')
    assert all(sha(ROOT/p)==h for p,h in {**frozen['code_hashes'],**frozen['data_hashes'],**frozen['source_task_hashes']}.items())
    assert not list(FOLDER.glob('replay-*.json'))
    sys.path.insert(0,str(ROOT/'基础/tests'));sys.path.insert(0,str(FOLDER))
    import ratio_calculation_proof as candidate
    import offline_gate
    def replay():
        rows=[]
        for index in range(1,9):
            task=load(SOURCE/f'task-{index:02d}.json')
            begin=time.perf_counter();proof=candidate.propose(task['question'],task['used_passages'],task['raw_answer'],task['original_passages']);elapsed=time.perf_counter()-begin
            proposed=proof['proposed_response'];raw=json.loads(task['raw_answer'])
            model={p['id']:p for p in task['used_passages']}
            extra=[copy.deepcopy(p) for p in task['original_passages'] if p['id'] not in model]
            facts=positions({k:proof[k] for k in ['definition','denominator','category_counts','statistical_scope','category_assignment','numerator'] if k in proof})
            assert all(e['passage_id'] in model and model[e['passage_id']]['text'][e['start']:e['end']]==e['quote'] for e in facts)
            if proposed is not None:assert set(proposed['citations'])<=model.keys() and proof['answer_changed']==(proposed['answer']!=raw['answer'])
            row={'replayed_at':now(),'case_id':task['case_id'],'source_path':(SOURCE/f'task-{index:02d}.json').relative_to(ROOT).as_posix(),
                'source_sha256':sha(SOURCE/f'task-{index:02d}.json'),'freeze_sha256':sha(FOLDER/'freeze.json'),'run_kind':'offline_ratio_proposal_not_model_rerun',
                'question':task['question'],'raw_response':task['raw_response'],'raw_content':task['raw_answer'],'original_answer_citations':raw,
                'existing_reference_proof':task['proof_record'],'existing_derived_response':task['derived_response'],'existing_final_output':task['actual_final_output'],
                'ratio_proof':proof,'proposed_response':proposed,'answer_changed_in_proposal':proof['answer_changed'],
                'candidate_composed_response':copy.deepcopy(proposed if proposed is not None else task['actual_final_output']),
                'proposal_kind':'local_rule_calculated_new_answer_not_original_model_response','not_automatically_adopted':True,
                'material_scope':{'model_final_input_passages':task['used_passages'],'audit_only_original_visible_passages':extra,
                    'model_final_input_ids':list(model),'audit_only_ids':[p['id'] for p in extra],
                    'audit_only_ids_consulted': [p['id'] for p in extra] if proof['applicable'] else [],
                    'policy':'计数/分类/分母事实与引用只来自最终回答模型输入；其余原始可见资料仅供范围、实体、唯一性审计，不能说是最终模型输入。'},
                'fact_sources_checked_against_final_model_input':facts,'local_rule_seconds':elapsed,'generation_calls':0}
            assert row['replayed_at']>frozen['frozen_at']
            write(FOLDER/f'replay-{index:02d}.json',row);rows.append((task,row))
        return rows
    results=offline_gate.after_offline_success(lambda:load(FOLDER/'offline-gate.json'),replay)
    # 全8条处理完之后读取旧原文依据评价；这些依据不会进入比例证明。
    review_path=ROOT/'基础/runs/proof_full_r0_repeat/20261015-124627/review/review_proof_full_repeat.py'
    reviewer=module(review_path,'existing_original_text_evaluation')
    reviews=[]
    for task,row in results:
        cid=row['case_id'];basis_path=ROOT/f'基础/runs/formal_review/round1/evidence-{cid}.json';basis=load(basis_path)
        original={p['id']:p for p in task['original_passages']}
        assert basis['source_sha256']==frozen['data_hashes']['基础/data/cases.json']
        assert all(e['quote'] in original[e['id']]['text'] for e in basis['required_evidence'])
        raw=reviewer.evaluate(task,task['raw_answer'],basis)
        existing=reviewer.evaluate(task,task['actual_final_output'],basis)
        combined=reviewer.evaluate(task,row['candidate_composed_response'],basis)
        proposed=row['proposed_response'];proof=row['ratio_proof']
        review={'reviewed_at':now(),'reviewer_note':'Codex辅助原文复核，尚未经本人逐项确认。非官方成绩；无新模型生成。',
            'case_id':cid,'applicable':proof['applicable'],'proposed':proposed is not None,'refused':proof['applicable'] and proposed is None,
            'reason':proof.get('reason'),'metric':proof.get('requested_metric'),'raw_review':raw,'existing_system_review':existing,
            'candidate_composed_review':combined,'erroneous_proposal':proposed is not None and (combined['answer_correct'] is not True or combined['support_actual_answer'] is not True),
            'answer_changed':row['answer_changed_in_proposal'],'basis_path':basis_path.relative_to(ROOT).as_posix(),'basis_sha256':sha(basis_path),
            'proof_is_not_automatic_semantic_score':True,'original_text_assessment':basis['derivation'],
            'source_evidence':combined['source_evidence'],'material_scope':row['material_scope']}
        write(FOLDER/f'review-{cid}.json',{'basis':basis,'review':review});reviews.append(review)
    def metric(side,key):
        return {'numerator':sum(r[side][key] is True for r in reviews),'denominator':8,'percent':sum(r[side][key] is True for r in reviews)*12.5,
            'ambiguous':sum(r[side][key]=='ambiguous' for r in reviews)}
    counts={'applicable':sum(r['applicable'] for r in reviews),'not_applicable':sum(not r['applicable'] for r in reviews),
        'proposed':sum(r['proposed'] for r in reviews),'refused_when_applicable':sum(r['refused'] for r in reviews),
        'erroneous_proposal':sum(r['erroneous_proposal'] for r in reviews),'denominator':8}
    rows=[]
    for task,row in results:
        proof=row['ratio_proof']
        rows.append({'case_id':row['case_id'],'requested_metric':proof.get('requested_metric'),'status':proof['status'],'reason':proof.get('reason'),
            'numerator':proof.get('numerator'),'denominator':proof.get('denominator'),'category_definition':proof.get('definition'),
            'category_assignment':proof.get('category_assignment'),'statistical_scope':proof.get('statistical_scope'),
            'expression':proof.get('expression'),'rounding':proof.get('rounding'),'old_answer':row['original_answer_citations']['answer'],
            'proposed_response':row['proposed_response'],'answer_changed':row['answer_changed_in_proposal']})
    summary={'reviewed_at':now(),'reviewer_note':reviews[0]['reviewer_note'],'counts':counts,'rows':rows,'generation_calls':0,
        'model_raw_answer_correct':metric('raw_review','answer_correct'),'existing_system_strict':metric('existing_system_review','strict_complete_success'),
        'offline_tool_candidate_answer_correct':metric('candidate_composed_review','answer_correct'),
        'offline_tool_candidate_strict':metric('candidate_composed_review','strict_complete_success'),
        'candidate_is_not_model_accuracy_or_a_new_full_model_run':True}
    write(FOLDER/'summary.json',summary)
    generated={}
    for p in (ROOT/'基础/runs').rglob('*.json'):
        v=load(p)
        if not isinstance(v,dict):continue
        usage=v.get('usage')
        if not isinstance(usage,dict) and isinstance(v.get('response'),dict):usage=v['response'].get('usage')
        if v.get('run_id') and isinstance(usage,dict) and usage.get('completion_tokens',0)>0:
            generated.setdefault(v['run_id'],[]).append(p.relative_to(ROOT).as_posix())
    assert len(generated)==372
    write(FOLDER/'generation-count.json',{'checked_at':now(),'new_generations':0,'unique_generated_run_ids':len(generated),'sources':generated})
    protected=load(FOLDER/'protected-hashes.json');changed=[p for p,h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
    assert not changed
    assert all(sha(ROOT/p)==h for p,h in frozen['code_hashes'].items())
    shutil.copyfile(Path(__file__),FOLDER/Path(__file__).name)
    write(FOLDER/'final-audit.json',{'checked_at':now(),'protected_files':len(protected),'changed':changed,'frozen_before_all_eight_replays':True,
        'raw_responses_and_existing_proofs_and_derived_outputs_preserved':True,'new_answers_only_in_separate_proposed_response':True,
        'all_new_fact_and_citation_sources_within_final_model_input':True,'models_loaded':False,'services_started':False,
        'new_generation_calls':0,'cumulative':372,'evaluation_auxiliary_not_personally_confirmed':True})
    print(json.dumps({'counts':counts,'rows':[{'case_id':r['case_id'],'metric':r['requested_metric'],'status':r['status'],
        'expression':r['expression'],'old':r['old_answer'],'proposed':r['proposed_response'],'reason':r['reason']} for r in rows],
        'candidate_answer':summary['offline_tool_candidate_answer_correct'],'candidate_strict':summary['offline_tool_candidate_strict'],'cumulative':372},ensure_ascii=False))

if __name__=='__main__':main()
