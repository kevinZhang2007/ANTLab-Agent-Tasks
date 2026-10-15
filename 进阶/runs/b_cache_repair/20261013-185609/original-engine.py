"""Intentionally flawed teaching implementation; follow spec.md, not this code as truth."""
import copy
import time
import uuid

class Engine:
    def __init__(self):
        self.cache = {}

    def evaluate(self, request, corpus, draft):
        started = time.perf_counter()
        key = request['query'].strip().lower()
        hit = key in self.cache
        if hit:
            result = copy.deepcopy(self.cache[key])
        else:
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
            self.cache[key] = copy.deepcopy(result)
        result.update(request_id=str(uuid.uuid4()), request=copy.deepcopy(request), cache_hit=hit,
                      elapsed_ms=(time.perf_counter()-started)*1000, run_kind='offline_replay')
        return result
