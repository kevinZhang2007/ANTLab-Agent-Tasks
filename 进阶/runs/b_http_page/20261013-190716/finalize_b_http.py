from pathlib import Path
import json, hashlib, shutil, ast, socket, subprocess
from datetime import datetime
work=Path(__file__).parent
folder=Path((work/'b_http_folder.txt').read_text(encoding='utf-8'))
repo=folder.parents[3]
source=work.parent/'outputs/b-http-page'
dest=folder/'page'
dest.mkdir(exist_ok=False)
for p in source.iterdir():
    shutil.copyfile(p,dest/p.name)
def save(name,value):
    p=folder/name
    if p.exists():raise RuntimeError(str(p))
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
logs={}
for variant in ['original','fixed']:
    lines=(folder/(variant+'-service')/'events.jsonl').read_text(encoding='utf-8').splitlines()
    logs[variant]=[(i+1,json.loads(line)) for i,line in enumerate(lines)]
page_records=[json.loads(p.read_text(encoding='utf-8')) for p in sorted(dest.glob('page-*.json')) if p.name!='page-index.json']
http_records=[json.loads(p.read_text(encoding='utf-8')) for p in sorted(folder.glob('http-*.json'))]
closure=[]
for record in page_records:
    variant=record['variant']; seq=record['sequence']; request_id=record['request_id']
    hits=[(line,event) for line,event in logs[variant] if event.get('request_id')==request_id]
    assert len(hits)==1
    line,event=hits[0]
    assert event['response']==record['response'] and event['http_body']==record['submitted']
    assert record['summary']['request_id']==request_id
    assert (dest/record['screenshot']).stat().st_size>0
    corresponding=next(r for r in http_records if r['variant']==variant and r['sequence']==seq)
    assert record['submitted']==corresponding['http_request']
    # IDs与耗时随每次请求变化；其余结构和实际处理结果必须一致。
    def stable(x):
        if isinstance(x,dict):return {k:stable(v) for k,v in x.items() if k not in ['request_id','elapsed_ms']}
        if isinstance(x,list):return [stable(v) for v in x]
        return x
    assert stable(record['response'])==stable(corresponding['response'])
    r=record['response']
    closure.append({'variant':variant,'sequence':seq,'request_id':request_id,
                    'http_page_record':f'page/page-{variant}-{seq}.json','screenshot':f'page/{record["screenshot"]}',
                    'backend_log':f'{variant}-service/events.jsonl','backend_line':line,
                    'same_request_response_and_id':True,'equivalent_to_http_sequence':True,
                    'engine':r['service']['engine'],'answer':r['answer'],
                    'locator_status':r['locator_status'],'support_status':r['support_status'],
                    'scope_status':r['scope_status'],'actual_evidence':r['evidence']})
save('04-page-log-closure.json',closure)
protected=json.loads((folder/'00-protected-hashes.json').read_text(encoding='utf-8'))
changed=[p for p,h in protected.items() if hashlib.sha256((repo/p).read_bytes()).hexdigest()!=h]
assert not changed
ids=[r['response']['request_id'] for r in http_records]+[r['request_id'] for r in page_records]
assert len(ids)==28 and len(set(ids))==28
for r in http_records:
    hits=[event for line,event in logs[r['variant']] if event.get('request_id')==r['response']['request_id']]
    assert len(hits)==1 and hits[0]['response']==r['response'] and hits[0]['http_body']==r['http_request']
ports={}
for port in [8876,8877]:
    with socket.socket() as s:
        s.settimeout(1); ports[str(port)]=s.connect_ex(('127.0.0.1',port))!=0
assert all(ports.values())
for name in ['server_review.py']:
    ast.parse((repo/'进阶/challenge_b'/name).read_text(encoding='utf-8'))
git=r'C:\Users\86186\AppData\Local\Programs\Git\cmd\git.exe'
def command(*args):
    p=subprocess.run([git,*args],cwd=repo,capture_output=True,text=True,encoding='utf-8')
    return {'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
checks={'checked_at':datetime.now().astimezone().isoformat(),'protected_files':len(protected),'changed_protected_files':changed,
        'http_runs':len(http_records),'page_runs':len(page_records),'backend_request_logs':sum(e['type']=='request' for entries in logs.values() for l,e in entries),
        'unique_request_ids':len(set(ids)),'all_page_request_ids_matched_to_logs':True,
        'all_original_fixed_http_bodies_equal':all(next(r for r in http_records if r['variant']=='original' and r['sequence']==i)['http_request']==next(r for r in http_records if r['variant']=='fixed' and r['sequence']==i)['http_request'] for i in range(1,8)),
        'all_page_runs_equivalent_to_http_runs':True,'service_ports_stopped':ports,'syntax_check':'AST parse passed, no cache generated',
        'code_hashes':{n:hashlib.sha256((repo/'进阶/challenge_b'/n).read_bytes()).hexdigest() for n in ['server_review.py','review.html','challenge.py','no_cache_engine.py']},
        'new_model_calls':0,'cumulative_model_generations':124,
        'status':command('-c','core.quotepath=false','status','--short','--branch'),
        'tracked_diff':command('diff','--stat'),'staged_diff':command('diff','--cached','--stat')}
assert not checks['tracked_diff']['stdout'] and not checks['staged_diff']['stdout']
save('05-final-checks.json',checks)
save('06-findings.json',{'recorded_at':datetime.now().astimezone().isoformat(),
     'observed':['原版暖v2仍返回v1/b01，原Engine valid/supported保留，展示层invalid/not_checked。','修复版暖v2返回v2/b02，定位valid，语义not_checked。','修复版beta返回当前5秒draft，evidence=[]、locator invalid；不是成功查证。','原/修复冷R05和重复R05内容一致；修复版始终无缓存命中。','未知文档和未知快照冷请求均证据为空，不回退范围；展示invalid_scope。'],
     'unresolved':['top-k先截取后范围过滤，beta仍漏证。','Engine ID有效即supported，语义判断未修；对外另列not_checked/unverified。','未知范围Engine仍返回status=ok和固定draft；展示标注不等于修复Engine。','本轮未知范围测试是清空状态后的边界，不证明原Engine暖缓存边界安全。','页面请求等待期间上一响应仍可见，响应区request_id及request用于区别；未做异步交互压力测试。','没有验证多用户、并发、生产安全；不存在真实模型服务请求。'],
     'automation_issue':'选择label精确匹配失败发生在提交前，未新增HTTP调用；使用已观察的combobox角色完成。',
     'stopping':'完成后用Ctrl+C停止两个本轮服务，端口均不再监听；进程退出1是中断，不是请求失败。'})
for name in ['prepare_b_http.py','check_b_http.py','finalize_b_http.py']:
    shutil.copyfile(work/name,folder/name)
files=[repo/'进阶/challenge_b/server_review.py',repo/'进阶/challenge_b/review.html',*sorted(p for p in folder.rglob('*') if p.is_file()),folder/'07-file-list.json']
save('07-file-list.json',{'count':len(files),'files':[p.relative_to(repo).as_posix() for p in files],'all_new':True})
for name in ['code-full.diff','04-page-log-closure.json','05-final-checks.json','06-findings.json','07-file-list.json']:
    shutil.copyfile(folder/name,source/name)
print(json.dumps({'folder':str(folder),'new_files':len(files),'checks':checks},ensure_ascii=False,indent=2))
