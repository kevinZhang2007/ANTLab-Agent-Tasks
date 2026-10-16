"""只读回看A开发归档；不启动模型，禁止生成POST。"""
from pathlib import Path
from urllib.parse import urlparse
from types import SimpleNamespace
from http.server import HTTPServer
import argparse,json,time
import server
from runtime import load,write,now,HERE
from contracts import normalize_pair

class Replay(server.Handler):
    def do_GET(self):
        if urlparse(self.path).path=='/api/saved-pairs':
            rows=[load(p) for p in self.server.folder.glob('http-*.json') if not p.name.startswith('http-error')]
            for row in rows:row['normalized_arms']=normalize_pair(row['response']);row['view_run_kind']='offline_replay'
            return self.reply(200,sorted(rows,key=lambda r:r['task_id']))
        if self.path=='/':
            source=(HERE/'index.html').read_text(encoding='utf-8').replace('__TOKEN__',server.TOKEN)
            script="""<script>el('run').disabled=true;el('run').onclick=null;const pick=document.createElement('select');pick.id='archived-pair';document.querySelector('h1').after(pick);async function saved(){const records=await(await fetch('/api/saved-pairs')).json();for(const r of records){const o=document.createElement('option');o.value=r.request_id;o.textContent=r.task_id+' 已归档请求 '+r.request_id;pick.append(o)}function showSaved(){const r=records.find(x=>x.request_id===pick.value);pair=r.response;el('state').textContent='只读归档回放，0新增生成 / '+pair.request_id;el('task').value=r.task_id;show()}pick.onchange=showSaved;showSaved()}saved();</script>"""
            raw=(source+script).encode();self.send_response(200);self.send_header('Content-Type','text/html;charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
        return super().do_GET()
    def do_POST(self):
        if self.path=='/api/stop':
            write(self.server.folder/'replay-stop.json',{'at':now(),'generation_calls':0});return self.reply(200,{'stopping':True})
        return self.reply(403,{'error':'只读回放禁止模型生成','generation_calls':0})

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--port',type=int,default=8890);a=p.parse_args()
    folder=a.out.resolve();s=HTTPServer(('127.0.0.1',a.port),Replay);s.folder=folder;s.development=load(folder/'development-inputs.json');s.engine=SimpleNamespace(technical_stop=False);s.timeout=.5
    write(folder/'replay-ready.json',{'at':now(),'port':a.port,'run_kind':'offline_replay','generation_calls':0});print('READ_ONLY_READY',flush=True);start=time.perf_counter()
    try:
        while time.perf_counter()-start<900 and not (folder/'replay-stop.json').exists():s.handle_request()
    finally:s.server_close();write(folder/'replay-stopped.json',{'at':now(),'generation_calls':0});print('REPLAY_STOPPED',flush=True)

if __name__=='__main__':main()
