"""按已保存计划执行开发题对照；公开答案仅在响应保存后用于评价。"""
from pathlib import Path
import argparse
import copy
import datetime
import hashlib
import json
import sys
import urllib.request
import uuid

repo = Path(__file__).resolve().parents[2]
base = repo / '基础'
folder = base / 'runs/diagnostics/round2'
plan = json.loads((folder/'plan.json').read_text(encoding='utf-8'))
sys.path.insert(0, str(base/'starter'))
import runner
import provider

original = json.loads((base/'runs'/f"{plan['original_nonthinking_run']}.json").read_text(encoding='utf-8'))
thinking = json.loads((base/'runs/diagnostics'/f"run-{plan['previous_thinking_run']}.json").read_text(encoding='utf-8'))
extra = json.loads((folder/'prompt-variant-B.json').read_text(encoding='utf-8'))['additional_system_instruction']
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def service(route, payload=None):
    data = None if payload is None else json.dumps(payload,ensure_ascii=False).encode()
    request = urllib.request.Request('http://127.0.0.1:8080/'+route, data=data,
                                     headers={'Content-Type':'application/json'})
    with opener.open(request, timeout=15) as response:
        return json.loads(response.read())

def evaluate(record, passages):
    # 先保存模型结果，再单独读取开发答案；此函数不参与消息构造。
    gold = next(a for a in json.loads((base/'data/dev_answers.json').read_text(encoding='utf-8'))
                if a['id']==record['case_id'])
    message = (record.get('response') or {}).get('choices',[{}])[0].get('message',{})
    content = message.get('content','')
    finish = (record.get('response') or {}).get('choices',[{}])[0].get('finish_reason')
    answer = None
    try:
        answer = json.loads(content)
    except ValueError:
        pass
    valid = (isinstance(answer,dict) and set(answer)=={'answer','citations'} and
             isinstance(answer['answer'],str) and isinstance(answer['citations'],list) and
             all(isinstance(value,str) for value in answer['citations']))
    citations = answer['citations'] if valid else []
    ids_exist = valid and all(value in record['selected_passage_ids'] for value in citations)
    correct = valid and answer['answer'].strip() in gold['aliases']
    by_id = {p['id']:p for p in passages}
    required = gold['evidence_ids']
    snippets = [{'id':p['id'],'text':p['text'].split('。')[0]+'。'} for p in passages]
    if required:
        enough = set(required).issubset(citations)
        citation_basis = '两段分别给出数据与补页依据；必须共同支撑计算或选择。'
    else:
        enough = any(value in by_id and '均未被采集' in by_id[value]['text'] for value in citations)
        citation_basis = '资料明确写资产、设备遥测与推理节点字段均未被采集；区域或耗时不能推定GPU型号。'
    supported = correct and ids_exist and enough
    failures = []
    if record['status']!='ok': failures.append(record['status'])
    if finish=='length': failures.append('输出预算耗尽')
    if not valid: failures.append('没有完整合法的answer/citations JSON')
    if valid and not correct: failures.append('答案不符合公开开发答案和原文')
    if valid and not ids_exist: failures.append('引用ID不属于实际输入')
    if valid and not supported: failures.append('引用不足以支持回答')
    return {'checked_by':'Codex','public_answer_used_for_evaluation_only':True,
            'valid_answer_citations_json':valid,'answer_matches_public_and_text':correct,
            'citation_ids_in_input':ids_exist,'citation_support_sufficient':supported,
            'answer_basis':gold['reason'],'citation_basis':citation_basis,
            'visible_source_sentences':snippets,'public_answer':gold['answer'],
            'answer':answer['answer'] if valid else None,'citations':citations if valid else None,
            'finish_reason':finish,'output_tokens':(record.get('usage') or {}).get('completion_tokens'),
            'elapsed_seconds':record.get('elapsed_seconds'),'failure_reasons':failures,
            'qualified':valid and correct and ids_exist and supported}

def call(case_id, variant, label):
    assert case_id in plan['development_cases']
    assert len(list(folder.glob('run-*.json'))) < 5, '本脚本只执行五次计划调用'
    config = copy.deepcopy(thinking['config'] if variant=='A' else original['config'])
    if variant=='A': config['parameters']['max_tokens']=1024
    case, originals, passages, messages = runner.prepare(case_id,'E','baseline')
    if variant=='B': messages[0]['content'] += '\n'+extra
    if case_id=='D01':
        if variant=='A':
            assert messages==thinking['messages']
            assert {key for key in config['parameters'] if config['parameters'][key]!=thinking['config']['parameters'][key]}=={'max_tokens'}
        else:
            assert config==original['config']
            assert messages[1]==original['messages'][1]
            assert messages[0]['content']==original['messages'][0]['content']+'\n'+extra
    assert json.loads(messages[1]['content'])=={'question':case['question'],'passages':passages}
    erase = service('slots/0?action=erase',{})
    body = {'model':config['model'],'messages':messages,'stream':False,**config['parameters']}
    prompt = service('apply-template',body)['prompt']
    tokens = service('tokenize',{'content':prompt,'add_special':True,'parse_special':True})['tokens']
    record = {'schema_version':1,'run_id':str(uuid.uuid4()),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'case_id':case_id,'split':'dev','condition':'E','variant':'baseline',
              'mode':'local','run_kind':'live_api','experiment_role':'development_diagnostic_round2',
              'diagnostic_label':label,'candidate_setting':variant,'plan_recorded_at':plan['recorded_at'],
              'comparator_run_id':plan['previous_thinking_run'] if variant=='A' else plan['original_nonthinking_run'],
              'config':config,'messages':messages,'original_passage_ids':[p['id'] for p in originals],
              'selected_passage_ids':[p['id'] for p in passages], 'input_characters':sum(len(m['content']) for m in messages),
              'data_sha256':runner.digest((base/'data/cases.json').read_bytes()),
              'dataset_version':json.loads((base/'data/manifest.json').read_text(encoding='utf-8'))['version'],
              'student_sha256':plan['source_hashes']['student.py'],'provider_sha256':plan['source_hashes']['provider.py'],
              'cache_erase':erase,'rendered_prompt':prompt,'rendered_prompt_tokens':len(tokens),'status':'request_pending'}
    path = folder/f"run-{record['run_id']}.json"
    def save(): path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    save()
    build_opener = urllib.request.build_opener
    class CaptureOpener:
        def __init__(self,inner): self.inner=inner
        def open(self,request,*args,**kwargs):
            record['actual_http_request_body']=json.loads(request.data)
            record['raw_http_request_body']=request.data.decode('utf-8')
            return self.inner.open(request,*args,**kwargs)
    urllib.request.build_opener=lambda *args,**kwargs: CaptureOpener(build_opener(*args,**kwargs))
    try:
        record.update(provider.call_model(messages,config))
    except Exception as error:
        record.update(status='driver_exception',error=type(error).__name__,error_detail=str(error),response=None,usage=None,elapsed_seconds=None)
    finally:
        urllib.request.build_opener=build_opener
        save()
    record['transport_body_matches_expected']=record.get('actual_http_request_body')==body
    try: record['server_slot_after_request']=service('slots')
    except Exception as error: record['slot_audit_error']=str(error)
    record['evaluation']=evaluate(record,passages)
    save()
    summary={'case_id':case_id,'candidate':variant,'label':label,'run_id':record['run_id'],
             'path':str(path.relative_to(repo)),'status':record['status'],'evaluation':record['evaluation']}
    print(json.dumps(summary,ensure_ascii=False),flush=True)
    return summary

args=argparse.ArgumentParser()
args.add_argument('--stage',choices=['d01','transfer'],required=True)
stage=args.parse_args().stage
for name,expected in plan['source_hashes'].items():
    assert hashlib.sha256((base/'starter'/name).read_bytes()).hexdigest()==expected
if stage=='d01':
    assert not list(folder.glob('run-*.json'))
    results=[call('D01','A','D01_A_budget1024'),call('D01','B','D01_B_generic_ratio_instruction')]
    (folder/'d01-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
else:
    assert len(list(folder.glob('run-*.json')))==2
    d01=json.loads((folder/'d01-results.json').read_text(encoding='utf-8'))
    a,b=d01
    selected='B' if b['evaluation']['qualified'] else ('A' if a['evaluation']['qualified'] else 'B')
    reason=('B全部评价项合格，按事前规则优先选择较低预算的B' if b['evaluation']['qualified'] else
            ('只有A全部评价项合格，按事前规则选择A' if a['evaluation']['qualified'] else
             'A和B均未全部合格；按事前规则使用低预算B作为未验证改善的候选'))
    selection={'selected':selected,'reason':reason,'selected_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'basis':'plan.json selection_rule and saved D01 evaluations','d01_run_ids':[r['run_id'] for r in d01]}
    (folder/'selection.json').write_text(json.dumps(selection,ensure_ascii=False,indent=2),encoding='utf-8')
    print('SELECTION:',json.dumps(selection,ensure_ascii=False),flush=True)
    results=d01+[call(cid,selected,f'{cid}_selected_{selected}') for cid in ('D02','D03','D04')]
    (folder/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
for relative,expected in plan['old_record_hashes'].items():
    assert hashlib.sha256((base/relative).read_bytes()).hexdigest()==expected
print('PASS source files and all old records unchanged',flush=True)
