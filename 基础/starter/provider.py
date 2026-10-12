import os, json, time, urllib.request, urllib.error
from urllib.parse import urlparse

def call_model(messages, config, mock=False):
    if mock:
        return {'status':'mock','elapsed_seconds':0.0,
                'response':{'choices':[{'message':{'content':'{"answer":"MOCK_NOT_EVIDENCE","citations":[]}'}}]},
                'usage':None,'http_status':None}
    endpoint=config['endpoint']
    local=config.get('provider')=='llama.cpp'
    headers={'Content-Type':'application/json'}
    if local:
        url=urlparse(endpoint)
        if url.scheme!='http' or url.hostname not in ('127.0.0.1','localhost','::1') or url.username or url.password:
            raise ValueError('llama.cpp只允许本机回环HTTP地址，不发送API密钥')
    else:
        if urlparse(endpoint).scheme != 'https':
            raise ValueError('自费API endpoint必须为https')
        key=os.environ.get('ASSESSMENT_API_KEY','')
        if not key: raise ValueError('缺少环境变量ASSESSMENT_API_KEY；不要写入配置文件')
        headers['Authorization']='Bearer '+key
    params=config.get('parameters',{})
    if not isinstance(params,dict) or set(params)&{'messages','model','stream'}:
        raise ValueError('parameters不可覆盖messages/model/stream')
    body={'model':config['model'],'messages':messages,'stream':False,**params}
    req=urllib.request.Request(endpoint, data=json.dumps(body,ensure_ascii=False).encode(),
                               headers=headers)
    # 本地请求绕过代理，禁止重定向到其他服务。
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect()) if local else urllib.request.build_opener()
    start=time.perf_counter()
    try:
        with opener.open(req, timeout=float(config.get('timeout_seconds',90))) as response:
            raw=response.read().decode('utf-8'); status=response.status
        try: parsed=json.loads(raw)
        except json.JSONDecodeError:
            return {'status':'invalid_provider_json','elapsed_seconds':time.perf_counter()-start,
                    'response':raw,'usage':None,'http_status':status}
        return {'status':'ok','elapsed_seconds':time.perf_counter()-start,'response':parsed,'raw_response':raw,
                'usage':parsed.get('usage') if isinstance(parsed,dict) else None,'http_status':status}
    except urllib.error.HTTPError as e:
        # 不保存错误页正文，避免意外收录请求凭据；成功模型响应原样保存。
        return {'status':'http_error','elapsed_seconds':time.perf_counter()-start,
                'http_status':e.code,'error':'HTTP '+str(e.code),'response':None,'usage':None}
    except (urllib.error.URLError,TimeoutError) as e:
        return {'status':'transport_error','elapsed_seconds':time.perf_counter()-start,
                'http_status':None,'error':type(e).__name__,'response':None,'usage':None}
