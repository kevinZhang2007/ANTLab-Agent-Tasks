"""16次回答结束后的标签复用核对；无模型调用，保留旧评价。"""
import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import statistics
import sys

repo=Path(__file__).resolve().parents[2]
folder=Path(sys.argv[1]).resolve()
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now().astimezone().isoformat()
def write(name,value):
    path=folder/name;assert not path.exists()
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
summary=load(folder/'execution-summary.json')
assert summary['completed_answers']==16 and summary['service_stopped'] and not summary['technical_stop']
records=sorted([load(p) for p in folder.glob('run-*.json')],key=lambda r:r['sequence'])
round2=repo/'基础/runs/formal/round2-20261014-133000'
old_reviews=load(round2/'review/effective-reviews.json')['rows']
tasks=[load(p) for p in round2.glob('task-*.json')]
review=[]
for r in records:
    original=next(t for t in tasks if t['case_id']==r['case_id'] and t['variant']=='improved')
    old=next(x for x in old_reviews if x['case_id']==r['case_id'] and x['variant']=='improved')
    assert r['original_passages']==original['original_passages']
    assert r['used_passages']==original['used_passages']
    assert r['question']==original['question'] and r['raw_content']==original['raw_answer']==old['raw_content']
    assert r['messages']==original['stages'][-1]['messages'] and r['config']==original['stages'][-1]['config']
    # 只在原问题、完整输入、最终输入、原始输出和配置全相同后复用标签。
    row=copy.deepcopy(old)
    row.update(variant=r['variant'],run_id=r['run_id'],run_ids=[r['run_id']],sequence=r['sequence'],
        reviewed_at=now(),answer_stage_seconds=r['elapsed_seconds'],
        label_provenance='复用第二轮相同问题、原文、最终输入及逐字相同输出的辅助暂判；不是重新独立人工评分。',
        reused_review_path=(round2/'review/effective-reviews.json').relative_to(repo).as_posix(),
        reused_review_sha256=sha(round2/'review/effective-reviews.json'),
        question_input_output_config_exact_match=True,
        current_record_path=(folder/('run-'+r['run_id']+'.json')).relative_to(repo).as_posix())
    row.pop('end_to_end_seconds',None)
    row.pop('main_task_id',None)
    row['cost_scope']='只计本轮回答阶段客户端完整非流式请求时间；定位来自历史重放。'
    review.append(row)
write('evaluations.json',{'reviewed_at':now(),'reviewer_note':'Codex辅助原文复核，尚未经本人逐项确认。','rows':review})
table=[]
metrics=['necessary_input_coverage','answer_correct','semantic_consistent','format_complete','citation_ids_exist',
         'necessary_coverage','support_actual_answer','strict_complete_success']
for variant in ['old','new']:
    rows=[r for r in review if r['variant']==variant];assert len(rows)==8
    table.append({'variant':variant,'denominator':8,
        'metrics':{m:{'true':sum(r[m] is True for r in rows),'false':sum(r[m] is False for r in rows),
                     'ambiguous':sum(r[m]=='ambiguous' for r in rows),'denominator':8} for m in metrics},
        'irrelevant_reference_records':sum(bool(r['irrelevant_ids']) for r in rows),
        'answer_stage_median_seconds':statistics.median(r['answer_stage_seconds'] for r in rows)})
write('evaluation-summary.json',{'reviewed_at':now(),'table':table,'scope':'评测后机制对照，历史选择重放；不是独立评测集或完整两步流程。',
    'selected':'old','selection_reason':'两方案严格完整成功均1/8，指定答法正确均4/8；同分保留旧方案。',
    'semantic_note':'同一主任务原始资料含必要证据，定位漏选后的拒答仍算端到端答案失败。'})
pairs=[]
for cid in ['T01','T02','T03','T04','T05','T06','T07','T08']:
    rows=[r for r in review if r['case_id']==cid]
    old=next(r for r in rows if r['variant']=='old');new=next(r for r in rows if r['variant']=='new')
    pairs.append({'case_id':cid,'old':old,'new':new,'raw_response_content_identical':old['raw_content']==new['raw_content'],
                  'strict_change':'unchanged','answer_change':'unchanged'})
write('paired-comparison.json',{'reviewed_at':now(),'items':pairs,'improved_strict':0,'regressed_strict':0,'unchanged_strict':8})
print(json.dumps({'table':table,'selected':'old'},ensure_ascii=False,indent=2))
