"""整轮停止后离线评价开发配对；不调用模型，不改原响应。"""
from pathlib import Path
from datetime import datetime
import json
import hashlib
import re

repo=Path(__file__).resolve().parents[2]
base=repo/'基础'
folder=base/'runs/two_step/dev_r0'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
runtime=load(folder/'runtime.json')
assert runtime['server_stopped'], '服务停止后才能评价'
assert runtime['all_planned_tasks_finished'], '中途技术停止时不伪造完整配对评价'
# 公开答案首次读取在全部调用结束之后；仅用于开发评价。
gold={g['id']:g for g in load(base/'data/dev_answers.json')}
parents=load(folder/'task-results.json')
records={r['run_id']:r for r in [load(p) for p in folder.glob('run-*.json')]}
rows=[]
for parent in parents:
    cid=parent['case_id'];g=gold[cid]
    original=parent['ordered_passages'];by_id={p['id']:p for p in original}
    required=set(g['evidence_ids'])
    if cid=='D02':
        # 检查来源来自当题原文观察边界，不把空gold列表当作必须空引用。
        required={p['id'] for p in original if ('夜间组代号' in p['text'] and '只收到HTTP响应和模型显示名' in p['text']) or ('资产、设备遥测与推理节点字段均未被采集' in p['text'])}
    def coverage(ids):
        return bool(set(ids)&required) if cid=='D02' else required.issubset(ids)
    stage1=next((records[rid] for rid in parent['stage_run_ids'] if records[rid]['stage']=='selection'),None)
    selection=parent.get('selection_validation')
    selected_ids=selection['selected_ids'] if selection and selection['valid'] else []
    answer_validation=parent.get('answer_validation',{})
    parsed=answer_validation.get('parsed')
    answer=parsed.get('answer') if isinstance(parsed,dict) else None
    citations=parsed.get('citations') if isinstance(parsed,dict) else []
    if not isinstance(citations,list) or not all(isinstance(i,str) for i in citations):citations=[]
    correct=isinstance(answer,str) and answer.strip() in g['aliases']
    semantic=correct or (cid=='D02' and answer in ['服务端GPU型号未知','未提及具体型号'])
    used=parent.get('final_used_passages',[]);used_ids={p['id'] for p in used}
    ids_exist=bool(citations) and all(i in used_ids for i in citations)
    necessary=coverage(citations)
    support=bool(semantic and ids_exist and necessary)
    irrelevant=[i for i in citations if i in by_id and i not in required]
    selection_ok=selection is None or selection['valid']
    full=bool(answer_validation.get('format_complete') and correct and ids_exist and support and not irrelevant and selection_ok)
    reason=[]
    if not answer_validation.get('format_complete'):reason.append('最终JSON格式不完整或第二步未执行')
    if not correct:reason.append('最终答案不符合指定答法及公开开发答案')
    if not necessary:reason.append('最终引用没有覆盖全部必要依据')
    if irrelevant:reason.append('引用含范围不符或无关段落')
    if not selection_ok:reason.append('定位输出非法，未修补或回退')
    stage_checks=[]
    for rid in parent['stage_run_ids']:
        r=records[rid]
        assert r['request_verified_before_send']
        assert r['actual_http_request_body']['messages']==r['messages']
        assert r['actual_http_request_body']['max_tokens']==256
        assert all(r['parameter_checks'].values())
        assert r['rendered_prompt_tokens']+256<4096
        assert json.loads(r['messages'][1]['content'])=={'question':parent['question'],'passages':r['used_passages']}
        assert all(p in original for p in r['used_passages'])
        stage_checks.append({'run_id':rid,'stage':r['stage'],'record_path':'基础/runs/two_step/dev_r0/run-'+rid+'.json','elapsed_seconds':r['elapsed_seconds'],'usage':r['usage'],'finish_reason':r['response']['choices'][0]['finish_reason']})
    if selection and selection['valid']:
        assert used==[p for p in original if p['id'] in selected_ids]
    row={'parent_request_id':parent['parent_request_id'],'case_id':cid,'variant':parent['variant'],'status':parent['status'],'raw_final_content':parent.get('raw_final_content'),'answer':answer,'citations':citations,'format_complete':bool(answer_validation.get('format_complete')),'answer_correct_specified_form':correct,'semantic_consistent':semantic,'D02_specified_form':correct if cid=='D02' else None,'citation_ids_exist':ids_exist,'necessary_evidence_covered':necessary,'evidence_supports_actual_answer':support,'irrelevant_citations':irrelevant,'strict_complete_success':full,'end_to_end_seconds':parent['end_to_end_seconds'],'stage_records':stage_checks,'public_answer_reason':g['reason'],'failure_reasons':reason,
        'source_basis':[{'id':p['id'],'source':p['source'],'quote':p['text'].split('。')[0]+'。'} for p in original if p['id'] in required],
        'selection':None if selection is None else {'validation':selection,'raw_content':parent['raw_selection_content'],'necessary_evidence_covered':selection['valid'] and coverage(selected_ids),'missing_necessary_ids':sorted(required-set(selected_ids)) if cid!='D02' else ([] if coverage(selected_ids) else sorted(required)),'irrelevant_or_conflicting_ids':[i for i in selected_ids if i not in required],'selected_sources':[{'id':i,'source':by_id[i]['source'],'quote':by_id[i]['text'].split('。')[0]+'。'} for i in selected_ids if i in by_id],'judgment_limit':'这是开发原文复核，参考ID只在评价阶段使用；不自动把ID存在或选对段落当作回答成功。'}}
    rows.append(row)
table=[]
for variant in ['baseline','candidate']:
    group=[r for r in rows if r['variant']==variant]
    table.append({'variant':variant,'tasks':len(group),'format_complete':sum(r['format_complete'] for r in group),'answer_correct':sum(r['answer_correct_specified_form'] for r in group),'strict_complete_success':sum(r['strict_complete_success'] for r in group),'end_to_end_total_seconds':sum(r['end_to_end_seconds'] for r in group)})
baseline,candidate=table
selected='candidate' if (candidate['strict_complete_success'],candidate['answer_correct'])>(baseline['strict_complete_success'],baseline['answer_correct']) else 'baseline'
log=(folder/'server-log.txt').read_text(encoding='utf-8')
truncated=re.findall(r'truncated\s*=\s*(\d+)',log)
assert len(truncated)==len(records) and set(truncated)=={'0'}
assert len(records)<=12 and runtime['generation_attempts']==len(records)
protected=load(folder/'protected-hashes.json')
assert all(hashlib.sha256((repo/name).read_bytes()).hexdigest()==value for name,value in protected.items())
summary={'reviewed_at':datetime.now().astimezone().isoformat(),'table':table,'selected':selected,'selection_rule':'完整成功数优先，其次答案正确数；同分或退步保留原方案。','generation_calls':len(records),'previous_generation_calls':72,'cumulative_generation_calls':72+len(records),'all_planned_tasks_finished':True,'service_stopped':True,'unchanged_protected_files':len(protected),'truncation_flags':truncated,'attribution_limit':'调用次数、总输出预算、选取和资料数量共同变化，只比较实际整套方案；不单独归因定位。'}
for name,value in [('semantic-review.json',rows),('summary.json',summary)]:
    path=folder/name;assert not path.exists();path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
for row in rows:print(json.dumps(row,ensure_ascii=False))
