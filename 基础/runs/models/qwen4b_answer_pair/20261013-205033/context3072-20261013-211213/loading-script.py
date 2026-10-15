"""一次3072上下文尝试；通过加载及容量核查后仅请求D01一次。"""
from pathlib import Path
from datetime import datetime
import ctypes,hashlib,json,os,re,socket,subprocess,threading,time,urllib.request,urllib.error

repo=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');base=repo/'基础';parent=base/'runs/models/qwen4b_answer_pair/20261013-205033'
now=datetime.now().astimezone();folder=parent/('context3072-' +now.strftime('%Y%m%d-%H%M%S'));folder.mkdir(parents=True,exist_ok=False)
def write(name,value):(folder/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def digest(p):
    with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
protected={p.relative_to(repo).as_posix():digest(p) for p in repo.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts and p.name!='config.local.json' and folder not in p.parents}
write('protected-hashes.json',protected)
plan={'revised_at':now.isoformat(),'original_plan':'基础/runs/models/qwen4b_answer_pair/20261013-205033/design-plan.json','previous_attempt':'基础/runs/models/qwen4b_answer_pair/20261013-205033/load-revised-20261013-210834/loading-result.json','old_context':4096,'new_context':3072,'reason':'用户授权一次降低上下文的低内存尝试，其余服务与生成参数不变；不把修订追溯成旧计划。','stop_rule':'每0.5秒采样，一次低于1GiB立即停止自有服务；分配失败、崩溃、容量超限或技术错误保存停止，不重试。','scope':'仅D01原定配对输入的最终回答阶段；健康就绪后先检查实际4B模板及完整输入加256预算，最多一次生成。','prior_generation_count':162,'expected':'上下文减少可能降低KV等内存占用，能否就绪及生成仍未验证。','old_records_preserved':True,'not_comparable_to_original_4096_pair':'本次3072属于单独资源修订，不混入原8次配对。'}
write('resource-plan-revision.json',plan)
(folder/'loading-script.py').write_bytes(Path(__file__).read_bytes())
root=Path(os.environ['LOCALAPPDATA'])/'ANTLabLocalModel';weight=root/'models/Qwen3-4B-Q4_K_M.gguf'
source=json.loads((parent/'locked-source.json').read_text(encoding='utf-8'))['official_metadata']
args=[str(root/'llama-b11429/llama-server.exe'),'-m',str(weight),'--host','127.0.0.1','--port','8080','--alias','Qwen3-4B-Q4_K_M','--ctx-size','3072','--parallel','1','--batch-size','128','--ubatch-size','64','--threads','4','--gpu-layers','0','--no-context-shift','--no-warmup','--temp','0.7','--top-p','0.8','--top-k','20','--min-p','0','--presence-penalty','1.5','--repeat-penalty','1.0','--reasoning','off','--seed','42','--predict','256','--slot-save-path',str(root/'diagnostic-cache')]
write('service-arguments.json',{'recorded_at':datetime.now().astimezone().isoformat(),'arguments':[a.replace(str(root),'%LOCALAPPDATA%/ANTLabLocalModel') for a in args],'generation_limit':1})
class MemoryStatus(ctypes.Structure):
    _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ['total_phys','available_phys','total_page','available_page','total_virtual','available_virtual','extended']]
class ProcessMemory(ctypes.Structure):
    _fields_=[('cb',ctypes.c_ulong),('faults',ctypes.c_ulong)]+[(n,ctypes.c_size_t) for n in ['peak_working','working','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile','private']]
process=None;stop=threading.Event();abort=threading.Event();monitor=None
state={'started_at':datetime.now().astimezone().isoformat(),'status':'preparing','generation_calls':0,'health_checks':[],'memory_samples':[],'cumulative_generation_calls':162}
def memory():
    s=MemoryStatus();s.length=ctypes.sizeof(s);assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s))
    row={'measured_at':datetime.now().astimezone().isoformat(),'available_bytes':s.available_phys,'available_gib':s.available_phys/1024**3,'total_bytes':s.total_phys}
    if process is not None and process.poll() is None:
        counters=ProcessMemory();counters.cb=ctypes.sizeof(counters)
        if ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(int(process._handle)),ctypes.byref(counters),counters.cb):row.update(working_set_bytes=counters.working,private_bytes=counters.private,peak_working_set_bytes=counters.peak_working)
        else:row['process_memory']='unknown'
    return row
def watch():
    while not stop.is_set():
        row=memory();state['memory_samples'].append(row)
        with (folder/'memory-samples.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
        if row['available_bytes']<1024**3:
            state['low_memory_observed']=row;abort.set()
            if process is not None and process.pid==state.get('owned_pid') and process.poll() is None:process.terminate()
            return
        stop.wait(.5)
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def endpoint(route):
    assert route in {'health','props'}
    with opener.open('http://127.0.0.1:8080/'+route,timeout=3) as response:return json.loads(response.read())
stderr=folder/'server-stderr.txt';stdout=folder/'server-stdout.txt'
allocation=re.compile(r'failed to allocate|allocation failed|out of memory|bad_alloc|cannot allocate',re.I)
def check_running():
    assert not abort.is_set(),'可用物理内存低于1GiB，停止'
    assert process.poll() is None,'服务退出，exit_code='+str(process.poll())
    log=stderr.read_text(encoding='utf-8',errors='replace') if stderr.exists() else ''
    errors=[line for line in log.splitlines() if allocation.search(line)]
    if errors:state['allocation_errors']=errors;raise RuntimeError('服务日志报告内存分配失败')
try:
    assert weight.stat().st_size==source['Bytes'] and digest(weight)==source['SHA256'],'锁定权重校验失败'
    state['weight_verified']={'bytes':source['Bytes'],'sha256':source['SHA256'],'revision':source['Revision']}
    with socket.socket() as s:s.settimeout(1);assert s.connect_ex(('127.0.0.1',8080))!=0,'已有8080服务，不接管或停止'
    state['before_load']=memory();assert state['before_load']['available_bytes']>=1024**3,'加载前已低于1GiB'
    state['server_binary_sha256']=digest(root/'llama-b11429/llama-server.exe')
    write('before-load.json',state)
    begun=time.perf_counter()
    with stdout.open('wb') as out,stderr.open('wb') as err:process=subprocess.Popen(args,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
    state['owned_pid']=process.pid;write('owned-service.json',{'pid':process.pid,'started_at':datetime.now().astimezone().isoformat()})
    monitor=threading.Thread(target=watch,daemon=True);monitor.start()
    while True:
        check_running()
        try:
            health=endpoint('health');state['health_checks'].append({'at':datetime.now().astimezone().isoformat(),'response':health})
            if health.get('status')=='ok':break
        except urllib.error.HTTPError as e:
            state['health_checks'].append({'at':datetime.now().astimezone().isoformat(),'http_status':e.code})
            if e.code!=503:raise
        except (urllib.error.URLError,TimeoutError):pass
        if time.perf_counter()-begun>120:raise TimeoutError('加载120秒内未就绪')
        time.sleep(.5)
    state.update(load_seconds=time.perf_counter()-begun,after_ready=memory(),ready_at=datetime.now().astimezone().isoformat())
    assert state['after_ready']['available_bytes']>=1024**3
    props=endpoint('props');assert props['default_generation_settings']['n_ctx']==3072
    assert props['model_alias']=='Qwen3-4B-Q4_K_M' and props['build_info']=='b11429-d81235049'
    props['model_path']='%LOCALAPPDATA%/ANTLabLocalModel/models/Qwen3-4B-Q4_K_M.gguf'
    state['props']=props;write('ready-state.json',state)
    print(json.dumps({'ready':True,'load_seconds':state['load_seconds'],'before':state['before_load'],'after':state['after_ready']},ensure_ascii=False),flush=True)
    observed=time.perf_counter()
    while time.perf_counter()-observed<20:
        check_running();time.sleep(.5)
    state['health_after_observation']=endpoint('health');state['after_observation']=memory();check_running()
    import copy,sys,uuid,math
    sys.path.insert(0,str(base/'starter'));sys.path.insert(0,str(base/'tests'))
    import student,provider,answer_form_candidate as form
    historical=base/'runs/two_step_linked_form/20261013-202853/task-D01.json'
    task=json.loads(historical.read_text(encoding='utf-8'));question=task['question'];passages=task['used_passages']
    config=json.loads((base/'runs/two_step_linked_form/20261013-202853/config.answer.json').read_text(encoding='utf-8'))
    config['model']='Qwen3-4B-Q4_K_M'
    schema,rule=form.constrain_schema(question,config['parameters']['response_format']['json_schema']['schema'])
    config['parameters']['response_format']['json_schema']['schema']=schema
    messages=student.prepare_messages(question,copy.deepcopy(passages))
    body={'model':config['model'],'messages':messages,'stream':False,**config['parameters']}
    assert body['max_tokens']==256
    def nongeneration(route,payload):
        assert route in {'apply-template','tokenize','slots/0?action=erase'}
        request=urllib.request.Request('http://127.0.0.1:8080/'+route,data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
        with opener.open(request,timeout=15) as response:return json.loads(response.read())
    prompt=nongeneration('apply-template',body)['prompt']
    assert all(m['content'] in prompt for m in messages) and prompt.endswith('<think>\n\n</think>\n\n')
    tokens=nongeneration('tokenize',{'content':prompt,'add_special':True,'parse_special':True})['tokens']
    write('d01-capacity.json',{'checked_at':datetime.now().astimezone().isoformat(),'input_tokens':len(tokens),'output_budget':256,'total':len(tokens)+256,'context':3072,'fits':len(tokens)+256<=3072,'rendered_prompt':prompt,'counts_as_generation':False,'complete_passages_preserved':True})
    assert len(tokens)+256<=3072,'完整输入加预算超限，不截断'
    defaults=state['props']['default_generation_settings']['params']
    for k,v in config['parameters'].items():
        if k not in {'response_format','max_tokens'}:assert math.isclose(defaults[k],v,rel_tol=1e-6,abs_tol=1e-6)
    run={'run_id':str(uuid.uuid4()),'recorded_at':datetime.now().astimezone().isoformat(),'case_id':'D01','condition':'R0','model':'4B','run_kind':'live_api','input_kind':'historical_evidence_selection_replay','context':3072,'config':config,'messages':messages,'question':question,'used_passages':passages,'source_path':historical.relative_to(repo).as_posix(),'source_sha256':digest(historical),'weight_revision':source['Revision'],'weight_sha256':source['SHA256'],'schema_rule':rule,'status':'prepared','memory_before_request':memory()}
    recordfile='run-'+run['run_id']+'.json';write(recordfile,run)
    write('precall-config.json',{'recorded_at':datetime.now().astimezone().isoformat(),'config':config,'service_arguments':args,'max_generation_calls':1,'capacity_passed':True,'student_sha256':digest(base/'starter/student.py'),'provider_sha256':digest(base/'starter/provider.py'),'schema_rule_sha256':digest(base/'tests/answer_form_candidate.py')})
    check_running();assert run['memory_before_request']['available_bytes']>=1024**3
    run['cache_erase']=nongeneration('slots/0?action=erase',{})
    saved_opener=urllib.request.build_opener
    class CaptureOpener:
        def __init__(self,inner):self.inner=inner
        def open(self,request,*a,**kw):
            actual=json.loads(request.data);assert actual==body
            run['actual_http_request_body']=actual;run['raw_http_request_body']=request.data.decode('utf-8');run['actual_send_at']=datetime.now().astimezone().isoformat();write(recordfile,run)
            return self.inner.open(request,*a,**kw)
    urllib.request.build_opener=lambda *a,**kw:CaptureOpener(saved_opener(*a,**kw))
    try:
        assert state['generation_calls']==0
        state['generation_attempts']=1
        run.update(provider.call_model(messages,config))
    finally:
        urllib.request.build_opener=saved_opener
        run['memory_after_request']=memory();write(recordfile,run)
    if isinstance(run.get('response'),dict) and run['response'].get('choices'):
        state['generation_calls']=1;state['cumulative_generation_calls']=163
        run['finish_reason']=run['response']['choices'][0]['finish_reason'];run['raw_content']=run['response']['choices'][0]['message'].get('content');write(recordfile,run)
    else:state['generation_result_uncertain']=bool(run.get('actual_http_request_body'))
    state['generation_run_id']=run['run_id']
    assert run['status']=='ok' and state['generation_calls']==1,'实际请求技术失败，不重试'
    check_running()
    state['status']='single_d01_request_completed'

except Exception as error:state.update(status='stopped_on_resource_or_technical_failure',error_type=type(error).__name__,error_detail=str(error))
finally:
    stop.set()
    if monitor is not None:monitor.join(timeout=3)
    if process is not None and process.pid==state.get('owned_pid') and process.poll() is None:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait()
    state['owned_service_stopped']=process is not None and process.poll() is not None
    state['exit_code']=process.poll() if process is not None else None
    state['after_stop']=memory();state['finished_at']=datetime.now().astimezone().isoformat()
    state['minimum_available_gib']=min([r['available_gib'] for r in state['memory_samples']]+[state['after_stop']['available_gib']])
    write('loading-result.json',state)
    changed=[p for p,h in protected.items() if digest(repo/p)!=h]
    write('old-file-audit.json',{'checked_at':datetime.now().astimezone().isoformat(),'protected_file_count':len(protected),'changed_old_files':changed});assert not changed
    print(json.dumps({'folder':str(folder),'status':state['status'],'error':state.get('error_detail'),'load_seconds':state.get('load_seconds'),'after_ready':state.get('after_ready'),'after_observation':state.get('after_observation'),'minimum_available_gib':state['minimum_available_gib'],'owned_service_stopped':state['owned_service_stopped'],'generation_calls':state['generation_calls']},ensure_ascii=False,indent=2),flush=True)
