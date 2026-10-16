"""只在门禁通过后启动本轮自有模型与A页面。"""
from pathlib import Path
import argparse,subprocess,socket,threading,time,sys,json,os
from runtime import HERE,ROOT,Engine,TechnicalStop,load,write,sha,now,memory,config
from engine import query_messages,answer_messages,neighbors
from server import Handler,HTTPServer
from checks import run as offline_checks

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--port',type=int,default=8890);a=p.parse_args();folder=a.out.resolve()
    pre=load(folder/'offline-preflight.json');assert pre['passed'] and offline_checks()['status']=='passed'
    gate=load(folder/'import-and-failure-gate.json');assert gate['passed'] and gate['generation_calls']==0
    if (folder/'owned-service.json').exists():raise ValueError('本目录曾启动，不自动重试')
    for name,h in {**pre['code_hashes'],**pre['data_hashes']}.items():assert sha(ROOT/name)==h,'预检后文件改变 '+name
    for port in [8080,a.port]:
        with socket.socket() as s:s.bind(('127.0.0.1',port))
    if memory()['available_bytes']<2*1024**3:raise RuntimeError('加载前可用内存低于2 GiB，不加载')
    engine=Engine(folder);development=load(folder/'development-inputs.json')
    protected={n:sha(ROOT/n) for n in ['README.md','report.md','decisions.md','declaration.md','基础/开发记录.md','基础/starter/student.py','进阶/challenge_b/challenge.py','进阶/challenge_b/no_cache_engine.py']}
    plan={'saved_at':now(),'kind':'A开发调试，不是正式冻结','hypothesis':'同章节相邻原段落可能补回判定所需条件；增加文本也可能引入干扰。','competing_explanations':['错误来自中文到英文查询转换或命中不足，邻段未必有用','证据已足够，但回答模型没有正确处理否定、条件或跨段组合'],'prediction':'只在邻段确有必要信息时预期改善；语义支持/完整成功无改善则保留简单基线。','selection':'两个正TF-IDF最高分完整原段；改进补同章节前后各一段，去重并原顺序','shared_query':'每主张仅一次，两个方案共享同一run_id，实际计1次；各侧分摊50%查询成本并另报整对真实耗时','orders':[{'task_id':t['id'],'order':['baseline','improved'] if i%2==0 else ['improved','baseline']} for i,t in enumerate(development)],'config':{'query':config('query'),'answer':config('answer')},'generation_limit_this_phase':9,'A_total_budget':54,'baseline_cumulative':534,'quality_retry':False,'technical_failure':'保存后停止，不自动重发；未执行保持未执行','evaluation':'全部调用结束后由独立评价模块读取开发参考；分别评主张判断、格式、范围ID、必要覆盖、引用支持、无关引用、PDF定位，AI辅助暂判','stopping_memory':'加载前至少2 GiB；运行可用物理内存连续3次(每2秒)低于1 GiB停止自有PID，分配失败/崩溃停止','boundaries':'A为附加探索，B为主要交付；双提交与自有本地服务验收未明确，不宣称获认可；未读AT正文。','preflight_hash':sha(folder/'offline-preflight.json'),'code_hashes':pre['code_hashes'],'data_hashes':pre['data_hashes'],'frozen':False,'implementation_not_effect_claim':True}
    write(folder/'development-plan.json',plan)
    base=Path.home()/'AppData/Local/ANTLabLocalModel';launch=[x.replace('%LOCALAPPDATA%/ANTLabLocalModel',str(base)) for x in pre['service_arguments']]
    # 原生槽接口需要启用保存目录；使用本轮cwd下的ASCII相对路径。
    slot=launch.index('--slot-save-path')+1;(folder/'slot-cache').mkdir();launch[slot]='slot-cache'
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
        while time.perf_counter()-start<120:
            if abort.is_set() or process.poll() is not None:raise TechnicalStop('内存或模型进程停止')
            try:
                if engine.service('health').get('status')=='ok':break
            except Exception:pass
            time.sleep(.5)
        else:raise TechnicalStop('健康检查超时')
        props=engine.service('props');write(folder/'props.json',props)
        assert props['build_info']=='b11429-d81235049' and props['default_generation_settings']['n_ctx']==4096 and props['total_slots']==1
        runtime.update(load_seconds=time.perf_counter()-start,memory_after_load=memory());phase='slot_erase_preflight'
        write(folder/'startup-slot-erase.json',{'request':{'method':'POST','route':'slots/0?action=erase','body':{}},'response':engine.service('slots/0?action=erase',{}),'generation_calls':0})
        phase='actual_template_preflight'
        for t in development:
            engine.capacity(query_messages(t['claim']),config('query'),'startup-query-'+t['id'])
            engine.capacity(answer_messages(t['claim'],[]),config('answer'),'startup-empty-'+t['id'])
            blocks=engine.corpus.scope(t['doc_ids'],t['snapshot']);sizes=load(folder/'offline-capacity.json')['block_token_bounds']
            ranked=sorted(blocks,key=lambda b:sum(sizes[x['block_id']] for x in neighbors([b],blocks)[0]),reverse=True)
            worst,_=neighbors(ranked[:2],blocks);engine.capacity(answer_messages(t['claim'],worst),config('answer'),'startup-worst-'+t['id'])
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
        stop.set()
        if thread.is_alive():thread.join(5)
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        runtime.update(ended_at=now(),generation_dispatches=engine.dispatches,confirmed_generations=engine.completed,model_stopped=process is None or process.poll() is not None,page_stopped=True,memory_samples=samples,memory_after_stop=memory())
        write(folder/'runtime.json',runtime);write(folder/'protection.json',{'at':now(),'changed':[n for n,h in protected.items() if sha(ROOT/n)!=h]})
        print('FINAL',json.dumps({'generations':engine.completed,'dispatches':engine.dispatches,'stopped':True},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
