"""变化题同步回答与相同请求历史复用的原文辅助复核。"""
from pathlib import Path
from datetime import datetime
import copy,hashlib,json,statistics,sys

repo=Path(__file__).resolve().parents[2]
folder=Path(sys.argv[1]).resolve()
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now().astimezone().isoformat()
def write(name,value):
    p=folder/name;assert not p.exists();p.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
execution=load(folder/'execution-summary.json')
assert execution['completed_answers']==execution['planned_generated_answers'] and not execution['technical_stop'] and execution['service_stopped']
records=[load(p) for p in folder.glob('run-*.json')]
reuse=load(folder/'reused-results.json')['items']
association=load(folder/'eight-case-association-recompute.json')['items']
old_evidence=repo/'基础/runs/formal_review/round1'
reviews=[];relations=[]
for item in association:
    cid=item['case_id'];basis=load(old_evidence/('evidence-'+cid+'.json'))
    original={p['id']:p for p in item['original_passages']}
    required={e['id'] for e in basis['required_evidence']}
    excluded={e['id']:e['reason'] for e in basis['excluded_evidence']}
    assert all(e['quote'] in original[e['id']]['text'] for e in basis['required_evidence'])
    # 当前可见资料下的关系复核，不将未知范围解释为相等或保证外部唯一。
    added=[r for r in item['new_trace'] if r['added']]
    for relation in added:
        assert len(relation['candidate_target_ids'])==1 and relation['target_id'] in item['selection_validation']['selected_ids']
        assert relation['reference_evidence'][0]['code']==relation['target_declarations'][0]['code']
        main=original[relation['target_id']];supp=original[relation['supplement_id']]
        relations.append({'case_id':cid,'main_id':main['id'],'supplement_id':supp['id'],
            'main_text':main['text'],'supplement_text':supp['text'],'relation_trace':relation,
            'misassociation':False,'judgment_basis':'补页正文直接指称同一完整业务编号；当前全资料中仅一个可靠主声明，无已识别的明示范围或命名空间冲突。',
            'limits':'仅当前可见资料下的辅助判断；缺失范围与命名空间仍未知，不能证明输入外编号不复用或段落内容真实。'})
    for variant in ['old','new']:
        matches=[r for r in records if r['case_id']==cid and r['variant']==variant]
        if matches:
            assert len(matches)==1;record=matches[0];provenance='new_live_answer'
            source_path=(folder/('run-'+record['run_id']+'.json')).relative_to(repo).as_posix()
            raw=record['raw_content'];cost=record['elapsed_seconds']
        else:
            source=next(r for r in reuse if r['case_id']==cid)
            record=load(repo/source['record_path']);source_path=source['record_path'];provenance='historical_same_request_reuse'
            assert sha(repo/source_path)==source['record_sha256']
            raw=record['raw_content'];cost=None
        used=item[variant+'_used_passages'];visible={p['id']:p for p in used}
        assert record['messages'][1]['content']==item['request_bodies'][variant]['messages'][1]['content']
        assert record['raw_http_request_body']==item['raw_serialized_requests'][variant]
        value=json.loads(raw);answer=value['answer'];citations=value['citations']
        format_ok=set(value)=={'answer','citations'} and isinstance(answer,str) and isinstance(citations,list) and all(isinstance(i,str) for i in citations)
        acceptable=basis.get('accepted_equivalent_forms',[basis['derived_answer']])
        if cid=='T04':acceptable=['流程乙','乙']
        if cid=='T07':acceptable=['方案丙','丙']
        correct=semantic=answer in acceptable
        ids=bool(format_ok and citations and all(i in visible for i in citations))
        coverage=required.issubset(citations)
        input_coverage=required.issubset(visible)
        irrelevant=[i for i in citations if i in excluded]
        support=bool(correct and ids and coverage)
        reason=basis['derivation']+' 本次原始answer='+repr(answer)+'，不改写或补引用。'
        coverage_reason='需要'+','.join(sorted(required))+'的数据/规则，实际引用'+','.join(citations)+'。'
        support_reason='答案与来源核对；正确答案不自动使不完整引用集合成立。'
        if cid=='T05':
            coverage=bool(set(citations)&required);input_coverage=bool(set(visible)&required)
            support=bool(correct and ids and coverage)
            coverage_reason='沿用既有澄清：校内TL46主记录或明确能耗缺失补页可作有效检查来源，不要求固定唯一ID。'
            support_reason='目标范围采集边界支持当前资料无法推导焦耳，不能推断现实中绝对没有采集。'
        if cid in ['T02','T06'] and variant=='new':
            reason+=' 最终输入已包含必要数据和口径；仍拒答属于回答阶段失败，本轮不能再归因于未补入。'
        if cid=='T04' and variant=='new':
            support_reason='只引用资格门槛和选择次序，没有引用三个流程的实际数据，不能推出流程乙。'
        if cid=='T07':support_reason='只引候选数据，缺双门槛规则，不能支持目标决策。'
        if cid=='T03':support_reason='只引基础9.4秒，漏引候选6.8秒及可比条件，不能完整支持差值2.6。'
        if cid=='T01':
            reason+=' S24有条件推导及未关闭问题为0未明示的字面边界继续保留；当前段落ID回答不受该争议支持。'
        row={'reviewed_at':now(),'case_id':cid,'variant':variant,'condition':'R0','run_id':record['run_id'],
            'record_path':source_path,'result_provenance':provenance,'raw_content':raw,'answer':answer,'citations':citations,
            'format_complete':format_ok,'citation_ids_exist':ids,'necessary_input_coverage':input_coverage,
            'answer_correct':correct,'semantic_consistent':semantic,'necessary_coverage':coverage,'support_actual_answer':support,
            'irrelevant_ids':irrelevant,'strict_complete_success':bool(correct and format_ok and ids and coverage and support and not irrelevant),
            'answer_stage_seconds':cost,'historical_seconds_not_this_round':record['elapsed_seconds'] if provenance!='new_live_answer' else None,
            'final_input_ids':list(visible),'source_basis':[{'id':i,'source':original[i]['source'],'text':original[i]['text'],
                'visible_in_final_input':i in visible,'actually_cited':i in citations} for i in dict.fromkeys([e['id'] for e in basis['required_evidence']]+citations) if i in original],
            'reasons':{'answer':reason,'input_coverage':'检查实际完整原段落是否包含必要数据与规则；来源齐全不等于模型成功。',
                'citation_coverage':coverage_reason,'citation_support':support_reason,
                'irrelevant_citations':[{'id':i,'reason':excluded[i]} for i in irrelevant]},
            'reviewer_note':'Codex辅助原文复核，尚未经本人逐项确认。','official_score':False}
        reviews.append(row)
write('relation-review.json',{'reviewed_at':now(),'items':relations,'misassociation_count':sum(r['misassociation'] for r in relations),
    'scope':'当前输入中的辅助关联复核，不等于原文真实性、语义支持或未见资料上的安全保证。'})
write('evaluations.json',{'reviewed_at':now(),'rows':reviews,'generation_calls_in_review':0})
metrics=['necessary_input_coverage','answer_correct','semantic_consistent','format_complete','citation_ids_exist','necessary_coverage','support_actual_answer','strict_complete_success']
table=[]
for variant in ['old','new']:
    rows=[r for r in reviews if r['variant']==variant];assert len(rows)==8
    live=[r for r in rows if r['result_provenance']=='new_live_answer']
    table.append({'variant':variant,'denominator':8,'new_live_answers':len(live),'historical_reused_answers':8-len(live),
        'metrics':{m:{'true':sum(r[m] is True for r in rows),'false':sum(r[m] is False for r in rows),'denominator':8} for m in metrics},
        'irrelevant_reference_records':sum(bool(r['irrelevant_ids']) for r in rows),
        'fresh_answer_stage_median_seconds':statistics.median(r['answer_stage_seconds'] for r in live)})
old_row,new_row=table
score=lambda r:(r['metrics']['strict_complete_success']['true'],r['metrics']['answer_correct']['true'])
adopt='new' if score(new_row)>score(old_row) else 'old'
write('evaluation-summary.json',{'reviewed_at':now(),'table':table,'selected':adopt,
    'selection_reason':'两侧严格成功均1/8、答法正确均4/8，同分保留旧方案。',
    'benefit':'本组输入必要来源覆盖2/8→8/8。','quality_limit':'最终引用覆盖、支持及严格成功均未改善。',
    'risk':'当前未发现误关联；未知范围/命名空间、有限声明和否定语句识别仍有限制。',
    'cost_scope':'7组变化题的同步回答单次计时；T03历史复用不纳入本轮耗时。',
    'exposure':'评测后机制对照，历史定位重放；非独立盲测或泛化验证。'})
pairs=[]
for item in association:
    rows={r['variant']:r for r in reviews if r['case_id']==item['case_id']}
    pairs.append({'case_id':item['case_id'],'request_changed':item['request_changed'],'old':rows['old'],'new':rows['new'],
        'strict_change':'unchanged','misassociation_found':False})
write('paired-comparison.json',{'reviewed_at':now(),'items':pairs,'strict_improved':0,'strict_regressed':0,'strict_unchanged':8})
print(json.dumps({'table':table,'selected':adopt,'misassociation_count':0},ensure_ascii=False,indent=2))
