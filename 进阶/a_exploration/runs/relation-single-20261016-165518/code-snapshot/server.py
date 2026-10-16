from http.server import HTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse,parse_qs
from pathlib import Path
import json,secrets,time
from runtime import HERE,ROOT,write,now
from reader import reader_html
from contracts import normalize_pair

TOKEN=secrets.token_urlsafe(24)
class Handler(BaseHTTPRequestHandler):
    def reply(self,code,obj):
        raw=json.dumps(obj,ensure_ascii=False).encode();self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
    def file(self,path,mime):
        data=path.read_bytes();self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def do_GET(self):
        url=urlparse(self.path)
        if url.path=='/':
            text=(HERE/'index.html').read_text(encoding='utf-8').replace('__TOKEN__',TOKEN).encode();self.send_response(200);self.send_header('Content-Type','text/html;charset=utf-8');self.send_header('Content-Length',str(len(text)));self.end_headers();self.wfile.write(text);return
        if url.path=='/reader':
            try:
                raw=reader_html(ROOT,parse_qs(url.query));self.send_response(200);self.send_header('Content-Type','text/html;charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
            except (ValueError,KeyError):return self.reply(400,{'error':'未知文档或物理页'})
        if url.path=='/api/development':return self.reply(200,self.server.development)
        if url.path=='/api/locator-examples':return self.reply(200,json.loads((self.server.folder/'locator-anchors.json').read_text(encoding='utf-8')))
        if url.path.startswith('/pdf/'):
            doc=url.path.split('/')[-1]
            if doc not in ('P1','P2'):return self.reply(404,{'error':'unknown document'})
            return self.file(ROOT/'进阶/materials/papers'/f'{doc}.pdf','application/pdf')
        if url.path.startswith('/assets/'):
            filename=url.path.split('/')[-1]
            if filename not in {f'{doc}-{page}.png' for doc,count in [('P1',4),('P2',8)] for page in range(1,count+1)}:return self.reply(404,{'error':'unknown asset'})
            return self.file(HERE/'assets'/filename,'image/png')
        return self.reply(404,{'error':'not found'})
    def do_POST(self):
        if self.headers.get('X-A-Session')!=TOKEN:return self.reply(403,{'error':'会话不匹配'})
        try:
            length=int(self.headers.get('Content-Length',0))
            if not 0<length<10000:raise ValueError('请求长度不合法')
            raw=self.rfile.read(length);body=json.loads(raw)
            if self.path=='/api/stop':write(self.server.folder/'stop-requested.json',{'at':now()});return self.reply(200,{'stopping':True})
            if self.path!='/api/run-pair':return self.reply(404,{'error':'not found'})
            task=next((x for x in self.server.development if x['id']==body.get('task_id')),None)
            if not task or any(body.get(k)!=task[k] for k in ('claim','doc_ids','snapshot')):raise ValueError('本轮仅允许三条已授权开发输入')
            i=self.server.development.index(task);order=['baseline','improved'] if i%2==0 else ['improved','baseline']
            result=self.server.engine.execute_pair(body['claim'],body['doc_ids'],body['snapshot'],order)
            result['normalized_arms']=normalize_pair(result)
            request_id=result['request_id']
            write(self.server.folder/('http-'+request_id+'.json'),{'request_id':request_id,'task_id':task['id'],'method':'POST','path':self.path,'raw_request':raw.decode(),'request':body,'response':result,'run_kind':'live_api','token_header':'省略会话令牌'})
            self.server.engine.event('http_response',request_id=request_id,task_id=task['id'],record='http-'+request_id+'.json')
            return self.reply(200,result)
        except Exception as e:
            write(self.server.folder/('http-error-'+str(time.time_ns())+'.json'),{'at':now(),'path':self.path,'request_raw':locals().get('raw',b'').decode(errors='replace'),'error':repr(e),'generation_dispatches':self.server.engine.dispatches})
            return self.reply(500 if self.server.engine.technical_stop else 400,{'error':str(e),'technical_stop':self.server.engine.technical_stop,'retry_allowed':False})
    def log_message(self,*args):pass
