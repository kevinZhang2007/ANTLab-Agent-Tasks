"""local_rule状态表4项对照；复用已有provider及记录接口，失败门禁先于模型启动。"""
from pathlib import Path
import sys
sys.path.insert(0,str(next(p for p in Path(__file__).resolve().parents if (p/'基础/starter/provider.py').is_file())/"基础/tests"))
sys.path.insert(0,str(next(p for p in Path(__file__).resolve().parents if (p/'基础/starter/provider.py').is_file())/"基础/starter"))
import copy,ctypes,hashlib,json,math,os,re,socket,subprocess,sys,threading,time,uuid
import urllib.request,urllib.error
import general_candidate as generic
from run_formal_round2 import now,load,sha
import provider

from offline_gate import after_offline_success

def main():
    repo=next(p for p in Path(__file__).resolve().parents if (p/'基础/starter/provider.py').is_file())
    base=repo/'基础'
    folder=Path(sys.argv[1]).resolve()
    assert not list(folder.glob('run-*.json')) and not (folder/'runtime.json').exists(),'禁止自动重复或续发'
    def write(name,value,update=False):
        path=folder/name;assert update or not path.exists()
        with path.open('w',encoding='utf-8') as stream:
            json.dump(value,stream,ensure_ascii=False,indent=2);stream.flush();os.fsync(stream.fileno())
    design=load(folder/'design-plan.json')
    plan={'order':design['order'],'planned_generation_calls':2}
    assert load(folder/'offline-check.json')['passed']
    pairs=load(folder/'request-pairs.json')['items']
    inputs={r['case_id']:dict(r,passages=json.loads(r['control']['messages'][1]['content'])['passages'],question=json.loads(r['control']['messages'][1]['content'])['question']) for r in pairs}
    reused={'items':[]}
    freeze=load(base/'runs/formal/round2-20261014-133000/freeze.json')
    config=freeze['answer_config']
    root=Path(os.environ['LOCALAPPDATA'])/'ANTLabLocalModel'
    args=[a.replace('%LOCALAPPDATA%/ANTLabLocalModel',str(root)) for a in freeze['service_arguments']]
    source_names=['基础/starter/provider.py','基础/tests/run_formal_round2.py']
    source_names += [(folder/n).relative_to(repo).as_posix() for n in ['run_small_pairs.py','explicit_state_checker.py','local_rule_state_candidate.py','offline_gate.py','request-pairs.json','offline-check.json','design-plan.json','six-state-recompute.json','six-state-original-text-review.json']]
    source_hashes={n:sha(repo/n) for n in source_names}
    (folder/'code-snapshot').mkdir(parents=True,exist_ok=True)
    for name in source_names:
        dest=folder/'code-snapshot'/Path(name).name
        if dest.exists():assert sha(dest)==source_hashes[name]
        else:dest.write_bytes((repo/name).read_bytes())
    records=[];templates=[];process=None;thread=None
    stop=threading.Event();abort=threading.Event()
    runtime={'started_at':now(),'generation_dispatches':0,'technical_stop':False,'memory_samples':[]}
    class Memory(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ('total','available','total_page','available_page','total_virtual','available_virtual','extended')]
    def memory():
        m=Memory();m.length=ctypes.sizeof(m);assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return {'time':now(),'available_bytes':m.available,'total_bytes':m.total}
    def monitor():
        low=0
        while not stop.is_set():
            m=memory();runtime['memory_samples'].append(m);low=low+1 if m['available_bytes']<1024**3 else 0
            if low>=3:
                abort.set()
                if process and process.poll() is None:process.terminate()
                return
            stop.wait(2)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def service(route,body=None):
        assert route in {'health','props','slots','apply-template','tokenize','slots/0?action=erase'}
        request=urllib.request.Request('http://127.0.0.1:8080/'+route,data=None if body is None else json.dumps(body,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
        with opener.open(request,timeout=20) as response:return json.loads(response.read())
    numeric={k:v for k,v in config['parameters'].items() if isinstance(v,(int,float)) and k!='max_tokens'}
    jobs=[];log=folder/'server-log.txt'
    try:
        assert all(sha(repo/n)==h for n,h in source_hashes.items())
        assert sha(root/'models/Qwen3-0.6B-Q8_0.gguf')==freeze['model']['actual_sha256']
        assert sha(root/'llama-b11429/llama-server.exe')==freeze['llama_cpp']['executable_sha256']
        runtime['memory_before']=memory();assert runtime['memory_before']['available_bytes']>=2*1024**3
        with socket.socket() as sock:sock.bind(('127.0.0.1',8080))
        with (folder/'server-stdout.log').open('wb') as out,log.open('wb') as err:
            process=subprocess.Popen(args,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
        runtime['owned_pid']=process.pid;write('owned-service.json',{'pid':process.pid,'started_at':now(),'arguments':freeze['service_arguments']})
        begin=time.perf_counter();thread=threading.Thread(target=monitor,daemon=True);thread.start()
        while True:
            assert not abort.is_set() and process.poll() is None,'服务或内存错误'
            try:
                if service('health').get('status')=='ok':break
            except (urllib.error.URLError,TimeoutError):pass
            if time.perf_counter()-begin>120:raise TimeoutError('服务加载超时')
            time.sleep(.5)
        runtime['load_seconds']=time.perf_counter()-begin;runtime['memory_after_load']=memory()
        props=service('props');write('service-props.json',props)
        assert props['default_generation_settings']['n_ctx']==4096 and props['total_slots']==1
        assert props['build_info']=='b11429-d81235049' and props['model_alias']==config['model']
        params=props['default_generation_settings']['params']
        assert all(math.isclose(params[k],v,rel_tol=1e-6,abs_tol=1e-6) for k,v in numeric.items())
        assert math.isclose(params['repeat_penalty'],1.0)
        for job in plan['order']:
            row=inputs[job['case_id']];used=row['passages']
            body=copy.deepcopy(row[job['variant']]);messages=body['messages']
            conf=copy.deepcopy(config)
            conf['parameters']={k:v for k,v in body.items() if k not in {'model','messages','stream'}}
            conf['model']=body['model'];rule={'only_answer_enum_changed':True,'qualification_excluded':job['variant']=='excluded','audit':row['qualification_audit']}
            assert body['max_tokens']==256 and body=={'model':conf['model'],'messages':messages,'stream':False,**conf['parameters']}
            raw=service('apply-template',body);prompt=raw['prompt']
            tokens=service('tokenize',{'content':prompt,'add_special':True,'parse_special':True})['tokens']
            item={**job,'messages':messages,'config':conf,'schema_rule':rule,'body':body,'used_passages':used,
                  'template_response':raw,'input_tokens':len(tokens),'budget':256,'total':len(tokens)+256}
            jobs.append(item);write('capacity-check.json',{'checked_at':now(),'rows':jobs,'counts_as_generation':False},True)
            assert all(m['content'] in prompt for m in messages) and prompt.endswith('<think>\n\n</think>\n\n')
            assert item['total']<=4096,'完整输入超限'
        for cid in inputs:
            pair=[j for j in jobs if j['case_id']==cid]
            assert len(pair)==2 and pair[0]['body']!=pair[1]['body']
            for item in pair:assert item['body']==inputs[cid][item['variant']]
        assert len(jobs)==2 and plan['planned_generation_calls']==2
        write('freeze.json',{'saved_at':now(),'generation_calls_so_far':0,'frozen':True,'experiment_kind':'post_evaluation_eligibility_enum_small','design':design,'execution_plan':plan,'reused_results':reused,'order':plan['order'],
            'config':config,'service_arguments':freeze['service_arguments'],'code_hashes':source_hashes,
            'data_hashes':freeze['data_hashes'],'model':freeze['model'],'llama_cpp':freeze['llama_cpp'],
            'actual_schemas':[{'case_id':j['case_id'],'variant':j['variant'],'response_format':j['body']['response_format']} for j in jobs],
            'only_changed_request_pairs_generated':True,'max_input_tokens':max(j['input_tokens'] for j in jobs),
            'max_total_tokens':max(j['total'] for j in jobs),'evaluation_rules':freeze['evaluation_rules'],
            'selection_provenance':'历史补齐原文重放；同步生成对照和资格排除enum，仅answer enum变化，剩余候选不标合格。'})
        fixed_hash=sha(folder/'freeze.json')
        print('FREEZE SAVED',now(),'planned calls',len(jobs),'max tokens',max(j['total'] for j in jobs),flush=True)
        for job in jobs:
            assert sha(folder/'freeze.json')==fixed_hash
            assert not abort.is_set() and memory()['available_bytes']>=1024**3
            assert all(sha(repo/n)==h for n,h in source_hashes.items())
            row=inputs[job['case_id']]
            record={k:copy.deepcopy(job[k]) for k in ['sequence','case_id','variant','messages','config','used_passages','input_tokens','schema_rule']}
            record.update(run_id=str(uuid.uuid4()),started_at=now(),run_kind='live_api',mode='local',
                condition='R0',answer_stage_only=True,selection_provenance='historical_replay',
                original_passages=row['passages'],question=row['question'],
                original_request_source=row['control_source'],original_request_source_sha256=row['control_source_sha256'],
                judgment_source='local_rule_eligibility_exclusion' if job['variant']=='excluded' else 'original_prompt',
                checker_sha256=design['checker_sha256'],memory_before=memory(),status='pending',
                generation_dispatched=False,model_revision=freeze['model']['revision'],weight_sha256=freeze['model']['actual_sha256'],
                attempt=1,retry_of=None)
            records.append(record);name='run-'+record['run_id']+'.json';write(name,record)
            record['cache_erase']=service('slots/0?action=erase',{})
            offset=log.stat().st_size;build=urllib.request.build_opener
            class Capture:
                def __init__(self,inner):self.inner=inner
                def open(self,request,*a,**kw):
                    actual=json.loads(request.data);assert actual==job['body'] and actual['max_tokens']==256
                    assert runtime['generation_dispatches']<plan['planned_generation_calls']==2
                    record.update(actual_http_request_body=actual,raw_http_request_body=request.data.decode(),generation_dispatched=True)
                    runtime['generation_dispatches']+=1;write(name,record,True)
                    try:return self.inner.open(request,*a,**kw)
                    except urllib.error.HTTPError as error:
                        record['raw_http_error_body']=error.read().decode(errors='replace');raise
            urllib.request.build_opener=lambda *a,**kw:Capture(build(*a,**kw))
            try:record.update(provider.call_model(job['messages'],job['config']))
            finally:urllib.request.build_opener=build;write(name,record,True)
            record['memory_after']=memory();record['returned_at']=now()
            if record['status']!='ok' or not isinstance(record.get('response'),dict) or not record['response'].get('choices'):
                record['technical_failure']=True;write(name,record,True);raise RuntimeError('技术请求失败 '+record['run_id'])
            choice=record['response']['choices'][0]
            record.update(raw_content=choice.get('message',{}).get('content',''),finish_reason=choice.get('finish_reason'),
                budget_exhausted=choice.get('finish_reason')=='length',raw_reasoning=choice.get('message',{}).get('reasoning_content'))
            slots=service('slots');record['slot_after']=slots;echo=slots[0]['params']
            record['parameter_checks']={k:math.isclose(echo[k],v,rel_tol=1e-6,abs_tol=1e-6) for k,v in numeric.items() if k in echo}
            record['parameters_not_echoed']=[k for k in numeric if k not in echo]+['response_format','effective_max_tokens']
            with log.open('rb') as stream:stream.seek(offset);segment=stream.read().decode(errors='replace')
            record['server_log_segment']=segment.replace(str(root),'%LOCALAPPDATA%/ANTLabLocalModel')
            flags=re.findall(r'truncated\s*=\s*(\d+)',segment)
            record['truncated']=any(int(f) for f in flags) if flags else 'not_verified'
            write(name,record,True)
            assert all(record['parameter_checks'].values()) and record['truncated'] is not True
            write('result-index.json',{'items':[{'sequence':r['sequence'],'case_id':r['case_id'],'variant':r['variant'],
                'run_id':r['run_id'],'path':(folder/('run-'+r['run_id']+'.json')).relative_to(repo).as_posix(),
                'elapsed_seconds':r.get('elapsed_seconds'),'status':r['status']} for r in records]},True)
            print('RESULT',job['sequence'],job['case_id'],job['variant'],record['run_id'],record['finish_reason'],flush=True)
    except Exception as error:
        runtime.update(technical_stop=True,error=repr(error));write('technical-stop.json',{'stopped_at':now(),'error':repr(error),'generation_dispatches':runtime['generation_dispatches']})
        print('STOP',repr(error),flush=True)
    finally:
        stop.set()
        if thread:thread.join(timeout=5)
        if process and process.pid==runtime.get('owned_pid') and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        runtime.update(ended_at=now(),service_stopped=process is None or process.poll() is not None,memory_after_stop=memory())
        write('runtime.json',runtime)
        confirmed=[r for r in records if (r.get('usage') or {}).get('completion_tokens',0)>0]
        summary={'completed_answers':len(confirmed),'generation_dispatches':runtime['generation_dispatches'],
            'technical_stop':runtime['technical_stop'],'service_stopped':runtime['service_stopped'],
            'previous_cumulative':316,'cumulative_confirmed':316+len(confirmed),'planned_generated_answers':plan['planned_generation_calls'],'reused_logical_answers':2*len(reused['items']),
            'unique_run_ids':[r['run_id'] for r in confirmed],'budget_exhausted':sum(r.get('budget_exhausted',False) for r in records),
            'truncation_true':sum(r.get('truncated') is True for r in records),'truncation_unverified':sum(r.get('truncated')=='not_verified' for r in records)}
        write('execution-summary.json',summary)
        print('FINAL',json.dumps({k:v for k,v in summary.items() if k!='unique_run_ids'},ensure_ascii=False),flush=True)


def dispatch_checked(check_step, run_step):
    return after_offline_success(check_step, run_step)


def preflight():
    folder = Path(sys.argv[1]).resolve()
    result = load(folder/'offline-check.json')
    design = load(folder/'design-plan.json')
    assert result['checker_sha256'] == design['checker_sha256'] == sha(folder/'explicit_state_checker.py')
    assert load(folder/'six-state-original-text-review.json')['passed']
    assert load(folder/'regression-results.json')['failed'] == 0
    assert load(folder/'runner-gate-integration.json')['passed']
    assert all(sha(next(p for p in Path(__file__).resolve().parents if (p/'基础/starter/provider.py').is_file())/p) == h for p,h in design['protected_hashes'].items())
    return result


if __name__ == '__main__':
    dispatch_checked(preflight, main)
