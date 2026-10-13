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
experiment=base/'runs/two_step/dev_r0'
folder=experiment
assert not list(folder.glob('run-*.json')), '已有配对记录，禁止重复调用'
config_fixed=json.loads((experiment/'config.answer.json').read_text(encoding='utf-8'))
design=json.loads((experiment/'execution-details.json').read_text(encoding='utf-8'))
provenance=json.loads((base/'runs/prompts/qwen06_abc_r0/source-validation.json').read_text(encoding='utf-8'))
source_hashes={name:hashlib.sha256((base/'starter'/name).read_bytes()).hexdigest() for name in ('student.py','provider.py','runner.py')}
assert source_hashes==json.loads((folder/'student-source-hashes.json').read_text(encoding='utf-8'))
assert (base/'starter/student.py').read_bytes()==(base/'runs/improve/linked_r0/student-v1.py').read_bytes()
call_order=design['call_order']
import two_step_candidate as candidate
config_selection=json.loads((folder/'config.selection.json').read_text(encoding='utf-8'))
assert candidate.SELECTION_PROMPT==(folder/'system.selection.txt').read_text(encoding='utf-8')
assert candidate.SELECTION_SCHEMA==json.loads((folder/'schema.selection.json').read_text(encoding='utf-8'))
assert json.loads((folder/'offline-check.json').read_text(encoding='utf-8'))['passed']
plan={'source_hashes':source_hashes,'config':config_fixed,'call_order':call_order}
numeric_parameters={k:v for k,v in config_fixed['parameters'].items() if k!='response_format'}
sys.path.insert(0,str(base/'starter'))
import student
import provider
capacity=json.loads((base/'runs/capacity/stage3/inputs.json').read_text(encoding='utf-8'))
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
startup={'record_kind':'two_step_development_runtime','recorded_at_utc':datetime.now(timezone.utc).isoformat(),
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

try:
    # 权重再次核对；不下载、不改变已选代码。
    with (root/'models/Qwen3-0.6B-Q8_0.gguf').open('rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==provenance['sha256']
    startup['before_load']=memory_sample()
    assert startup['before_load']['available_bytes']>=2*1024**3, '可用内存不足2 GiB，停止本轮加载'
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
    props['model_path']='%LOCALAPPDATA%/ANTLabLocalModel/models/Qwen3-0.6B-Q8_0.gguf'
    startup['props']=props
    startup['candidate_default_parameter_checks']={key:math.isclose(props['default_generation_settings']['params'][key],value,rel_tol=1e-6,abs_tol=1e-6) for key,value in numeric_parameters.items() if key!='max_tokens'}
    startup['default_check_scope']='sampling defaults only; request budget checked in serialized body'
    assert all(startup['candidate_default_parameter_checks'].values()), '生成前候选参数未生效'
    assert startup['after_load']['available_bytes']>=1024**3 if 'after_load' in startup else True
    startup['load_seconds']=time.monotonic()-started
    startup['after_load']=memory_sample()
    template=props.get('chat_template')
    assert isinstance(template,str) and '<|im_start|>' in template and '<|im_end|>' in template, '未识别模型自己的ChatML模板'
    assert 'enable_thinking' in template or '<think>' in template, '未识别Qwen3自己的思考模板'
    assert props.get('model_alias')==config_fixed['model'], '模型别名不一致'
    preflight=[]
    inputs={}
    for cid in ('D01','D02','D03','D04'):
        row=next(r for r in capacity['rows'] if r['case_id']==cid and r['condition']=='R0')
        payload=json.loads(row['messages'][1]['content'])
        ordered=student.improve(payload['question'],copy.deepcopy(payload['passages']))
        inputs[cid]={'question':payload['question'],'original':payload['passages'],'ordered':ordered}
        for label,messages,config in [
            ('answer_full',student.prepare_messages(payload['question'],ordered),config_fixed),
            ('selection_full',candidate.prepare_selection_messages(payload['question'],ordered),config_selection),
            ('answer_empty',student.prepare_messages(payload['question'],[]),config_fixed)]:
            request_body={'model':config['model'],'messages':messages,'stream':False,**config['parameters']}
            prompt=service('apply-template',request_body)['prompt']
            assert all(m['content'] in prompt for m in messages)
            assert prompt.endswith('<think>\n\n</think>\n\n')
            tokens=service('tokenize',{'content':prompt,'add_special':True,'parse_special':True})['tokens']
            preflight.append({'case_id':cid,'input_kind':label,'input_tokens':len(tokens),'with_budget':len(tokens)+256,'messages':messages,'rendered_prompt':prompt})
            assert len(tokens)+256<4096
    (folder/'preflight.json').write_text(json.dumps({'checked_at':datetime.now().astimezone().isoformat(),'counts_as_generation':False,'schema_unique_items_checked_locally':True,'actual_stage2_checked_again_before_send':True,'rows':preflight},ensure_ascii=False,indent=2),encoding='utf-8')
    plan.update(recorded_at=datetime.now().astimezone().isoformat(),stage1_config=config_selection,service_arguments=startup['arguments'],generation_limit=12,evaluation='No answer file read until driver has ended all scheduled calls',order=call_order)
    (folder/'precall-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    (folder/'runtime-before-generation.json').write_text(json.dumps(startup,ensure_ascii=False,indent=2),encoding='utf-8')
    print('PREFLIGHT PASS',[(p['case_id'],p['input_kind'],p['input_tokens']) for p in preflight],flush=True)

    def save_parent(parent):
        path=folder/('task-'+parent['parent_request_id']+'.json')
        path.write_text(json.dumps(parent,ensure_ascii=False,indent=2),encoding='utf-8')

    def finish_parent(key,parent,status):
        parent['status']=status
        parent['ended_at']=datetime.now().astimezone().isoformat()
        parent['end_to_end_seconds']=time.perf_counter()-start_times[key]
        save_parent(parent)
        (folder/'task-results.json').write_text(json.dumps(list(parents.values()),ensure_ascii=False,indent=2),encoding='utf-8')

    def validate_answer(content,passages):
        try:parsed=json.loads(content,object_pairs_hook=candidate.unique_fields)
        except (ValueError,TypeError):parsed=None
        valid=isinstance(parsed,dict) and set(parsed)=={'answer','citations'} and isinstance(parsed.get('answer'),str) and isinstance(parsed.get('citations'),list) and all(isinstance(c,str) for c in parsed['citations'])
        citations=parsed['citations'] if valid else []
        return {'format_complete':valid,'citation_ids_exist':bool(citations) and all(c in {p['id'] for p in passages} for c in citations),'parsed':parsed}

    for item in call_order:
        key=(item['case_id'],item['variant'])
        data=inputs[item['case_id']]
        if item['stage']=='answer' and item['variant']=='candidate' and not parents[key]['selection_validation']['valid']:
            skipped.append({**item,'reason':'定位输出非法；不执行第二步、不回退'})
            continue
        assert startup['generation_attempts']<12
        if memory_abort.is_set():raise RuntimeError('内存不足，停止')
        for name,digest in source_hashes.items():assert hashlib.sha256((base/'starter'/name).read_bytes()).hexdigest()==digest
        assert hashlib.sha256((base/'tests/two_step_candidate.py').read_bytes()).hexdigest()==json.loads((folder/'offline-check.json').read_text(encoding='utf-8'))['module_sha256']
        used=(candidate.select_original_passages(data['ordered'],parents[key]['selection_validation']) if item['variant']=='candidate' and item['stage']=='answer' else copy.deepcopy(data['ordered']))
        assert all(p in data['ordered'] for p in used)
        messages=(candidate.prepare_selection_messages(data['question'],used) if item['stage']=='selection' else student.prepare_messages(data['question'],used))
        assert json.loads(messages[1]['content'])=={'question':data['question'],'passages':used}
        config=copy.deepcopy(config_selection if item['stage']=='selection' else config_fixed)
        body={'model':config['model'],'messages':messages,'stream':False,**config['parameters']}
        prompt=service('apply-template',body)['prompt']
        assert all(m['content'] in prompt for m in messages)
        tokens=service('tokenize',{'content':prompt,'add_special':True,'parse_special':True})['tokens']
        assert len(tokens)+256<4096,'本次完整输入超限；不删段或改配置'
        erase=service('slots/0?action=erase',{})
        if key not in parents:
            parents[key]={'parent_request_id':str(uuid.uuid4()),'case_id':item['case_id'],'condition':'R0','variant':item['variant'],'started_at':datetime.now().astimezone().isoformat(),'original_passages':data['original'],'ordered_passages':data['ordered'],'question':data['question'],'stage_run_ids':[],'status':'pending'}
        parent=parents[key]
        record={'schema_version':1,'run_id':str(uuid.uuid4()),'parent_request_id':parent['parent_request_id'],'utc':datetime.now(timezone.utc).isoformat(),'case_id':item['case_id'],'split':'dev','condition':'R0','variant':item['variant'],'stage':item['stage'],'execution_index':item['index'],'mode':'local','run_kind':'live_api','experiment_role':'two_step_development','config':config,'context':4096,'messages':messages,'original_passages':data['original'],'used_passages':used,'original_passage_ids':[p['id'] for p in data['original']],'selected_passage_ids':[p['id'] for p in used],'rendered_prompt':prompt,'rendered_prompt_tokens':len(tokens),'weight_sha256':provenance['sha256'],'model_revision':provenance['revision'],'source_hashes':source_hashes,'driver_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'cache_erase':erase,'status':'request_pending'}
        path=folder/f"run-{record['run_id']}.json"
        assert not path.exists()
        def save():path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
        save()
        parent['stage_run_ids'].append(record['run_id']);save_parent(parent)
        build_opener=urllib.request.build_opener
        class CaptureOpener:
            def __init__(self,inner):self.inner=inner
            def open(self,request,*args,**kwargs):
                record['actual_http_request_body']=json.loads(request.data)
                record['raw_http_request_body']=request.data.decode('utf-8')
                assert record['actual_http_request_body']==body and record['actual_http_request_body']['max_tokens']==256
                record['request_verified_before_send']=True
                try:return self.inner.open(request,*args,**kwargs)
                except urllib.error.HTTPError as error:
                    record['raw_http_error_body']=error.read().decode('utf-8',errors='replace');raise
        urllib.request.build_opener=lambda *args,**kwargs:CaptureOpener(build_opener(*args,**kwargs))
        if key not in start_times:start_times[key]=time.perf_counter()
        try:
            startup['generation_attempts']+=1
            record.update(provider.call_model(messages,config))
        except Exception as error:
            record.update(status='driver_exception',error=type(error).__name__,error_detail=str(error),response=None,usage=None)
        finally:
            urllib.request.build_opener=build_opener;save()
        technical=record['status']!='ok' or not isinstance(record.get('response'),dict) or not record['response'].get('choices')
        if technical:
            startup['stopped_on_technical_failure']=True
            finish_parent(key,parent,'technical_failure')
            print('TECHNICAL FAILURE',record['run_id'],record['status'],flush=True)
            break
        record['server_slot_after_request']=service('slots')
        params=record['server_slot_after_request'][0]['params']
        record['parameter_checks']={k:math.isclose(params[k],v,rel_tol=1e-6,abs_tol=1e-6) for k,v in numeric_parameters.items() if k in params}
        record['parameters_not_echoed']=[k for k in numeric_parameters if k not in params]+['response_format','effective_n_predict_max']
        record['request_budget_observation']={'actual_body_max_tokens':record['actual_http_request_body']['max_tokens'],'task_max_tokens_echo':params.get('max_tokens'),'task_n_predict_echo':params.get('n_predict'),'finish_reason_is_not_budget_echo':True}
        save();assert all(record['parameter_checks'].values()),'请求参数未生效，停止'
        message=record['response']['choices'][0]['message'];content=message.get('content','')
        if item['stage']=='selection':
            validation=candidate.validate_selection(content,used)
            record['selection_validation']=validation;parent['selection_validation']=validation
            parent['raw_selection_content']=content
            if not validation['valid']:finish_parent(key,parent,'selection_output_failure')
            else:save_parent(parent)
        else:
            validation=validate_answer(content,used)
            record['answer_validation']=validation;parent['answer_validation']=validation
            parent['raw_final_content']=content;parent['final_used_passages']=used
            finish_parent(key,parent,'completed')
        save()
        summary.append({'run_id':record['run_id'],**item,'status':record['status'],'content':content,'elapsed_seconds':record['elapsed_seconds']})
        (folder/'stage-results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(summary[-1],ensure_ascii=False),flush=True)
    startup['completed_tasks']=sum(p['status'] in ['completed','selection_output_failure'] for p in parents.values())
    startup['planned_tasks']=8
    startup['skipped_calls']=skipped
    startup['all_planned_tasks_finished']=startup['completed_tasks']==8 and not startup['stopped_on_technical_failure']
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
    (folder/'stage-results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print('FINAL ATTEMPTS:',startup['generation_attempts'],'SERVICE STOPPED:',startup['server_stopped'],flush=True)
