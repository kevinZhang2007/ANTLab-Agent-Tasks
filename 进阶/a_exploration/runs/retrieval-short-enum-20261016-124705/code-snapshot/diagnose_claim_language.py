"""开发期中英文主张诊断；复用A请求器，不执行检索或读取答案。"""
from pathlib import Path
import argparse, ast, json, socket, subprocess, threading, time, uuid
from runtime import Engine,TechnicalStop,load,write,sha,now,memory,ROOT,HERE

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);a=parser.parse_args();out=a.out.resolve()
    plan=load(out/'intervention-plan.json');inputs=load(out/'diagnostic-inputs.json')
    if (out/'owned-service.json').exists() or list(out.glob('run-*.json')):raise ValueError('已有启动或请求记录，不重发')
    assert load(out/'offline-checks.json')['passed']
    assert sha(out/'diagnostic-inputs.json')==plan['input_sha256']
    for path,h in plan['code_hashes'].items():assert sha(ROOT/path)==h,path
    for path,h in plan['data_hashes'].items():assert sha(ROOT/path)==h,path
    for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
    for item in inputs:
        assert item['blocks'] and all(b['doc_id'] in item['doc_ids'] for b in item['blocks'])
        assert item['messages']['zh'][0]==item['messages']['en'][0]
        zh=json.loads(item['messages']['zh'][1]['content']);en=json.loads(item['messages']['en'][1]['content'])
        assert zh['claim']==item['claim_zh'] and en['claim']==item['claim_en']
        assert en=={**zh,'claim':item['claim_en']}
        assert zh['passages']==en['passages'] and item['config']==plan['config']
    with socket.socket() as s:s.bind(('127.0.0.1',8080))
    m=memory();write(out/'resource-before.json',m)
    if m['available_bytes']<2*1024**3:
        write(out/'resource-stop.json',{'at':now(),'available_GiB':m['available_bytes']/2**30,'required_GiB':2,'generation_calls':0});print('RESOURCE_STOP',flush=True);return
    launch=plan['service_arguments'];assert sha(launch[0])==plan['executable_hash'] and sha(launch[launch.index('-m')+1])==plan['model_hash']
    (out/'slot-cache').mkdir();engine=Engine(out);stop=threading.Event();abort=threading.Event();samples=[];process=None;phase='loading';start=time.perf_counter()
    record={'at':now(),'run_kind':'live_api','diagnostic_input_origin':'manual_development_evidence','generations_baseline':plan['cumulative_baseline'],'service_arguments':launch,'memory_before':m}
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
    try:
        with (out/'model-stdout.log').open('xb') as stdout,(out/'model-stderr.log').open('xb') as stderr:
            process=subprocess.Popen(launch,stdout=stdout,stderr=stderr,cwd=out,creationflags=subprocess.CREATE_NO_WINDOW)
        write(out/'owned-service.json',{'pid':process.pid,'started_at':now(),'arguments':launch});thread.start();phase='health'
        while time.perf_counter()-start<120:
            if abort.is_set() or process.poll() is not None:raise TechnicalStop('加载期间资源/进程停止')
            try:
                if engine.service('health').get('status')=='ok':break
            except Exception:pass
            time.sleep(.5)
        else:raise TechnicalStop('健康超时')
        props=engine.service('props');write(out/'props.json',props)
        assert props['build_info']=='b11429-d81235049' and props['default_generation_settings']['n_ctx']==4096 and props['total_slots']==1
        record.update(load_seconds=time.perf_counter()-start,memory_after_load=memory());phase='template_preflight'
        write(out/'startup-slot-erase.json',engine.service('slots/0?action=erase',{}))
        for item in inputs:
            for variant in ['zh','en']:engine.capacity(item['messages'][variant],item['config'],'before-'+item['id']+'-'+variant)
        phase='generation'
        by_id={x['id']:x for x in inputs}
        for n,entry in enumerate(plan['order']):
            if abort.is_set() or process.poll() is not None:raise TechnicalStop('请求前资源停止')
            if engine.dispatches>=6:raise TechnicalStop('达到6次上限')
            item=by_id[entry['id']];variant=entry['variant'];request_id=str(uuid.uuid4())
            raw=engine.generate(item['messages'][variant],item['config'],f'diagnostic-{n+1}-{entry["id"]}-{variant}',request_id,item['blocks'])
            write(out/f'item-{n+1:02}.json',{'at':now(),'id':entry['id'],'variant':variant,'request_id':request_id,'run_id':raw['run_id'],'raw_record':'run-'+raw['run_id']+'.json','input_origin':'manual_verified_development_evidence','not_automatic_retrieval':True,'not_end_to_end_score':True})
            print('SAVED',entry['id'],variant,raw['run_id'],flush=True)
    except Exception as e:
        record.update(error=repr(e),failure_phase=phase);write(out/'technical-stop.json',{'at':now(),'phase':phase,'error':repr(e),'dispatches':engine.dispatches,'confirmed_generations':engine.completed,'no_automatic_resend':True});print('TECHNICAL_STOP',phase,repr(e),flush=True)
    finally:
        stop.set()
        if thread.is_alive():thread.join(5)
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        record.update(ended_at=now(),dispatches=engine.dispatches,confirmed_generations=engine.completed,model_stopped=process is None or process.poll() is not None,memory_samples=samples,memory_after_stop=memory())
        write(out/'runtime.json',record);print('FINAL',engine.completed,'STOPPED',record['model_stopped'],flush=True)

if __name__=='__main__':main()
