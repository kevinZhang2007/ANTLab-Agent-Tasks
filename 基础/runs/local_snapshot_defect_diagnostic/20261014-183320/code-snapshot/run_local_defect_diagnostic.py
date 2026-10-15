"""历史答案复用；8次独立引用复核，派生结果不是原始响应。"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/"基础/tests"))
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/"基础/starter"))
import copy,ctypes,hashlib,json,math,os,re,socket,subprocess,sys,threading,time,uuid
import urllib.request,urllib.error
import general_candidate as generic
import local_defect_candidate as reviewer
from run_formal_round2 import now,load,sha
import provider

repo=Path(__file__).resolve().parents[4]
base=repo/'基础'
folder=Path(sys.argv[1]).resolve()
assert not list(folder.glob('run-*.json')) and not (folder/'runtime.json').exists(),'禁止自动重复或续发'
def write(name,value,update=False):
    path=folder/name;assert update or not path.exists()
    with path.open('w',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.flush();os.fsync(stream.fileno())
design=load(folder/'design-plan.json')
plan=load(folder/'execution-plan.json')
assert load(folder/'offline-check.json')['passed']
assert load(folder/'request-diff.json')['only_local_task_inputs']
recomputed=load(folder/'source-inputs.json')
inputs={r['case_id']:r for r in recomputed['items']}
freeze=load(base/'runs/formal/round2-20261014-133000/freeze.json')
config=load(folder/'config.diagnostic.json')
assert 'response_format' not in config['parameters']
assert (folder/'system.diagnostic.txt').read_text(encoding='utf-8')==reviewer.REVIEW_PROMPT
root=Path(os.environ['LOCALAPPDATA'])/'ANTLabLocalModel'
args=[a.replace('%LOCALAPPDATA%/ANTLabLocalModel',str(root)) for a in freeze['service_arguments']]
source_names=['基础/tests/citation_review_candidate.py','基础/tests/check_citation_review.py',
    '基础/tests/run_citation_review.py','基础/tests/run_formal_round2.py' ,'基础/tests/general_candidate.py','基础/tests/answer_form_candidate.py',
    '基础/tests/two_step_linked_candidate.py','基础/tests/two_step_candidate.py','基础/runs/improve/linked_r0/student-v2.py',
    '基础/starter/student.py','基础/starter/provider.py']
source_names += [(folder/n).relative_to(repo).as_posix() for n in ['source-inputs.json','config.diagnostic.json','request-diff.json','system.diagnostic.txt','local_defect_candidate.py','run_local_defect_diagnostic.py']]
(folder/'code-snapshot').mkdir(parents=True,exist_ok=True)
source_hashes={n:sha(repo/n) for n in source_names}
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
        messages=copy.deepcopy(row['revised_messages'])
        conf=copy.deepcopy(config);rule={'kind':'explicit_defect_diagnostic','answer_not_generated':True}
        assert messages==reviewer.prepare_local_messages(row['local_clause'])
        body={'model':conf['model'],'messages':messages,'stream':False,**conf['parameters']}
        assert body['max_tokens']==128 and 'response_format' not in body
        raw=service('apply-template',body);prompt=raw['prompt']
        tokens=service('tokenize',{'content':prompt,'add_special':True,'parse_special':True})['tokens']
        item={**job,'messages':messages,'config':conf,'schema_rule':rule,'body':body,'used_passages':used,
              'template_response':raw,'input_tokens':len(tokens),'budget':128,'total':len(tokens)+128}
        jobs.append(item);write('capacity-check.json',{'checked_at':now(),'rows':jobs,'counts_as_generation':False},True)
        assert all(m['content'] in prompt for m in messages) and prompt.endswith('<think>\n\n</think>\n\n')
        assert item['total']<=4096,'完整输入超限'
    assert len(jobs)==2 and len({j['case_id'] for j in jobs})==2
    for row in inputs.values():
        assert sha(repo/row['source_path'])==row['source_sha256']
    write('freeze.json',{'saved_at':now(),'generation_calls_so_far':0,'frozen':True,'experiment_kind':'local_first_clause_defect_reading_diagnostic','design':design,'execution_plan':plan,'order':plan['order'],'review_prompt':reviewer.REVIEW_PROMPT,'review_schema':reviewer.REVIEW_SCHEMA,
        'config':config,'service_arguments':freeze['service_arguments'],'code_hashes':source_hashes,
        'data_hashes':freeze['data_hashes'],'model':freeze['model'],'llama_cpp':freeze['llama_cpp'],
        'actual_schemas':[{'case_id':j['case_id'],'variant':j['variant'],'response_format':j['body'].get('response_format')} for j in jobs],
        'original_answer_side':'historical_reuse_not_synchronous_control','max_input_tokens':max(j['input_tokens'] for j in jobs),
        'max_total_tokens':max(j['total'] for j in jobs),'evaluation_rules':freeze['evaluation_rules'],
        'selection_provenance':'历史完整原段落和候选重放；本轮只摘录缺陷，不生成最终答案。'})
    fixed_hash=sha(folder/'freeze.json')
    print('FREEZE SAVED',now(),'review calls',len(jobs),'max tokens',max(j['total'] for j in jobs),flush=True)
    for job in jobs:
        assert sha(folder/'freeze.json')==fixed_hash
        assert not abort.is_set() and memory()['available_bytes']>=1024**3
        assert all(sha(repo/n)==h for n,h in source_hashes.items())
        row=inputs[job['case_id']]
        record={k:copy.deepcopy(job[k]) for k in ['sequence','case_id','variant','messages','config','used_passages','input_tokens','schema_rule']}
        record.update(run_id=str(uuid.uuid4()),started_at=now(),run_kind='live_api',mode='local',
            condition='R0',review_stage_only=True,original_answer_provenance='historical_replay',
            original_passages=row['passages'],question=row['question'],original_response=row['original_response'],
            original_raw_content=row['original_raw_content'],source_path=row['source_path'],source_sha256=row['source_sha256'],
            source_run_id=row['source_run_id'],memory_before=memory(),status='pending',
            generation_dispatched=False,model_revision=freeze['model']['revision'],weight_sha256=freeze['model']['actual_sha256'],
            attempt=1,retry_of=None)
        records.append(record);name='run-'+record['run_id']+'.json';write(name,record)
        record['cache_erase']=service('slots/0?action=erase',{})
        offset=log.stat().st_size;build=urllib.request.build_opener
        class Capture:
            def __init__(self,inner):self.inner=inner
            def open(self,request,*a,**kw):
                actual=json.loads(request.data);assert actual==job['body'] and actual['max_tokens']==128
                assert runtime['generation_dispatches']<2
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
        record['id_validation']=reviewer.check_local(record['raw_content'],row['passages'])
        record['snapshot_candidates']=row['candidates']
        write(name,record,True)
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
    summary={'completed_diagnostic_responses':len(confirmed),'generation_dispatches':runtime['generation_dispatches'],
        'technical_stop':runtime['technical_stop'],'service_stopped':runtime['service_stopped'],
        'previous_cumulative':304,'cumulative_confirmed':304+len(confirmed),'initial_answer_generation_calls':0,
        'unique_run_ids':[r['run_id'] for r in confirmed],'budget_exhausted':sum(r.get('budget_exhausted',False) for r in records),
        'truncation_true':sum(r.get('truncated') is True for r in records),'truncation_unverified':sum(r.get('truncated')=='not_verified' for r in records)}
    write('execution-summary.json',summary)
    print('FINAL',json.dumps({k:v for k,v in summary.items() if k!='unique_run_ids'},ensure_ascii=False),flush=True)
