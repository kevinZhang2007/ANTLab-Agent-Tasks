"""独立证据与计算候选：历史原文重放、同步对照、来源核验及受限计算。"""
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
import evidence_calculation_candidate as evidence
config_evidence=json.loads((folder/'config.evidence.json').read_text(encoding='utf-8'))
assert evidence.EVIDENCE_PROMPT==(folder/'system.evidence.txt').read_text(encoding='utf-8')
assert evidence.EVIDENCE_SCHEMA==json.loads((folder/'schema.evidence.json').read_text(encoding='utf-8'))
assert json.loads((folder/'offline-check.json').read_text(encoding='utf-8'))['passed']
plan={'source_hashes':source_hashes,'config':config_fixed,'call_order':call_order}
numeric_parameters={k:v for k,v in config_fixed['parameters'].items() if k!='response_format'}
sys.path.insert(0,str(base/'starter'))
import student
import provider

root=Path(os.environ['LOCALAPPDATA'])/'ANTLabLocalModel'
log_id=str(uuid.uuid4())
stdout_path=root/f'logs/two-step-{log_id}.stdout.log'
stderr_path=root/f'logs/two-step-{log_id}.stderr.log'
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
startup={'record_kind':'post_formal_evidence_calculation_runtime','recorded_at_utc':datetime.now(timezone.utc).isoformat(),
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

def write(name, value):
    (folder/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def preserved():
    protected=json.loads((folder/'protected-hashes.json').read_text(encoding='utf-8'))
    assert all(hashlib.sha256((repo/p).read_bytes()).hexdigest()==h for p,h in protected.items())
    hashes=json.loads((folder/'pre-generation-code-hashes.json').read_text(encoding='utf-8'))
    assert all(hashlib.sha256((repo/p).read_bytes()).hexdigest()==h for p,h in hashes.items())

def call_stage(cid,stage,question,used,original,config,messages=None):
    record={'run_id':str(uuid.uuid4()),'recorded_at':datetime.now().astimezone().isoformat(),
        'case_id':cid,'condition':'R0','split':'dev','stage':stage,'run_kind':'live_api',
        'experiment_role':'post_formal_development_historical_evidence_replay','config':copy.deepcopy(config),
        'weight_sha256':provenance['sha256'],'model_revision':provenance['revision'],
        'original_passages':original,'used_passages':copy.deepcopy(used),'source_hashes':source_hashes,
        'status':'preparing','context':4096,'driver_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    path=folder/('run-'+record['run_id']+'.json');assert not path.exists()
    save=lambda:path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    record['messages']=messages if messages is not None else (evidence.prepare_evidence_messages(question,used) if stage=='evidence' else student.prepare_messages(question,used))
    budget=config['parameters']['max_tokens'];assert budget==(512 if stage=='evidence' else 256)
    body={'model':config['model'],'messages':record['messages'],'stream':False,**config['parameters']}
    prompt=service('apply-template',body)['prompt']
    assert all(m['content'] in prompt for m in record['messages'])
    assert prompt.endswith('<think>\n\n</think>\n\n')
    tokens=service('tokenize',{'content':prompt,'add_special':True,'parse_special':True})['tokens']
    record.update(rendered_prompt=prompt,input_tokens=len(tokens),total_capacity=len(tokens)+budget)
    save();assert len(tokens)+budget<4096,'实际完整输入超限，不删段'
    assert not memory_abort.is_set();preserved()
    record['cache_erase']=service('slots/0?action=erase',{})
    build_opener=urllib.request.build_opener
    class CaptureOpener:
        def __init__(self,inner):self.inner=inner
        def open(self,request,*args,**kwargs):
            record['actual_http_request_body']=json.loads(request.data)
            record['raw_http_request_body']=request.data.decode('utf-8')
            assert record['actual_http_request_body']==body and body['max_tokens']==budget
            record['request_verified_before_send']=True;save()
            try:return self.inner.open(request,*args,**kwargs)
            except urllib.error.HTTPError as e:
                record['raw_http_error_body']=e.read().decode('utf-8',errors='replace');raise
    urllib.request.build_opener=lambda *a,**kw:CaptureOpener(build_opener(*a,**kw))
    try:
        assert startup['generation_attempts']<12
        startup['generation_attempts']+=1
        record.update(provider.call_model(record['messages'],config))
    except Exception as e:
        record.update(status='driver_exception',error=repr(e),response=None)
    finally:
        urllib.request.build_opener=build_opener;save()
    if record['status']!='ok' or not isinstance(record.get('response'),dict) or not record['response'].get('choices'):
        raise RuntimeError('技术请求失败:'+record['run_id'])
    record['slot_after']=service('slots')
    params=record['slot_after'][0]['params']
    record['parameter_checks']={k:math.isclose(params[k],v,rel_tol=1e-6,abs_tol=1e-6) for k,v in numeric_parameters.items() if k in params and k!='max_tokens'}
    record['parameters_not_echoed']=[k for k in numeric_parameters if k not in params]+['response_format','effective_n_predict_max']
    record['request_budget_observation']={'actual_body_max_tokens':body['max_tokens'],'finish_reason_is_not_budget_echo':True}
    save();assert all(record['parameter_checks'].values()),'请求参数不符'
    print(json.dumps({'case_id':cid,'stage':stage,'run_id':record['run_id'],'content':record['response']['choices'][0]['message'].get('content'),'elapsed_seconds':record['elapsed_seconds']},ensure_ascii=False),flush=True)
    return record


import answer_form_candidate as form
tasks=[]
try:
    with socket.socket() as sock:
        sock.settimeout(1);assert sock.connect_ex(('127.0.0.1',8080))!=0,'已有8080服务，不停止他人服务'
    preserved()
    with (root/'models/Qwen3-0.6B-Q8_0.gguf').open('rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==provenance['sha256']
    startup['weight_provenance']=provenance
    startup['server_binary_sha256']=hashlib.sha256((root/'llama-b11429/llama-server.exe').read_bytes()).hexdigest()
    startup['before_load']=memory_sample();assert startup['before_load']['available_bytes']>=2*1024**3,'可用内存不足2 GiB'
    with stdout_path.open('wb') as stdout,stderr_path.open('wb') as stderr:
        process=subprocess.Popen(args,stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
    startup['owned_pid']=process.pid;write('owned-service.json',{'pid':process.pid,'started_at':datetime.now().astimezone().isoformat(),'arguments':startup['arguments']})
    started=time.monotonic();memory_thread=threading.Thread(target=monitor_memory,daemon=True);memory_thread.start()
    while True:
        if memory_abort.is_set() or process.poll() is not None:raise RuntimeError('服务加载或内存失败')
        try:
            if service('health').get('status')=='ok':break
        except (urllib.error.URLError,TimeoutError):pass
        if time.monotonic()-started>120:raise TimeoutError('加载超过120秒')
        time.sleep(.5)
    props=service('props');assert props['default_generation_settings']['n_ctx']==4096
    assert props['model_alias']==config_fixed['model']
    assert '11429' in props.get('build_info','') and 'd81235049' in props.get('build_info',''), '同版本服务核对失败'
    defaults=props['default_generation_settings']['params']
    assert all(math.isclose(defaults[k],v,rel_tol=1e-6,abs_tol=1e-6) for k,v in numeric_parameters.items() if k!='max_tokens')
    props['model_path']='%LOCALAPPDATA%/ANTLabLocalModel/models/Qwen3-0.6B-Q8_0.gguf'
    startup.update(props=props,load_seconds=time.monotonic()-started,after_load=memory_sample())
    assert startup['after_load']['available_bytes']>=1024**3
    preflight=[];inputs={}
    for item in call_order:
        cid=item['case_id']
        source=base/'runs/two_step_linked_form/20261013-202853'/('task-'+cid+'.json')
        historic=json.loads(source.read_text(encoding='utf-8'))
        question=historic['question'];used=historic['used_passages']
        conf=copy.deepcopy(config_fixed)
        schema,rule=form.constrain_schema(question,conf['parameters']['response_format']['json_schema']['schema'])
        conf['parameters']['response_format']['json_schema']['schema']=schema
        inputs[cid]={'question':question,'used':used,'answer_config':conf,'source':source.relative_to(repo).as_posix(),'source_hash':hashlib.sha256(source.read_bytes()).hexdigest(),'answer_form_rule':rule}
        probe={'valid':True,'source_verified':True,'raw_structured_evidence':{'target_scope':'容量探针，不用于生成','evidence':[{'passage_id':p['id'],'quote':p['text'],'role':'data'} for p in used],'calculation':{'operation':'none','operands':[]}},'tool_result':None,'scope_and_operation_semantics_verified':False}
        for label,messages,cfg in [('control',student.prepare_messages(question,used),conf),('evidence',evidence.prepare_evidence_messages(question,used),config_evidence),('candidate_capacity_probe',evidence.prepare_final_messages(question,used,probe,student.prepare_messages),conf)]:
            body={'model':cfg['model'],'messages':messages,'stream':False,**cfg['parameters']}
            prompt=service('apply-template',body)['prompt'];assert all(m['content'] in prompt for m in messages) and prompt.endswith('<think>\n\n</think>\n\n')
            tokens=service('tokenize',{'content':prompt,'add_special':True,'parse_special':True})['tokens']
            preflight.append({'case_id':cid,'stage':label,'input_tokens':len(tokens),'output_budget':cfg['parameters']['max_tokens'],'total':len(tokens)+cfg['parameters']['max_tokens'],'messages':messages,'probe_not_sent_for_generation':label=='candidate_capacity_probe'})
            assert preflight[-1]['total']<4096,'容量超限，不截断'
    write('preflight.json',{'checked_at':datetime.now().astimezone().isoformat(),'counts_as_generation':False,'rows':preflight,'actual_candidate_input_rechecked_before_send':True})
    write('precall-plan.json',{'recorded_at':datetime.now().astimezone().isoformat(),'order':call_order,'limit':12,'config_evidence':config_evidence,'config_answer':config_fixed,'service_arguments':startup['arguments'],'input_source_kind':'historical_evidence_selection_replay','public_answers_read_only_after_all_calls':True})
    write('runtime-before-generation.json',startup)
    print('PREFLIGHT PASS',[(r['case_id'],r['stage'],r['total']) for r in preflight],flush=True)
    index=[]
    for item in call_order:
        cid=item['case_id'];data=inputs[cid];used=data['used'];question=data['question']
        task={'case_id':cid,'question':question,'used_passages':used,'input_kind':'historical_evidence_selection_replay','source_path':data['source'],'source_sha256':data['source_hash'],'stages':{},'status':'pending'}
        filename='task-'+cid+'.json';write(filename,task);candidate_start=None
        for stage in item['stages']:
            if stage=='candidate_answer' and not task['validation']['valid']:
                task['stages'][stage]={'status':'not_executed_invalid_evidence','included_in_denominator':True};write(filename,task);continue
            if stage=='evidence':candidate_start=time.perf_counter()
            messages=None;config=config_evidence if stage=='evidence' else data['answer_config']
            if stage=='candidate_answer':messages=evidence.prepare_final_messages(question,used,task['validation'],student.prepare_messages)
            result=call_stage(cid,stage,question,used,used,config,messages)
            raw=result['response']['choices'][0]['message'].get('content','')
            task['stages'][stage]={'run_id':result['run_id'],'raw_content':raw,'http_seconds':result['elapsed_seconds']}
            index.append({'case_id':cid,'stage':stage,'run_id':result['run_id']});write('result-index.json',index)
            if stage=='evidence':
                before=time.perf_counter();task['validation']=evidence.validate_and_calculate(raw,used);task['validation_seconds']=time.perf_counter()-before
                task['candidate_end_to_end_seconds']=time.perf_counter()-candidate_start
            elif stage=='candidate_answer':task['candidate_end_to_end_seconds']=time.perf_counter()-candidate_start
            write(filename,task)
        task['status']='completed' if task['validation']['valid'] else 'candidate_evidence_failure'
        tasks.append(task);write(filename,task);write('task-results.json',tasks)
    startup['all_tasks_finished']=len(tasks)==4
except Exception as e:
    startup.update(stopped_on_technical_failure=True,error=type(e).__name__,error_detail=str(e))
    print('STOPPED:',repr(e),flush=True)
finally:
    memory_stop.set()
    if memory_thread is not None:memory_thread.join(timeout=5)
    if process is not None and process.pid==startup.get('owned_pid') and process.poll() is None:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait()
    startup['server_stopped']=process is not None and process.poll() is not None
    startup['memory_abort']=memory_abort.is_set();startup['after_stop']=memory_sample()
    log=stderr_path.read_text(encoding='utf-8',errors='replace') if stderr_path.exists() else ''
    write('runtime.json',startup)
    (folder/'server-log.txt').write_text(log.replace(str(root),'%LOCALAPPDATA%\\ANTLabLocalModel'),encoding='utf-8')
    if stdout_path.exists():(folder/'server-stdout.txt').write_text(stdout_path.read_text(encoding='utf-8',errors='replace').replace(str(root),'%LOCALAPPDATA%\\ANTLabLocalModel'),encoding='utf-8')
    print('FINAL ATTEMPTS:',startup['generation_attempts'],'STOPPED:',startup['server_stopped'],flush=True)
