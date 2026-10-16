"""固定自动证据的输入组织×presence惩罚四组合对照；复用请求记录器，不重检索或读答案。"""
from pathlib import Path
import argparse, ast, json, socket, subprocess, threading, time, uuid
from runtime import Engine,TechnicalStop,load,write,sha,now,memory,ROOT,HERE

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);a=parser.parse_args();out=a.out.resolve()
    plan=load(out/'intervention-plan.json');inputs=load(out/'diagnostic-inputs.json')
    if (out/'owned-service.json').exists() or list(out.glob('run-*.json')):raise ValueError('已有启动或请求记录，不重发')
    assert load(out/'offline-checks.json')['passed']
    assert load(out/'byte-and-scope-audit.json')['passed']
    assert sha(out/'diagnostic-inputs.json')==plan['input_sha256']
    for path,h in plan['code_hashes'].items():assert sha(ROOT/path)==h,path
    for path,h in plan['data_hashes'].items():assert sha(ROOT/path)==h,path
    for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
    from compact_factorial import compact_messages,audit
    from sentence_selection import schema,build_index
    for item in inputs:
        assert item['sentence_index']==build_index(item['blocks'],item['doc_ids'],item['snapshot'])
        expected=compact_messages(item['messages']['repeated_15'],item['blocks'],item['sentence_index'],item['doc_ids'],item['snapshot'])
        for variant in item['messages']:
            conf=item['configs'][variant];assert conf['parameters']['max_tokens']==512
            assert conf['parameters']['response_format']['json_schema']['schema']==schema(item['sentence_index'])
            assert item['messages'][variant]==(expected if variant.startswith('compact') else item['messages']['repeated_15'])
            assert conf['parameters']['presence_penalty']==(1.5 if variant.endswith('15') else 0)
            if variant.startswith('compact'):audit(item['messages'][variant],item['blocks'],item['sentence_index'],item['doc_ids'],item['snapshot'])
    with socket.socket() as s:s.bind(('127.0.0.1',8080))
    m=memory();write(out/'resource-before.json',m)
    if m['available_bytes']<2*1024**3:
        write(out/'resource-stop.json',{'at':now(),'available_GiB':m['available_bytes']/2**30,'required_GiB':2,'generation_calls':0});print('RESOURCE_STOP',flush=True);return
    launch=plan['service_arguments'];assert sha(launch[0])==plan['executable_hash'] and sha(launch[launch.index('-m')+1])==plan['model_hash']
    (out/'slot-cache').mkdir();engine=Engine(out);clients={};stop=threading.Event();abort=threading.Event();samples=[];process=None;phase='loading';start=time.perf_counter()
    record={'at':now(),'run_kind':'live_api','diagnostic_input_origin':'automatic_improved_evidence_replay','generations_baseline':plan['cumulative_baseline'],'service_arguments':launch,'memory_before':m}
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
        assert props['default_generation_settings']['params']['repeat_penalty']==1.0
        record.update(load_seconds=time.perf_counter()-start,memory_after_load=memory());phase='template_preflight'
        write(out/'startup-slot-erase.json',engine.service('slots/0?action=erase',{}))
        for item in inputs:
            for variant in item['messages']:engine.capacity(item['messages'][variant],item['configs'][variant],'before-'+item['id']+'-'+variant)
        phase='generation'
        by_id={x['id']:x for x in inputs}
        for n,entry in enumerate(plan['order']):
            if abort.is_set() or process.poll() is not None:raise TechnicalStop('请求前资源停止')
            if sum(c.dispatches for c in clients.values())>=12:raise TechnicalStop('达到12次总上限')
            item=by_id[entry['id']];variant=entry['variant'];request_id=str(uuid.uuid4())
            if entry['id'] not in clients:clients[entry['id']]=Engine(out)
            client=clients[entry['id']]
            if client.dispatches>=4:raise TechnicalStop('达到单题4次上限')
            raw=client.generate(item['messages'][variant],item['configs'][variant],f'diagnostic-{n+1}-{entry["id"]}-{variant}',request_id,item['blocks'])
            expected=next(x for x in load(out/'serialized-request-plan.json') if x['id']==entry['id'] and x['variant']==variant)
            params=raw['slot_after'][0].get('params',{})
            verified={'actual_serialization_matches_plan':raw['actual_http_request_raw']==expected['serialized_utf8'],'presence_explicit_in_request':raw['actual_http_request_body']['presence_penalty']==item['configs'][variant]['parameters']['presence_penalty'],'presence_echo_matches':params.get('presence_penalty')==item['configs'][variant]['parameters']['presence_penalty'],'repeat_penalty_echo_1':params.get('repeat_penalty')==1.0,'budget_request_512':raw['actual_http_request_body']['max_tokens']==512,'slot_budget_512':params.get('max_tokens')==512}
            write(out/f'parameter-check-{n+1:02}.json',verified)
            if not all(verified.values()):raise TechnicalStop('请求序列化或惩罚回显不符')
            from sentence_selection import expand
            expansion=expand(raw['content'],item['blocks'],item['sentence_index'],item['doc_ids'],item['snapshot'])
            write(out/f'expansion-{n+1:02}.json',expansion)
            write(out/f'item-{n+1:02}.json',{'at':now(),'id':entry['id'],'variant':variant,'request_id':request_id,'run_id':raw['run_id'],'raw_record':'run-'+raw['run_id']+'.json','input_origin':'automatic_improved_evidence_replay','not_automatic_retrieval':True,'not_end_to_end_score':True})
            print('SAVED',entry['id'],variant,raw['run_id'],flush=True)
    except Exception as e:
        record.update(error=repr(e),failure_phase=phase);write(out/'technical-stop.json',{'at':now(),'phase':phase,'error':repr(e),'dispatches':sum(c.dispatches for c in clients.values()),'confirmed_generations':sum(c.completed for c in clients.values()),'no_automatic_resend':True});print('TECHNICAL_STOP',phase,repr(e),flush=True)
    finally:
        stop.set()
        if thread.is_alive():thread.join(5)
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        record.update(ended_at=now(),dispatches=sum(c.dispatches for c in clients.values()),confirmed_generations=sum(c.completed for c in clients.values()),model_stopped=process is None or process.poll() is not None,memory_samples=samples,memory_after_stop=memory())
        write(out/'runtime.json',record);print('FINAL',sum(c.completed for c in clients.values()),'STOPPED',record['model_stopped'],flush=True)

if __name__=='__main__':main()
