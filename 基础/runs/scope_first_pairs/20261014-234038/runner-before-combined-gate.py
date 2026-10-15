"""评测后范围顺序修复：同一题旧/新完整流程，最多4次生成。"""
from pathlib import Path
from datetime import datetime
import copy, ctypes, hashlib, json, math, os, re, socket, subprocess, sys, threading, time, uuid
import urllib.request, urllib.error
sys.path.insert(0,str(next(p for p in Path(__file__).resolve().parents if (p/'基础/starter/provider.py').is_file())/'基础/tests'))
import eligibility_general_candidate as candidate
import old_eligibility_general_candidate as old_candidate

repo = next(p for p in Path(__file__).resolve().parents if (p/'基础/starter/provider.py').is_file())
base = repo/'基础'
sys.path.insert(0, str(base/'starter'))
import runner, provider

def now(): return datetime.now().astimezone().isoformat()
def load(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
    folder = Path(sys.argv[1]).resolve()
    assert folder.exists() and not list(folder.glob('run-*.json')) and not (folder/'runtime.json').exists(), '禁止重复或自动续发'
    def write(name, value, update=False):
        path = folder/name
        assert update or not path.exists(), '禁止覆盖'+name
        with path.open('w',encoding='utf-8') as stream:
            json.dump(value,stream,ensure_ascii=False,indent=2); stream.flush(); os.fsync(stream.fileno())
    first = base/'runs/formal_preparation/20261013-131201'
    settings = load(folder/'settings.prepared.json')
    answer = load(folder/'answer.prepared.json')
    selection = load(folder/'selection.prepared.json')
    jobs = load(folder/'execution-plan.prepared.json')['items']
    assert len(jobs)==2 and all(j['condition']=='R0' and j['variant']=='improved' for j in jobs)
    assert len({(j['case_id'],j['scheme']) for j in jobs})==2
    root = Path(os.environ['LOCALAPPDATA'])/'ANTLabLocalModel'
    args = [a.replace('%LOCALAPPDATA%/ANTLabLocalModel',str(root)) for a in settings['service_arguments']]
    sources = ['基础/tests/general_candidate.py','基础/tests/check_general_candidate.py',
               '基础/tests/run_formal_round2.py','基础/tests/two_step_candidate.py',
               '基础/tests/two_step_linked_candidate.py','基础/tests/answer_form_candidate.py',
               '基础/runs/improve/linked_r0/student-v2.py',
               '基础/starter/student.py','基础/starter/provider.py','基础/starter/runner.py']
    sources += ['基础/tests/direct_reference_candidate.py','基础/tests/association_repair_candidate.py']
    sources += [(folder/name).relative_to(repo).as_posix() for name in ['run_scope_first_pairs.py','eligibility_general_candidate.py','explicit_state_checker.py','eligibility_exclusion_candidate.py','typed_enum_role_revision.py','typed_identifier_enum_candidate.py','body_identifier_enum_candidate.py','offline_gate.py','settings.prepared.json','answer.prepared.json','selection.prepared.json','execution-plan.prepared.json','old_eligibility_general_candidate.py','scope_first_occurrences.py']]
    code_hashes = {p:sha(repo/p) for p in sources}
    data_hashes = {p:sha(repo/p) for p in settings['data_sha256']}
    old = {p.relative_to(repo).as_posix():sha(p) for p in (base/'runs').rglob('*') if p.is_file() and folder not in p.parents}
    for name in ['report.md','README.md','基础/开发记录.md','基础/config.local.json',*sources]:
        if (repo/name).exists(): old[name]=sha(repo/name)
    write('protected-hashes.json',old)
    failure = {'technical':'HTTP/超时/服务错误、容量超限、参数或哈希不符立即保存并停止；无自动重试。',
               'quality':'错误答案、非法定位、漏选、空选择、格式错误、预算耗尽均保留，不重试。',
               'selection_failure':'主任务保留分母，不执行第二步，不回退。',
               'memory':'加载前至少2 GiB；请求前至少1 GiB；连续3个2秒样本低于1 GiB停止自有服务。',
               'denominator':'同一题旧/新两个完整流程，每侧一次定位+回答，最多4次生成，不是独立两题。'}
    evaluation = load(first/'evaluation-rules.json')
    research = {'recorded_at':now(),'main_question':'范围优先核对后，同一完整R0资料旧/新资格排除、答案与引用表现是否变化。',
                'competing_explanations':['第一步可能漏选或选错范围，补页关系识别也可能失败。',
                    '资料缩减、顺序、额外调用和答案形式Schema共同变化；覆盖齐全后仍可能计算或回答错误。'],
                'timing':'开发和首轮评测结果已接触；这是评测后重复评测，不是独立盲测或泛化验证。',
                'K':'同时改变资料选择和数量，单独分析。',
                'history_differences':['本轮不跑baseline或其他条件；只报告本轮完整R0 improved，不把历史差异归因于单一因素。',
                    '当前完整流程为新定位、直接补页、原输入相对顺序回答、通用答案形式及类型enum；可靠资格规则自动核查通过才排除。',
                    '额外定位请求、最终资料选择和调用总量变化；模型/最终提示词/采样/256预算/服务设置不变。'],
                'development_lineage':'复用已验证组件；为遵守本轮原输入相对顺序契约，最终展示顺序不沿用历史开发的排序后顺序。'}
    write('design-plan.json',{'saved_at':now(),'research':research,'order':jobs,'failure_rules':failure,
          'evaluation':evaluation,'maximum_generation_calls':4,'evaluation_after_all_calls':True})
    write('config.answer.json',answer); write('config.selection.json',selection)
    assert load(folder/'offline-check.json')['passed']
    assert load(folder/'runner-gate-integration.json')['passed']
    differences=[]
    for name, expected in {**settings['data_sha256'],**{n:v for n,v in settings['code_sha256'].items() if n.startswith('基础/starter/')}}.items():
        if sha(repo/name)!=expected: differences.append(name)
    for path,expected in [(root/'models/Qwen3-0.6B-Q8_0.gguf',settings['model']['actual_sha256']),
                         (root/'llama-b11429/llama-server.exe',settings['llama_cpp']['executable_sha256'])]:
        if sha(path)!=expected: differences.append(str(path))
    write('source-check.json',{'checked_at':now(),'differences':differences,'code_hashes':code_hashes,'data_hashes':data_hashes})
    assert not differences, '来源哈希不符'
    process=None; stop=threading.Event(); abort=threading.Event(); monitor_thread=None
    calls=[]; tasks=[]; templates=[]; context=4096
    runtime={'started_at':now(),'generation_dispatches':0,'technical_stop':False,'arguments':settings['service_arguments'],'memory_samples':[]}
    class Memory(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ('total','available','total_page','available_page','total_virtual','available_virtual','extended')]
    def memory():
        value=Memory();value.length=ctypes.sizeof(value)
        assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value))
        return {'time':now(),'available_bytes':value.available,'total_bytes':value.total}
    def monitor():
        low=0
        while not stop.is_set():
            m=memory();runtime['memory_samples'].append(m)
            low=low+1 if m['available_bytes']<1024**3 else 0
            if low>=3:
                abort.set()
                if process and process.poll() is None: process.terminate()
                return
            stop.wait(2)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def service(route,body=None):
        assert route in {'health','props','slots','apply-template','tokenize','slots/0?action=erase'}
        request=urllib.request.Request('http://127.0.0.1:8080/'+route,data=None if body is None else json.dumps(body,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
        with opener.open(request,timeout=20) as response: return json.loads(response.read())
    def render(messages,conf,label):
        body={'model':conf['model'],'messages':messages,'stream':False,**conf['parameters']}
        raw=service('apply-template',body);prompt=raw['prompt']
        tokens=service('tokenize',{'content':prompt,'add_special':True,'parse_special':True})['tokens']
        row={'label':label,'request':body,'template_response':raw,'rendered_prompt':prompt,
             'input_tokens':len(tokens),'output_budget':256,'total':len(tokens)+256,'fits':len(tokens)+256<=context}
        templates.append(row); write('template-checks.json',templates,update=(folder/'template-checks.json').exists())
        assert all(m['content'] in prompt for m in messages),'模板未保留消息'
        assert prompt.endswith('<think>\n\n</think>\n\n'),'关闭思考模板不符'
        assert row['fits'],'完整输入超限，不截断'
        return row
    numeric={k:v for k,v in answer['parameters'].items() if isinstance(v,(int,float)) and k!='max_tokens'}
    log=folder/'server-log.txt'
    freeze_hash=None; current=None
    def dispatch(stage,messages,conf,used):
        assert freeze_hash and sha(folder/'freeze.json')==freeze_hash
        assert all(sha(repo/n)==v for n,v in {**code_hashes,**data_hashes}.items())
        assert not abort.is_set() and memory()['available_bytes']>=1024**3
        rendered=render(messages,conf,{'main_task_id':current['main_task_id'],'stage':stage,'actual_branch':True})
        record={'run_id':str(uuid.uuid4()),'main_task_id':current['main_task_id'],'stage':stage,
                'case_id':current['case_id'],'condition':current['condition'],'variant':current['variant'],
                'run_kind':'live_api','mode':'local','started_at':now(),'attempt':1,'retry_of':None,
                'freeze_sha256':freeze_hash,'config':conf,'messages':messages,'used_passages':copy.deepcopy(used),
                'input_tokens':rendered['input_tokens'],'rendered_prompt':rendered['rendered_prompt'],
                'memory_before':memory(),'status':'request_pending','generation_dispatched':False}
        path='run-'+record['run_id']+'.json';write(path,record);calls.append(record)
        record['cache_erase']=service('slots/0?action=erase',{})
        offset=log.stat().st_size;build=urllib.request.build_opener
        class Capture:
            def __init__(self,inner): self.inner=inner
            def open(self,request,*a,**kw):
                actual=json.loads(request.data)
                assert actual==rendered['request'] and actual['max_tokens']==256
                assert runtime['generation_dispatches']<4
                record.update(actual_http_request_body=actual,raw_http_request_body=request.data.decode(),generation_dispatched=True)
                runtime['generation_dispatches']+=1;write(path,record,True)
                try:return self.inner.open(request,*a,**kw)
                except urllib.error.HTTPError as error:
                    record['raw_http_error_body']=error.read().decode(errors='replace');raise
        urllib.request.build_opener=lambda *a,**kw:Capture(build(*a,**kw))
        try: record.update(provider.call_model(messages,conf))
        finally: urllib.request.build_opener=build;write(path,record,True)
        record['memory_after']=memory();record['returned_at']=now()
        if record['status']!='ok' or not isinstance(record.get('response'),dict) or not record['response'].get('choices'):
            record['technical_failure']=True;write(path,record,True);raise RuntimeError('技术请求失败 '+record['run_id'])
        choice=record['response']['choices'][0]
        record.update(finish_reason=choice.get('finish_reason'),budget_exhausted=choice.get('finish_reason')=='length',
                      raw_content=choice.get('message',{}).get('content',''),raw_reasoning=choice.get('message',{}).get('reasoning_content'))
        slots=service('slots');params=slots[0]['params'];record['slot_after']=slots
        record['parameter_checks']={k:math.isclose(params[k],v,rel_tol=1e-6,abs_tol=1e-6) for k,v in numeric.items() if k in params}
        record['parameters_not_echoed']=[k for k in numeric if k not in params]+['response_format','effective_max_tokens']
        record['budget_verification']='发送正文max_tokens=256；finish_reason不是请求预算回显。'
        with log.open('rb') as stream:stream.seek(offset);segment=stream.read().decode(errors='replace')
        record['server_log_segment']=segment.replace(str(root),'%LOCALAPPDATA%/ANTLabLocalModel')
        flags=re.findall(r'truncated\s*=\s*(\d+)',segment)
        record['truncated']=any(int(f) for f in flags) if flags else 'not_verified'
        write(path,record,True)
        assert all(record['parameter_checks'].values()),'参数回显不符'
        assert record['truncated'] is not True,'服务截断'
        print('STAGE',current['sequence'],current['case_id'],stage,record['run_id'],record['finish_reason'],flush=True)
        return copy.deepcopy(record)
    try:
        runtime['memory_before']=memory();assert runtime['memory_before']['available_bytes']>=2*1024**3
        with socket.socket() as sock: sock.bind(('127.0.0.1',8080))
        with (folder/'server-stdout.log').open('wb') as out,log.open('wb') as err:
            process=subprocess.Popen(args,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
        runtime['owned_pid']=process.pid;write('owned-service.json',{'pid':process.pid,'started_at':now(),'arguments':settings['service_arguments']})
        begin=time.perf_counter();monitor_thread=threading.Thread(target=monitor,daemon=True);monitor_thread.start()
        while True:
            assert not abort.is_set() and process.poll() is None,'服务或内存错误'
            try:
                if service('health').get('status')=='ok':break
            except (urllib.error.URLError,TimeoutError):pass
            if time.perf_counter()-begin>120:raise TimeoutError('加载超时')
            time.sleep(.5)
        runtime['load_seconds']=time.perf_counter()-begin;runtime['memory_after_load']=memory()
        props=service('props');write('service-props.json',props)
        assert props['default_generation_settings']['n_ctx']==4096 and props['total_slots']==1
        assert props['build_info']=='b11429-d81235049' and props['model_alias']==answer['model']
        defaults=props['default_generation_settings']['params']
        assert all(math.isclose(defaults[k],v,rel_tol=1e-6,abs_tol=1e-6) for k,v in numeric.items())
        assert math.isclose(defaults['repeat_penalty'],1.0)
        inputs={}
        for job in jobs:
            case,original,_,_=runner.prepare(job['case_id'],job['condition'],'baseline')
            inputs[job['sequence']]=(case['question'],original)
            engine=old_candidate if job['scheme']=='old' else candidate
            messages,conf,_=engine.answer_request(case['question'],original,answer)
            render(messages,conf,{**job,'kind':'answer_full_original'})
            if job['variant']=='improved':
                ordered=candidate.student.improve(case['question'],copy.deepcopy(original))
                render(candidate.selection.prepare_selection_messages(case['question'],ordered),selection,{**job,'kind':'selection_full_sorted'})
                messages,conf,_=candidate.answer_request(case['question'],[],answer)
                render(messages,conf,{**job,'kind':'answer_empty'})
        write('capacity-summary.json',{'checked_at':now(),'all_fit':True,'main_tasks':2,'template_checks':len(templates),
              'maximum_input_tokens':max(r['input_tokens'] for r in templates),'maximum_total':max(r['total'] for r in templates),
              'context':4096,'output_budget':256,'actual_selected_branch_checked_before_each_request':True})
        write('freeze.json',{'frozen_at':now(),'frozen':True,'round':'post_evaluation_eligibility_r0_repeat','research':research,
              'source_commit':subprocess.check_output([str(Path(os.environ['LOCALAPPDATA'])/'Programs/Git/cmd/git.exe'),'rev-parse','HEAD'],cwd=repo,text=True).strip(),
              'code_hashes':code_hashes,'data_hashes':data_hashes,'model':settings['model'],'llama_cpp':settings['llama_cpp'],
              'answer_config':answer,'selection_config':selection,'service_arguments':settings['service_arguments'],
              'selection_prompt':candidate.selection.SELECTION_PROMPT,'selection_schema':candidate.selection.SELECTION_SCHEMA,
              'answer_prompt':candidate.student.prepare_messages('',[])[0]['content'],
              'answer_form_patterns':candidate.constrain_schema.__globals__['PATTERNS'],
              'order':jobs,'evaluation_rules':evaluation,'failure_rules':failure,'main_task_limit':2,'generation_limit':4,
              'final_order':'最终所选完整原段落按当前原输入相对顺序',
              'capacity_reference':'capacity-summary.json','cache_policy':'每阶段清空单槽缓存',
              'review_note':'所有生成结束后再复用已有原文依据与澄清；有争议保留，所有标签辅助暂判。'})
        freeze_hash=sha(folder/'freeze.json');print('FREEZE',folder.relative_to(repo),now(),flush=True)
        for job in jobs:
            current={**job,'main_task_id':str(uuid.uuid4()),'started_at':now(),'status':'pending'}
            tasks.append(current);path='task-'+str(job['sequence']).zfill(2)+'.json'
            def save(value):
                current.update(value);write(path,current,update=(folder/path).exists())
            question,original=inputs[job['sequence']]
            engine=old_candidate if job['scheme']=='old' else candidate
            save(engine.execute(question,original,job['variant'],answer,selection,dispatch,save))
            current['completed_at']=now();write(path,current,True)
            write('result-index.json',{'items':[{'sequence':t['sequence'],'case_id':t['case_id'],'condition':t['condition'],
                  'variant':t['variant'],'main_task_id':t['main_task_id'],'status':t['status'],
                  'path':(folder/('task-'+str(t['sequence']).zfill(2)+'.json')).relative_to(repo).as_posix(),
                  'run_ids':[s['run_id'] for s in t.get('stages',[])],'end_to_end_seconds':t.get('end_to_end_seconds')} for t in tasks]},True)
            print('TASK',job['sequence'],job['case_id'],job['condition'],job['variant'],current['status'],flush=True)
    except Exception as error:
        runtime.update(technical_stop=True,error_type=type(error).__name__,error_detail=str(error))
        write('technical-stop.json',{'recorded_at':now(),'error_type':type(error).__name__,'error_detail':str(error),
              'generation_dispatches':runtime['generation_dispatches'],'current_task':current})
        print('STOP',type(error).__name__,str(error),flush=True)
    finally:
        stop.set()
        if monitor_thread:monitor_thread.join(timeout=5)
        if process and process.pid==runtime.get('owned_pid') and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        runtime.update(ended_at=now(),service_stopped=process is None or process.poll() is not None,memory_after_stop=memory())
        write('runtime.json',runtime)
        confirmed=[r for r in calls if (r.get('usage') or {}).get('completion_tokens',0)>0]
        ids=[r['run_id'] for r in confirmed];assert len(ids)==len(set(ids))
        summary={'completed_main_tasks':sum(t.get('status') in ('completed','selection_output_failure') for t in tasks),
                 'selection_output_failures':sum(t.get('status')=='selection_output_failure' for t in tasks),
                 'planned_main_tasks':2,'generation_dispatches':runtime['generation_dispatches'],'confirmed_generation_calls':len(ids),
                 'previous_cumulative':334,'cumulative_confirmed':334+len(ids),'unique_run_ids':ids,
                 'technical_stop':runtime['technical_stop'],'service_stopped':runtime['service_stopped'],
                 'budget_exhausted':sum(r.get('budget_exhausted',False) for r in calls),
                 'truncated':sum(r.get('truncated') is True for r in calls),'truncation_unverified':sum(r.get('truncated')=='not_verified' for r in calls)}
        write('execution-summary.json',summary)
        changed=[n for n,v in old.items() if not (repo/n).exists() or sha(repo/n)!=v]
        write('protected-file-audit.json',{'checked_at':now(),'protected_count':len(old),'changed':changed,'all_unchanged':not changed})
        print('FINAL',json.dumps({k:v for k,v in summary.items() if k!='unique_run_ids'},ensure_ascii=False),flush=True)

from offline_gate import after_offline_success

if __name__=='__main__':
    target=Path(sys.argv[1]).resolve()
    after_offline_success(lambda:load(target/'offline-check.json'),main)
