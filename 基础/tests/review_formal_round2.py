"""生成全部结束后的原文辅助复核；不供推理入口导入，不调用模型。"""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import statistics
import sys

repo=Path(__file__).resolve().parents[2]
folder=Path(sys.argv[1]).resolve()
old=repo/'基础/runs/formal_review/round1'
out=folder/'review'
assert not out.exists(),'不覆盖评价'
out.mkdir()
def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def now():return datetime.now().astimezone().isoformat()
def write(name,value):
    path=out/name;assert not path.exists()
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

execution=load(folder/'execution-summary.json')
assert execution['completed_main_tasks']==40 and not execution['technical_stop'] and execution['service_stopped']
tasks=[load(path) for path in sorted(folder.glob('task-*.json'))]
note='Codex辅助原文复核，尚未经本人逐项确认。'
write('protocol.json',{'recorded_at':now(),'reviewer_note':note,'official_score':False,
      'basis':'复用首轮原文推导，核对相同数据哈希、问题和本次可见资料；不是官方答案。',
      'main_task_scope':'答案以主任务完整原输入评价；定位删掉必要证据后拒答不能计为端到端成功。最终引用须存在于最终实际输入。',
      'K':'只用本次K原输入；T03/T04/T07确定答复保留事实与语义ambiguous，另记缺证应答不合规。',
      'support':'有效引用子集支持实际答案与额外无关引用分列；ID存在不等于语义支持。',
      'strict':'开发选定综合指标，不是任务原文唯一评分标准。',
      'denominator':'每条件8题，8组R0配对，40主任务不是40个独立样本。',
      'clarifications':[p.relative_to(repo).as_posix() for p in (old/'clarifications').rglob('*.json')]})

def parse(content):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('duplicate_key')
            result[key]=value
        return result
    try:
        value=json.loads(content,object_pairs_hook=unique)
        valid=isinstance(value,dict) and set(value)=={'answer','citations'} and isinstance(value['answer'],str) and isinstance(value['citations'],list) and all(isinstance(x,str) for x in value['citations'])
        return value,valid
    except (ValueError,TypeError):return {},False

reviews=[];applicability=[]
for cid in ['T01','T02','T03','T04','T05','T06','T07','T08']:
    basis=load(old/('evidence-'+cid+'.json'))
    selected=[t for t in tasks if t['case_id']==cid]
    full=next(t for t in selected if t['condition']=='R0' and t['variant']=='baseline')
    by_id={p['id']:p for p in full['original_passages']}
    assert all(e['quote'] in by_id[e['id']]['text'] for e in basis['required_evidence'])
    assert all(t['question']==full['question'] for t in selected)
    required={e['id'] for e in basis['required_evidence']}
    excluded={e['id']:e['reason'] for e in basis['excluded_evidence']}
    applicability.append({'case_id':cid,'basis_path':(old/('evidence-'+cid+'.json')).relative_to(repo).as_posix(),
        'basis_sha256':sha(old/('evidence-'+cid+'.json')),'source_sha256':basis['source_sha256'],
        'data_hash_matches':basis['source_sha256']==load(folder/'freeze.json')['data_hashes']['基础/data/cases.json'],
        'all_required_quotes_match_original':True,'scope':basis['scope'],'limits':basis['limits']})
    rows=[]
    for task in selected:
        raw=task.get('raw_answer','');value,format_ok=parse(raw)
        answer=value.get('answer','');citations=value.get('citations',[]) if format_ok else []
        visible={p['id']:p for p in task.get('used_passages',[])}
        initial={p['id']:p for p in task['original_passages']}
        ids_ok=bool(format_ok and citations and all(i in visible for i in citations))
        irrelevant=[i for i in citations if i in excluded]
        expected=basis['derived_answer']
        acceptable=basis.get('accepted_equivalent_forms',[expected])
        if cid=='T04':acceptable=['流程乙','乙']
        if cid=='T07':acceptable=['方案丙','丙']
        correct=answer in acceptable
        semantic=correct
        missing='not_checked'
        coverage=required.issubset(citations)
        support=bool(semantic and coverage and ids_ok)
        reason=basis['derivation']+' 原始answer='+repr(answer)+'，未做删单位、去前缀或补引用。'
        coverage_reason='需要'+','.join(sorted(required))+'提供的数据或规则；本次引用'+','.join(citations)+'。'
        support_reason='引用集合须足以推出实际answer；回答正确不自动使单一运算量或缺规则引用通过。'
        if cid=='T05':
            # 沿用先前澄清：当前目标范围的采集边界也是有效缺证检查来源。
            valid_check=bool(set(citations)&required)
            coverage=valid_check;support=bool(correct and ids_ok and valid_check)
            coverage_reason='校内TL46采集边界或明确未采集能耗段可作检查来源；不要求固定单一ID。'
            support_reason='目标检查来源支持当前资料无法推导焦耳；迁移或压力批次不能代替校内组，不推断现实中绝对没有能耗采集。'
        if task['condition']=='K' and cid in ['T02','T06']:
            expected='证据不足';correct=semantic=answer=='证据不足'
            target=basis['required_evidence'][0]['id']
            coverage=target in citations;support=bool(correct and coverage and ids_ok)
            reason=('K缺LX63完全支持计数。' if cid=='T02' else 'K缺SY37将超时和格式不合法合并的技术失败分类定义。')+'不能借不可见补页或通常术语选口径。'
            coverage_reason='目标主记录'+target+'是当前可见的有效缺证检查来源。'
            support_reason='引用目标范围记录并回答证据不足，未借用不可见定义或计数。'
        if task['condition']=='K' and cid in ['T03','T04','T07']:
            correct=semantic='ambiguous';coverage=support=False;missing=answer=='证据不足'
            reason={'T03':'K缺WS84候选中位数及可比条件，迁移XQ56不能补证。',
                    'T04':'K缺NZ95资格门槛及正式选择次序。',
                    'T07':'K缺ZQ58双门槛及代价比较规则。'}[cid]+'确定结果的事实与语义无法核验，不拿全文答案判K。'
            coverage_reason='当前K缺关键来源，不以其他范围段落替代。'
            support_reason='可见引用不能推出确定answer；缺证应答合规另列，不与事实正确性合并。'
        if cid=='T01':
            reason+=' S24仅有条件推导：完成三项明示，但未关闭问题为0未明示；当前响应均不是可支持的S24推导。'
        if task['variant']=='improved' and answer=='证据不足' and cid in ['T02','T06']:
            reason+=' 最终输入缺证是定位漏选造成；主任务原输入含完整数据及定义，所以端到端答案失败。'
        no_irrelevant=not irrelevant
        strict=bool(correct is True and format_ok and ids_ok and coverage and support and no_irrelevant)
        source_basis=[]
        for i in dict.fromkeys([e['id'] for e in basis['required_evidence']]+citations):
            if i in initial:
                p=initial[i]
                source_basis.append({'id':i,'source':p['source'],'text':p['text'],
                    'visible_in_main_input':True,'visible_in_final_input':i in visible,'actually_cited':i in citations})
        r={k:task[k] for k in ['case_id','condition','variant','sequence','main_task_id','end_to_end_seconds']}
        r.update(reviewed_at=now(),reviewer_note=note,raw_content=raw,answer=answer,citations=citations,
            answer_correct=correct,semantic_consistent=semantic,format_complete=format_ok,citation_ids_exist=ids_ok,
            necessary_coverage=coverage,support_actual_answer=support,irrelevant_ids=irrelevant,
            no_irrelevant_references=no_irrelevant,strict_complete_success=strict,
            missing_evidence_response_compliant=missing,main_input_ids=list(initial),final_input_ids=list(visible),
            necessary_input_coverage=(bool(set(visible)&required) if cid=='T05' else required.issubset(visible)),
            final_stage_local_missing_evidence=not required.issubset(visible),source_basis=source_basis,
            run_ids=[s['run_id'] for s in task['stages']],
            reasons={'answer_correct':reason,'semantic_consistent':reason,'necessary_coverage':coverage_reason,
                'support_actual_answer':support_reason,'irrelevant_citations':[{ 'id':i,'reason':excluded[i]} for i in irrelevant],
                'format':'原始JSON严格解析，不补字段。','ids':'逐ID核对最终实际输入；空数组不能算引用成功。'},
            status='provisional_not_personally_confirmed')
        rows.append(r);reviews.append(r)
    write('review-'+cid+'.json',{'reviewed_at':now(),'reviewer_note':note,'basis':basis,'items':rows})
write('evidence-applicability.json',{'checked_at':now(),'items':applicability})
write('effective-reviews.json',{'reviewed_at':now(),'reviewer_note':note,'rows':reviews})
table=[]
metrics=['answer_correct','semantic_consistent','format_complete','citation_ids_exist','necessary_coverage','support_actual_answer','strict_complete_success']
for condition,variant in [('R0','baseline'),('R1','baseline'),('R2','baseline'),('K','baseline'),('R0','improved')]:
    rows=[r for r in reviews if (r['condition'],r['variant'])==(condition,variant)]
    assert len(rows)==8
    table.append({'condition':condition,'variant':variant,'denominator':8,
        'metrics':{m:{'numerator':sum(r[m] is True for r in rows),'denominator':8,
                     'false':sum(r[m] is False for r in rows),'ambiguous':sum(r[m]=='ambiguous' for r in rows)} for m in metrics},
        'irrelevant_reference_records':sum(bool(r['irrelevant_ids']) for r in rows),
        'end_to_end_seconds':{'median':statistics.median(r['end_to_end_seconds'] for r in rows),
                             'min':min(r['end_to_end_seconds'] for r in rows),'max':max(r['end_to_end_seconds'] for r in rows)}})
write('summary.json',{'reviewed_at':now(),'reviewer_note':note,'table':table,'pairing_unit':'8道题，非40个独立样本'})
pairs=[]
for cid in ['T01','T02','T03','T04','T05','T06','T07','T08']:
    baseline=next(r for r in reviews if r['case_id']==cid and r['condition']=='R0' and r['variant']=='baseline')
    improved=next(r for r in reviews if r['case_id']==cid and r['variant']=='improved')
    pairs.append({'case_id':cid,'baseline':baseline,'improved':improved,
        'strict_change':'improved' if improved['strict_complete_success'] and not baseline['strict_complete_success'] else 'regressed' if baseline['strict_complete_success'] and not improved['strict_complete_success'] else 'unchanged'})
write('paired-comparison.json',{'reviewed_at':now(),'reviewer_note':note,'items':pairs})
write('historical-comparison.json',{'reviewed_at':now(),'reviewer_note':note,
    'first_round_table':load(old/'summary.json')['table'],'second_round_table':table,
    'differences':load(folder/'freeze.json')['research']['history_differences'],
    'limits':'评测后重复评测；模型和最终采样未变，但答案形式、资料选择、顺序及调用次数变化；不能归因于单一机制，不声称统计显著。'})
write('confirmation-needed.json',{'reviewed_at':now(),'reviewer_note':note,
    'T01':'S24有条件推导与严格字面边界继续保留；本轮五条回答的支持失败不受该争议影响。',
    'K_ambiguous':[r for r in reviews if r['answer_correct']=='ambiguous'],
    'pipeline_scope':'定位漏选后局部拒答与主任务端到端失败分列，不能用删减后的输入制造成功。'})
print(json.dumps({'table':table,'pairs':[{'case_id':p['case_id'],'baseline_answer':p['baseline']['answer'],'improved_answer':p['improved']['answer'],
    'baseline_seconds':round(p['baseline']['end_to_end_seconds'],3),'improved_seconds':round(p['improved']['end_to_end_seconds'],3),
    'strict_change':p['strict_change']} for p in pairs]},ensure_ascii=False,indent=2))
