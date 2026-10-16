"""只在门禁通过后启动本轮自有模型与A页面。"""
from pathlib import Path
import argparse,subprocess,socket,threading,time,sys,json,os
from runtime import HERE,ROOT,TechnicalStop,load,write,sha,now,memory
from current_candidate import CurrentEngine as Engine,query_config,build_answer
from audited_health import wait_health
from engine import query_messages,answer_messages,neighbors
from current_server import Handler
from http.server import HTTPServer
from checks import run as offline_checks

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--port',type=int,default=8890);a=p.parse_args();folder=a.out.resolve()
    pre=load(folder/'offline-preflight.json');assert pre['passed']
    if (folder/'owned-service.json').exists() or list(folder.glob('run-*.json')):raise ValueError('已有启动/请求，不重发')
    for name,h in {**pre['code_hashes'],**pre['data_hashes']}.items():assert sha(ROOT/name)==h,name
    for port in [8080,a.port]:
        with socket.socket() as s:s.bind(('127.0.0.1',port))
    if memory()['available_bytes']<2*1024**3:raise RuntimeError('加载前可用内存低于2 GiB，不加载')
    engine=Engine(folder);development=load(folder/'development-inputs.json')
    protected={n:sha(ROOT/n) for n in ['README.md','report.md','decisions.md','declaration.md','基础/开发记录.md','基础/starter/student.py','进阶/challenge_b/challenge.py','进阶/challenge_b/no_cache_engine.py']}
    plan=load(folder/'development-plan.json')
    launch=plan['service_arguments'];(folder/'slot-cache').mkdir()
    assert sha(Path(launch[0]))==pre['executable_hash'] and sha(Path(launch[launch.index('-m')+1]))==pre['model_hash']
    process=None;server=None;stop=threading.Event();abort=threading.Event();samples=[];start=time.perf_counter();phase='loading'
    runtime={'started_at':now(),'service_arguments':launch,'service_working_directory':str(folder),'only_service_argument_difference':'slot-save-path使用本轮cwd内ASCII相对路径，保留槽erase接口；不改模型、采样和上下文。','memory_before':memory(),'technical_stop':False}
    def monitor():
        low=0
        while not stop.is_set():
            m=memory();samples.append(m);low=low+1 if m['available_bytes']<1024**3 else 0
            if low>=3:
                abort.set()
                if process and process.poll() is None:process.terminate()
                return
            stop.wait(2)
    thread=threading.Thread(target=monitor,daemon=True)
    try:
        with (folder/'model-stdout.log').open('wb') as stdout,(folder/'model-stderr.log').open('wb') as stderr:process=subprocess.Popen(launch,stdout=stdout,stderr=stderr,cwd=folder,creationflags=subprocess.CREATE_NO_WINDOW)
        write(folder/'owned-service.json',{'pid':process.pid,'launcher_pid':os.getpid(),'arguments':launch,'started_at':now()});thread.start();phase='health'
        wait_health(engine,process,folder,abort,start,120)
        props=engine.service('props');write(folder/'props.json',props)
        assert props['build_info']=='b11429-d81235049' and props['default_generation_settings']['n_ctx']==4096 and props['total_slots']==1
        runtime.update(load_seconds=time.perf_counter()-start,memory_after_load=memory());phase='slot_erase_preflight'
        write(folder/'startup-slot-erase.json',{'request':{'method':'POST','route':'slots/0?action=erase','body':{}},'response':engine.service('slots/0?action=erase',{}),'generation_calls':0})
        phase='actual_template_preflight'
        for t in development:
            engine.capacity(query_messages(t['claim']),query_config(),'startup-query-'+t['id'])
            for variant,blocks in [('empty',[]),('worst',load(folder/'worst-inputs.json')[t['id']])]:
                ms,conf,index,audit=build_answer(t['claim'],blocks,t['doc_ids'],t['snapshot'],engine.answer_base)
                engine.capacity(ms,conf,'startup-'+variant+'-'+t['id'])
        server=HTTPServer(('127.0.0.1',a.port),Handler);server.engine=engine;server.development=development;server.folder=folder;server.timeout=.5
        write(folder/'page-ready.json',{'url':f'http://127.0.0.1:{a.port}/','ready_at':now(),'generation_calls':0,'model_pid':process.pid,'actual_template_checks':'passed'})
        print('PAGE_READY',f'http://127.0.0.1:{a.port}/',flush=True);phase='page_requests'
        while time.perf_counter()-start<2400 and not (folder/'stop-requested.json').exists():
            if abort.is_set() or process.poll() is not None:raise TechnicalStop('运行中模型/内存停止')
            server.handle_request()
            if engine.technical_stop:raise TechnicalStop('请求发生技术错误，停止')
    except Exception as e:
        runtime.update(technical_stop=True,error=repr(e),failure_phase=phase);write(folder/'technical-stop.json',{'at':now(),**runtime,'generation_dispatches':engine.dispatches});print('TECHNICAL_STOP',phase,repr(e),flush=True)
    finally:
        if server:server.server_close()
        runtime.update(exit_code_before_cleanup=process.poll() if process else None)
        stop.set()
        if thread.is_alive():thread.join(5)
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        runtime.update(exit_code_after_cleanup=process.poll() if process else None,ended_at=now(),generation_dispatches=engine.dispatches,confirmed_generations=engine.completed,model_stopped=process is None or process.poll() is not None,page_stopped=True,memory_samples=samples,memory_after_stop=memory())
        write(folder/'runtime.json',runtime);write(folder/'protection.json',{'at':now(),'changed':[n for n,h in protected.items() if sha(ROOT/n)!=h]})
        print('FINAL',json.dumps({'generations':engine.completed,'dispatches':engine.dispatches,'stopped':True},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
