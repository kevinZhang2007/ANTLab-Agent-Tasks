"""按资源计划修订仅加载及健康检查；不调用生成接口。"""
from pathlib import Path
from datetime import datetime
import ctypes,hashlib,json,os,re,socket,subprocess,threading,time,urllib.request,urllib.error

repo=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');base=repo/'基础';parent=base/'runs/models/qwen4b_answer_pair/20261013-205033'
now=datetime.now().astimezone();folder=parent/('load-revised-'+now.strftime('%Y%m%d-%H%M%S'));folder.mkdir(parents=True,exist_ok=False)
def write(name,value):(folder/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def digest(p):
    with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
protected={p.relative_to(repo).as_posix():digest(p) for p in repo.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts and p.name!='config.local.json' and folder not in p.parents}
write('protected-hashes.json',protected)
plan={'revised_at':now.isoformat(),'original_plan':'基础/runs/models/qwen4b_answer_pair/20261013-205033/design-plan.json','original_before_load_threshold_gib':5.25,'new_decision':'用户授权在约4.58GiB可用内存下受控尝试加载；取消本次加载的5.25GiB启动门槛，保留原记录。','reason':'权重已通过锁定大小与SHA校验；先实测加载资源，不把估计当作失败或安全结论。','scope':'仅加载及health检查，不生成、不执行8次对照。','service_settings':'原4B权重、llama.cpp b11429、4096、CPU单槽4线程、batch128/ubatch64、关闭思考、上下文移位与预热，原采样数值不变。','stop_rule':'每0.5秒采样；一次可用物理内存低于1GiB即停止自有服务，不再等待原连续三次规则；分配失败或服务崩溃保存并停止。','ready_observation_seconds':20,'limitations':'关闭预热，仅就绪状态，不证明生成阶段峰值可用内存足够。','generation_calls':0,'cumulative_generation_calls':162,'old_stop_records_preserved':True}
write('resource-plan-revision.json',plan)
(folder/'loading-script.py').write_bytes(Path(__file__).read_bytes())
root=Path(os.environ['LOCALAPPDATA'])/'ANTLabLocalModel';weight=root/'models/Qwen3-4B-Q4_K_M.gguf'
source=json.loads((parent/'locked-source.json').read_text(encoding='utf-8'))['official_metadata']
args=[str(root/'llama-b11429/llama-server.exe'),'-m',str(weight),'--host','127.0.0.1','--port','8080','--alias','Qwen3-4B-Q4_K_M','--ctx-size','4096','--parallel','1','--batch-size','128','--ubatch-size','64','--threads','4','--gpu-layers','0','--no-context-shift','--no-warmup','--temp','0.7','--top-p','0.8','--top-k','20','--min-p','0','--presence-penalty','1.5','--repeat-penalty','1.0','--reasoning','off','--seed','42','--predict','256','--slot-save-path',str(root/'diagnostic-cache')]
write('service-arguments.json',{'recorded_at':datetime.now().astimezone().isoformat(),'arguments':[a.replace(str(root),'%LOCALAPPDATA%/ANTLabLocalModel') for a in args],'generation_endpoint_not_used':True})
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
    assert route in {'health','props'},'禁止生成接口'
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
    props=endpoint('props');assert props['default_generation_settings']['n_ctx']==4096
    assert props['model_alias']=='Qwen3-4B-Q4_K_M' and props['build_info']=='b11429-d81235049'
    props['model_path']='%LOCALAPPDATA%/ANTLabLocalModel/models/Qwen3-4B-Q4_K_M.gguf'
    state['props']=props;write('ready-state.json',state)
    print(json.dumps({'ready':True,'load_seconds':state['load_seconds'],'before':state['before_load'],'after':state['after_ready']},ensure_ascii=False),flush=True)
    observed=time.perf_counter()
    while time.perf_counter()-observed<20:
        check_running();time.sleep(.5)
    state['health_after_observation']=endpoint('health');state['after_observation']=memory();check_running()
    state['status']='loaded_and_health_verified_no_generation'
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
    print(json.dumps({'folder':str(folder),'status':state['status'],'error':state.get('error_detail'),'load_seconds':state.get('load_seconds'),'after_ready':state.get('after_ready'),'after_observation':state.get('after_observation'),'minimum_available_gib':state['minimum_available_gib'],'owned_service_stopped':state['owned_service_stopped'],'generation_calls':0},ensure_ascii=False,indent=2),flush=True)
