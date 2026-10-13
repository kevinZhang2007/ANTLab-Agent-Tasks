"""按已确认清单执行第一轮正式请求；首次记录不可重发，语义评价另轮进行。"""
from pathlib import Path
from datetime import datetime
import copy, ctypes, hashlib, json, math, os, re, socket, subprocess, sys, threading, time, uuid
import urllib.request, urllib.error

repo=Path(__file__).resolve().parents[2]
base=repo/'基础'
prep=base/'runs/formal_preparation/20261013-131201'
folder=base/'runs/formal/round1'
assert not folder.exists(),'已有正式轮次；先核查保存记录，禁止自动重复或覆盖'
folder.mkdir(parents=True)
def now():return datetime.now().astimezone().isoformat()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def write(name,value,replace=False):
    p=folder/name
    if not replace:assert not p.exists(),'禁止覆盖已有结果'
    with p.open('w',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.flush();os.fsync(stream.fileno())
settings=load(prep/'candidate-settings.json');config=load(prep/'config.candidate.json')
run_list=load(prep/'run-list.json');jobs=run_list['items']
evaluation=load(prep/'evaluation-rules.json');failure=load(prep/'failure-rules.json')
capacity=load(prep/'capacity-summary.json')
root=Path(os.environ['LOCALAPPDATA'])/'ANTLabLocalModel'
args=[s.replace('%LOCALAPPDATA%/ANTLabLocalModel',str(root)) for s in settings['service_arguments']]
differences=[]
for name,expected in {**settings['code_sha256'],**settings['data_sha256']}.items():
    actual=sha(repo/name) if (repo/name).exists() else None
    if actual!=expected:differences.append({'path':name,'expected':expected,'actual':actual})
for path,expected in [(prep/'config.candidate.json',settings['request_config_sha256']),
 (root/'models/Qwen3-0.6B-Q8_0.gguf',settings['model']['actual_sha256']),
 (root/'llama-b11429/llama-server.exe',settings['llama_cpp']['executable_sha256'])]:
    actual=sha(path) if path.exists() else None
    if actual!=expected:differences.append({'path':str(path).replace(str(root),'%LOCALAPPDATA%/ANTLabLocalModel'),'expected':expected,'actual':actual})
if differences:
    write('precheck-differences.json',{'checked_at':now(),'differences':differences,'generation_calls':0});raise SystemExit('STOP: 准备哈希不一致，未加载或生成')
assert capacity['all_fit'] and capacity['checked_items']==40
assert len(jobs)==40 and [j['sequence'] for j in jobs]==list(range(1,41))
assert len({(j['case_id'],j['condition'],j['variant']) for j in jobs})==40
assert sum(j['variant']=='baseline' for j in jobs)==32
assert all(j['condition']=='R0' for j in jobs if j['variant']=='improved')
sys.path.insert(0,str(base/'starter'))
import runner,student,provider
assert hashlib.sha256(student.prepare_messages('',[])[0]['content'].encode()).hexdigest()==settings['system_prompt_sha256']
assert config['parameters']['response_format']==settings['schema']
old={p.relative_to(repo).as_posix():sha(p) for p in (base/'runs').rglob('*') if p.is_file() and folder not in p.parents}
for name in ['report.md','README.md','基础/开发记录.md','基础/config.local.json','基础/config.local.example.json',*settings['code_sha256'],*settings['data_sha256']]:
    if (repo/name).is_file():old[name]=sha(repo/name)
write('protected-hashes.json',old)
write('precheck.json',{'checked_at':now(),'all_preparation_hashes_match':True,'code_hashes':settings['code_sha256'],'data_hashes':settings['data_sha256'],'model_hash_verified':True,'service_arguments_match_preparation':True,'config_matches_preparation':True,'run_list_sha256':sha(prep/'run-list.json'),'generation_calls':0})
write('research-question.json',{'recorded_at':now(),'primary_question':'同一资料集合的顺序变化是否改变回答与引用表现；第一版文字排序是否改善R0结果。',
 'competing_explanation':'变化可能来自模型对范围、计算或证据组合的错误，不能仅凭输出变化认定位置是唯一原因。',
 'K_limit':'K同时改变资料选择和数量，单独分析，不当纯位置效应。',
 'design_timing':'这些命题在查看开发结果后制定，不声称是开发实验前预测；尚未查看本轮正式生成结果。',
 'comparison_unit':'8道题的配对观察，不把40次请求视作40道独立题。','quality_review':'本轮不核验答案正确、必要覆盖、支持、无关引用；下一轮依据实际原文逐题复核。'})
numeric={k:v for k,v in config['parameters'].items() if isinstance(v,(int,float))}
http_calls=[];index=[];records=[];inputs=[];process=None
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def service(route,body=None):
    assert route in {'health','props','slots','apply-template','tokenize','slots/0?action=erase'}
    http_calls.append({'route':route,'time':now()})
    req=urllib.request.Request('http://127.0.0.1:8080/'+route,data=None if body is None else json.dumps(body,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
    with opener.open(req,timeout=20) as response:return json.loads(response.read())
class MemoryStatus(ctypes.Structure):
    _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ('total','available','total_page','available_page','total_virtual','available_virtual','extended')]
def memory():
    m=MemoryStatus();m.length=ctypes.sizeof(m)
    assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return {'time':now(),'available_bytes':m.available,'total_bytes':m.total}
runtime={'started_at':now(),'generation_dispatches':0,'technical_stop':False,'arguments':settings['service_arguments'],'memory_before':memory(),'memory_samples':[]}
stop=threading.Event();abort=threading.Event();thread=None
def monitor():
    low=0
    while not stop.is_set():
        m=memory();runtime['memory_samples'].append(m)
        low=low+1 if m['available_bytes']<1024**3 else 0
        if low>=3:
            abort.set()
            if process and process.poll() is None:process.terminate()
            return
        stop.wait(2)
def duplicate_fields(pairs):
    value={}
    for k,v in pairs:
        if k in value:raise ValueError('duplicate_json_key')
        value[k]=v
    return value
def structure(content,used):
    try:value=json.loads(content,object_pairs_hook=duplicate_fields)
    except (ValueError,TypeError):value=None
    valid=isinstance(value,dict) and set(value)=={'answer','citations'} and isinstance(value.get('answer'),str) and isinstance(value.get('citations'),list) and all(isinstance(i,str) for i in value['citations'])
    citations=value['citations'] if valid else []
    visible={p['id'] for p in used}
    return {'format_complete':valid,'empty_content':not isinstance(content,str) or not content.strip(),'empty_answer':valid and not value['answer'].strip(),
     'citations_empty':valid and not citations,'citation_ids_exist':bool(valid and citations and all(i in visible for i in citations)),
     'unknown_citation_ids':[i for i in citations if i not in visible],'duplicate_citation_ids':sorted({i for i in citations if citations.count(i)>1}),
     'answer_correct':'not_checked','necessary_evidence_covered':'not_checked','citation_support':'not_checked','irrelevant_citations':'not_checked','strict_complete_success':'not_checked'}
def update_index(record):
    item={k:record[k] for k in ['sequence','case_id','condition','variant','run_id','status']}
    item.update(path='基础/runs/formal/round1/run-'+record['run_id']+'.json',technical_failure=record.get('technical_failure',False),elapsed_seconds=record.get('elapsed_seconds'),checks=record.get('structure_checks'),finish_reason=record.get('finish_reason'),budget_exhausted=record.get('budget_exhausted'),truncated=record.get('truncated','not_verified'))
    index.append(item);write('result-index.json',{'updated_at':now(),'planned_items':40,'items':index},replace=(folder/'result-index.json').exists())
log_path=folder/'server-log.txt'
try:
    assert runtime['memory_before']['available_bytes']>=2*1024**3,'可用内存不足2 GiB'
    with socket.socket() as sock:sock.bind(('127.0.0.1',8080))
    with (folder/'server-stdout.log').open('wb') as stdout,log_path.open('wb') as stderr:
        process=subprocess.Popen(args,stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
    start=time.perf_counter();thread=threading.Thread(target=monitor,daemon=True);thread.start()
    while True:
        if abort.is_set():raise RuntimeError('内存持续低于1 GiB')
        if process.poll() is not None:raise RuntimeError('服务加载失败')
        try:
            if service('health').get('status')=='ok':break
        except (urllib.error.URLError,TimeoutError):pass
        if time.perf_counter()-start>120:raise TimeoutError('服务启动超时')
        time.sleep(.5)
    runtime['load_seconds']=time.perf_counter()-start;runtime['memory_after_load']=memory()
    props=service('props');params=props['default_generation_settings']['params']
    assert props['default_generation_settings']['n_ctx']==4096 and props['total_slots']==1
    assert props['build_info']=='b11429-d81235049' and props['model_alias']==config['model']
    assert all(math.isclose(params[k],v,rel_tol=1e-6,abs_tol=1e-6) for k,v in numeric.items() if k!='max_tokens')
    runtime['service_checked']={'build':props['build_info'],'context':4096,'slots':1,'sampling_defaults_match':True,'repeat_penalty':params.get('repeat_penalty'),'reasoning_format':params.get('reasoning_format'),'template_sha256':hashlib.sha256(props['chat_template'].encode()).hexdigest()}
    for job in jobs:
        case,original,selected,messages=runner.prepare(job['case_id'],job['condition'],job['variant'])
        if job['variant']=='baseline':assert selected==original
        else:assert len(selected)==len(original) and {p['id'] for p in selected}=={p['id'] for p in original} and all(p in original for p in selected)
        assert json.loads(messages[1]['content'])=={'question':case['question'],'passages':selected}
        body={'model':config['model'],'messages':messages,'stream':False,**config['parameters']}
        prompt=service('apply-template',body)['prompt']
        assert all(m['content'] in prompt for m in messages) and prompt.endswith('<think>\n\n</think>\n\n')
        count=len(service('tokenize',{'content':prompt,'add_special':True,'parse_special':True})['tokens'])
        expected=next(r for r in capacity['items'] if r['sequence']==job['sequence'])
        assert count==expected['input_tokens'] and count+256<4096
        inputs.append({'job':job,'original':original,'selected':selected,'messages':messages,'body':body,'count':count})
    # 先将完整冻结记录fsync落盘，再允许第一次生成。
    write('freeze.json',{'frozen_at':now(),'frozen':True,'round':'first_formal_round','preparation_reference':'基础/runs/formal_preparation/20261013-131201','research_question':load(folder/'research-question.json'),
     'code_hashes':{**settings['code_sha256'],'基础/tests/run_formal_round1.py':sha(Path(__file__))},'data_hashes':settings['data_sha256'],'dataset_version':settings['dataset_version'],
     'model':settings['model'],'llama_cpp':settings['llama_cpp'],'complete_request_config':config,'service_arguments':settings['service_arguments'],'service_controls':settings['service_controls'],
     'actual_service_checks':runtime['service_checked'],'run_order':run_list,'evaluation_rules':evaluation,'failure_rules_from_preparation':failure,
     'execution_authorization':{'source':'本轮用户明确授权冻结并执行清单40项，不授权技术重试。','generation_allowed':True,'maximum_main_dispatches':40,'preparation_only_no_generation_flags_superseded_for_this_round':True},
     'input_manifest':[{'sequence':x['job']['sequence'],'case_id':x['job']['case_id'],'condition':x['job']['condition'],'variant':x['job']['variant'],
       'original_passage_ids':[p['id'] for p in x['original']],'selected_passage_ids':[p['id'] for p in x['selected']],
       'actual_request_sha256':hashlib.sha256(json.dumps(x['body'],ensure_ascii=False).encode()).hexdigest(),'input_tokens':x['count'],'output_budget':256} for x in inputs],
     'cache_policy':'每项生成前清空单槽缓存，沿用开发实验冷请求做法；清空结果逐条记录。',
     'evaluation_this_round':'仅格式、ID存在、用量、结束原因、参数及截断；所有语义评价not_checked。'})
    freeze_hash=sha(folder/'freeze.json')
    print('FREEZE SAVED',folder.relative_to(repo).as_posix(),now(),flush=True)
    for x in inputs:
        job=x['job']
        if abort.is_set():raise RuntimeError('内存不足，停止')
        assert all(sha(repo/n)==v for n,v in {**settings['code_sha256'],**settings['data_sha256']}.items()),'冻结后代码或数据变化'
        assert sha(prep/'config.candidate.json')==settings['request_config_sha256'] and sha(folder/'freeze.json')==freeze_hash
        erase=service('slots/0?action=erase',{})
        record={**job,'schema_version':1,'run_id':str(uuid.uuid4()),'started_at':now(),'split':'evaluation','attempt':1,'retry_of':None,'main_result':True,'mode':'local','run_kind':'live_api',
         'freeze_sha256':freeze_hash,'config':copy.deepcopy(config),'model_revision':settings['model']['revision'],'weight_sha256':settings['model']['actual_sha256'],
         'data_sha256':settings['data_sha256']['基础/data/cases.json'],'student_sha256':settings['code_sha256']['基础/starter/student.py'],
         'provider_sha256':settings['code_sha256']['基础/starter/provider.py'],'driver_sha256':sha(Path(__file__)),
         'messages':x['messages'],'original_passages':x['original'],'used_passages':x['selected'],
         'original_passage_ids':[p['id'] for p in x['original']],'selected_passage_ids':[p['id'] for p in x['selected']],
         'rendered_prompt_tokens':x['count'],'output_budget':256,'context':4096,'cache_erase':erase,'status':'request_pending','generation_dispatched':False}
        name='run-'+record['run_id']+'.json'
        write(name,record);records.append(record)
        original_opener=urllib.request.build_opener
        class CaptureOpener:
            def __init__(self,inner):self.inner=inner
            def open(self,request,*a,**kw):
                actual=json.loads(request.data)
                assert actual==x['body'] and actual['max_tokens']==256,'实际请求与冻结内容不符'
                record.update(actual_http_request_body=actual,raw_http_request_body=request.data.decode('utf-8'),request_verified_before_send=True,generation_dispatched=True)
                runtime['generation_dispatches']+=1;write(name,record,replace=True)
                try:return self.inner.open(request,*a,**kw)
                except urllib.error.HTTPError as error:
                    record['raw_http_error_body']=error.read().decode('utf-8',errors='replace');raise
        urllib.request.build_opener=lambda *a,**kw:CaptureOpener(original_opener(*a,**kw))
        log_offset=log_path.stat().st_size
        try:record.update(provider.call_model(x['messages'],config))
        except Exception as error:record.update(status='driver_exception',error_type=type(error).__name__,error_detail=str(error),response=None,usage=None)
        finally:
            urllib.request.build_opener=original_opener;record['returned_at']=now();write(name,record,replace=True)
        technical=record['status']!='ok' or not isinstance(record.get('response'),dict) or not record['response'].get('choices')
        record['provider_status']=record['status']
        if not technical:
            choice=record['response']['choices'][0];content=choice.get('message',{}).get('content','')
            record['finish_reason']=choice.get('finish_reason')
            record['budget_exhausted']=choice.get('finish_reason')=='length' or (record.get('usage') or {}).get('completion_tokens',0)>=256
            record['structure_checks']=structure(content,x['selected'])
            try:
                slots=service('slots');record['slot_after_request']=slots
                task_params=slots[0]['params']
                record['parameter_checks']={k:math.isclose(task_params[k],v,rel_tol=1e-6,abs_tol=1e-6) for k,v in numeric.items() if k in task_params}
                record['parameters_not_echoed']=[k for k in numeric if k not in task_params]+['response_format','effective_n_predict_max']
                record['budget_observation']={'actual_body_max_tokens':record['actual_http_request_body']['max_tokens'],'task_max_tokens_echo':task_params.get('max_tokens'),'task_n_predict_echo':task_params.get('n_predict'),'finish_reason_not_budget_echo':True}
                assert all(record['parameter_checks'].values()),'请求参数与冻结配置不一致'
                with log_path.open('rb') as stream:stream.seek(log_offset);segment=stream.read().decode('utf-8',errors='replace')
                record['server_log_segment']=segment.replace(str(root),'%LOCALAPPDATA%/ANTLabLocalModel')
                flags=re.findall(r'truncated\s*=\s*(\d+)',segment)
                record['truncated']=bool(int(flags[0])) if len(flags)==1 else 'not_verified'
                if flags and any(int(f) for f in flags):raise RuntimeError('服务日志显示截断')
            except Exception as error:
                technical=True;record.update(postcheck_error=type(error).__name__,postcheck_detail=str(error))
        record['technical_failure']=technical
        if technical:record['status']='technical_failure';runtime['technical_stop']=True
        record['completed_at']=now();write(name,record,replace=True);update_index(record)
        print('ITEM',job['sequence'],job['case_id'],job['condition'],job['variant'],record['run_id'],record['status'],'format=',record.get('structure_checks',{}).get('format_complete','not_checked'),flush=True)
        if technical:break
except Exception as error:
    runtime.update(technical_stop=True,error_type=type(error).__name__,error_detail=str(error));print('STOP',type(error).__name__,str(error),flush=True)
finally:
    stop.set()
    if thread:thread.join(timeout=5)
    if process and process.poll() is None:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait()
    runtime['service_stopped']=process is None or process.poll() is not None
    runtime['ended_at']=now();runtime['memory_after_stop']=memory();runtime['auxiliary_http_calls']=http_calls
    for log_name in ['server-log.txt','server-stdout.log']:
        p=folder/log_name
        if p.exists():p.write_text(p.read_text(encoding='utf-8',errors='replace').replace(str(root),'%LOCALAPPDATA%/ANTLabLocalModel'),encoding='utf-8')
    write('runtime.json',runtime)
    returned=[r for r in records if isinstance(r.get('response'),dict) and r['response'].get('choices')]
    confirmed=[r for r in returned if (r.get('usage') or {}).get('completion_tokens',0)>0]
    ids=[r['run_id'] for r in records];assert len(ids)==len(set(ids))
    successful=[r for r in records if r.get('provider_status')=='ok' and isinstance(r.get('response'),dict) and r['response'].get('choices')]
    summary={'checked_at':now(),'planned':40,'records_saved':len(records),'main_dispatches':runtime['generation_dispatches'],'successful_returns':len(successful),
     'technical_failure_records':sum(r.get('technical_failure',False) for r in records),'whole_round_technical_stop':runtime['technical_stop'],
     'format_failures':sum(not r['structure_checks']['format_complete'] for r in records if 'structure_checks' in r),
     'empty_content':sum(r['structure_checks']['empty_content'] for r in records if 'structure_checks' in r),
     'empty_answer':sum(r['structure_checks']['empty_answer'] for r in records if 'structure_checks' in r),
     'budget_exhausted':sum(r.get('budget_exhausted',False) for r in records),
     'unexecuted_items':[j for j in jobs if j['sequence'] not in {r['sequence'] for r in records if r.get('generation_dispatched')}],
     'confirmed_generation_calls':len(confirmed),'generation_dispatch_without_confirmed_completion':runtime['generation_dispatches']-len(confirmed),
     'previous_unique_generation_calls':84,'cumulative_confirmed_generation_calls':84+len(confirmed),'unique_run_ids':ids,
     'truncation_true':sum(r.get('truncated') is True for r in records),'truncation_unverified':sum(r.get('truncated','not_verified')=='not_verified' for r in records),
     'parameter_mismatch_records':sum(any(v is False for v in r.get('parameter_checks',{}).values()) for r in records),
     'semantic_review':'not_checked：答案正确、必要覆盖、语义支持、无关引用及严格完整成功下一轮逐题原文复核。','service_stopped':runtime['service_stopped']}
    write('summary.json',summary)
    unchanged=all(sha(repo/n)==v for n,v in old.items())
    write('protected-file-audit.json',{'checked_at':now(),'protected_count':len(old),'all_unchanged':unchanged,'changed':[n for n,v in old.items() if sha(repo/n)!=v]})
    names=[p.relative_to(repo).as_posix() for p in sorted(folder.rglob('*')) if p.is_file()]
    names+=['基础/tests/run_formal_round1.py','基础/runs/formal/round1/new-files.json']
    write('new-files.json',{'recorded_at':now(),'new_files':names,'modified_existing_files':[]})
    print('FINAL',json.dumps({k:v for k,v in summary.items() if k not in ['unique_run_ids','unexecuted_items']},ensure_ascii=False),flush=True)
