"""本轮全部生成结束后复用原评价函数；不影响生成流程。"""
from pathlib import Path
from datetime import datetime
import ast, hashlib, importlib.util, json, statistics, sys

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'基础/starter/provider.py').is_file())
FOLDER=Path(__file__).resolve().parent
DEV=ROOT/'基础/runs/repeat_integrated/20261015-171741'
EVAL=DEV
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now().astimezone().isoformat()
NOTE='Codex辅助原文复核，尚未经本人逐项确认；已接触题上的重复运行，非独立盲测、泛化验证或官方成绩。'
def write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as out:json.dump(value,out,ensure_ascii=False,indent=2);out.write('\n')
def get_functions(path,names):
    text=path.read_text(encoding='utf-8-sig');tree=ast.parse(text)
    parts=[ast.get_source_segment(text,node) for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names]
    assert len(parts)==len(names)
    return '\n\n'.join(parts)+'\n'
def positions(value,passages):
    lookup={p['id']:p['text'] for p in passages}
    if isinstance(value,dict):
        if all(k in value for k in ['passage_id','start','end','quote']):
            assert value['passage_id'] in lookup and lookup[value['passage_id']][value['start']:value['end']]==value['quote']
        for v in value.values():positions(v,passages)
    elif isinstance(value,list):
        for v in value:positions(v,passages)
def change(old,new):
    return 'improved' if old is not True and new is True else 'regressed' if old is True and new is not True else 'unchanged'

def main():
    execution=load(FOLDER/'execution-summary.json')
    assert not execution['technical_stop'] and execution['service_stopped'] and execution['completed_main_tasks']==12
    freeze=load(FOLDER/'freeze.json')
    assert all(sha(ROOT/p)==h for p,h in {**freeze['code_hashes'],**freeze['data_hashes']}.items())
    out=FOLDER/'review';out.mkdir(exist_ok=False)
    formal_source=DEV/'review/saved_evaluation_functions.py'
    dev_source=formal_source
    assert sha(formal_source)==load(DEV/'review/evaluation-lineage.json')['copied_functions_sha256']
    # 明确复制既有纯评价函数，消除本轮评价对仓库外临时模块的依赖。
    helper=formal_source.read_text(encoding='utf-8-sig')
    (out/'saved_evaluation_functions.py').write_text(helper,encoding='utf-8',newline='\n')
    spec=importlib.util.spec_from_file_location('saved_evaluation_functions',out/'saved_evaluation_functions.py');evaluator=importlib.util.module_from_spec(spec);spec.loader.exec_module(evaluator)
    write(out/'evaluation-lineage.json',{'saved_at':now(),'note':NOTE,'formal_source':formal_source.relative_to(ROOT).as_posix(),'formal_source_sha256':sha(formal_source),'development_source':'已归档于saved_evaluation_functions.py；函数逐字提取自上轮评价辅助文件','development_source_sha256':sha(dev_source),'copied_functions_sha256':sha(out/'saved_evaluation_functions.py'),'policy_changed':False,'read_only_evaluation_only':True})
    public=load(ROOT/'基础/data/dev_answers.json')
    previous={dataset:{row['case_id']:row for row in load(directory/'review/effective-reviews.json')['rows']} for dataset,directory in [('development',DEV),('evaluation_repeat',EVAL)]}
    rows=[];pairs=[]
    for i in range(1,13):
        task=load(FOLDER/f'task-{i:02d}.json');cid=task['case_id'];dataset=task['dataset'];old=previous[dataset][cid]
        old_task=load(DEV/f'task-{i:02d}.json')
        assert task['question']==old_task['question'] and task['original_passages']==old_task['original_passages']
        if dataset=='development':
            basis=evaluator.development_basis(task,public)
            evaluate=lambda response:evaluator.development_evaluate(task,response,basis,evaluator)
            basis_path='基础/data/dev_answers.json'
        else:
            basis_path=f'基础/runs/formal_review/round1/evidence-{cid}.json';basis=load(ROOT/basis_path)
            assert basis['source_sha256']==freeze['data_hashes']['基础/data/cases.json']
            original={p['id']:p for p in task['original_passages']}
            assert all(e['id'] in original and e['quote'] in original[e['id']]['text'] for e in basis['required_evidence'])
            evaluate=lambda response:evaluator.evaluate(task,response,basis)
        raw=evaluate(task.get('raw_answer',''));final=evaluate(task.get('actual_final_output'))
        assert task['selection_is_fresh']
        for stage in task['stages']:
            assert stage['started_at']>freeze['frozen_at'] and stage['freeze_sha256']==sha(FOLDER/'freeze.json')
            assert stage['actual_http_request_body']['max_tokens']==256 and all(stage['parameter_checks'].values()) and stage['truncated'] is not True
        if task['status']=='completed':assert task['raw_response']==task['stages'][-1]['response']
        for name in ['proof_fact_sources','ratio_fact_sources','difference_fact_sources']:positions(task.get(name,[]),task.get('used_passages',[]))
        reference=task.get('reference_derived_response');proposal=task.get('proposed_response');used={p['id'] for p in task.get('used_passages',[])}
        if reference is not None:assert reference['answer']==raw['answer'] and set(reference['citations'])<=used
        if proposal is not None:assert set(proposal['citations'])<=used
        reference_review=evaluate(reference) if reference is not None else None
        proposal_review=evaluate(proposal) if proposal is not None else None
        parsed,valid=evaluator.parse(task.get('raw_answer',''))
        assert task.get('actual_final_output')==(proposal if proposal is not None else reference if reference is not None else parsed if valid else None)
        row={'reviewed_at':now(),'reviewer_note':NOTE,'case_id':cid,'dataset':dataset,'main_task_id':task['main_task_id'],'raw_review':raw,'system_final_review':final,'raw_response':task.get('raw_response'),'reference_derived_response':reference,'reference_derived_review':reference_review,'calculation_proposed_response':proposal,'calculation_review':proposal_review,'actual_final_output':task.get('actual_final_output'),'output_source':task.get('actual_final_output_source'),'reference_proof':task.get('proof_record'),'ratio_proof':task.get('ratio_proof'),'difference_proposal':task.get('difference_proposal'),'material_scope':task.get('material_scope'),'timing':task.get('timing_summary'),'stage_run_ids':[stage['run_id'] for stage in task['stages']],'basis_path':basis_path,'basis_sha256':sha(ROOT/basis_path),'erroneous_reference_derivation':bool(reference_review and reference_review['support_actual_answer'] is not True),'erroneous_calculation_derivation':bool(proposal_review and (proposal_review['answer_correct'] is not True or proposal_review['support_actual_answer'] is not True))}
        pair={'case_id':cid,'dataset':dataset,'previous_raw_response':{'answer':old['raw_review']['answer'],'citations':old['raw_review']['citations']},'previous_final_response':{'answer':old['system_final_review']['answer'],'citations':old['system_final_review']['citations']},'current_raw_response':{'answer':raw['answer'],'citations':raw['citations']},'current_final_response':{'answer':final['answer'],'citations':final['citations']},'raw_response_changed':raw['answer']!=old['raw_review']['answer'] or raw['citations']!=old['raw_review']['citations'],'system_response_changed':final['answer']!=old['system_final_review']['answer'] or final['citations']!=old['system_final_review']['citations'],'raw_answer_change':change(old['raw_review']['answer_correct'],raw['answer_correct']),'system_answer_change':change(old['system_final_review']['answer_correct'],final['answer_correct']),'raw_strict_change':change(old['raw_review']['strict_complete_success'],raw['strict_complete_success']),'system_strict_change':change(old['system_final_review']['strict_complete_success'],final['strict_complete_success']),'previous_seconds':old['timing']['end_to_end_seconds'],'current_seconds':task['timing_summary']['end_to_end_seconds'],'ambiguity':raw.get('ambiguity')}
        write(out/f'review-{cid}.json',{'basis':basis,'row':row,'previous_comparison':pair});rows.append(row);pairs.append(pair)
    metrics={}
    for dataset in ['development','evaluation_repeat']:
        members=[row for row in rows if row['dataset']==dataset];n=len(members)
        metrics[dataset]={'denominator':n,'metrics':{side:{name:{'numerator':sum(row[side][name] is True for row in members),'denominator':n,'percent':100*sum(row[side][name] is True for row in members)/n,'ambiguous':sum(row[side][name]=='ambiguous' for row in members),'not_checked':sum(row[side][name]=='not_checked' for row in members)} for name in ['answer_correct','strict_complete_success']} for side in ['raw_review','system_final_review']},'total_e2e_seconds':sum(row['timing']['end_to_end_seconds'] for row in members),'erroneous_derivations':sum(row['erroneous_reference_derivation'] or row['erroneous_calculation_derivation'] for row in members),'raw_regressions':sum(pair['raw_strict_change']=='regressed' for pair in pairs if pair['dataset']==dataset),'system_regressions':sum(pair['system_strict_change']=='regressed' for pair in pairs if pair['dataset']==dataset)}
    ids=set()
    for p in (ROOT/'基础/runs').rglob('*.json'):
        data=load(p)
        if not isinstance(data,dict):continue
        usage=data.get('usage') or (data.get('response',{}).get('usage') if isinstance(data.get('response'),dict) else {}) or {}
        if data.get('run_id') and usage.get('completion_tokens',0)>0:ids.add(data['run_id'])
    assert len(ids)==454+execution['confirmed_generation_calls']
    write(out/'effective-reviews.json',{'reviewed_at':now(),'reviewer_note':NOTE,'rows':rows})
    write(out/'summary.json',{'reviewed_at':now(),'reviewer_note':NOTE,'datasets':metrics,'generation_calls':execution['confirmed_generation_calls'],'cumulative_generations':len(ids),'results_export_not_changed':True})
    write(out/'previous-run-comparison.json',{'reviewed_at':now(),'previous_development':DEV.relative_to(ROOT).as_posix(),'previous_evaluation':EVAL.relative_to(ROOT).as_posix(),'same_candidate':True,'no_history_output_reuse':True,'rows':pairs})
    write(FOLDER/'generation-count.json',{'checked_at':now(),'previous':454,'this_round':execution['confirmed_generation_calls'],'unique_generations':len(ids),'run_ids':sorted(ids)})
    protected=load(FOLDER/'protected-hashes.json');changed=[p for p,h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h];assert not changed
    write(FOLDER/'final-audit.json',{'checked_at':now(),'protected_count':len(protected),'changed':changed,'service_stopped':execution['service_stopped'],'results_exports_unchanged':True,'generation_calls':execution['confirmed_generation_calls'],'cumulative_generations':len(ids),'all_labels_auxiliary_provisional':True})
    (out/'review_repeat_integrated.py').write_text(Path(__file__).read_text(encoding='utf-8-sig'),encoding='utf-8',newline='\n')
    print(json.dumps({'datasets':metrics,'cumulative':len(ids),'rows':[{'case_id':row['case_id'],'raw':row['raw_review']['answer'],'raw_citations':row['raw_review']['citations'],'final':row['system_final_review']['answer'],'final_citations':row['system_final_review']['citations'],'raw_strict':row['raw_review']['strict_complete_success'],'final_strict':row['system_final_review']['strict_complete_success'],'seconds':round(row['timing']['end_to_end_seconds'],3),'source':row['output_source']} for row in rows],'pairs':pairs},ensure_ascii=False))

if __name__=='__main__':main()
