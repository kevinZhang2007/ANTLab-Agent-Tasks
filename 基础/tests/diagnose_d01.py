"""执行已记录的四次D01诊断，不修改提示词、不重试。"""
from pathlib import Path
import copy
import datetime
import hashlib
import json
import sys
import urllib.request
import uuid

repo = Path(__file__).resolve().parents[2]
base = repo / '基础'
folder = base / 'runs/diagnostics'
plan = json.loads((folder/'d01-plan.json').read_text(encoding='utf-8'))
original = json.loads((base/'runs'/f"{plan['original_run_id']}.json").read_text(encoding='utf-8'))
if any(folder.glob('run-*.json')):
    raise RuntimeError('已有诊断运行记录，停止以避免重复调用')
for name, expected in plan['source_hashes'].items():
    assert hashlib.sha256((base/'starter'/name).read_bytes()).hexdigest() == expected
sys.path.insert(0, str(base/'starter'))
import provider

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
def service(route, payload=None):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    request = urllib.request.Request('http://127.0.0.1:8080/'+route, data=data,
                                     headers={'Content-Type':'application/json'})
    with opener.open(request, timeout=15) as response:
        return json.loads(response.read())

summary = []
build_opener = urllib.request.build_opener
for index, item in enumerate(plan['ordered_calls'], 1):
    assert index <= 4
    config = copy.deepcopy(original['config'])
    config['parameters'].update(item['changes'])
    changed = {key for key in set(config['parameters'])|set(original['config']['parameters'])
               if config['parameters'].get(key) != original['config']['parameters'].get(key)}
    assert changed == set(item['changes'])
    erase = service('slots/0?action=erase', {})
    template = service('apply-template', {'messages':original['messages'], **item['changes']})
    record = {key:copy.deepcopy(original[key]) for key in (
        'schema_version','case_id','split','condition','variant','data_sha256','dataset_version',
        'student_sha256','provider_sha256','original_passage_ids','selected_passage_ids','messages','input_characters')}
    record.update(run_id=str(uuid.uuid4()), utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  mode='local', run_kind='live_api', experiment_role='diagnostic',
                  diagnostic_label=item['label'], original_run_id=original['run_id'],
                  plan_recorded_at=plan['recorded_at'], changed_factor=item['changed_factor'],
                  changed_parameters=sorted(changed), config=config, cache_erase=erase,
                  rendered_prompt=template['prompt'])
    path = folder/f"run-{record['run_id']}.json"
    assert not path.exists()
    record['status'] = 'request_pending'
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')

    class CaptureOpener:
        def __init__(self, inner):
            self.inner = inner
        def open(self, request, *args, **kwargs):
            record['actual_http_request_body'] = json.loads(request.data)
            record['raw_http_request_body'] = request.data.decode('utf-8')
            return self.inner.open(request, *args, **kwargs)
    def capture_opener(*args, **kwargs):
        return CaptureOpener(build_opener(*args, **kwargs))
    urllib.request.build_opener = capture_opener
    try:
        result = provider.call_model(copy.deepcopy(original['messages']), config)
    except Exception as error:
        result = {'status':'driver_exception','error':type(error).__name__,'error_detail':str(error),
                  'response':None,'elapsed_seconds':None,'usage':None}
    finally:
        urllib.request.build_opener = build_opener
    record.update(result)
    # 先保存所有响应，包括失败；之后的核验不丢弃请求。
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    actual = record.get('actual_http_request_body', {})
    expected = {'model':config['model'],'messages':original['messages'],'stream':False,**config['parameters']}
    record['transport_body_matches_expected'] = actual == expected
    try:
        record['server_slot_after_request'] = service('slots')
    except Exception as error:
        record['slot_audit_error'] = str(error)
    message = (record.get('response') or {}).get('choices', [{}])[0].get('message', {})
    content = message.get('content', '')
    judgment = {'basis':'可见D01 E两段资料：68/85=80%；必要来源为P312446和P898100',
                'checked_by':'Codex','answer_file_used':False,'raw_content':content}
    try:
        answer = json.loads(content)
        judgment.update(valid_json=True, answer=answer.get('answer'), citations=answer.get('citations'),
                        answer_matches_visible_calculation=answer.get('answer')=='80%',
                        citations_in_input=isinstance(answer.get('citations'),list) and all(
                            value in original['selected_passage_ids'] for value in answer['citations']),
                        both_evidence_ids_present=isinstance(answer.get('citations'),list) and
                            set(original['selected_passage_ids']).issubset(answer['citations']))
    except (ValueError, AttributeError):
        judgment['valid_json'] = False
    record['judgment'] = judgment
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    summary.append({'run_id':record['run_id'],'label':item['label'],'path':str(path.relative_to(repo)),
                    'status':record['status'],'elapsed_seconds':record.get('elapsed_seconds'),
                    'message':message,'judgment':judgment,
                    'finish_reason':(record.get('response') or {}).get('choices',[{}])[0].get('finish_reason'),
                    'usage':record.get('usage')})
    print(json.dumps(summary[-1], ensure_ascii=False), flush=True)

for relative, expected in plan['old_record_hashes'].items():
    assert hashlib.sha256((base/relative).read_bytes()).hexdigest() == expected
(folder/'d01-results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS: four calls only; all old records unchanged; no source or prompt changes', flush=True)
