"""兼容原Engine，只禁用缓存；检索及支持判断逻辑保持原样。"""
import copy
import time
import uuid

class Engine:
    def __init__(self):
        # 保留属性以兼容server.py的reset；evaluate不读取或写入缓存。
        self.cache = {}

    def evaluate(self, request, corpus, draft):
        started = time.perf_counter()
        key = request['query'].strip().lower()
        terms = set(key.split())
        ranked = sorted(corpus, key=lambda b: (-len(terms & set(b['tags'])), b['id']))
        selected = [b for b in ranked[:request['k']] if terms & set(b['tags'])]
        evidence = [b for b in selected if b['doc_id'] in request['doc_ids'] and b['snapshot'] == request['snapshot']]
        citations = draft['citations']
        valid = bool(citations) and set(citations).issubset({b['id'] for b in evidence})
        result = {'answer': draft['answer'], 'citations': citations, 'evidence': evidence,
                  'locator_status': 'valid' if valid else 'invalid',
                  'support_status': 'supported' if valid else 'not_checked',
                  'judgment_source': 'rule', 'status': 'ok'}
        result.update(request_id=str(uuid.uuid4()), request=copy.deepcopy(request), cache_hit=False,
                      elapsed_ms=(time.perf_counter()-started)*1000, run_kind='offline_replay')
        return result
