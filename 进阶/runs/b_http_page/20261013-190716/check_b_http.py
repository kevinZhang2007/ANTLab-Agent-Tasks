from pathlib import Path
import json, urllib.request
from datetime import datetime
folder=Path((Path(__file__).parent/'b_http_folder.txt').read_text(encoding='utf-8'))
repo=folder.parents[3]
data=json.loads((repo/'进阶/challenge_b/data.json').read_text(encoding='utf-8'))
plan=json.loads((folder/'01-plan.json').read_text(encoding='utf-8'))
results=[]
for variant,service in plan['services'].items():
    for i,item in enumerate(plan['http_sequence'],1):
        case=next(c for c in data['cases'] if c['id']==item['case_id'])
        body={'case_id':case['id'],'reset':item['reset'],'request':dict(case['request'],mode='offline_replay',**item['override'])}
        url=f"http://127.0.0.1:{service['port']}/api/run"
        r=urllib.request.urlopen(urllib.request.Request(url,data=json.dumps(body,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'}),timeout=10)
        raw=r.read().decode('utf-8'); response=json.loads(raw)
        record={'checked_at':datetime.now().astimezone().isoformat(),'variant':variant,'sequence':i,'url':url,'http_request':body,'http_status':r.status,'raw_response_body':raw,'response':response,'model_calls':0}
        (folder/f'http-{variant}-{i:02}.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        results.append({'variant':variant,'sequence':i,'case_id':case['id'],'request_id':response['request_id'],'answer':response['answer'],'evidence_ids':[b['block_id'] for b in response['evidence']],'scope_status':response['scope_status'],'locator_status':response['locator_status'],'support_status':response['support_status'],'raw_locator_status':response['engine_response']['locator_status'],'raw_support_status':response['engine_response']['support_status'],'cache_hit':response['engine_response']['cache_hit']})
(folder/'03-http-summary.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(results,ensure_ascii=False,indent=2))
