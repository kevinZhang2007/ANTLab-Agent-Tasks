"""历史证据输入的0.6B/3B固定回答对照；单模型驻留，最多八次。"""
from pathlib import Path
from datetime import datetime
import copy,ctypes,hashlib,json,math,os,re,socket,subprocess,sys,threading,time,urllib.request,urllib.error,uuid

repo=Path(__file__).resolve().parents[2];base=repo/'基础';folder=Path(sys.argv[1]);parent=folder.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def write(name,value):(folder/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert not list(folder.glob('run-*.json')),'已有请求，不重复执行'
assert read(folder/'native-pattern-validation.json')['passed']
plan=read(parent/'design-plan.json');inputs={r['case_id']:r for r in read(parent/'inputs-and-schemas.json')['rows']};configs=read(parent/'config.base.json');sources=read(parent/'model-sources.json')
root=Path(os.environ['LOCALAPPDATA'])/'ANTLabLocalModel'
sys.path.insert(0,str(base/'starter'));import student,provider
models={'0.6B':{'file':'Qwen3-0.6B-Q8_0.gguf','alias':'Qwen3-0.6B-Q8_0'},'3B':{'file':'qwen2.5-3b-instruct-q4_k_m.gguf','alias':'Qwen2.5-3B-Instruct-Q4_K_M'}}
runtime={'started_at':datetime.now().astimezone().isoformat(),'generation_attempts':0,'generation_calls':0,'stopped_on_technical_failure':False,'sessions':[],'prior_cumulative_calls':162,'input_kind':'historical_evidence_selection_replay'}
process=None;current=None;current_model=None;monitor=None;stop=None;abort=None;index=[];capacities={}
class MemoryStatus(ctypes.Structure):
    _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ['total_phys','available_phys','total_page','available_page','total_virtual','available_virtual','extended']]
class ProcessMemory(ctypes.Structure):
    _fields_=[('cb',ctypes.c_ulong),('faults',ctypes.c_ulong)]+[(n,ctypes.c_size_t) for n in ['peak_working','working','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile','private']]
def memory():
    s=MemoryStatus();s.length=ctypes.sizeof(s);assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s))
    row={'at':datetime.now().astimezone().isoformat(),'available_bytes':s.available_phys,'available_gib':s.available_phys/1024**3}
    if process is not None and process.poll() is None:
        p=ProcessMemory();p.cb=ctypes.sizeof(p)
        if ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(int(process._handle)),ctypes.byref(p),p.cb):row.update(working_set_bytes=p.working,private_bytes=p.private,peak_working_set_bytes=p.peak_working)
    return row
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def service(route,body=None):
    assert route in {'health','props','slots','apply-template','tokenize','slots/0?action=erase'}
    request=urllib.request.Request('http://127.0.0.1:8080/'+route,data=None if body is None else json.dumps(body,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
    with opener.open(request,timeout=10) as response:return json.loads(response.read())
def check_running():
    assert not abort.is_set(),'连续3次低于1GiB，停止'
    assert process.poll() is None,'服务退出:'+str(process.poll())
    log=(folder/current['stderr_file']).read_text(encoding='utf-8',errors='replace')
    errors=[line for line in log.splitlines() if re.search(r'failed to allocate|allocation failed|out of memory|bad_alloc|cannot allocate',line,re.I)]
    if errors:current['allocation_errors']=errors;raise RuntimeError('分配失败')
def watch():
    low=0
    while not stop.is_set():
        row=memory();current['memory_samples'].append(row)
        with (folder/current['memory_file']).open('a',encoding='utf-8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
        low=low+1 if row['available_bytes']<1024**3 else 0
        if low>=3:
            abort.set();current['low_memory_stop']=row
            if process.poll() is None and process.pid==current['owned_pid']:process.terminate()
            return
        stop.wait(2)
def stop_service():
    global process,monitor,current_model
    if process is None:return
    stop.set()
    if monitor is not None:monitor.join(timeout=3)
    if process.pid==current['owned_pid'] and process.poll() is None:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait()
    current['stopped']=process.poll() is not None;current['exit_code']=process.poll();current['after_stop']=memory()
    write('session-'+str(current['index'])+'.json',current);write('runtime-progress.json',runtime)
    process=None;current_model=None;time.sleep(1)
def start_service(model):
    global process,current,current_model,stop,abort,monitor
    assert process is None
    with socket.socket() as s:s.settimeout(1);assert s.connect_ex(('127.0.0.1',8080))!=0,'8080已占用，不接管'
    n=len(runtime['sessions'])+1
    current={'index':n,'model':model,'before_load':memory(),'memory_samples':[],'stdout_file':f'server-{n}.stdout.txt','stderr_file':f'server-{n}.stderr.txt','memory_file':f'memory-{n}.jsonl'}
    runtime['sessions'].append(current)
    assert current['before_load']['available_bytes']>=1024**3,'加载前低于1GiB'
    m=models[model]
    args=[str(root/'llama-b11429/llama-server.exe'),'-m',str(root/'models'/m['file']),'--host','127.0.0.1','--port','8080','--alias',m['alias'],'--ctx-size','4096','--parallel','1','--batch-size','128','--ubatch-size','64','--threads','4','--gpu-layers','0','--no-context-shift','--no-warmup','--temp','0.7','--top-p','0.8','--top-k','20','--min-p','0','--presence-penalty','1.5','--repeat-penalty','1.0','--seed','42','--predict','256','--slot-save-path',str(root/'diagnostic-cache')]
    if model=='0.6B':args+=['--reasoning','off']
    current['arguments']=[a.replace(str(root),'%LOCALAPPDATA%/ANTLabLocalModel') for a in args]
    write('session-'+str(n)+'-before-load.json',current)
    begin=time.perf_counter()
    with (folder/current['stdout_file']).open('wb') as out,(folder/current['stderr_file']).open('wb') as err:process=subprocess.Popen(args,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
    current['owned_pid']=process.pid;write('session-'+str(n)+'-owned.json',{'pid':process.pid,'model':model})
    stop=threading.Event();abort=threading.Event();monitor=threading.Thread(target=watch,daemon=True);monitor.start()
    while True:
        check_running()
        try:
            if service('health').get('status')=='ok':break
        except urllib.error.HTTPError as e:
            if e.code!=503:raise
        except (urllib.error.URLError,TimeoutError):pass
        if time.perf_counter()-begin>120:raise TimeoutError('加载120秒未就绪')
        time.sleep(.5)
    current.update(load_seconds=time.perf_counter()-begin,after_load=memory())
    write('session-'+str(n)+'-loaded.json',current)
    assert current['after_load']['available_bytes']>=1024**3,'加载后低于1GiB，不生成'
    props=service('props');assert props['default_generation_settings']['n_ctx']==4096 and props['total_slots']==1 and props['model_alias']==m['alias'] and props['build_info']=='b11429-d81235049'
    for k,v in configs['parameters'].items():
        if k not in {'response_format','max_tokens'}:assert math.isclose(props['default_generation_settings']['params'][k],v,rel_tol=1e-6,abs_tol=1e-6)
    assert math.isclose(props['default_generation_settings']['params']['repeat_penalty'],1.0)
    props['model_path']='%LOCALAPPDATA%/ANTLabLocalModel/models/'+m['file'];current['props']=props;current_model=model
    write('session-'+str(n)+'.json',current)
    print('READY',model,'memory',current['after_load']['available_gib'],flush=True)
def body_for(cid,model):
    data=inputs[cid];config=copy.deepcopy(configs);config['model']=models[model]['alias'];config['parameters']['response_format']['json_schema']['schema']=data['schema']
    return config,{'model':config['model'],'messages':data['messages'],'stream':False,**config['parameters']}
def capacity(cid,model):
    config,body=body_for(cid,model);prompt=service('apply-template',body)['prompt'];assert all(m['content'] in prompt for m in body['messages'])
    if model=='0.6B':assert prompt.endswith('<think>\n\n</think>\n\n')
    else:assert prompt.endswith('<|im_start|>assistant\n') and '<think>' not in prompt and '--reasoning' not in current['arguments']
    tokens=service('tokenize',{'content':prompt,'add_special':True,'parse_special':True})['tokens']
    row={'case_id':cid,'model':model,'input_tokens':len(tokens),'output_budget':256,'total':len(tokens)+256,'fits':len(tokens)+256<=4096,'rendered_prompt':prompt,'messages':body['messages'],'config':config}
    capacities[model+'-'+cid]=row;write('template-capacity.json',{'counts_as_generation':False,'rows':list(capacities.values())});assert row['fits'],'完整输入容量超限'
    return row
try:
    protected=read(folder/'protected-hashes.json');allowed=read(folder/'allowed-code-change.json')
    assert all(digest(repo/p)==(allowed['new_sha256'] if p==allowed['path'] else h) for p,h in protected.items())
    native=read(folder/'native-pattern-validation.json')
    assert len(native['tests'])==41 and native['checked_model_vocabulary']=='Qwen2.5-3B-Instruct-Q4_K_M'
    for n,h in native['dll_sha256'].items():assert digest(root/'llama-b11429'/n)==h
    original=read(base/'runs/answer_form/20261013-195237/config-D02-original.json')['parameters']['response_format']['json_schema']['schema']
    assert inputs['D02']['schema']==inputs['D04']['schema']==original
    assert inputs['D01']['schema']==read(base/'runs/answer_form/20261013-195237/schema-self-percent.json')
    assert inputs['D03']['schema']==read(base/'runs/answer_form/20261013-195237/schema-self-number.json')
    for model,m in models.items():
        assert digest(root/'models'/m['file'])==sources[model]['sha256'],'权重哈希不一致'
    write('verified-sources.json',{'recorded_at':datetime.now().astimezone().isoformat(),'sources':sources,'both_weight_hashes_verified':True,'native_dll_hashes_verified':True,'schemas_match_native_checked_inputs':True,'initial_memory':memory()})
    start_service('3B')
    for cid in inputs:capacity(cid,'3B')
    stop_service();start_service('0.6B')
    for cid in inputs:capacity(cid,'0.6B')
    write('precall-plan.json',{'recorded_at':datetime.now().astimezone().isoformat(),'original_plan':'../design-plan.json','call_order':plan['call_order'],'both_models_capacity_passed':True,'generation_limit':8,'native_schema_checks_passed':True,'parameters_unchanged':True})
    for item in plan['call_order']:
        cid=item['case_id'];model=item['model']
        if current_model!=model:stop_service();start_service(model)
        check_running();row=capacity(cid,model);config,body=body_for(cid,model)
        run={'run_id':str(uuid.uuid4()),'recorded_at':datetime.now().astimezone().isoformat(),'case_id':cid,'condition':'R0','variant':model,'model':model,'run_kind':'live_api','input_kind':'historical_evidence_selection_replay','config':config,'messages':body['messages'],'used_passages':inputs[cid]['passages'],'source_path':inputs[cid]['source_path'],'source_sha256':inputs[cid]['source_sha256'],'weight_source':sources[model],'input_tokens':row['input_tokens'],'capacity_total':row['total'],'context':4096,'memory_before_request':memory(),'session_index':current['index'],'status':'prepared'}
        name='run-'+run['run_id']+'.json';write(name,run)
        assert run['memory_before_request']['available_bytes']>=1024**3,'请求前低于1GiB'
        run['cache_erase']=service('slots/0?action=erase',{})
        saved_opener=urllib.request.build_opener
        class CaptureOpener:
            def __init__(self,inner):self.inner=inner
            def open(self,request,*a,**kw):
                actual=json.loads(request.data);assert actual==body and actual['max_tokens']==256
                run['actual_http_request_body']=actual;run['raw_http_request_body']=request.data.decode('utf-8');run['actual_send_at']=datetime.now().astimezone().isoformat();write(name,run)
                return self.inner.open(request,*a,**kw)
        urllib.request.build_opener=lambda *a,**kw:CaptureOpener(saved_opener(*a,**kw))
        try:
            assert runtime['generation_attempts']<8;runtime['generation_attempts']+=1
            run.update(provider.call_model(body['messages'],config))
        finally:urllib.request.build_opener=saved_opener;run['memory_after_request']=memory();write(name,run)
        if isinstance(run.get('response'),dict) and run['response'].get('choices'):runtime['generation_calls']+=1
        else:runtime['failed_request_generation_uncertain']=bool(run.get('actual_http_request_body'))
        assert run['status']=='ok' and run.get('response',{}).get('choices'),'请求技术失败，不重试'
        params=service('slots')[0]['params'];run['parameter_checks']={k:math.isclose(params[k],v,rel_tol=1e-6,abs_tol=1e-6) for k,v in configs['parameters'].items() if k in params and k not in {'response_format','max_tokens'}}
        run['parameter_checks']['repeat_penalty']=math.isclose(params['repeat_penalty'],1.0)
        run['parameters_not_echoed']=[k for k in configs['parameters'] if k not in params]+['effective_n_predict_max','compiled_grammar']
        run['schema_enforcement_proof']={'native_validation':'native-pattern-validation.json','same_dll_hashes_verified':True,'chatml_source':'基础/runs/format/schema_r0/official-chat.cpp.txt','actual_schema_matches_native_checked':True,'grammar_not_echoed_by_props':True}
        run['finish_reason']=run['response']['choices'][0]['finish_reason'];write(name,run);assert all(run['parameter_checks'].values());check_running()
        index.append({'case_id':cid,'variant':model,'run_id':run['run_id']});write('result-index.json',index);write('runtime-progress.json',runtime)
        print(json.dumps({'case_id':cid,'model':model,'content':run['response']['choices'][0]['message'].get('content'),'elapsed_seconds':run['elapsed_seconds']},ensure_ascii=False),flush=True)
    runtime['all_calls_completed']=len(index)==8
except Exception as error:runtime.update(stopped_on_technical_failure=True,error_type=type(error).__name__,error_detail=str(error));print('STOPPED',repr(error),flush=True)
finally:
    stop_service();runtime['owned_services_stopped']=all(s.get('stopped',False) for s in runtime['sessions']);runtime['after_stop']=memory();runtime['finished_at']=datetime.now().astimezone().isoformat();runtime['cumulative_generation_calls']=162+runtime['generation_calls'];write('runtime.json',runtime)
    print(json.dumps({'completed':len(index),'generation_calls':runtime['generation_calls'],'cumulative':runtime['cumulative_generation_calls'],'error':runtime.get('error_detail'),'services_stopped':runtime['owned_services_stopped']},ensure_ascii=False),flush=True)
