"""回环健康检查审计；不调用生成接口。"""
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
