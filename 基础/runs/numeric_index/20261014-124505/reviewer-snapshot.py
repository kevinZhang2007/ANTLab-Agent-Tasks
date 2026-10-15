"""所有请求结束后评价数值索引候选；模型计划、工具与最终回答分开判读。"""
from pathlib import Path
from datetime import datetime
from decimal import Decimal,InvalidOperation
import json,re,sys

repo=Path(__file__).resolve().parents[2];base=repo/'基础';folder=Path(sys.argv[1])
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
def write(name,value):(folder/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
runtime=read(folder/'runtime.json')
assert runtime['server_stopped'] and runtime.get('all_tasks_finished') and not runtime['stopped_on_technical_failure']
# 公开答案只在全部调用结束后读取，不参与整理、校验、计算或最终请求。
gold={g['id']:g for g in read(base/'data/dev_answers.json')}
basis=read(base/'runs/two_step_linked/20261013-193700/effective-semantic-review.json')
manual=read(folder/'calculation-semantic-assessment.json')
number=r'[-+]?([0-9]+([.][0-9]+)?|[.][0-9]+)([eE][-+]?[0-9]+)?'
def equal_decimal(a,b):
    try:return Decimal(a)==Decimal(b)
    except (InvalidOperation,ValueError):return False
def unique_fields(pairs):
    value={}
    for k,v in pairs:
        if k in value:raise ValueError('duplicate_field')
        value[k]=v
    return value
def judge(task,stage,source,g):
    info=task['stages'].get(stage,{})
    if info.get('run_id'):
        r=read(folder/('run-'+info['run_id']+'.json'))
        content=r['response']['choices'][0]['message'].get('content','')
    else:r={};content=None
    try:parsed=json.loads(content,object_pairs_hook=unique_fields)
    except (ValueError,TypeError):parsed=None
    valid=isinstance(parsed,dict) and set(parsed)=={'answer','citations'} and isinstance(parsed.get('answer'),str) and isinstance(parsed.get('citations'),list) and all(isinstance(x,str) for x in parsed['citations'])
    answer=parsed['answer'] if valid else None;citations=parsed['citations'] if valid else []
    correct=isinstance(answer,str) and answer.strip() in g['aliases'];semantic=correct
    if isinstance(answer,str) and g['task_kind']=='difference':
        correct=bool(re.fullmatch(number,answer) and equal_decimal(answer,g['answer']))
        match=re.fullmatch('('+number+r')\s*秒',answer)
        semantic=correct or bool(match and equal_decimal(match.group(1),g['answer']))
    elif isinstance(answer,str) and g['task_kind']=='percent':
        correct=bool(answer.endswith('%') and re.fullmatch(number,answer[:-1]) and equal_decimal(answer[:-1],g['answer'].rstrip('%')));semantic=correct
    elif isinstance(answer,str) and g['task_kind']=='insufficient':semantic=correct or answer in ['服务端GPU型号未知','未提及具体型号']
    ids={p['id'] for p in task['used_passages']};required={p['id'] for p in source['source_basis']}
    coverage=bool(set(citations)&required) if g['task_kind']=='insufficient' else required.issubset(citations)
    exists=valid and all(x in ids for x in citations)
    support=bool(semantic and exists and citations and coverage)
    irrelevant=[x for x in citations if x in ids and x not in required]
    strict=bool(correct and valid and exists and citations and support and not irrelevant)
    return {'case_id':task['case_id'],'variant':stage,'run_id':info.get('run_id'),'executed':bool(info.get('run_id')),'raw_content':content,'answer':answer,'citations':citations,'format_complete':valid,'answer_correct_specified_form':correct,'semantic_consistent':semantic,'citation_ids_exist':exists,'necessary_evidence_covered':coverage,'evidence_supports_actual_answer':support,'irrelevant_citations':irrelevant,'strict_complete_success':strict,'answer_http_seconds':r.get('elapsed_seconds'),'usage':r.get('usage'),'finish_reason':r.get('response',{}).get('choices',[{}])[0].get('finish_reason'),'source_basis':source['source_basis'],'public_answer_reason':g['reason'],'candidate_not_executed_reason':info.get('status'),'evaluation_source':'Codex辅助公开开发答案与原文复核，尚未经本人逐项确认'}

rows=[];intermediate=[];pairs=[]
for cid in ['D01','D02','D03','D04']:
    task=read(folder/('task-'+cid+'.json'));source=next(x for x in basis if x['case_id']==cid and x['variant']=='linked_answer');g=gold[cid]
    pair=[judge(task,stage,source,g) for stage in ['control','candidate_answer']];rows.extend(pair)
    assessment=next(x for x in manual['items'] if x['case_id']==cid)
    intermediate.append({'case_id':cid,'raw_calculation_plan':task['stages']['plan']['raw_content'],'validation':task['validation'],'scope_and_operation_review':assessment,'candidate_end_to_end_seconds':task['candidate_end_to_end_seconds'],'plan_http_seconds':task['stages']['plan']['http_seconds'],'validation_seconds':task['validation_seconds'],'source_basis':source['source_basis']})
    pairs.append({'case_id':cid,'control':pair[0],'candidate':pair[1],'candidate_end_to_end_seconds':task['candidate_end_to_end_seconds'],'failure_reason':task['validation']['errors']})
    write('review-'+cid+'.json',{'pair':pairs[-1],'intermediate':intermediate[-1]})
table=[]
for variant in ['control','candidate_answer']:
    group=[r for r in rows if r['variant']==variant]
    table.append({'variant':variant,'denominator':4,'executed_final_answers':sum(r['executed'] for r in group),'format_complete':sum(r['format_complete'] for r in group),'specified_answer_correct':sum(r['answer_correct_specified_form'] for r in group),'semantic_consistent':sum(r['semantic_consistent'] for r in group),'citation_support':sum(r['evidence_supports_actual_answer'] for r in group),'irrelevant_results':sum(bool(r['irrelevant_citations']) for r in group),'strict_complete_success':sum(r['strict_complete_success'] for r in group)})
run_records=[read(p) for p in folder.glob('run-*.json')]
assert len(run_records)==runtime['generation_attempts'] and len({r['run_id'] for r in run_records})==len(run_records)
old,new=table
quality_old=(old['strict_complete_success'],old['specified_answer_correct']);quality_new=(new['strict_complete_success'],new['specified_answer_correct'])
summary={'reviewed_at':datetime.now().astimezone().isoformat(),'table':table,'generation_calls':len(run_records),'cumulative_generation_calls':178+len(run_records),'counts_by_stage':{s:sum(r['stage']==s for r in run_records) for s in ['control','plan','candidate_answer']},'intermediate_failures':sum(not x['validation']['valid'] for x in intermediate),'selection_replay_not_rerun':True,'adoption':'新候选优于同步对照，可作为独立开发候选继续审阅，不自动替换生产。' if quality_new>quality_old else '新候选未超过同步对照，保留当前更简单的候选；不追加优化。','cost_limit':'计划256及回答256，额外调用、数字索引和工具一起构成配置变化；不能单独归因于算术工具。','source':'Codex辅助原文复核，尚未经本人逐项确认','truncation_flags':re.findall(r'truncated\s*=\s*(\d+)',(folder/'server-log.txt').read_text(encoding='utf-8'))}
write('semantic-review.json',rows);write('intermediate-review.json',intermediate);write('paired-results.json',pairs);write('summary.json',summary)
print(json.dumps(summary,ensure_ascii=False,indent=2))
for p in pairs:print(json.dumps({'case_id':p['case_id'],'control':p['control']['raw_content'],'candidate':p['candidate']['raw_content'],'errors':p['failure_reason'],'candidate_end_to_end_seconds':p['candidate_end_to_end_seconds']},ensure_ascii=False))
