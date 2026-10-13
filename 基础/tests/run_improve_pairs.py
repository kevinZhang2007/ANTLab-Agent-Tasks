"""按事前计划运行八次开发题配对；技术失败立即停止，不重试。"""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json
import math
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

repo=Path(__file__).resolve().parents[2]
base=repo/'基础'
folder=base/'runs/improve/dev_r0'
plan=json.loads((folder/'pair-plan.json').read_text(encoding='utf-8'))
assert not list(folder.glob('run-*.json')), '已有配对记录，禁止重复调用'
for name,digest in plan['source_hashes'].items():
    assert hashlib.sha256((base/'starter'/name).read_bytes()).hexdigest()==digest
sys.path.insert(0,str(base/'starter'))
import student
import provider
capacity=json.loads((base/'runs/capacity/stage3/inputs.json').read_text(encoding='utf-8'))
root=Path(os.environ['LOCALAPPDATA'])/'ANTLabLocalModel'
log_id=str(uuid.uuid4())
stdout_path=root/f'logs/improve-{log_id}.stdout.log'
stderr_path=root/f'logs/improve-{log_id}.stderr.log'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def service(route,body=None):
    assert route in {'health','props','slots','apply-template','tokenize','slots/0?action=erase'}
    data=None if body is None else json.dumps(body,ensure_ascii=False).encode()
    request=urllib.request.Request('http://127.0.0.1:8080/'+route,data=data,headers={'Content-Type':'application/json'})
    with opener.open(request,timeout=15) as response: return json.loads(response.read())

def evaluate(record,passages):
    # 公开答案只在原始响应落盘后用于评价，不影响排序、消息或运行顺序。
    gold=next(g for g in json.loads((base/'data/dev_answers.json').read_text(encoding='utf-8')) if g['id']==record['case_id'])
    choice=(record.get('response') or {}).get('choices',[{}])[0]
    content=choice.get('message',{}).get('content','')
    parsed=None
    try: parsed=json.loads(content)
    except ValueError: pass
    valid=(isinstance(parsed,dict) and set(parsed)=={'answer','citations'} and isinstance(parsed.get('answer'),str)
           and isinstance(parsed.get('citations'),list) and all(isinstance(v,str) for v in parsed['citations']))
    answer=parsed.get('answer') if isinstance(parsed,dict) else None
    correct=isinstance(answer,(str,int,float)) and str(answer).strip() in gold['aliases']
    citations=parsed.get('citations') if isinstance(parsed,dict) else None
    usable=isinstance(citations,list) and all(isinstance(v,str) for v in citations)
    by_id={p['id']:p for p in passages}
    exists=all(v in by_id for v in citations) if usable else None
    if gold['evidence_ids']:
        enough=usable and set(gold['evidence_ids']).issubset(citations)
    else:
        enough=usable and any(v in by_id and '均未被采集' in by_id[v]['text'] for v in citations)
    supported=bool(correct and exists and enough)
    quotes=[{'id':v,'source':by_id[v]['source'],'text':by_id[v]['text'].split('。')[0]+'。'}
            for v in citations if v in by_id] if usable else []
    required_quotes=[{'id':p['id'],'text':p['text'].split('。')[0]+'。'} for p in passages
                     if p['id'] in gold['evidence_ids'] or (not gold['evidence_ids'] and '均未被采集' in p['text'])]
    failures=[]
    if not valid: failures.append('answer/citations格式不完整')
    if not correct: failures.append('答案不符合公开答案和原文')
    if usable and not exists: failures.append('引用ID不属于实际输入')
    if not supported: failures.append('引用没有足够支持回答')
    if choice.get('finish_reason')=='length': failures.append('输出预算或容量限制')
    return {'checked_by':'Codex','public_answer_evaluation_only':True,
            'format_complete':valid,'answer_correct':correct,'citation_ids_in_input':exists,
            'citation_support_sufficient':supported,'answer':answer,'citations':citations,
            'answer_basis':gold['reason'],'cited_source_sentences':quotes,'required_source_sentences':required_quotes,
            'additional_citations':[v for v in citations if v not in gold['evidence_ids']] if usable and gold['evidence_ids'] else [],
            'complete_success':valid and correct and exists is True and supported,
            'failure_reasons':failures,'finish_reason':choice.get('finish_reason'),
            'elapsed_seconds':record.get('elapsed_seconds'),'output_tokens':(record.get('usage') or {}).get('completion_tokens')}

process=None
summary=[]
startup={'record_kind':'paired_development_runtime','recorded_at_utc':datetime.now(timezone.utc).isoformat(),
         'runtime_reference':'基础/runs/setup/62a41e78-da75-48ca-b9a3-d0ec29127825_runtime.json','context':4096,
         'generation_attempts':0,'stopped_on_technical_failure':False}
args=[str(root/'llama-b11429/llama-server.exe'),'-m',str(root/'models/Qwen3-0.6B-Q8_0.gguf'),
      '--host','127.0.0.1','--port','8080','--alias','Qwen3-0.6B-Q8_0','--ctx-size','4096',
      '--parallel','1','--batch-size','128','--ubatch-size','64','--threads','4','--gpu-layers','0',
      '--reasoning','off','--no-context-shift','--no-warmup','--slot-save-path',str(root/'diagnostic-cache')]
startup['arguments']=[a.replace(str(root),'%LOCALAPPDATA%/ANTLabLocalModel') for a in args]
try:
    with stdout_path.open('wb') as stdout,stderr_path.open('wb') as stderr:
        process=subprocess.Popen(args,stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
    started=time.monotonic()
    while True:
        if process.poll() is not None: raise RuntimeError('服务加载失败')
        try:
            if service('health').get('status')=='ok': break
        except (urllib.error.URLError,TimeoutError): pass
        if time.monotonic()-started>60: raise TimeoutError('启动超时')
        time.sleep(.5)
    props=service('props')
    assert props['default_generation_settings']['n_ctx']==4096
    props['model_path']='%LOCALAPPDATA%/ANTLabLocalModel/models/Qwen3-0.6B-Q8_0.gguf'
    startup['props']=props
    for item in plan['call_order']:
        assert startup['generation_attempts']<8
        for name,digest in plan['source_hashes'].items():
            assert hashlib.sha256((base/'starter'/name).read_bytes()).hexdigest()==digest
        row=next(r for r in capacity['rows'] if r['case_id']==item['case_id'] and r['condition']=='R0')
        payload=json.loads(row['messages'][1]['content'])
        original=copy.deepcopy(payload['passages'])
        selected=student.improve(payload['question'],copy.deepcopy(original)) if item['variant']=='improved' else copy.deepcopy(original)
        assert len(selected)==len(original)==7 and all(selected.count(p)==original.count(p) for p in original)
        messages=student.prepare_messages(payload['question'],selected)
        assert messages[0]==row['messages'][0]
        config=copy.deepcopy(plan['config'])
        erase=service('slots/0?action=erase',{})
        body={'model':config['model'],'messages':messages,'stream':False,**config['parameters']}
        prompt=service('apply-template',body)['prompt']
        tokens=service('tokenize',{'content':prompt,'add_special':True,'parse_special':True})['tokens']
        assert len(tokens)+256<4096
        record={'schema_version':1,'run_id':str(uuid.uuid4()),'utc':datetime.now(timezone.utc).isoformat(),
                'case_id':item['case_id'],'split':'dev','condition':'R0','variant':item['variant'],
                'mode':'local','run_kind':'live_api','experiment_role':'paired_development_improve',
                'execution_index':item['index'],'plan_recorded_at':plan['recorded_at'],
                'config':config,'context':4096,'messages':messages,
                'original_passage_ids':[p['id'] for p in original],'selected_passage_ids':[p['id'] for p in selected],
                'original_passages':original,'selected_passages':selected,
                'ranking_scores':[{'id':p['id'],'score':student.relevance_score(payload['question'],p)} for p in original],
                'rendered_prompt':prompt,'rendered_prompt_tokens':len(tokens),
                'student_sha256':plan['source_hashes']['student.py'],'provider_sha256':plan['source_hashes']['provider.py'],
                'cache_erase':erase,'status':'request_pending'}
        path=folder/f"run-{record['run_id']}.json"
        assert not path.exists()
        def save(): path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
        save()
        build_opener=urllib.request.build_opener
        class CaptureOpener:
            def __init__(self,inner): self.inner=inner
            def open(self,request,*args,**kwargs):
                record['actual_http_request_body']=json.loads(request.data)
                record['raw_http_request_body']=request.data.decode('utf-8')
                return self.inner.open(request,*args,**kwargs)
        urllib.request.build_opener=lambda *args,**kwargs: CaptureOpener(build_opener(*args,**kwargs))
        try:
            startup['generation_attempts']+=1
            record.update(provider.call_model(messages,config))
        except Exception as error:
            record.update(status='driver_exception',error=type(error).__name__,error_detail=str(error),response=None,usage=None,elapsed_seconds=None)
        finally:
            urllib.request.build_opener=build_opener
            save()
        record['actual_body_matches_expected']=record.get('actual_http_request_body')==body
        technical=record['status']!='ok' or not isinstance(record.get('response'),dict) or not record['response'].get('choices')
        if technical:
            startup['stopped_on_technical_failure']=True
            summary.append({'run_id':record['run_id'],'case_id':record['case_id'],'variant':record['variant'],'status':record['status'],'technical_failure':True})
            save()
            print('TECHNICAL FAILURE:',json.dumps(summary[-1],ensure_ascii=False),flush=True)
            break
        record['server_slot_after_request']=service('slots')
        params=record['server_slot_after_request'][0]['params']
        record['parameter_checks']={key:math.isclose(params[key],value,rel_tol=1e-6,abs_tol=1e-6) for key,value in config['parameters'].items()}
        record['evaluation']=evaluate(record,original)
        save()
        summary.append({'run_id':record['run_id'],'case_id':record['case_id'],'variant':record['variant'],
                        'execution_index':record['execution_index'],'status':record['status'],
                        'raw_message':record['response']['choices'][0]['message'],'evaluation':record['evaluation']})
        (folder/'results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(summary[-1],ensure_ascii=False),flush=True)
except Exception as error:
    startup.update(stopped_on_technical_failure=True,error=type(error).__name__,error_detail=str(error))
    print('STOPPED:',type(error).__name__,str(error),flush=True)
finally:
    if process is not None and process.poll() is None:
        process.terminate()
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired: process.kill(); process.wait()
    startup['server_stopped']=process is not None and process.poll() is not None
    log=stderr_path.read_text(encoding='utf-8',errors='replace') if stderr_path.exists() else ''
    (folder/'server-log.txt').write_text(log.replace(str(root),'%LOCALAPPDATA%\\ANTLabLocalModel'),encoding='utf-8')
    (folder/'runtime.json').write_text(json.dumps(startup,ensure_ascii=False,indent=2),encoding='utf-8')
    (folder/'results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print('FINAL ATTEMPTS:',startup['generation_attempts'],'SERVICE STOPPED:',startup['server_stopped'],flush=True)
