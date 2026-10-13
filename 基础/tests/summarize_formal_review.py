"""离线复算Codex辅助原文标签；不生成、不修改原始记录或逐题初评。"""
from pathlib import Path
from datetime import datetime
import copy,hashlib,json
repo=Path(__file__).resolve().parents[2]
folder=repo/'基础/runs/formal_review/round1'
note='Codex辅助原文复核，尚未经本人逐项确认。'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    with p.open('rb') as s:return hashlib.file_digest(s,'sha256').hexdigest()
def save(name,value):
    p=folder/name;assert not p.exists(),'保留已有评价，不覆盖'
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
rows=[];confirm=[];cases={c['id']:c for c in load(repo/'基础/data/cases.json')}
for i in range(1,9):
    cid='T%02d'%i;e=load(folder/('evidence-'+cid+'.json'));v=load(folder/('review-'+cid+'.json'))
    assert e['reviewed_at']<=v['reviewed_at']
    by={p['id']:p for p in cases[cid]['passages']}
    for needed in e['required_evidence']:assert needed['quote'] in by[needed['id']]['text']
    for row in v['items']:
        raw=load(repo/row['record_path'])
        assert row['raw_content']==raw['response']['choices'][0]['message']['content']
        assert row['actual_input_ids']==raw['selected_passage_ids']
        row.update(case_id=cid,reviewer_note=note,initial_review_path='基础/runs/formal_review/round1/review-'+cid+'.json')
        rows.append(copy.deepcopy(row))
    confirm.extend({'case_id':cid,'issue':s} for s in v.get('confirmation_needed',[]))
adjustments=load(folder/'review-adjustments.json')
for a in adjustments['adjustments']:
    r=next(r for r in rows if r['run_id']==a['run_id'])
    assert all(r[k]==v for k,v in a['old'].items())
    r.update(a['new']);r['review_adjustment_reason']=a['reason']
    r['judgment_reasons']['answer_correct']=a['reason'];r['judgment_reasons']['semantic_consistent']=a['reason']
    flags=[r['answer_correct'],r['format_complete'],r['citation_ids_exist'],r['necessary_coverage'],r['support_actual_answer'],not r['irrelevant_ids']]
    r['strict_complete_success']=False if False in flags else (True if all(x is True for x in flags) else 'ambiguous')
    confirm.append({'case_id':r['case_id'],'run_id':r['run_id'],'issue':a['reason']})
confirm+=adjustments['evidence_clarifications']
assert len(rows)==40 and len({r['run_id'] for r in rows})==40
rows.sort(key=lambda r:(r['case_id'],r['condition'],r['variant']))
for r in rows:r['support_status']='supported' if r['support_actual_answer'] is True else ('insufficient' if r['support_actual_answer'] is False else r['support_actual_answer'])
save('effective-reviews.json',{'reviewed_at':datetime.now().astimezone().isoformat(),'reviewer_note':note,'rows':rows,'adjustments_applied':'review-adjustments.json','semantic_label_source':'Codex-assisted source review; not independent human or official gold'})
metrics=['answer_correct','semantic_consistent','format_complete','citation_ids_exist','necessary_coverage','support_actual_answer','strict_complete_success']
table=[]
for condition,variant in [('R0','baseline'),('R1','baseline'),('R2','baseline'),('K','baseline'),('R0','improved')]:
    group=[r for r in rows if r['condition']==condition and r['variant']==variant]
    entry={'condition':condition,'variant':variant,'denominator':len(group),'metrics':{}}
    for m in metrics:entry['metrics'][m]={'numerator':sum(r[m] is True for r in group),'denominator':len(group),'false':sum(r[m] is False for r in group),'ambiguous':sum(r[m]=='ambiguous' for r in group),'not_checked':sum(r[m]=='not_checked' for r in group)}
    entry['irrelevant_reference_records']=sum(bool(r['irrelevant_ids']) for r in group)
    entry['no_irrelevant_references']=len(group)-entry['irrelevant_reference_records']
    entry['client_total_seconds']=sum(r['elapsed_seconds'] for r in group)
    table.append(entry)
pairs=[];orders=[]
for i in range(1,9):
    cid='T%02d'%i
    b=next(r for r in rows if r['case_id']==cid and r['condition']=='R0' and r['variant']=='baseline')
    p=next(r for r in rows if r['case_id']==cid and r['variant']=='improved')
    delta={m:{'baseline':b[m],'improved':p[m]} for m in metrics if b[m]!=p[m]}
    pairs.append({'case_id':cid,'baseline_run_id':b['run_id'],'improved_run_id':p['run_id'],'baseline_answer':b['answer'],'improved_answer':p['answer'],
     'baseline_citations':b['citations'],'improved_citations':p['citations'],'strict_baseline':b['strict_complete_success'],'strict_improved':p['strict_complete_success'],
     'strict_comparison':'improved' if not b['strict_complete_success'] and p['strict_complete_success'] else ('regressed' if b['strict_complete_success'] and not p['strict_complete_success'] else 'unchanged'),
     'metric_changes':delta,'irrelevant_records_changed':{'baseline':b['irrelevant_ids'],'improved':p['irrelevant_ids']},
     'baseline_elapsed_seconds':b['elapsed_seconds'],'improved_elapsed_seconds':p['elapsed_seconds'],
     'basis_paths':['基础/runs/formal_review/round1/evidence-'+cid+'.json','基础/runs/formal_review/round1/review-'+cid+'.json'],
     'limit':'质量分项与单次耗时分别看；不把一次耗时变化称稳定性能提升。'})
    obs=[next(r for r in rows if r['case_id']==cid and r['condition']==c and r['variant']=='baseline') for c in ['R0','R1','R2']]
    orders.append({'case_id':cid,'conditions':[{'condition':r['condition'],'run_id':r['run_id'],'answer':r['answer'],'citations':r['citations'],'answer_correct':r['answer_correct'],'semantic_consistent':r['semantic_consistent'],'coverage':r['necessary_coverage'],'support':r['support_actual_answer'],'irrelevant_ids':r['irrelevant_ids'],'strict_success':r['strict_complete_success']} for r in obs],
     'raw_output_changed':len({r['raw_content'] for r in obs})>1,'answer_changed':len({r['answer'] for r in obs})>1,
     'limit':'同一题三种顺序的观察，不足把位置认定唯一原因；无随机重复，不声称显著性。'})
save('paired-comparison.json',{'reviewer_note':note,'paired_units':8,'strict_improved':sum(p['strict_comparison']=='improved' for p in pairs),'strict_regressed':sum(p['strict_comparison']=='regressed' for p in pairs),'strict_unchanged':sum(p['strict_comparison']=='unchanged' for p in pairs),'pairs':pairs})
save('order-comparison.json',{'reviewer_note':note,'paired_units':8,'items':orders})
k=[]
for r in rows:
    if r['condition']!='K':continue
    e=load(folder/('evidence-'+r['case_id']+'.json'))
    missing=[p['id'] for p in e['required_evidence'] if p['id'] not in r['actual_input_ids']]
    k.append({'case_id':r['case_id'],'run_id':r['run_id'],'actual_visible_ids':r['actual_input_ids'],'missing_full_reference_evidence_ids':missing,
     'cited_visible_quotes':[p for p in r['source_basis'] if p['visible_in_this_run'] and p['id'] in r['citations']],
     'answer_correct':r['answer_correct'],'semantic_consistent':r['semantic_consistent'],'coverage':r['necessary_coverage'],'support':r['support_actual_answer'],'strict_success':r['strict_complete_success'],'reason':r['judgment_reasons']['answer_correct'],
     'limit':'缺失的全文段仅说明检索遗漏，不能当当前回答依据；T05单个有效检查来源可足够，不机械要求所有参考ID。'})
save('K-visibility-review.json',{'reviewer_note':note,'items':k,'comparison_limit':'K同时改变选择与数量，不能解释为纯位置效应。'})
save('confirmation-needed.json',{'reviewer_note':note,'all_40_labels_await_personal_confirmation':True,'focused_issues':confirm,'ambiguous_records':[{'run_id':r['run_id'],'case_id':r['case_id'],'condition':r['condition'],'reason':r.get('review_adjustment_reason',r['reason'])} for r in rows if r['answer_correct']=='ambiguous' or r['semantic_consistent']=='ambiguous']})
save('summary.json',{'reviewed_at':datetime.now().astimezone().isoformat(),'reviewer_note':note,'table':table,'independent_paired_units':8,'total_records':40,'unreviewed_records':0,'personal_confirmation_pending':40,
 'strict_metric_origin':'开发选定综合指标，不是官方唯一评分标准','limitations':['本次为评测后原文推导，非官方标准答案。','Codex辅助复核，不称独立人工判分。','K三个具体答案因缺必要规则/数据无法核验，保留ambiguous，不用全文正确值替K判分。','T01未显式写S24无未关闭问题，候选枚举读法待本人确认。','以题目配对，不把40次请求当40个独立样本，不声称统计显著。'],
 'error_types':['范围混用：另一项目、旧版本、探索/迁移/压力批次。','全文有依据仍拒答，未组合分子分母或统计定义。','只引数据或规则，必要覆盖不足。','数值差错误、段落ID/批次号充当答案。','语义正确但不遵守只填数值或名称；夹带无关引用。'],
 'generated_calls':0,'cumulative_generation_calls_unchanged':124})
protected=load(folder/'protected-hashes.json');changed=[n for n,v in protected.items() if sha(repo/n)!=v]
assert not changed
save('audit.json',{'checked_at':datetime.now().astimezone().isoformat(),'old_files_unchanged':len(protected),'all_40_run_ids_matched':True,'all_quotes_present_in_originals':True,'evidence_saved_before_case_response_review':True,'generated_calls':0,'frozen_code_and_config_unchanged':True})
files=[p.relative_to(repo).as_posix() for p in sorted(folder.rglob('*')) if p.is_file()]+['基础/tests/summarize_formal_review.py','基础/runs/formal_review/round1/new-files.json']
save('new-files.json',{'new_files':files,'modified_existing_files':[]})
print(json.dumps({'table':table,'strict_pair_changes':{'improved':sum(p['strict_comparison']=='improved' for p in pairs),'regressed':sum(p['strict_comparison']=='regressed' for p in pairs),'unchanged':sum(p['strict_comparison']=='unchanged' for p in pairs)},'new_files':len(files),'protected_unchanged':len(protected)},ensure_ascii=False,indent=2))
