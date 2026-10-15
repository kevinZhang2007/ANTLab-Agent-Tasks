from pathlib import Path
import json,urllib.request
from datetime import datetime
work=Path(__file__).parent
folder=Path((work/'b_warm_folder.txt').read_text(encoding='utf-8'))
repo=folder.parents[3]
plan=json.loads((folder/'01-plan.json').read_text(encoding='utf-8'))
data=json.loads((repo/'进阶/challenge_b/data.json').read_text(encoding='utf-8'))
case=next(c for c in data['cases'] if c['id']=='R01')
summary=[]
for variant,service in plan['services'].items():
    for i,item in enumerate(plan['sequence'],1):
        body={'case_id':'R01','reset':item['reset'],'request':dict(case['request'],mode='offline_replay',**item['override'])}
        url=f"http://127.0.0.1:{service['port']}/api/run"
        wire=json.dumps(body,ensure_ascii=False)
        record={'attempted_at':datetime.now().astimezone().isoformat(),'variant':variant,'sequence':i,'role':item['role'],'url':url,'http_request':body,'raw_request_body':wire}
        try:
            with urllib.request.urlopen(urllib.request.Request(url,data=wire.encode(),headers={'Content-Type':'application/json'}),timeout=10) as response:
                raw=response.read().decode('utf-8');r=json.loads(raw)
                record.update(http_status=response.status,raw_response_body=raw,response=r,engine_response=r['engine_response'])
        except Exception as e:
            record['technical_error']=repr(e)
            (folder/f'http-{variant}-{i}.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            raise
        (folder/f'http-{variant}-{i}.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        summary.append({'variant':variant,'sequence':i,'role':item['role'],'request_id':r['request_id'],'evidence_ids':[b['id'] for b in r['evidence']],'scope_status':r['scope_status'],'locator_status':r['locator_status'],'support_status':r['support_status'],'cache_hit':r['engine_response']['cache_hit'],'engine_status':r['engine_response']['status'],'answer':r['answer']})
(folder/'02-http-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
