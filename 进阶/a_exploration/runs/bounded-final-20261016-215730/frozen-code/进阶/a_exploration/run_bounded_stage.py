"""复用当前候选、请求记录器、健康检查及逐任务目录；不自动评语义或重试。"""
from pathlib import Path
import argparse,os,sys,time,subprocess,threading,copy,uuid
from datetime import datetime
from runtime import load,write,sha,now,memory,TechnicalStop,ROOT,HERE
from bounded_candidate import BoundedEngine,query_config
from engine import neighbors,public,parse_terms
from audited_health import wait_health
from sentence_selection import expand
from sentence_interface import interface_response

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--stage',type=Path,required=True);a=ap.parse_args();stage=a.stage.resolve();plan=load(stage/'plan.json');batch=stage.parent
    if plan['phase']=='development' and datetime.now().hour*60+datetime.now().minute>=22*60+35:raise RuntimeError('22:35后不启动新的开发轮次')
    if (stage/'owned-service.json').exists() or list(stage.rglob('run-*.json')):raise RuntimeError('已有启动或请求，不重试')
    assert load(stage/'offline-checks.json')['passed']
    for n,h in plan['code_hashes'].items():assert sha(ROOT/n)==h,n
    for n,h in plan['data_hashes'].items():assert sha(ROOT/n)==h,n
    cfg=load(batch/'configuration.json');profile=load(stage/'profile.json');tasks=load(stage/'tasks.json');launch=cfg['service_arguments'];assert sha(Path(launch[0]))==cfg['executable']['sha256'] and sha(Path(launch[launch.index('-m')+1]))==cfg['model']['sha256']
    import socket
    with socket.socket() as s:s.bind(('127.0.0.1',8080))
    before=memory();write(stage/'resource-before.json',before)
    if before['available_bytes']<2*1024**3:write(stage/'resource-stop.json',{'at':now(),'memory':before,'minimum_GiB':2,'generation_calls':0});print('RESOURCE_STOP',flush=True);return
    engines=[];results=[];samples=[];stop=threading.Event();abort=threading.Event();process=None;phase='loading';start=time.perf_counter();record={'at':now(),'plan':plan,'memory_before':before}
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
    def engine_for(name):
        folder=stage/name;folder.mkdir();write(folder/'configuration.json',cfg);write(folder/'profile.json',profile);os.link(stage/'model-stderr.log',folder/'model-stderr.log');e=BoundedEngine(folder);engines.append(e);return e
    try:
        (stage/'slot-cache').mkdir()
        with (stage/'model-stdout.log').open('xb') as stdout,(stage/'model-stderr.log').open('xb') as stderr:process=subprocess.Popen(launch,cwd=stage,stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
        write(stage/'owned-service.json',{'at':now(),'pid':process.pid,'arguments':launch,'cwd':str(stage)});thread.start();phase='health';control=engine_for('service-preflight');wait_health(control,process,stage,abort,start,120);props=control.service('props');write(stage/'props.json',props)
        assert props['build_info']=='b11429-d81235049' and props['default_generation_settings']['n_ctx']==4096 and props['total_slots']==1 and props['default_generation_settings']['params']['repeat_penalty']==1.0
        record.update(load_seconds=time.perf_counter()-start,memory_after_load=memory());phase='template_preflight'
        for task in tasks:
            control.capacity(control.query_messages(task['claim']),query_config(),'pre-query-'+task['id'])
            scope=control.corpus.scope(task['doc_ids'],task['snapshot']);ranked=sorted(scope,key=lambda b:sum(len(x['text']) for x in neighbors([b],scope)[0]),reverse=True);worst,_=neighbors(ranked[:2],scope)
            if task.get('block_id_mapping'):worst=[{**b,'block_id':task['block_id_mapping'][b['block_id']]} for b in worst]
            ms,conf,idx,byte=control.build_answer(task['claim'],worst,task['doc_ids'],task['snapshot']);control.capacity(ms,conf,'pre-worst-'+task['id'])
        phase='generation'
        for task in tasks:
            if abort.is_set() or process.poll() is not None:raise TechnicalStop('运行前资源或进程停止')
            e=engine_for(task['id']);scope=e.corpus.scope(task['doc_ids'],task['snapshot'])
            if task.get('block_id_mapping'):
                mapping=task['block_id_mapping'];e.corpus.blocks=[{**b,'block_id':mapping.get(b['block_id'],b['block_id'])} for b in e.corpus.blocks];scope=e.corpus.scope(task['doc_ids'],task['snapshot'])
            result={'at':now(),'task_id':task['id'],'claim':task['claim'],'doc_ids':task['doc_ids'],'snapshot':task['snapshot'],'kind':plan['kind'],'profile':profile,'arms':{},'query':None};clock=time.perf_counter();path=e.folder/'task-result.json';write(path,result)
            if plan['kind']=='full_pairs':
                pair=e.execute_pair(task['claim'],task['doc_ids'],task['snapshot'],task['order']);result.update(pair=pair,query=pair['shared_query'],status=pair['status']);write(path,result)
            else:
                if plan['kind']=='query_answer':
                    q=e.generate(e.query_messages(task['claim']),query_config(),'query',str(uuid.uuid4()),[]);result['query']=q;write(path,result)
                    try:terms=parse_terms(q['content'])
                    except Exception as ex:result.update(status='query_quality_failure',error=repr(ex));write(path,result);results.append(result);continue
                else:terms=task['terms'];result['query_origin']='historical_query_replay';result['query_source']=task['query_source']
                seeds,scores=e.retrieve(terms,scope);extended,added=neighbors(seeds,scope);result.update(terms=terms,ranking=scores,seeds=[b['block_id'] for b in seeds],added_neighbors=added,baseline_blocks=[public(b) for b in seeds],improved_blocks=[public(b) for b in extended]);write(path,result)
                for arm in task['order']:
                    used=seeds if arm=='baseline' else extended;ms,conf,idx,byte=e.build_answer(task['claim'],used,task['doc_ids'],task['snapshot']);e.capacity(ms,conf,'before-'+arm)
                    total=sum(x.dispatches for x in engines)
                    if total>=plan['generation_cap']:raise TechnicalStop('阶段调用上限')
                    r=e.generate(ms,conf,arm,str(uuid.uuid4()),used);ex=expand(r['content'],[public(b) for b in used],idx,task['doc_ids'],task['snapshot']);view=interface_response(r['request_id'],task['claim'],task['doc_ids'],task['snapshot'],r['run_id'],ex,r['elapsed_seconds'],locator=e.locator,actual_input_blocks=used)
                    result['arms'][arm]={'raw':r,'blocks':[public(b) for b in used],'sentence_index':idx,'byte_audit':byte,'expansion':ex,'interface':view};write(path,result)
                result['status']='completed';write(path,result)
            result['elapsed_seconds']=time.perf_counter()-clock;write(path,result);results.append(result);print('SAVED',task['id'],'dispatches',sum(x.dispatches for x in engines),flush=True)
        write(stage/'result-index.json',{'at':now(),'tasks':[{'id':t['task_id'],'path':t['task_id']+'/task-result.json','status':t['status']} for t in results]})
    except Exception as ex:record.update(error=repr(ex),failure_phase=phase);write(stage/'technical-stop.json',{'at':now(),'phase':phase,'error':repr(ex),'dispatches':sum(x.dispatches for x in engines),'confirmed_generations':sum(x.completed for x in engines),'no_retry':True});print('TECHNICAL_STOP',phase,repr(ex),flush=True)
    finally:
        record['exit_code_before_cleanup']=process.poll() if process else None;stop.set()
        if thread.is_alive():thread.join(5)
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        record.update(ended_at=now(),dispatches=sum(x.dispatches for x in engines),confirmed_generations=sum(x.completed for x in engines),model_stopped=process is None or process.poll() is not None,memory_samples=samples,memory_after_stop=memory(),exit_code_after_cleanup=process.poll() if process else None);write(stage/'runtime.json',record);print('FINAL',record['confirmed_generations'],'STOPPED',record['model_stopped'],flush=True)

if __name__=='__main__':main()
