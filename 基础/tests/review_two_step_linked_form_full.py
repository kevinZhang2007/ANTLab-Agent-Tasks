"""全部完整流程结束后评价；公开答案只用于判读，不改写响应。"""
from pathlib import Path
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json,re,hashlib,sys
folder=Path(sys.argv[1]);repo=Path(__file__).resolve().parents[2];base=repo/'基础'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
runtime=read(folder/'runtime.json');assert runtime['server_stopped'] and runtime.get('all_tasks_finished') and not runtime['stopped_on_technical_failure']
# 到这里才读取公开答案；本文件不参与生成、Schema识别或原文选择。
gold={g['id']:g for g in read(base/'data/dev_answers.json')}
basis=read(base/'runs/two_step_linked/20261013-193700/effective-semantic-review.json')
number=r'[-+]?([0-9]+([.][0-9]+)?|[.][0-9]+)([eE][-+]?[0-9]+)?'
def equal_decimal(a,b):
    try:return Decimal(a)==Decimal(b)
    except (InvalidOperation,ValueError):return False
def parse_pairs(pairs):
    value={}
    for k,v in pairs:
        if k in value:raise ValueError('duplicate_field')
        value[k]=v
    return value
rows=[]
for item in read(folder/'result-index.json'):
    r=read(folder/('run-'+item['run_id']+'.json'));g=gold[r['case_id']]
    task=read(folder/('task-'+r['case_id']+'.json'))
    source=next(x for x in basis if x['case_id']==r['case_id'] and x['variant']=='linked_answer')
    content=r['response']['choices'][0]['message'].get('content','')
    try:parsed=json.loads(content,object_pairs_hook=parse_pairs)
    except (ValueError,TypeError):parsed=None
    valid=isinstance(parsed,dict) and set(parsed)=={'answer','citations'} and isinstance(parsed.get('answer'),str) and isinstance(parsed.get('citations'),list) and all(isinstance(x,str) for x in parsed['citations'])
    answer=parsed['answer'] if valid else None;citations=parsed['citations'] if valid else []
    correct=isinstance(answer,str) and answer.strip() in g['aliases'];semantic=correct
    if isinstance(answer,str) and g['task_kind']=='difference':
        correct=bool(re.fullmatch(number,answer) and equal_decimal(answer,g['answer']))
        with_unit=re.fullmatch('('+number+r')\s*秒',answer)
        semantic=correct or bool(with_unit and equal_decimal(with_unit.group(1),g['answer']))
    elif isinstance(answer,str) and g['task_kind']=='percent':
        correct=bool(answer.endswith('%') and re.fullmatch(number,answer[:-1]) and equal_decimal(answer[:-1],g['answer'].rstrip('%')))
        semantic=correct
    elif isinstance(answer,str) and g['task_kind']=='insufficient':
        semantic=correct or answer in ['服务端GPU型号未知','未提及具体型号']
    used=r['used_passages'];ids={p['id'] for p in used};required={p['id'] for p in source['source_basis']}
    coverage=(bool(set(citations)&required) if g['task_kind']=='insufficient' else required.issubset(citations))
    exists=valid and all(x in ids for x in citations);nonempty=bool(citations)
    support=bool(semantic and exists and nonempty and coverage)
    irrelevant=[x for x in citations if x in ids and x not in required]
    strict=bool(correct and valid and exists and nonempty and support and not irrelevant)
    reason=[]
    if not valid:reason.append('JSON字段或类型不完整')
    if not correct:reason.append('指定答法或答案值不合要求')
    if semantic and not correct:reason.append('语义一致但附带单位/其他形式不符合题目要求')
    if not coverage:reason.append('引用未覆盖必要依据')
    if not support:reason.append('引用集合未支持实际answer')
    if irrelevant:reason.append('含无关/范围冲突引用')
    rows.append({'case_id':r['case_id'],'variant':item['variant'],'run_id':r['run_id'],'raw_content':content,'answer':answer,'citations':citations,'format_complete':valid,'answer_correct_specified_form':correct,'semantic_consistent':semantic,'citation_ids_exist':exists,'citations_nonempty':nonempty,'necessary_evidence_covered':coverage,'evidence_supports_actual_answer':support,'irrelevant_citations':irrelevant,'strict_complete_success':strict,'client_answer_seconds':r['elapsed_seconds'],'selection_http_seconds':task['selection_http_seconds'],'end_to_end_seconds':task['end_to_end_seconds'],'selected_ids':task['selection_validation']['selected_ids'],'added_ids':task['added_ids'],'association_trace':task['association_trace'],'input_necessary_evidence_covered':(bool(ids & required) if g['task_kind']=='insufficient' else required.issubset(ids)),'usage':r.get('usage'),'finish_reason':r['response']['choices'][0]['finish_reason'],'actual_schema':r['config']['parameters']['response_format']['json_schema']['schema'],'public_answer_reason':g['reason'],'source_basis':source['source_basis'],'question':json.loads(r['messages'][1]['content'])['question'],'failure_reasons':reason,'evaluation_limit':'数值等值与单位仅用于判读，不改原answer；未登记本人逐项核验。'})
table=[]
group=rows
table.append({'variant':'fresh_full_flow','denominator':4,'format_complete':sum(r['format_complete'] for r in group),'specified_answer_correct':sum(r['answer_correct_specified_form'] for r in group),'semantic_consistent':sum(r['semantic_consistent'] for r in group),'input_necessary_coverage':sum(r['input_necessary_evidence_covered'] for r in group),'citation_support':sum(r['evidence_supports_actual_answer'] for r in group),'irrelevant_citation_results':sum(bool(r['irrelevant_citations']) for r in group),'strict_complete_success':sum(r['strict_complete_success'] for r in group),'total_end_to_end_seconds':sum(r['end_to_end_seconds'] for r in group)})
history=read(base/'runs/answer_form/20261013-195237/resume-20261013-200333/semantic-review.json')
comparison=[]
for r in rows:
    prior=next(x for x in history if x['case_id']==r['case_id'] and x['variant']=='answer_form_schema')
    comparison.append({'case_id':r['case_id'],'historic_answer':prior['raw_content'],'current_answer':r['raw_content'],'historic_strict':prior['strict_complete_success'],'current_strict':r['strict_complete_success'],'historic_specified_correct':prior['answer_correct_specified_form'],'current_specified_correct':r['answer_correct_specified_form'],'historic_answer_http_seconds':prior['client_answer_seconds'],'current_end_to_end_seconds':r['end_to_end_seconds'],'limit':'历史重放只执行回答，本轮重新定位并补页；没有同步原方案，耗时口径不同，不作公平性能对比。'})
runs=[read(p) for p in folder.glob('run-*.json')]
assert len(runs)==runtime['generation_attempts']==8 and len({r['run_id'] for r in runs})==8
summary={'reviewed_at':datetime.now().astimezone().isoformat(),'source':'Codex辅助公开开发答案与原文评价，尚未经本人逐项确认','table':table,'generation_calls':len(runs),'cumulative_generation_calls':144+len(runs),'fresh_selection_calls':4,'answer_calls':4,'no_synchronous_original_control':True,'timing_scope':'每题端到端包括两次实际请求、中间验证及容量核查；另列请求耗时。历史重放只回答，不能直接比较流程耗时。','limit':'本轮只验证完整候选；未自动替换生产方案，不能声称正式效果改善。','truncation_flags':re.findall(r'truncated\s*=\s*(\d+)',(folder/'server-log.txt').read_text(encoding='utf-8')),'choice':'与历史形式约束重放同质量时不追加优化、不自动采用；按预先规则保留更简单的原生产方案。'}
assert len(summary['truncation_flags'])==8 and set(summary['truncation_flags'])=={'0'}
protected=read(folder/'protected-hashes.json');assert all(hashlib.sha256((repo/p).read_bytes()).hexdigest()==h for p,h in protected.items())
for name,value in [('semantic-review.json',rows),('summary.json',summary),('historical-comparison.json',comparison)]:
    p=folder/name;assert not p.exists();p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
for r in rows:print(json.dumps({k:r[k] for k in ['case_id','raw_content','selected_ids','added_ids','input_necessary_evidence_covered','answer_correct_specified_form','semantic_consistent','evidence_supports_actual_answer','strict_complete_success','end_to_end_seconds']},ensure_ascii=False))
