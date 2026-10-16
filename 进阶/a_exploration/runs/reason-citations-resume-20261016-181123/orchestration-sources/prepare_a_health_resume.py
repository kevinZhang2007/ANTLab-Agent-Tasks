from pathlib import Path
import sys,json,copy,ast,shutil,difflib,os
from datetime import datetime
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
from compact_factorial import offline_checks as compact_checks
from thinking_modes import offline_checks as thinking_checks
from sentence_selection import offline_checks as sentence_checks
from sentence_interface import offline_checks as interface_checks
from checks_extended import run as old_checks
failed=HERE/'runs/reason-citations-20261016-180433';successful=HERE/'runs/thinking-compact-20261016-175212'
out=HERE/'runs'/('reason-citations-resume-'+datetime.now().strftime('%Y%m%d-%H%M%S'));out.mkdir();Path('a-health-resume-out.txt').write_text(str(out),encoding='utf-8')
protected={p.relative_to(ROOT).as_posix():sha(p) for p in HERE.rglob('*') if p.is_file() and out not in p.parents and not {'slot-cache','__pycache__'}&set(p.parts)}
for n in ['README.md','report.md','decisions.md','declaration.md','基础/开发记录.md','基础/starter/student.py','进阶/challenge_b/challenge.py','进阶/challenge_b/no_cache_engine.py']:protected[n]=sha(ROOT/n)
write(out/'protected-before.json',protected)
a=load(failed/'intervention-plan.json');b=load(successful/'intervention-plan.json');fr=load(failed/'runtime.json');sr=load(successful/'runtime.json')
assert a['service_arguments']==b['service_arguments'] and fr['dispatches']==fr['confirmed_generations']==0 and not list(failed.glob('run-*.json'))
write(out/'offline-health-diagnosis.json',{'at':now(),'failed_run':failed.relative_to(ROOT).as_posix(),'successful_run':successful.relative_to(ROOT).as_posix(),'same_launch_arguments':True,'launch_arguments':a['service_arguments'],'executable_and_model_hashes_same':a['executable_hash']==b['executable_hash'] and a['model_hash']==b['model_hash'],'cwd_failed':str(failed),'cwd_successful':str(successful),'cwd_note':'两次都用各自实验目录和相对slot-cache；目录名不同，布局相同。','environment_old':'旧记录未保存完整环境，无法确认旧失败与成功的环境差异；不推断相同。','health_url_from_code':'http://127.0.0.1:8080/health','expected_host_port':'由命令--host 127.0.0.1 --port 8080与Engine.url核对一致。','proxy_from_code':'urllib.request.build_opener(ProxyHandler({}))，健康请求不使用环境代理。','old_per_request_timeout_seconds':30,'old_total_wait_seconds':120,'old_health_exception_logging':'except Exception:pass，未记录实际异常；HTTPError另存分支未出现文件，不能据此排除连接异常。','old_actual_http_status':'not_saved','old_actual_response_body':'not_saved','old_exception_type':'not_saved','old_process_exit_code':'not_saved','failed_log_model_loaded_seconds':1.552982,'failed_log_listening_seconds':1.552991,'successful_health_seconds':sr['load_seconds'],'failed_min_available_GiB':min(x['available_bytes'] for x in fr['memory_samples'])/2**30,'observed_old_process_exit_before_timeout':False,'reason_for_previous_value':'轮询未记录poll返回值；若发现退出会进入另一错误分支，旧错误仅健康超时。不能确认自然退出码。','confirmed_defect':'异常被吞掉且缺少健康HTTP及进程退出审计，不能定位旧失败根因。','not_proven':['内存不足','加载尚未完成','等待错误端口','健康正文误判','网络或执行环境问题'],'repair':'独立启动器保留120秒总限，每次健康请求最多2秒并保存完整结果、异常链、进程poll；输出进度，保存停止前后退出码。','old_records_unchanged':True,'new_start_cap':1,'generation_cap':6})
module=HERE/'audited_health.py';assert not module.exists()
module.write_text('''"""回环健康检查审计；不调用生成接口。"""
import json,time,urllib.request,urllib.error
from runtime import write,now,TechnicalStop

def probe(opener,url,timeout):
    row={'at':now(),'url':url,'method':'GET','timeout_seconds':timeout,'proxy_policy':'explicit ProxyHandler({})','http_status':None,'raw_body':None,'parsed_body':None,'healthy':False}
    start=time.perf_counter()
    try:
        request=urllib.request.Request(url,method='GET')
        with opener.open(request,timeout=timeout) as response:
            row['http_status']=response.status;row['raw_body']=response.read().decode('utf-8',errors='replace');row['headers']=dict(response.headers)
        row['parsed_body']=json.loads(row['raw_body'])
        row['healthy']=row['http_status']==200 and isinstance(row['parsed_body'],dict) and row['parsed_body'].get('status')=='ok'
    except Exception as e:
        row.update(exception_type=type(e).__name__,exception_repr=repr(e),exception_string=str(e),errno=getattr(e,'errno',None),winerror=getattr(e,'winerror',None))
        reason=getattr(e,'reason',None)
        if reason is not None:row['reason']={'type':type(reason).__name__,'repr':repr(reason),'errno':getattr(reason,'errno',None),'winerror':getattr(reason,'winerror',None)}
        if isinstance(e,urllib.error.HTTPError):row['http_status']=e.code;row['raw_body']=e.read().decode('utf-8',errors='replace')
    row['elapsed_seconds']=time.perf_counter()-start
    return row

def wait_health(engine,process,out,abort,start,limit=120):
    attempts=[];deadline=start+limit;last_print=-10
    while time.perf_counter()<deadline:
        code=process.poll()
        if abort.is_set() or code is not None:
            write(out/'health-checks.json',{'at':now(),'attempts':attempts,'process_exit_code':code,'memory_abort':abort.is_set(),'healthy':False});raise TechnicalStop('健康阶段进程退出或资源停止')
        row=probe(engine.opener,engine.url+'health',min(2,max(.1,deadline-time.perf_counter())))
        row['process_exit_code_after_probe']=process.poll();attempts.append(row)
        write(out/'health-checks.json',{'at':now(),'url':engine.url+'health','wait_limit_seconds':limit,'attempts':attempts,'healthy':row['healthy'],'pid':process.pid})
        elapsed=time.perf_counter()-start
        if elapsed-last_print>=5 or row['healthy']:
            print('HEALTH',round(elapsed,2),'seconds',row['http_status'],row.get('exception_type'),'healthy',row['healthy'],flush=True);last_print=elapsed
        if row['healthy']:
            if process.poll() is not None:raise TechnicalStop('健康返回后进程退出')
            return row
        time.sleep(min(.5,max(0,deadline-time.perf_counter())))
    raise TechnicalStop('健康超时，逐次HTTP及异常已保存')

def offline_checks():
    import io
    class Reply:
        def __init__(self,status,body):self.status=status;self.body=body;self.headers={}
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def read(self):return self.body
    class Fake:
        def __init__(self,reply):self.reply=reply
        def open(self,request,timeout):
            assert request.full_url=='http://127.0.0.1:8080/health' and timeout==2
            if isinstance(self.reply,Exception):raise self.reply
            return self.reply
    cases=[('ok',Reply(200,b'{"status":"ok"}'),True),('wrong_status',Reply(503,b'{"status":"ok"}'),False),('loading',Reply(200,b'{"status":"loading"}'),False),('wrong_shape',Reply(200,b'[]'),False),('bad_json',Reply(200,b'not json'),False),('timeout',TimeoutError('synthetic timeout'),False),('refused',urllib.error.URLError(ConnectionRefusedError(10061,'synthetic refusal')),False),('http503',urllib.error.HTTPError('http://127.0.0.1:8080/health',503,'loading',{},io.BytesIO(b'{"status":"loading"}')),False)]
    rows=[]
    for name,reply,expected in cases:
        row=probe(Fake(reply),'http://127.0.0.1:8080/health',2);assert row['healthy'] is expected
        if isinstance(reply,Exception):assert row['exception_type']
        rows.append({'name':name,'passed':True,'actual':row})
    return {'passed':True,'count':len(rows),'rows':rows,'only_synthetic_no_network':True}
''',encoding='utf-8')
from audited_health import offline_checks as health_checks
checks={'health':health_checks(),'compact':compact_checks(),'thinking':thinking_checks(),'sentence':sentence_checks(),'interface':interface_checks(),'existing':old_checks(out)};assert all(x['passed'] for x in checks.values())
for name in ['diagnostic-inputs.json','serialized-request-plan.json','byte-and-scope-audit.json','strict-formula-provenance.json','original-strict-formula-source.txt']:
    shutil.copy2(failed/name,out/name)
for name in ['offline-checks.json','mode-offline-checks.json']:write(out/name,{'at':now(),'passed':True,'checks':checks,'generation_calls':0,'old_plan_prechecks_preserved':str(failed/name),'actual_http_template_required':True})
oldsrc=(HERE/'diagnose_reason_citations.py').read_text(encoding='utf-8');src=oldsrc.replace('import argparse, ast, json, socket, subprocess, threading, time, uuid','import argparse, ast, json, socket, subprocess, threading, time, uuid, os, urllib.request\nfrom audited_health import wait_health')
src=src.replace("record={'at':now()", "assert engine.url=='http://127.0.0.1:8080/'\n    write(out/'launch-environment.json',{'at':now(),'cwd':str(out),'python':os.sys.executable,'proxy_env_presence':{k:bool(os.environ.get(k)) for k in ['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY','http_proxy','https_proxy','all_proxy','no_proxy']},'environment_proxy_bypassed':True,'actual_proxy_handlers':[getattr(h,'proxies',None) for h in engine.opener.handlers if isinstance(h,urllib.request.ProxyHandler)],'path_length':len(str(out)),'launch_attempt_cap':1})\n    record={'at':now()")
begin=src.index('        while time.perf_counter()-start<120:');end=src.index("        props=engine.service('props')",begin)
src=src[:begin]+"        wait_health(engine,process,out,abort,start,limit=120)\n"+src[end:]
src=src.replace("write(out/'owned-service.json',{'pid':process.pid,'started_at':now(),'arguments':launch})","write(out/'owned-service.json',{'pid':process.pid,'started_at':now(),'arguments':launch,'cwd':str(out),'creationflags':subprocess.CREATE_NO_WINDOW,'one_start_only':True})")
src=src.replace('        stop.set()','        record.update(process_exit_code_before_cleanup=process.poll() if process else None,cleanup_termination_requested=bool(process and process.poll() is None))\n        stop.set()')
src=src.replace("record.update(ended_at=now()", "record.update(process_exit_code_after_cleanup=process.poll() if process else None,ended_at=now()")
ast.parse(src);assert 'except Exception:pass' not in src
runner=HERE/'diagnose_reason_citations_resume.py';assert not runner.exists();runner.write_text(src,encoding='utf-8')
(out/'health-repair.diff').write_text(''.join(difflib.unified_diff(oldsrc.splitlines(True),src.splitlines(True),fromfile='diagnose_reason_citations.py',tofile='diagnose_reason_citations_resume.py')),encoding='utf-8')
plan={**a,'resumed_at':now(),'original_plan':(failed/'intervention-plan.json').relative_to(ROOT).as_posix(),'original_plan_sha256':sha(failed/'intervention-plan.json'),'original_stop_preserved':True,'single_new_start_authorized':True,'health_wait_seconds':120,'health_request_timeout_seconds':2,'code_hashes':{p.relative_to(ROOT).as_posix():sha(p) for p in HERE.glob('*.py')},'input_sha256':sha(out/'diagnostic-inputs.json'),'serialized_requests_sha256':sha(out/'serialized-request-plan.json')}
assert (out/'diagnostic-inputs.json').read_bytes()==(failed/'diagnostic-inputs.json').read_bytes() and (out/'serialized-request-plan.json').read_bytes()==(failed/'serialized-request-plan.json').read_bytes()
write(out/'intervention-plan.json',plan);snap=out/'new-code-snapshot';snap.mkdir()
for p in [module,runner]:shutil.copy2(p,snap/p.name)
shutil.copy2(__file__,out/Path(__file__).name)
write(out/'repair-preflight.json',{'at':now(),'passed':True,'all_checks':checks,'requests_identical_to_authorized_plan':True,'model_hash':a['model_hash'],'executable_hash':a['executable_hash'],'new_start_count':0,'new_generation_count':0,'old_generation_count':0,'new_runner_sha256':sha(runner),'old_runner_preserved_sha256':sha(HERE/'diagnose_reason_citations.py'),'health_url_asserted':True,'actual_diff_checked':True})
print(json.dumps({'out':str(out),'passed':True,'health_tests':8,'preserved_old_files':len(protected),'generations':0},ensure_ascii=False))
