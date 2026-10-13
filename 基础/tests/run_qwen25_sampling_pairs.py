"""Qwen2.5本机加载、模板容量检查及八次开发题配对；技术失败立即停止，不重试。"""
from pathlib import Path
from datetime import datetime, timezone
import copy
import ctypes
import threading
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
experiment=base/'runs/models/qwen25_3b_sampling_r0'
folder=experiment/'after_budget_check_verified'
folder.mkdir(exist_ok=False)
assert not list(folder.glob('run-*.json')), '已有配对记录，禁止重复调用'
config_fixed=json.loads((experiment/'config.candidate.json').read_text(encoding='utf-8'))
design=json.loads((experiment/'design-plan.json').read_text(encoding='utf-8'))
provenance=json.loads((experiment/'source-validation.json').read_text(encoding='utf-8'))
source_hashes={name:hashlib.sha256((base/'starter'/name).read_bytes()).hexdigest() for name in ('student.py','provider.py','runner.py')}
assert source_hashes==design['source_hashes']
assert (base/'starter/student.py').read_bytes()==(base/'runs/improve/linked_r0/student-v1.py').read_bytes()
call_order=[{'index':i+1,'case_id':cid,'condition':'R0','variant':variant} for i,(cid,variant) in enumerate((
    ('D01','baseline'),('D01','improved'),('D02','improved'),('D02','baseline'),
    ('D03','baseline'),('D03','improved'),('D04','improved'),('D04','baseline')))]
plan={'source_hashes':source_hashes,'config':config_fixed,'call_order':call_order}
numeric_parameters={k:v for k,v in config_fixed['parameters'].items() if k!='response_format'}
sys.path.insert(0,str(base/'starter'))
import student
import provider
capacity=json.loads((base/'runs/capacity/stage3/inputs.json').read_text(encoding='utf-8'))
root=Path(os.environ['LOCALAPPDATA'])/'ANTLabLocalModel'
log_id=str(uuid.uuid4())
stdout_path=root/f'logs/qwen25-{log_id}.stdout.log'
stderr_path=root/f'logs/qwen25-{log_id}.stderr.log'
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
    exists=all(v in by_id for v in citations) if usable and citations else None
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
            'citation_support_sufficient':supported,'citations_nonempty':bool(usable and citations),'answer':answer,'citations':citations,
            'answer_basis':gold['reason'],'cited_source_sentences':quotes,'required_source_sentences':required_quotes,
            'additional_citations':[v for v in citations if v not in gold['evidence_ids']] if usable and gold['evidence_ids'] else [],
            'complete_success':valid and correct and exists is True and supported,
            'failure_reasons':failures,'finish_reason':choice.get('finish_reason'),
            'elapsed_seconds':record.get('elapsed_seconds'),'output_tokens':(record.get('usage') or {}).get('completion_tokens')}

process=None
summary=[]
startup={'record_kind':'qwen25_development_runtime','recorded_at_utc':datetime.now(timezone.utc).isoformat(),
         'runtime_reference':'基础/runs/setup/62a41e78-da75-48ca-b9a3-d0ec29127825_runtime.json','context':4096,
         'generation_attempts':0,'stopped_on_technical_failure':False}
args=[str(root/'llama-b11429/llama-server.exe'),'-m',str(root/'models/qwen2.5-3b-instruct-q4_k_m.gguf'),
      '--host','127.0.0.1','--port','8080','--alias','Qwen2.5-3B-Instruct-Q4_K_M','--ctx-size','4096',
      '--parallel','1','--batch-size','128','--ubatch-size','64','--threads','4','--gpu-layers','0',
      '--no-context-shift','--no-warmup','--temp','0.7','--top-p','0.8','--top-k','20','--min-p','0','--presence-penalty','0','--repeat-penalty','1.05','--seed','42','--predict','256','--slot-save-path',str(root/'diagnostic-cache')]
startup['arguments']=[a.replace(str(root),'%LOCALAPPDATA%/ANTLabLocalModel') for a in args]
class MemoryStatus(ctypes.Structure):
    _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(name,ctypes.c_ulonglong) for name in
        ('total_phys','available_phys','total_page','available_page','total_virtual','available_virtual','extended')]
class ProcessMemory(ctypes.Structure):
    _fields_=[('cb',ctypes.c_ulong),('faults',ctypes.c_ulong)]+[(name,ctypes.c_size_t) for name in
        ('peak_working','working','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile','private')]
def memory_sample():
    status=MemoryStatus();status.length=ctypes.sizeof(status)
    assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
    result={'time':datetime.now().astimezone().isoformat(),'available_bytes':status.available_phys,'total_bytes':status.total_phys}
    if process is not None and process.poll() is None:
        counters=ProcessMemory();counters.cb=ctypes.sizeof(counters)
        if ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(int(process._handle)),ctypes.byref(counters),counters.cb):
            result.update(working_set_bytes=counters.working,private_bytes=counters.private)
    return result
memory_stop=threading.Event();memory_abort=threading.Event();memory_thread=None
startup['before_load']=memory_sample();startup['memory_samples']=[]
startup['low_memory_rule']='3 consecutive 2-second samples below 1 GiB; terminate only this model service'
def monitor_memory():
    low=0
    while not memory_stop.is_set():
        sample=memory_sample();startup['memory_samples'].append(sample)
        low=low+1 if sample['available_bytes']<1024**3 else 0
        if low>=3:
            memory_abort.set()
            if process is not None and process.poll() is None:process.terminate()
            return
        memory_stop.wait(2)

try:
    # 权重再次核对；不下载、不改变已选代码。
    with (root/'models/qwen2.5-3b-instruct-q4_k_m.gguf').open('rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==provenance['sha256']
    startup['before_load']=memory_sample()
    assert startup['before_load']['available_bytes']>=4.5*1024**3, '可用内存不足4.5 GiB，停止本轮加载'
    with stdout_path.open('wb') as stdout,stderr_path.open('wb') as stderr:
        process=subprocess.Popen(args,stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
    started=time.monotonic()
    memory_thread=threading.Thread(target=monitor_memory,daemon=True);memory_thread.start()
    while True:
        if memory_abort.is_set():raise RuntimeError('可用内存持续低于1 GiB，停止')
        if process.poll() is not None: raise RuntimeError('服务加载失败')
        try:
            if service('health').get('status')=='ok': break
        except (urllib.error.URLError,TimeoutError): pass
        if time.monotonic()-started>120: raise TimeoutError('启动超时')
        time.sleep(.5)
    props=service('props')
    assert props['default_generation_settings']['n_ctx']==4096
    props['model_path']='%LOCALAPPDATA%/ANTLabLocalModel/models/qwen2.5-3b-instruct-q4_k_m.gguf'
    startup['props']=props
    startup['candidate_default_parameter_checks']={key:math.isclose(props['default_generation_settings']['params'][key],value,rel_tol=1e-6,abs_tol=1e-6) for key,value in numeric_parameters.items() if key!='max_tokens'}
    startup['default_check_scope']='sampling defaults only; request budget checked in serialized body'
    assert all(startup['candidate_default_parameter_checks'].values()), '生成前候选参数未生效'
    assert startup['after_load']['available_bytes']>=1024**3 if 'after_load' in startup else True
    startup['load_seconds']=time.monotonic()-started
    startup['after_load']=memory_sample()
    template=props.get('chat_template')
    assert isinstance(template,str) and '<|im_start|>' in template and '<|im_end|>' in template, '未识别模型自己的ChatML模板'
    assert '<think>' not in template and 'enable_thinking' not in template, '模板不应使用Qwen3思考块'
    preflight=[]
    for item in call_order:
        row=next(r for r in capacity['rows'] if r['case_id']==item['case_id'] and r['condition']=='R0')
        payload=json.loads(row['messages'][1]['content'])
        selected=student.improve(payload['question'],copy.deepcopy(payload['passages'])) if item['variant']=='improved' else copy.deepcopy(payload['passages'])
        messages=student.prepare_messages(payload['question'],selected)
        body={'model':config_fixed['model'],'messages':messages,'stream':False,**config_fixed['parameters']}
        rendered=service('apply-template',body)
        prompt=rendered['prompt']
        assert all(message['content'] in prompt for message in messages), '模板没有完整保留输入'
        assert '<think>' not in prompt, '不能套用Qwen3思考块'
        tokens=service('tokenize',{'content':prompt,'add_special':True,'parse_special':True})['tokens']
        preflight.append({**item,'messages':messages,'rendered_prompt':prompt,'input_tokens':len(tokens),'capacity_with_output':len(tokens)+256})
        assert len(tokens)+256<4096, '完整输入及256预算无法容纳'
    old_capacity=json.loads((base/'runs/models/qwen25_3b_r0/template-capacity.json').read_text(encoding='utf-8'))['rows']
    assert all(x['messages']==next(y for y in old_capacity if y['case_id']==x['case_id'] and y['variant']==x['variant'])['messages'] and x['input_tokens']==next(y for y in old_capacity if y['case_id']==x['case_id'] and y['variant']==x['variant'])['input_tokens'] for x in preflight), '输入或分词与上一轮不一致'
    (folder/'template-capacity.json').write_text(json.dumps({'checked_at':datetime.now().astimezone().isoformat(),'counts_as_generation':False,'chat_template':template,'rows':preflight},ensure_ascii=False,indent=2),encoding='utf-8')
    plan.update(recorded_at=datetime.now().astimezone().isoformat(),purpose='固定配置的四组开发题配对，不预先认定新模型更好',
        prediction_reference='../design-plan.json#prediction',changed_parameters=design['changed_parameters'],design_plan='../design-plan.json',historical_reference='基础/runs/models/qwen25_3b_r0/pair-summary.json',
        evaluation_rules=['HTTP、完整JSON、答案正确、引用ID存在、原文支持分开检查','空引用不算成功；不补字段、引用或答案','公开开发答案只在原响应落盘后评价','人工语义复核另存，不覆盖自动判断'],
        stop_conditions=['固定8次，不因错误重试','技术错误、内存不足、模板或容量检查失败即停止，不补跑','不调参、不跑正式题、完成后停止服务'],
        source_validation='../source-validation.json',capacity_reference='template-capacity.json',model_quantization='Qwen2.5-3B-Instruct Q4_K_M')
    (folder/'execution-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    print('LOAD AND PREFLIGHT PASS',startup['load_seconds'],[(p['case_id'],p['variant'],p['input_tokens']) for p in preflight],flush=True)

    for item in plan['call_order']:
        assert startup['generation_attempts']<8
        if memory_abort.is_set():raise RuntimeError('内存不足，停止请求')
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
                'mode':'local','run_kind':'live_api','experiment_role':'qwen25_paired_development',
                'execution_index':item['index'],'plan_recorded_at':plan['recorded_at'],
                'config':config,'context':4096,'messages':messages,
                'original_passage_ids':[p['id'] for p in original],'selected_passage_ids':[p['id'] for p in selected],
                'original_passages':original,'selected_passages':selected,
                'ranking_scores':[{'id':p['id'],'score':student.relevance_score(payload['question'],p)} for p in original],
                'rendered_prompt':prompt,'rendered_prompt_tokens':len(tokens),
                'weight_sha256':provenance['sha256'],'model_revision':provenance['revision'],
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
                assert record['actual_http_request_body']['max_tokens']==256, '序列化实际请求预算不是256'
                record['request_budget_checked_before_send']=True
                try:
                    return self.inner.open(request,*args,**kwargs)
                except urllib.error.HTTPError as error:
                    record['raw_http_error_body']=error.read().decode('utf-8',errors='replace')
                    raise
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
        record['memory_after_request']=memory_sample()
        record['parameter_checks']={key:math.isclose(params[key],value,rel_tol=1e-6,abs_tol=1e-6) for key,value in numeric_parameters.items() if key in params}
        record['parameters_not_echoed']=[key for key in numeric_parameters if key not in params]+['response_format','effective_n_predict_max']
        record['request_budget_observation']={'actual_body_max_tokens':record['actual_http_request_body']['max_tokens'],'task_max_tokens_echo':params.get('max_tokens'),'task_n_predict_echo':params.get('n_predict'),'effective_limit_not_separately_echoed':True,'finish_reason_is_not_budget_echo':True}
        save()
        assert all(record['parameter_checks'].values()), '请求参数未生效，保存后停止'
        record['evaluation']=evaluate(record,original)
        save()
        summary.append({'run_id':record['run_id'],'case_id':record['case_id'],'variant':record['variant'],
                        'execution_index':record['execution_index'],'status':record['status'],
                        'raw_message':record['response']['choices'][0]['message'],'evaluation':record['evaluation']})
        (folder/'results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'index':record['execution_index'],'run_id':record['run_id'],'case':record['case_id'],'variant':record['variant'],'content':record['response']['choices'][0]['message']['content'],'seconds':record['elapsed_seconds']},ensure_ascii=False),flush=True)
except Exception as error:
    startup.update(stopped_on_technical_failure=True,error=type(error).__name__,error_detail=str(error))
    print('STOPPED:',type(error).__name__,str(error),flush=True)
finally:
    memory_stop.set()
    if memory_thread is not None:memory_thread.join(timeout=5)
    startup['memory_abort']=memory_abort.is_set()
    if process is not None and process.poll() is None:
        process.terminate()
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired: process.kill(); process.wait()
    startup['server_stopped']=process is not None and process.poll() is not None
    startup['after_stop']=memory_sample()
    log=stderr_path.read_text(encoding='utf-8',errors='replace') if stderr_path.exists() else ''
    (folder/'server-log.txt').write_text(log.replace(str(root),'%LOCALAPPDATA%\\ANTLabLocalModel'),encoding='utf-8')
    (folder/'runtime.json').write_text(json.dumps(startup,ensure_ascii=False,indent=2),encoding='utf-8')
    (folder/'results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print('FINAL ATTEMPTS:',startup['generation_attempts'],'SERVICE STOPPED:',startup['server_stopped'],flush=True)
