"""Qwen3-0.6B固定提示词变体、模板容量检查及最多十二次两步开发调用；技术失败立即停止，不重试。"""
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
experiment=Path(sys.argv[1])
folder=experiment
assert not list(folder.glob('run-*.json')), '已有配对记录，禁止重复调用'
config_fixed=json.loads((experiment/'config.answer.json').read_text(encoding='utf-8'))
design=json.loads((experiment/'execution-details.json').read_text(encoding='utf-8'))
provenance=json.loads((base/'runs/prompts/qwen06_abc_r0/source-validation.json').read_text(encoding='utf-8'))
source_hashes={name:hashlib.sha256((base/'starter'/name).read_bytes()).hexdigest() for name in ('student.py','provider.py','runner.py')}
assert source_hashes==json.loads((folder/'student-source-hashes.json').read_text(encoding='utf-8'))
assert (base/'starter/student.py').read_bytes()==(base/'runs/improve/linked_r0/student-v1.py').read_bytes()
call_order=design['call_order']
assert json.loads((folder/'native-pattern-validation.json').read_text(encoding='utf-8'))['passed']
plan={'source_hashes':source_hashes,'config':config_fixed,'call_order':call_order}
numeric_parameters={k:v for k,v in config_fixed['parameters'].items() if k!='response_format'}
sys.path.insert(0,str(base/'starter'))
import student
import provider
root=Path(os.environ['LOCALAPPDATA'])/'ANTLabLocalModel'
log_id=str(uuid.uuid4())
stdout_path=root/f'logs/answer-form-{log_id}.stdout.log'
stderr_path=root/f'logs/answer-form-{log_id}.stderr.log'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def service(route,body=None):
    assert route in {'health','props','slots','apply-template','tokenize','slots/0?action=erase'}
    data=None if body is None else json.dumps(body,ensure_ascii=False).encode()
    request=urllib.request.Request('http://127.0.0.1:8080/'+route,data=data,headers={'Content-Type':'application/json'})
    with opener.open(request,timeout=15) as response: return json.loads(response.read())

process=None
summary=[]
parents={}
start_times={}
skipped=[]
startup={'record_kind':'historical_replay_answer_form_runtime','recorded_at_utc':datetime.now(timezone.utc).isoformat(),
         'runtime_reference':'基础/runs/setup/62a41e78-da75-48ca-b9a3-d0ec29127825_runtime.json','context':4096,
         'generation_attempts':0,'stopped_on_technical_failure':False}
args=[str(root/'llama-b11429/llama-server.exe'),'-m',str(root/'models/Qwen3-0.6B-Q8_0.gguf'),
      '--host','127.0.0.1','--port','8080','--alias','Qwen3-0.6B-Q8_0','--ctx-size','4096',
      '--parallel','1','--batch-size','128','--ubatch-size','64','--threads','4','--gpu-layers','0',
      '--no-context-shift','--no-warmup','--temp','0.7','--top-p','0.8','--top-k','20','--min-p','0','--presence-penalty','1.5','--repeat-penalty','1.0','--reasoning','off','--seed','42','--predict','256','--slot-save-path',str(root/'diagnostic-cache')]
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


import socket

owned_processes={}
records=[]
def write(name,value):
    (folder/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def check_old():
    hashes=json.loads((folder/'protected-hashes.json').read_text(encoding='utf-8'))
    assert all(hashlib.sha256((repo/p).read_bytes()).hexdigest()==h for p,h in hashes.items())
    assert Path(__file__).read_bytes()==(folder/'snapshot-run_answer_form_pairs.py').read_bytes()
    assert (base/'tests/answer_form_candidate.py').read_bytes()==(folder.parent/'snapshot-answer_form_candidate.py').read_bytes()
def stop_owned(process):
    if process is None:return 'no_process'
    assert owned_processes.get(process.pid) is process,'不停止非本轮进程'
    if process.poll() is None:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait()
    return 'owned_stopped'
assert stop_owned(None)=='no_process'
try:
    with socket.socket() as s:s.settimeout(1);assert s.connect_ex(('127.0.0.1',8080))!=0,'8080已占用，不接管他人服务'
    check_old()
    with (root/'models/Qwen3-0.6B-Q8_0.gguf').open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==provenance['sha256']
    startup['weight_provenance']=provenance
    startup['before_load']=memory_sample();assert startup['before_load']['available_bytes']>=2*1024**3
    with stdout_path.open('wb') as stdout,stderr_path.open('wb') as stderr:process=subprocess.Popen(args,stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
    owned_processes[process.pid]=process;startup['owned_service_pid']=process.pid
    started=time.monotonic();memory_thread=threading.Thread(target=monitor_memory,daemon=True);memory_thread.start()
    while True:
        assert process.poll() is None and not memory_abort.is_set(),'加载/内存失败'
        try:
            if service('health').get('status')=='ok':break
        except (urllib.error.URLError,TimeoutError):pass
        if time.monotonic()-started>120:raise TimeoutError('加载超过120秒')
        time.sleep(.5)
    props=service('props');assert props['default_generation_settings']['n_ctx']==4096 and props['model_alias']==config_fixed['model']
    assert '11429' in props['build_info'] and 'd81235049' in props['build_info']
    assert all(math.isclose(props['default_generation_settings']['params'][k],v,rel_tol=1e-6,abs_tol=1e-6) for k,v in numeric_parameters.items() if k!='max_tokens')
    props['model_path']='%LOCALAPPDATA%/ANTLabLocalModel/models/Qwen3-0.6B-Q8_0.gguf'
    startup.update(props=props,load_seconds=time.monotonic()-started,after_load=memory_sample())
    assert startup['after_load']['available_bytes']>=1024**3
    inputs=json.loads((folder.parent/'historical-replay-inputs-and-schemas.json').read_text(encoding='utf-8'))
    prepared=[]
    for item in call_order:
        data=next(r for r in inputs if r['case_id']==item['case_id'])
        for variant in item['variants']:
            config=json.loads((folder.parent/('config-'+item['case_id']+('-original.json' if variant=='original_schema' else '-constrained.json'))).read_text(encoding='utf-8'))
            messages=student.prepare_messages(data['question'],data['passages'])
            body={'model':config['model'],'messages':messages,'stream':False,**config['parameters']}
            prompt=service('apply-template',body)['prompt']
            assert all(m['content'] in prompt for m in messages) and prompt.endswith('<think>\n\n</think>\n\n')
            tokens=service('tokenize',{'content':prompt,'add_special':True,'parse_special':True})['tokens']
            assert len(tokens)+256<4096
            assert {k:v for k,v in config['parameters'].items() if k!='response_format'}==numeric_parameters
            prepared.append({'case_id':item['case_id'],'variant':variant,'config':config,'messages':messages,'passages':data['passages'],'question':data['question'],'historical_selection_run_id':data['historical_selection_run_id'],'rule':data['rule'],'rendered_prompt':prompt,'input_tokens':len(tokens),'output_budget':256})
    write('preflight.json',{'checked_at':datetime.now().astimezone().isoformat(),'generation_calls':0,'items':prepared})
    write('precall-plan.json',{'recorded_at':datetime.now().astimezone().isoformat(),'original_plan':'../design-plan.json','call_order':call_order,'max_generations':8,'source_hashes':source_hashes,'service_arguments':startup['arguments'],'owned_pid':process.pid,'input_role':'历史重放原段落，只执行回答，不是完整两步流程','native_validation':'native-pattern-validation.json','evaluate_after_all_calls':True})
    write('runtime-before-generation.json',startup)
    print('PREFLIGHT PASS',[(r['case_id'],r['variant'],r['input_tokens']) for r in prepared],flush=True)
    for item in prepared:
        check_old();assert not memory_abort.is_set()
        record={'run_id':str(uuid.uuid4()),'recorded_at':datetime.now().astimezone().isoformat(),'case_id':item['case_id'],'split':'dev','condition':'R0','variant':item['variant'],'run_kind':'live_api','experiment_role':'post_formal_historical_input_answer_form_control','selection_role':'historical_replay_not_reexecuted','historical_selection_run_id':item['historical_selection_run_id'],'config':item['config'],'messages':item['messages'],'used_passages':item['passages'],'original_passage_ids':[p['id'] for p in item['passages']],'input_tokens':item['input_tokens'],'rendered_prompt':item['rendered_prompt'],'total_capacity':item['input_tokens']+256,'source_hashes':source_hashes,'weight_provenance':provenance,'status':'request_pending'}
        path=folder/('run-'+record['run_id']+'.json');assert not path.exists()
        save=lambda:path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        record['cache_erase']=service('slots/0?action=erase',{});save()
        body={'model':item['config']['model'],'messages':item['messages'],'stream':False,**item['config']['parameters']}
        build_opener=urllib.request.build_opener
        class Capture:
            def __init__(self,inner):self.inner=inner
            def open(self,request,*a,**kw):
                record['actual_http_request_body']=json.loads(request.data);record['raw_http_request_body']=request.data.decode()
                assert record['actual_http_request_body']==body and body['max_tokens']==256
                record['request_verified_before_send']=True;save()
                try:return self.inner.open(request,*a,**kw)
                except urllib.error.HTTPError as e:record['raw_http_error_body']=e.read().decode('utf-8',errors='replace');raise
        urllib.request.build_opener=lambda *a,**kw:Capture(build_opener(*a,**kw))
        try:
            assert startup['generation_attempts']<8;startup['generation_attempts']+=1
            record.update(provider.call_model(item['messages'],item['config']))
        except Exception as e:record.update(status='driver_exception',error=repr(e),response=None)
        finally:urllib.request.build_opener=build_opener;save()
        if record['status']!='ok' or not isinstance(record.get('response'),dict) or not record['response'].get('choices'):raise RuntimeError('技术请求失败:'+record['run_id'])
        record['slot_after']=service('slots');params=record['slot_after'][0]['params']
        record['parameter_checks']={k:math.isclose(params[k],v,rel_tol=1e-6,abs_tol=1e-6) for k,v in numeric_parameters.items() if k in params and k!='max_tokens'}
        record['parameters_not_echoed']=[k for k in numeric_parameters if k not in params]+['response_format','effective_n_predict_max']
        record['request_budget_note']='序列化请求max_tokens=256；finish_reason不当预算回显。'
        save();assert all(record['parameter_checks'].values())
        records.append({'case_id':item['case_id'],'variant':item['variant'],'run_id':record['run_id'],'content':record['response']['choices'][0]['message'].get('content',''),'elapsed_seconds':record['elapsed_seconds'],'finish_reason':record['response']['choices'][0]['finish_reason']})
        write('result-index.json',records);print(json.dumps(records[-1],ensure_ascii=False),flush=True)
    startup['all_calls_completed']=len(records)==8
except Exception as e:
    startup.update(stopped_on_technical_failure=True,error=type(e).__name__,error_detail=str(e));print('STOPPED',repr(e),flush=True)
finally:
    memory_stop.set()
    if memory_thread is not None:memory_thread.join(timeout=5)
    startup['cleanup_result']=stop_owned(process)
    startup['server_stopped']=process is not None and process.poll() is not None
    startup['memory_abort']=memory_abort.is_set();startup['after_stop']=memory_sample();write('runtime.json',startup)
    for source,name in [(stderr_path,'server-log.txt'),(stdout_path,'server-stdout.txt')]:
        if source.exists():(folder/name).write_text(source.read_text(encoding='utf-8',errors='replace').replace(str(root),'%LOCALAPPDATA%\\ANTLabLocalModel'),encoding='utf-8')
    print('FINAL',startup['generation_attempts'],'SERVICE STOPPED',startup['server_stopped'],flush=True)
