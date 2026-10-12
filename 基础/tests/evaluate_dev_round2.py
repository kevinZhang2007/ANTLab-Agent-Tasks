"""只读模型记录和公开开发答案，独立评价格式、答案及引用。"""
from pathlib import Path
from datetime import datetime, timezone
import json

repo = Path(__file__).resolve().parents[2]
base = repo / '基础'
folder = base / 'runs/diagnostics/round2'
answers = {a['id']:a for a in json.loads((base/'data/dev_answers.json').read_text(encoding='utf-8'))}
rows = []
for summary in json.loads((folder/'results.json').read_text(encoding='utf-8')):
    record = json.loads((folder/f"run-{summary['run_id']}.json").read_text(encoding='utf-8'))
    gold = answers[record['case_id']]
    message = record['response']['choices'][0]['message']
    parsed = json.loads(message['content'])
    valid = (isinstance(parsed,dict) and set(parsed)=={'answer','citations'} and
             isinstance(parsed.get('answer'),str) and isinstance(parsed.get('citations'),list) and
             all(isinstance(value,str) for value in parsed['citations']))
    answer_correct = isinstance(parsed.get('answer'),str) and parsed['answer'].strip() in gold['aliases']
    citations = parsed.get('citations')
    citations_present = isinstance(citations,list) and all(isinstance(value,str) for value in citations)
    ids_exist = all(value in record['selected_passage_ids'] for value in citations) if citations_present else None
    payload = json.loads(record['messages'][1]['content'])
    by_id = {p['id']:p for p in payload['passages']}
    if gold['evidence_ids']:
        enough = citations_present and set(gold['evidence_ids']).issubset(citations)
    else:
        enough = citations_present and any(value in by_id and '均未被采集' in by_id[value]['text'] for value in citations)
    supported = bool(answer_correct and ids_exist and enough)
    source_sentences = [p['text'].split('。')[0]+'。' for p in payload['passages']]
    answer_basis = gold['reason']+' 原文：'+' '.join(source_sentences)
    if not citations_present:
        citation_basis = '响应缺少citations，无法回溯其引用；原文的选择表和签署规则共同支持配置丙，但不能代替模型提供引用。'
    elif supported:
        citation_basis = '实际引用原文：'+' '.join(by_id[value]['text'].split('。')[0]+'。' for value in citations)
    else:
        citation_basis = '实际引用只给出85个有效问题，并未给出85%或证明证据不足；补页明确给出68个获支持问题。'
    reasons = []
    if not valid: reasons.append('缺少citations，answer/citations接口不完整')
    if not answer_correct: reasons.append('答案不符合公开开发答案和原文')
    if not supported: reasons.append('没有足够引用支持回答')
    rows.append({'run_id':record['run_id'],'case_id':record['case_id'],'candidate':record['candidate_setting'],
                 'raw_content':message['content'],'complete_answer_citations_json':valid,
                 'answer_matches_public_and_text':answer_correct,'citation_ids_in_input':ids_exist,
                 'citation_support_sufficient':supported,'citations':citations,
                 'answer_basis':answer_basis,'citation_basis':citation_basis,
                 'elapsed_seconds':record['elapsed_seconds'],'output_tokens':record['usage']['completion_tokens'],
                 'failure_reasons':reasons,'checked_by':'Codex',
                 'evaluation_only':True,'model_input_changed':False})
review={'record_kind':'independent_semantic_review','recorded_at_utc':datetime.now(timezone.utc).isoformat(),
        'notes':['The initial driver gates answer evaluation on full schema validity. This independent review separates answer correctness from missing citations, correcting D04 interpretation without rewriting any model record.','Transfer cases have no same-case baseline in this round; comparator_run_id inherited from D01 is not a paired transfer comparison.'],
        'rows':rows}
path=folder/'semantic-review.json'
assert not path.exists()
path.write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
for row in rows:
    print(json.dumps({key:row[key] for key in ('case_id','candidate','run_id','raw_content','complete_answer_citations_json','answer_matches_public_and_text','citation_ids_in_input','citation_support_sufficient','elapsed_seconds','output_tokens')},ensure_ascii=False))
