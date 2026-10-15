"""只管理本轮自有模型和基础页面进程；模型生成只能来自页面提交。"""
from pathlib import Path
from http.server import HTTPServer
import argparse, ctypes, json, math, os, socket, subprocess, sys, threading, time

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'基础/starter/provider.py').is_file())
sys.path.insert(0,str(ROOT/'基础/starter'))
from server_exploration import Exploration, Handler, FROZEN, load, sha, now, write, evidence_for

class Memory(ctypes.Structure):
    _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ('total','available','total_page','available_page','total_virtual','available_virtual','extended')]
def memory():
    state=Memory();state.length=ctypes.sizeof(state)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)):raise OSError('无法测量内存')
    return {'time':now(),'available_bytes':state.available,'total_bytes':state.total}
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);parser.add_argument('--port',type=int,default=8765);parser.add_argument('--case',default='D03');parser.add_argument('--preflight-only',action='store_true');args=parser.parse_args()
    folder=args.out.resolve();folder.mkdir(parents=True,exist_ok=True)
    if (folder/'runtime.json').exists() or (folder/'owned-service.json').exists() or list(folder.glob('run-*.json')):raise ValueError('本目录已启动或执行，不允许重复')
    engine=Exploration(folder,args.case,folder/'server-log.txt')
    engine.memory_status=memory
    frozen=engine.contract;modelroot=Path(os.environ['LOCALAPPDATA'])/'ANTLabLocalModel'
    launch=[s.replace('%LOCALAPPDATA%/ANTLabLocalModel',str(modelroot)) for s in frozen['service_arguments']]
    if sha(Path(launch[0]))!=frozen['llama_cpp']['executable_sha256'] or sha(modelroot/'models/Qwen3-0.6B-Q8_0.gguf')!=frozen['model']['actual_sha256']:raise ValueError('模型或工具哈希改变')
    for port in [args.port,8080]:
        with socket.socket() as sock:sock.bind(('127.0.0.1',port))
    # 自造样例只检查展示映射，不伪造模型请求或答案。
    for config,key in [(engine.answer,'answer'),(engine.selection,'selected_ids')]:
        response_format=config['parameters']['response_format'];schema=response_format['json_schema']['schema']
        if response_format['type']!='json_schema' or schema['type']!='object' or key not in schema['required'] or config['parameters']['max_tokens']!=256:raise ValueError('Schema或预算离线核查失败')
    synthetic=[{'id':'synthetic','source':'self_test','text':'测试原文'}]
    checks=[evidence_for({'citations':['synthetic']},synthetic)['support_status']=='not_checked',evidence_for({'citations':['missing']},synthetic)['locator_status']=='invalid',evidence_for({'citations':[]},synthetic)['locator_status']=='absent']
    if not all(checks):raise ValueError('定位/支持展示离线检查失败')
    protected={p:sha(ROOT/p) for p in {**frozen['code_hashes'],**frozen['data_hashes']}}
    for p in (ROOT/'results').rglob('*'):
        if p.is_file():protected[p.relative_to(ROOT).as_posix()]=sha(p)
    for name in ['README.md','report.md','基础/开发记录.md']:protected[name]=sha(ROOT/name)
    preflight={'checked_at':now(),'passed':True,'returncode':0,'case':args.case,'condition':'R0','ports_available':[8080,args.port],'model_and_frozen_hashes_match':True,'locator_support_separation_checks':checks,'memory':memory(),'generation_limit':2,'source_freeze':(FROZEN/'freeze.json').relative_to(ROOT).as_posix(),'source_freeze_sha256':engine.freeze_hash,'entry_hashes':{p:sha(ROOT/p) for p in ['基础/starter/server_exploration.py','基础/starter/index.html','基础/tests/run_page_closure.py']},'configs':{'answer':frozen['answer_config'],'selection':frozen['selection_config']},'original_records_not_changed':True}
    if preflight['memory']['available_bytes']<2*1024**3:raise ValueError('加载前可用内存不足2 GiB')
    write(folder/'offline-preflight.json',preflight);write(folder/'protected-hashes.json',protected)
    if args.preflight_only:print('OFFLINE_PREFLIGHT_PASSED',flush=True);return
    process=None;server=None;stop=threading.Event();abort=threading.Event();samples=[];phase='model_loading';started=time.perf_counter()
    def monitor():
        low=0
        while not stop.is_set():
            sample=memory();samples.append(sample);low=low+1 if sample['available_bytes']<1024**3 else 0
            if low>=3:
                abort.set()
                if process and process.poll() is None:process.terminate()
                return
            stop.wait(2)
    thread=threading.Thread(target=monitor,daemon=True)
    runtime={'started_at':now(),'arguments':frozen['service_arguments'],'memory_before':memory(),'generation_limit':2,'technical_stop':False}
    try:
        with (folder/'server-stdout.log').open('wb') as stdout,(folder/'server-log.txt').open('wb') as stderr:process=subprocess.Popen(launch,stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
        write(folder/'owned-service.json',{'pid':process.pid,'launcher_pid':os.getpid(),'started_at':now(),'model_arguments':frozen['service_arguments'],'page_port':args.port})
        thread.start();phase='health_check'
        while time.perf_counter()-started<120:
            if abort.is_set() or process.poll() is not None:raise RuntimeError('服务或内存停止')
            try:
                if engine.service('health').get('status')=='ok':break
            except Exception:pass
            time.sleep(.5)
        else:raise TimeoutError('模型健康检查超时')
        props=engine.service('props');write(folder/'service-props.json',props)
        if props['build_info']!='b11429-d81235049' or props['default_generation_settings']['n_ctx']!=4096 or props['total_slots']!=1:raise ValueError('服务版本、上下文或槽不符')
        defaults=props['default_generation_settings']['params']
        numeric={k:v for k,v in engine.answer['parameters'].items() if isinstance(v,(int,float)) and k!='max_tokens'}
        if not all(math.isclose(defaults[k],v,rel_tol=1e-6,abs_tol=1e-6) for k,v in numeric.items()) or not math.isclose(defaults['repeat_penalty'],1.0):raise ValueError('服务采样参数不符')
        runtime['memory_after_load']=memory();phase='template_capacity_preflight';engine.preflight_templates()
        write(folder/'page-freeze.json',{'frozen_at':now(),'status':'page_closure_only_not_main_experiment','source_freeze':preflight['source_freeze'],'source_freeze_sha256':engine.freeze_hash,'entry_hashes':preflight['entry_hashes'],'config':preflight['configs'],'service_arguments':frozen['service_arguments'],'generation_limit':2,'no_accuracy_update':True,'meaning':'先有离线及实际模板容量检查，再允许页面提交；原算法和首次40项不改动。'})
        server=HTTPServer(('127.0.0.1',args.port),Handler);server.engine=engine;server.config=engine.answer;server.allow_paid=False;server.timeout=.5
        phase='page_wait_or_request';runtime['page_url']=f'http://127.0.0.1:{args.port}/';write(folder/'page-ready.json',{'ready_at':now(),'url':runtime['page_url'],'owned_pid':process.pid,'generation_calls':0})
        print('PAGE_READY',runtime['page_url'],flush=True)
        while not (folder/'stop-requested.json').exists() and time.perf_counter()-started<900:
            if abort.is_set() or process.poll() is not None:raise RuntimeError('本轮模型服务停止')
            server.handle_request()
            if (folder/'technical-stop.json').exists():break
    except Exception as error:
        runtime.update(technical_stop=True,error_type=type(error).__name__,error=str(error),phase=phase)
        write(folder/'launcher-stop.json',{'recorded_at':now(),**runtime,'generation_calls':engine.calls})
        print('STOP',phase,type(error).__name__,str(error),flush=True)
    finally:
        if server:server.server_close()
        stop.set()
        if thread.is_alive():thread.join(5)
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        runtime.update(ended_at=now(),model_service_stopped=process is None or process.poll() is not None,page_service_stopped=True,generation_dispatches=engine.calls,memory_samples=samples,memory_after_stop=memory())
        write(folder/'runtime.json',runtime)
        changed=[p for p,h in protected.items() if sha(ROOT/p)!=h];write(folder/'protected-file-audit.json',{'checked_at':now(),'changed':changed,'all_unchanged':not changed})
        print('FINAL',json.dumps({'generation_calls':engine.calls,'service_stopped':runtime['model_service_stopped'],'protected_changed':changed},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
