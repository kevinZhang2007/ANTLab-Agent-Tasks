"""8次回答完成后复用既有开发评价，另核对示例污染与退步；无生成。"""
from pathlib import Path
from datetime import datetime
import ast,copy,hashlib,importlib.util,json,re,shutil,sys
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
F=ROOT/'基础/runs/few_shot/20261015-212723';D=F/'round1'
P=ROOT/'基础/runs/final_five/20261015-210223/round5'
L=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
N=lambda:datetime.now().astimezone().isoformat()
def W(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2)
def main():
    summary=L(D/'execution-summary.json');assert not summary['technical_stop'] and summary['service_stopped']
    assert summary['confirmed_generation_calls']==8
    freeze=L(D/'freeze.json');assert all(H(ROOT/p)==h for p,h in {**freeze['code_hashes'],**freeze['data_hashes']}.items())
    assert L(D/'protected-file-audit.json')['all_unchanged']
    spec=importlib.util.spec_from_file_location('saved_development_evaluator',F/'development_evaluator.py');e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
    public=L(ROOT/'基础/data/dev_answers.json')
    markers=['绮叶项目','苇舟项目','山葵项目','箱桔','箱梨','清单玉','蓝标率','蓝标徽章','封签','防潮']
    examples=L(F/'examples.json')['examples'];example_ids=[p['id'] for item in examples for p in item['passages']]
    numeric=['37.5','48','18']
    rows=[];jobs=L(D/'execution-plan.prepared.json')['items'];ids=set();audits=[]
    for job in jobs:
        task=L(D/f"task-{job['sequence']:02d}.json");original=L(ROOT/job['historical_task'])
        assert task['used_passages']==original['used_passages'] and task['question']==original['question'] and task['original_passages']==original['original_passages']
        assert task['selection_is_fresh'] is False
        stage=task['stages'][-1];assert stage['stage']=='answer'
        actual=L(D/f"run-{stage['run_id']}.json");assert actual==stage
        assert stage['run_id'] not in ids;ids.add(stage['run_id'])
        assert stage['started_at']>freeze['frozen_at'] and stage['freeze_sha256']==H(D/'freeze.json')
        assert stage['actual_http_request_body']['max_tokens']==256 and all(stage['parameter_checks'].values()) and stage['truncated'] is False
        assert stage['messages'][1:]==original['stages'][-1]['messages'][1:]
        assert stage['config']==original['stages'][-1]['config']
        expected=original['stages'][-1]['messages'][0]['content']
        if job['comparison_arm']=='candidate':expected+='\n\n'+L(F/'examples.json')['system_appendix']
        assert stage['messages'][0]['content']==expected
        basis=e.development_basis(task,public);basis['timing']='本轮8次生成结束并停止服务后才读取公开开发答案，仅评价使用。'
        evaluate=lambda v:e.development_evaluate(task,v,basis,e)
        raw=evaluate(task.get('raw_answer'));final=evaluate(task.get('actual_final_output'))
        reference=task.get('reference_derived_response');proposal=task.get('proposed_response')
        wrong=bool(reference and evaluate(reference)['support_actual_answer'] is not True or proposal and (evaluate(proposal)['answer_correct'] is not True or evaluate(proposal)['support_actual_answer'] is not True))
        text=(task.get('raw_answer') or '')+'\n'+json.dumps(task.get('actual_final_output'),ensure_ascii=False)
        current='\n'.join(p['text'] for p in task['used_passages'])
        hits=[m for m in markers+example_ids if m in text and m not in current]
        value,valid=e.parse(task.get('raw_answer'));answer=value.get('answer','')
        if valid and answer.rstrip('%') in numeric:
            n=answer.rstrip('%')
            if not re.search(r'(?<![0-9.])'+re.escape(n)+r'(?![0-9.])',current):hits.append('示例数值:'+answer)
        row={'reviewed_at':N(),'case_id':task['case_id'],'arm':job['comparison_arm'],'main_task_id':task['main_task_id'],'run_id':stage['run_id'],'raw_content':task['raw_answer'],'raw_response':stage['response'],'raw_review':raw,'system_review':final,'actual_final_output':task['actual_final_output'],'output_source':task['actual_final_output_source'],'reference_derived_response':reference,'calculation_proposed_response':proposal,'wrong_derivation':wrong,'contamination_markers':hits,'visible_contamination_detected':bool(hits),'contamination_limit':'只核对可见输出和实际来源；未发现字面污染不能证明没有隐性类比或定义迁移。','basis':basis,'task_path':(D/f"task-{job['sequence']:02d}.json").relative_to(ROOT).as_posix(),'answer_seconds':task['timing_summary']['answer_seconds'],'answer_and_rule_seconds':task['timing_summary']['end_to_end_seconds'],'historical_selection_replay':True,'evaluation_note':'Codex辅助原文复核，尚未经本人逐项确认；回答阶段开发对照，不是端到端验证。'}
        W(D/f"evaluation-{job['sequence']:02d}.json",row);rows.append(row)
        audits.append({'run_id':stage['run_id'],'actual_input_unchanged':True,'only_system_appendix_changed':True,'actual_parameters_unchanged':True,'token_count':stage['input_tokens'],'total_budget':stage['input_tokens']+256,'finish_reason':stage['finish_reason'],'truncated':stage['truncated']})
    metrics={}
    for arm in ['control','candidate']:
        members=[r for r in rows if r['arm']==arm]
        metrics[arm]={'denominator':4,'raw_answer_correct':sum(r['raw_review']['answer_correct'] is True for r in members),'raw_strict':sum(r['raw_review']['strict_complete_success'] is True for r in members),'system_answer_correct':sum(r['system_review']['answer_correct'] is True for r in members),'system_strict':sum(r['system_review']['strict_complete_success'] is True for r in members),'contaminated_cases':[r['case_id'] for r in members if r['visible_contamination_detected']],'wrong_derivations':sum(r['wrong_derivation'] for r in members),'answer_total_seconds':sum(r['answer_seconds'] for r in members)}
    regressions=[]
    for i in range(1,5):
        cid=f'D{i:02d}';old=L(P/f'review-{i:02d}.json');control=next(r for r in rows if r['case_id']==cid and r['arm']=='control');new=next(r for r in rows if r['case_id']==cid and r['arm']=='candidate')
        for label,previous in [('same_round_control',control),('latest_frozen_run',{'raw_review':old['raw'],'system_review':old['final']})]:
            for side in ['raw_review','system_review']:
                for metric in ['answer_correct','strict_complete_success','format_complete','citation_ids_exist','necessary_coverage','support_actual_answer']:
                    if previous[side][metric] is True and new[side][metric] is not True:regressions.append({'case_id':cid,'reference':label,'side':side,'metric':metric,'before':True,'after':new[side][metric]})
    key=lambda x:(x['system_strict'],x['system_answer_correct'])
    improved=key(metrics['candidate'])>key(metrics['control'])
    retained=bool(improved and not regressions and not metrics['candidate']['contaminated_cases'] and not metrics['candidate']['wrong_derivations'])
    decision={'saved_at':N(),'candidate_improved_system_metrics':improved,'keep_as_independent_candidate':retained,'adopted_into_production':False,'selected_arm':'candidate' if retained else 'control','reason':'仅系统指标改善、无污染、无既有成功退步时保留独立候选；同分或否决时保留原方案。','metrics':metrics,'regression_veto':regressions,'public_answer_used_only_after_all_calls':True,'D01_definition_not_supplied_by_examples':True,'next_stage_not_executed':True,'new_generation_calls':8,'previous_cumulative':526,'cumulative':534,'T_generation_calls':0}
    W(F/'selection.json',decision);W(F/'evaluation-summary.json',{'saved_at':N(),'rows':rows,'metrics':metrics,'decision':decision})
    W(F/'actual-request-audit.json',{'checked_at':N(),'passed':True,'rows':audits,'all_inputs_and_order_unchanged':True,'schema_sampling_budget_rules_unchanged':True})
    # 同口径复核累计唯一run ID；历史选择的嵌套原响应不算新生成。
    all_ids=set()
    for path in (ROOT/'基础/runs').rglob('*.json'):
        obj=L(path)
        if not isinstance(obj,dict) or not obj.get('run_id'):continue
        response=obj.get('response');usage=obj.get('usage') or (response.get('usage') if isinstance(response,dict) else {}) or {}
        if usage.get('completion_tokens',0)>0:all_ids.add(obj['run_id'])
    assert len(ids)==8 and len(all_ids)==534
    W(F/'generation-ledger.json',{'checked_at':N(),'baseline':526,'new_count':8,'new_unique_ids':sorted(ids),'cumulative_unique_ids':len(all_ids),'offline_replay_not_counted':True,'service_stopped':summary['service_stopped']})
    shutil.copyfile(Path(__file__),F/'review_few_shot.py')
    files=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':H(p)} for p in F.rglob('*') if p.is_file()]
    W(F/'file-list.json',{'saved_at':N(),'files_excluding_this_list':len(files),'total_including_this_list':len(files)+1,'files':files})
    print(json.dumps(decision,ensure_ascii=False));print(json.dumps([{'id':r['case_id'],'arm':r['arm'],'raw':r['raw_content'],'final':r['actual_final_output'],'raw_answer_correct':r['raw_review']['answer_correct'],'raw_strict':r['raw_review']['strict_complete_success'],'final_answer_correct':r['system_review']['answer_correct'],'final_strict':r['system_review']['strict_complete_success'],'pollution':r['contamination_markers']} for r in rows],ensure_ascii=False))
if __name__=='__main__':main()
