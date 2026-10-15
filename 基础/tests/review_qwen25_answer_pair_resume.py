"""全部对照结束后评价0.6B/3B回答；不改写任何原始响应。"""
from pathlib import Path
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json,re,hashlib,sys
folder=Path(sys.argv[1]);repo=Path(__file__).resolve().parents[2];base=repo/'基础'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
runtime=read(folder/'runtime.json');assert runtime['owned_services_stopped'] and runtime.get('all_calls_completed') and not runtime['stopped_on_technical_failure']
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
    rows.append({'case_id':r['case_id'],'variant':r['variant'],'run_id':r['run_id'],'raw_content':content,'answer':answer,'citations':citations,'format_complete':valid,'answer_correct_specified_form':correct,'semantic_consistent':semantic,'citation_ids_exist':exists,'citations_nonempty':nonempty,'necessary_evidence_covered':coverage,'evidence_supports_actual_answer':support,'irrelevant_citations':irrelevant,'strict_complete_success':strict,'client_answer_seconds':r['elapsed_seconds'],'usage':r.get('usage'),'finish_reason':r['response']['choices'][0]['finish_reason'],'actual_schema':r['config']['parameters']['response_format']['json_schema']['schema'],'public_answer_reason':g['reason'],'source_basis':source['source_basis'],'question':json.loads(r['messages'][1]['content'])['question'],'failure_reasons':reason,'evaluation_limit':'数值等值与单位仅用于判读，不改原answer；未登记本人逐项核验。'})
table=[]
for v in ['0.6B','3B']:
    group=[r for r in rows if r['variant']==v]
    table.append({'variant':v,'denominator':4,'format_complete':sum(r['format_complete'] for r in group),'specified_answer_correct':sum(r['answer_correct_specified_form'] for r in group),'semantic_consistent':sum(r['semantic_consistent'] for r in group),'citation_support':sum(r['evidence_supports_actual_answer'] for r in group),'strict_complete_success':sum(r['strict_complete_success'] for r in group),'total_answer_http_seconds':sum(r['client_answer_seconds'] for r in group)})
summary={'reviewed_at':datetime.now().astimezone().isoformat(),'source':'Codex辅助公开开发答案与原文评价，尚未经本人逐项确认','table':table,'generation_calls':8,'cumulative_generation_calls':170,'historical_selection_not_reexecuted':True,'timing_scope':'仅本轮回答阶段完整非流式HTTP请求，不与两步流程耗时直接比较','limit':'只比较四题历史证据输入回答阶段；模型模板、训练和量化均不同，不归因于参数量，不推断模型能力上限。','truncation_flags':re.findall(r'truncated\s*=\s*(\d+)','\n'.join(p.read_text(encoding='utf-8') for p in folder.glob('server-*.stderr.txt')))}
assert len(summary['truncation_flags'])==8 and set(summary['truncation_flags'])=={'0'}
protected=read(folder/'protected-hashes.json');allowed=read(folder/'allowed-code-change.json');assert all(hashlib.sha256((repo/p).read_bytes()).hexdigest()==(allowed['new_sha256'] if p==allowed['path'] else h) for p,h in protected.items())
quality=[(g['strict_complete_success'],g['specified_answer_correct']) for g in table]
summary['choice']='3B本轮质量优于0.6B，可保留为独立候选审阅，不自动替换生产。' if quality[1]>quality[0] else '3B未超过0.6B，按预先规则保留资源成本更低的0.6B，不追加调用。'
for name,value in [('semantic-review.json',rows),('summary.json',summary)]:
    p=folder/name;assert not p.exists();p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
for r in rows:print(json.dumps({k:r[k] for k in ['case_id','variant','raw_content','answer_correct_specified_form','semantic_consistent','evidence_supports_actual_answer','strict_complete_success','client_answer_seconds']},ensure_ascii=False))
