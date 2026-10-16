"""仅切换页面，复用原HTTP鉴权、开发白名单、日志和PDF路由。"""
from server import Handler as OriginalHandler,TOKEN
from runtime import HERE
class Handler(OriginalHandler):
    def do_GET(self):
        if self.path=='/':
            raw=(HERE/'current_page.html').read_text(encoding='utf-8').replace('__TOKEN__',TOKEN).encode();self.send_response(200);self.send_header('Content-Type','text/html;charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw);return
        return super().do_GET()
