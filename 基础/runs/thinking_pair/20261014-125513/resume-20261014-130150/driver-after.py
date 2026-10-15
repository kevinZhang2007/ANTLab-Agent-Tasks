"""同预算思考模式独立对照；历史原文重放，最多八次。"""
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
startup={'record_kind':'post_formal_same_budget_thinking_runtime','recorded_at_utc':datetime.now(timezone.utc).isoformat(),
         'runtime_reference':'基础/runs/setup/62a41e78-da75-48ca-b9a3-d0ec29127825_runtime.json','context':4096,
         'generation_attempts':0,'stopped_on_technical_failure':False}
args=[str(root/'llama-b11429/llama-server.exe'),'-m',str(root/'models/Qwen3-0.6B-Q8_0.gguf'),
      '--host','127.0.0.1','--port','8080','--alias','Qwen3-0.6B-Q8_0','--ctx-size','4096',
      '--parallel','1','--batch-size','128','--ubatch-size','64','--threads','4','--gpu-layers','0',
      '--no-context-shift','--no-warmup','--temp','0.7','--top-p','0.8','--top-k','20','--min-p','0','--presence-penalty','1.5','--repeat-penalty','1.0','--reasoning','on','--seed','42','--predict','1024','--slot-save-path',str(root/'diagnostic-cache')]
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
    allowed=json.loads((folder/'allowed-code-change.json').read_text(encoding='utf-8'))
    assert all(hashlib.sha256((repo/p).read_bytes()).hexdigest()==(allowed['sha256'] if p==allowed['path'] else h) for p,h in protected.items())
    hashes=json.loads((folder/'pre-generation-code-hashes.json').read_text(encoding='utf-8'))
    assert all(hashlib.sha256((repo/p).read_bytes()).hexdigest()==h for p,h in hashes.items())

def audited_template(cid, thinking, body, label):
    evidence={'recorded_at':datetime.now().astimezone().isoformat(),'case_id':cid,'thinking':thinking,'counts_as_generation':False,'template_http':{'route':'apply-template','method':'POST','actual_request_body':body}}
    filename='template-evidence-'+label+'.json'
    write(filename,evidence)
    def audited_call(route,payload,key):
        data=json.dumps(payload,ensure_ascii=False).encode('utf-8')
        evidence[key]={'route':route,'method':'POST','raw_request_body':data.decode('utf-8'),'actual_request_body':payload};write(filename,evidence)
        request=urllib.request.Request('http://127.0.0.1:8080/'+route,data=data,headers={'Content-Type':'application/json'})
        try:
            with opener.open(request,timeout=15) as response:
                raw=response.read().decode('utf-8');evidence[key].update(http_status=response.status,raw_response=raw);write(filename,evidence)
                parsed=json.loads(raw);evidence[key]['parsed_response']=parsed;write(filename,evidence);return parsed
        except Exception as error:
            evidence[key]['error']=repr(error)
            if isinstance(error,urllib.error.HTTPError):evidence[key]['raw_error_response']=error.read().decode('utf-8',errors='replace')
            write(filename,evidence);raise
    template=audited_call('apply-template',body,'template_http');prompt=template['prompt']
    evidence['rendered_prompt']=prompt;write(filename,evidence)
    (folder/('rendered-'+label+'.txt')).write_text(prompt,encoding='utf-8')
    token_response=audited_call('tokenize',{'content':prompt,'add_special':True,'parse_special':True},'tokenize_http')
    tokens=token_response['tokens'];evidence.update(input_tokens=len(tokens),output_budget=1024,total_capacity=len(tokens)+1024);write(filename,evidence)
    # 证据已保存，以下才核验；开模式不预填think起始标签是本机模板的实际分支。
    model_template=startup['props']['chat_template']
    marker='<|im_start|>assistant\n';disabled='<think>\n\n</think>\n\n';position=prompt.rfind(marker)
    suffix=prompt[position+len(marker):] if position>=0 else None
    checks={'switch_boolean_and_matches_mode':type(body['chat_template_kwargs']['enable_thinking']) is bool and body['chat_template_kwargs']['enable_thinking']==thinking,
        'input_messages_retained':all(m['content'] in prompt for m in body['messages']),
        'actual_model_template_has_disabled_branch':'if enable_thinking is defined and enable_thinking is false' in model_template,
        'assistant_boundary_present':position>=0,
        'branch_matches_actual_template':suffix==('' if thinking else disabled),
        'actual_request_budget_1024':body['max_tokens']==1024,
        'complete_input_fits':len(tokens)+1024<=4096}
    evidence.update(actual_generation_suffix=suffix,checks=checks,verified=all(checks.values()),not_echoed=['实际enable_thinking内部布尔状态','本次编译grammar与PEG parser对象']);write(filename,evidence)
    assert all(checks.values()),'模板开关、原文、分支或容量核验失败，完整证据见'+filename
    return prompt,tokens,evidence

def call_stage(cid,stage,question,used,original,config,messages=None):
    record={'run_id':str(uuid.uuid4()),'recorded_at':datetime.now().astimezone().isoformat(),
        'case_id':cid,'condition':'R0','split':'dev','stage':stage,'run_kind':'live_api',
        'experiment_role':'post_formal_development_historical_evidence_replay','config':copy.deepcopy(config),
        'weight_sha256':provenance['sha256'],'model_revision':provenance['revision'],
        'original_passages':original,'used_passages':copy.deepcopy(used),'source_hashes':source_hashes,
        'status':'preparing','context':4096,'driver_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    path=folder/('run-'+record['run_id']+'.json');assert not path.exists()
    save=lambda:path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    record['messages']=messages if messages is not None else student.prepare_messages(question,used)
    budget=config['parameters']['max_tokens'];assert budget==1024
    body={'model':config['model'],'messages':record['messages'],'stream':False,**config['parameters']}
    prompt,tokens,template_evidence=audited_template(cid,config['parameters']['chat_template_kwargs']['enable_thinking'],body,record['run_id'])
    record['template_evidence_file']='template-evidence-'+record['run_id']+'.json'
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
        assert startup['generation_attempts']<8
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
    stored=json.loads((folder/'inputs-messages-schemas.json').read_text(encoding='utf-8'));inputs={r['case_id']:r for r in stored['rows']};preflight=[]
    for item in call_order:
        cid=item['case_id'];thinking=item['thinking'];data=inputs[cid]
        conf=copy.deepcopy(config_fixed);conf['parameters']['response_format']['json_schema']['schema']=data['schema'];conf['parameters']['chat_template_kwargs']={'enable_thinking':thinking}
        assert conf['parameters']['max_tokens']==1024
        body={'model':conf['model'],'messages':data['messages'],'stream':False,**conf['parameters']}
        label=cid+('-on' if thinking else '-off')
        prompt,tokens,template_evidence=audited_template(cid,thinking,body,label)
        row={'case_id':cid,'thinking':thinking,'config':conf,'messages':data['messages'],'rendered_prompt':prompt,'input_tokens':len(tokens),'output_budget':1024,'total':len(tokens)+1024,'actual_generation_suffix':template_evidence['actual_generation_suffix'],'template_evidence_file':'template-evidence-'+label+'.json'}
        preflight.append(row);write('template-capacity.json',{'checked_at':datetime.now().astimezone().isoformat(),'counts_as_generation':False,'rows':preflight});assert row['total']<=4096,'完整输入加1024超限，不截断'
    pairs=[]
    for cid in inputs:
        off=next(r for r in preflight if r['case_id']==cid and not r['thinking']);on=next(r for r in preflight if r['case_id']==cid and r['thinking'])
        left=copy.deepcopy(off['config']);right=copy.deepcopy(on['config']);left['parameters'].pop('chat_template_kwargs');right['parameters'].pop('chat_template_kwargs')
        checks={'same_messages':off['messages']==on['messages'],'same_schema_sampling_and_budget':left==right,'only_disabled_block_differs':off['rendered_prompt']==on['rendered_prompt']+'<think>\n\n</think>\n\n'}
        pairs.append({'case_id':cid,'checks':checks,'off_evidence':off['template_evidence_file'],'on_evidence':on['template_evidence_file']})
        write('paired-template-verification.json',{'checked_at':datetime.now().astimezone().isoformat(),'pairs':pairs,'not_a_generation':True});assert all(checks.values()),'两侧模板差异不符合源码分支'
    write('precall-plan.json',{'recorded_at':datetime.now().astimezone().isoformat(),'order':call_order,'generation_limit':8,'both_output_budgets':1024,'service_arguments':startup['arguments'],'request_level_switch':'chat_template_kwargs.enable_thinking布尔值','actual_template_difference_verified':True,'same_schema_accepted_by_apply_template':True,'evaluation_after_all_calls':True})
    write('runtime-before-generation.json',startup);print('PREFLIGHT PASS',[(r['case_id'],r['thinking'],r['total']) for r in preflight],flush=True)
    index=[]
    for item in call_order:
        cid=item['case_id'];thinking=item['thinking'];variant='thinking_on' if thinking else 'thinking_off';data=inputs[cid];row=next(r for r in preflight if r['case_id']==cid and r['thinking']==thinking)
        record=call_stage(cid,variant,data['question'],data['passages'],data['passages'],row['config'],row['messages'])
        message=record['response']['choices'][0]['message']
        write('output-'+record['run_id']+'.json',{'source_run_id':record['run_id'],'thinking':thinking,'raw_message':message,'content':message.get('content'),'reasoning_content':message.get('reasoning_content'),'message_fields':list(message),'usage':record.get('usage'),'finish_reason':record['response']['choices'][0]['finish_reason'],'no_answer_or_citation_repair':True})
        index.append({'case_id':cid,'variant':variant,'run_id':record['run_id']});write('result-index.json',index)
    startup['all_calls_completed']=len(index)==8
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
