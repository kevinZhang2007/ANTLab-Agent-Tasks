"""本机固定draft重放；保留Engine响应，单列展示层状态。"""
import argparse
import copy
import hashlib
import importlib
import json
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
VERSION = 'b-http-review-v1'

def now():
    return datetime.now().astimezone().isoformat()

def save_event(event):
    event['logged_at'] = now()
    with (LOG_DIR / 'events.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps(event, ensure_ascii=False) + '\n')

def public_result(raw, request):
    evidence = [dict(b, block_id=b['id']) for b in raw['evidence']]
    scope_known = bool(request['doc_ids']) and all(
        any(b['doc_id'] == doc and b['snapshot'] == request['snapshot'] for b in DATA['corpus'])
        for doc in request['doc_ids'])
    ids = {b['id'] for b in evidence}
    in_scope = all(b['doc_id'] in request['doc_ids'] and b['snapshot'] == request['snapshot'] for b in evidence)
    cited = raw['citations']
    locator = 'absent' if not cited else ('valid' if set(cited) <= ids and in_scope else 'invalid')
    return {
        'request_id': raw['request_id'], 'request': copy.deepcopy(request),
        'answer': raw['answer'], 'citations': cited, 'evidence': evidence,
        'actual_scopes': sorted({(b['doc_id'], b['snapshot']) for b in evidence}),
        'locator_status': locator, 'support_status': 'not_checked',
        'judgment_source': 'unverified', 'elapsed_ms': raw['elapsed_ms'],
        'run_kind': 'offline_replay', 'scope_status': 'known' if scope_known else 'invalid_scope',
        'evidence_in_scope': in_scope,
        'citation_status': 'absent' if not cited else ('present' if set(cited) <= ids else 'missing_or_outside_evidence'),
        'engine_response': raw, 'service': SERVICE,
        'state_mapping': {
            'locator_status': '展示层检查引用ID、实际证据及请求范围；不替换Engine原值。',
            'support_status': 'not_checked：Engine只按ID产生状态，未做语义检查。',
            'judgment_source': 'unverified：没有语义判分器。',
            'scope_status': '只核对输入范围存在性，不修复Engine检索或改变其响应。'
        }
    }

class Handler(BaseHTTPRequestHandler):
    def reply(self, status, value, mime='application/json; charset=utf-8'):
        raw = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == '/':
            self.reply(200, (ROOT / 'review.html').read_bytes(), 'text/html; charset=utf-8')
        elif self.path == '/api/cases':
            self.reply(200, dict(DATA, service=SERVICE))
        else:
            self.reply(404, {'error': 'not_found'})

    def do_POST(self):
        if self.path != '/api/run':
            return self.reply(404, {'error': 'not_found'})
        body = None
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 32768:
                raise ValueError('invalid_size')
            body = json.loads(self.rfile.read(length))
            case = next(c for c in DATA['cases'] if c['id'] == body['case_id'])
            request = copy.deepcopy(body['request'])
            if not isinstance(request['query'], str) or not isinstance(request['snapshot'], str):
                raise ValueError('invalid_request')
            if not isinstance(request['doc_ids'], list) or not all(isinstance(d, str) for d in request['doc_ids']):
                raise ValueError('invalid_doc_ids')
            if type(request['k']) is not int or not 1 <= request['k'] <= 100:
                raise ValueError('invalid_k')
            if request['mode'] != 'offline_replay':
                raise ValueError('only_offline_replay')
            if body.get('reset'):
                ENGINE.cache.clear()
            cache_before = copy.deepcopy(ENGINE.cache)
            raw = ENGINE.evaluate(request, DATA['corpus'], case['draft'])
            response = public_result(raw, request)
            save_event({'type': 'request', 'request_id': raw['request_id'], 'http_body': body,
                        'engine_request': request, 'corpus': DATA['corpus'], 'draft': case['draft'],
                        'draft_source': 'challenge_b/data.json:' + case['id'],
                        'cache_before': cache_before, 'cache_after': copy.deepcopy(ENGINE.cache),
                        'response': response, 'http_status': 200, 'service': SERVICE})
            self.reply(200, response)
        except (ValueError, KeyError, StopIteration, TypeError) as error:
            response = {'request_id': str(uuid.uuid4()), 'error': str(error) or 'invalid_case',
                        'run_kind': 'offline_replay', 'service': SERVICE}
            save_event({'type': 'error', 'http_body': body, 'response': response, 'http_status': 400})
            self.reply(400, response)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--engine', choices=['challenge:Engine', 'no_cache_engine:Engine'], default='challenge:Engine')
    parser.add_argument('--log-dir', required=True)
    args = parser.parse_args()
    LOG_DIR = Path(args.log_dir)
    LOG_DIR.mkdir(parents=True, exist_ok=False)
    DATA = json.loads((ROOT / 'data.json').read_text(encoding='utf-8'))
    module, name = args.engine.split(':')
    ENGINE = getattr(importlib.import_module(module), name)()
    SERVICE = {'version': VERSION, 'engine': args.engine, 'default_engine': 'challenge:Engine',
               'host': '127.0.0.1', 'port': args.port, 'run_kind': 'offline_replay',
               'engine_sha256': hashlib.sha256((ROOT / (module + '.py')).read_bytes()).hexdigest()}
    save_event({'type': 'startup', 'service': SERVICE, 'argv': vars(args)})
    print(json.dumps(SERVICE, ensure_ascii=False), flush=True)
    server = HTTPServer(('127.0.0.1', args.port), Handler)
    try:
        server.serve_forever()
    finally:
        save_event({'type': 'shutdown', 'service': SERVICE})
        server.server_close()
