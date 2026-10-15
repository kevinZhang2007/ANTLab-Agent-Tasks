from pathlib import Path
import json, hashlib, shutil, socket, subprocess, re
from datetime import datetime
work=Path(__file__).parent
folder=Path((work/'b_warm_folder.txt').read_text(encoding='utf-8'))
repo=folder.parents[3]
out=work.parent/'outputs/b-warm-boundary'
page=folder/'page'; page.mkdir(exist_ok=False)
for p in out.iterdir():shutil.copyfile(p,page/p.name)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(name,value):
    path=folder/name
    if path.exists():raise RuntimeError(str(path))
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
plan=read(folder/'01-plan.json')
http=[read(p) for p in sorted(folder.glob('http-*.json'))]
pages=[read(p) for p in sorted(page.glob('page-*.json')) if p.name!='page-index.json']
events={variant:[(i+1,json.loads(line)) for i,line in enumerate((folder/(variant+'-service')/'events.jsonl').read_text(encoding='utf-8').splitlines())] for variant in ['original','fixed']}
def stable(value):
    if isinstance(value,dict):return {k:stable(v) for k,v in value.items() if k not in ['request_id','elapsed_ms']}
    if isinstance(value,list):return [stable(v) for v in value]
    return value
closure=[]
for record in pages:
    variant=record['variant'];i=record['sequence'];r=record['response']
    hits=[(line,e) for line,e in events[variant] if e.get('request_id')==record['request_id']]
    assert len(hits)==1
    line,event=hits[0]
    h=next(h for h in http if h['variant']==variant and h['sequence']==i)
    assert record['summary']['request_id']==event['request_id']
    assert record['submitted']==event['http_body']==h['http_request']
    assert event['response']==r and stable(r)==stable(h['response'])
    assert (page/record['screenshot']).stat().st_size>0
    if i in [2,4]:
        assert r['scope_status']=='invalid_scope' and r['locator_status']=='invalid' and r['support_status']=='not_checked'
        if variant=='original':assert '范围冲突：不是当前请求资料' in record['dom_snapshot']
        else:assert '实际证据为空，不能视为成功查证。' in record['dom_snapshot']
    closure.append({'variant':variant,'sequence':i,'role':plan['sequence'][i-1]['role'],'request_id':r['request_id'],
                    'page_record':f'page/page-{variant}-{i}.json','screenshot':f'page/{record["screenshot"]}',
                    'backend_log':f'{variant}-service/events.jsonl','backend_line':line,
                    'http_page_log_equal':True,'response':r,'evaluation':{
                        'unknown_scope_display_correct':r['scope_status']=='invalid_scope' if i in [2,4] else None,
                        'semantic_not_verified':r['support_status']=='not_checked',
                        'cache_pollution_eliminated':not r['evidence'] and r['engine_response']['cache_hit'] is False if i in [2,4] and variant=='fixed' else None,
                        'engine_unknown_scope_contract_met':False if i in [2,4] else None}})
save('03-page-log-closure.json',closure)
old=repo/'进阶/runs/b_scope_diagnosis/20261013-184411'
repair=repo/'进阶/runs/b_cache_repair/20261013-185609'
web=repo/'进阶/runs/b_http_page/20261013-190716'
rel=lambda p:p.relative_to(repo).as_posix()
coverage=[
 {'requirement':'主故障复现','state':'已保存','paths':[rel(old/'04-observation-02.json'),rel(old/'04-observation-06.json'),rel(old/'06-findings.json')]},
 {'requirement':'两个竞争机制与区分性干预','state':'已保存机制比较；窄症状解释有边界','paths':[rel(old/'03-design-plan.json'),rel(old/'04-observation-03.json'),rel(old/'04-observation-04.json'),rel(old/'04-observation-07.json'),rel(old/'04-observation-08.json')],'limit':'缓存解释旧来源复用；top-k前置解释冷请求漏证。源码已排除top-k单独产生旧范围证据，不能将两者写成同一窄症状的同等竞争解释。'},
 {'requirement':'最小修复及差异/哈希','state':'已保存','paths':['进阶/challenge_b/no_cache_engine.py',rel(repair/'01-implementation.json'),rel(repair/'engine-logic.diff')]},
 {'requirement':'两个正常回归','state':'冷请求、同范围重复已保存','paths':[rel(repair/'04-normal_cold.json'),rel(repair/'04-normal_repeat.json')]},
 {'requirement':'两个等价变体','state':'顺序打乱、ID一致重映射已保存','paths':[rel(repair/'04-equivalent_corpus_order.json'),rel(repair/'04-equivalent_block_ids.json')],'limit':'ID重映射保留字典序，未证明任意ID改名在并列排序时无差异。'},
 {'requirement':'边界','state':'draft、正文变化及冷/暖未知范围已保存；未知范围Engine契约仍不合格','paths':[rel(repair/'04-boundary_draft_changed.json'),rel(repair/'04-boundary_corpus_changed.json'),rel(web/'04-page-log-closure.json'),rel(folder/'03-page-log-closure.json')]},
 {'requirement':'HTTP、页面与同request_id日志','state':'已实际操作并关联','paths':[rel(web/'04-page-log-closure.json'),rel(folder/'03-page-log-closure.json')]},
 {'requirement':'两个其他风险','state':'已列检索漏证与语义误标风险','paths':[rel(old/'01-source-review.json'),rel(web/'06-findings.json')]},
 {'requirement':'阅读范围依据','state':'复用已归档范围，不新增阅读','paths':['基础/runs/reading/p1-reading-evidence.json','基础/runs/reading/p2-reading-evidence.json','基础/runs/reading/technical-evidence-index.json']},
 {'requirement':'三项关键决策的本人判断及AI影响、整合报告/README入口映射','state':'本轮未写入，不登记已完成','paths':[],'limit':'已有技术计划不替代本人决策声明；三个说明文档按授权保持原样。'},
 {'requirement':'迁移到多用户/多worker的可执行验证计划与停止条件','state':'未完成','paths':[],'limit':'当前单进程样机结果不能证明并发或隔离安全。'}]
for item in coverage:
    for p in item['paths']:assert (repo/p).exists(),p
save('04-requirement-coverage.json',coverage)
all_ids=[]
for p in old.glob('04-observation-*.json'):
    data=read(p);all_ids.append(data['response']['request_id'])
for p in repair.glob('03-run-*.json'):all_ids.append(read(p)['response']['request_id'])
http_direct=[];page_ids=[]
for f in [web,folder]:
    for p in f.glob('http-*.json'):http_direct.append(read(p)['response']['request_id'])
    for p in (f/'page').glob('page-*.json'):
        if p.name!='page-index.json':page_ids.append(read(p)['request_id'])
assert len(all_ids)==44 and len(http_direct)==22 and len(page_ids)==22
assert len(set(all_ids+http_direct+page_ids))==88
facts={'recorded_at':datetime.now().astimezone().isoformat(),
       'directories':[rel(p) for p in [old,repair,web,folder]],
       'counts':{'initial_direct_engine':10,'repair_direct_engine':34,'direct_engine_total':44,'first_direct_http':14,'warm_boundary_direct_http':8,'direct_http_total':22,'first_page_submissions':14,'warm_boundary_page_submissions':8,'page_submissions_total':22,'all_http_post_including_page':44,'all_engine_evaluations_including_http_and_page':88,'unique_request_ids':88,'new_model_generations':0,'foundation_model_generations':124},
       'counting_note':'直接Engine44、直接HTTP22、页面22为互斥计数。页面22也在HTTP POST44和后端Engine88内，日志不是额外调用。',
       'new_code_files':['进阶/challenge_b/no_cache_engine.py','进阶/challenge_b/server_review.py','进阶/challenge_b/review.html'],
       'actual_startup':[{ 'variant':v,'working_directory':'进阶/challenge_b','python_executable':r'C:\Users\86186\AppData\Local\Programs\Python\Python314\python.exe','flags':['-X','utf8','-B'],'script':'server_review.py','argv':next(e['argv'] for l,e in events[v] if e['type']=='startup'),'log_path':rel(folder/(v+'-service')/'events.jsonl')} for v in ['original','fixed']],
       'page_opened':['http://127.0.0.1:8876/','http://127.0.0.1:8877/'],
       'reset_verified':{'http_body_field':'reset=true','effect':'Engine.cache.clear()','page_action':'勾选运行前清空状态再点击提交请求；每组预热独立重置。','warm_action':'取消勾选，不清空状态后提交未知范围。'},
       'remaining':['top-k先截取后过滤，beta仍漏证。','Engine仅ID有效即supported，展示not_checked不是新增语义判分。','未知范围Engine仍返回固定draft/status=ok，外层invalid_scope只是如实标注。','重复请求缓存被移除，可能增加开销，没有性能保持证明。','单进程全局Engine无用户隔离；未验证并发、多worker一致性、生产安全。','页面请求等待期间上一响应可见；未做异步压力检查。']}
save('05-delivery-facts.json',facts)
protected=read(folder/'00-protected-hashes.json')
changed=[p for p,h in protected.items() if hashlib.sha256((repo/p).read_bytes()).hexdigest()!=h]
assert not changed
ports={}
for port in [8876,8877]:
    with socket.socket() as s:s.settimeout(1);ports[str(port)]=s.connect_ex(('127.0.0.1',port))!=0
assert all(ports.values())
git=r'C:\Users\86186\AppData\Local\Programs\Git\cmd\git.exe'
def command(*args):
    p=subprocess.run([git,*args],cwd=repo,capture_output=True,text=True,encoding='utf-8')
    return {'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
tracked=command('diff','--name-only');staged=command('diff','--cached','--name-only')
assert not tracked['stdout'] and not staged['stdout']
save('06-preservation-checks.json',{'checked_at':datetime.now().astimezone().isoformat(),'protected_file_count':len(protected),'changed_files':changed,'base_frozen_and_responses_reviews_unchanged':True,'three_documents_unchanged':True,'all_old_b_records_unchanged':True,'plan_saved_before_requests':all(plan['planned_at']<read(p)['attempted_at'] for p in folder.glob('http-*.json')),'all_16_http_posts_successful':sum(e['type']=='request' and e['http_status']==200 for entries in events.values() for l,e in entries)==16,'unique_new_request_ids':len(set([r['response']['request_id'] for r in http]+[r['request_id'] for r in pages])),'ports_stopped':ports,'git_status':command('-c','core.quotepath=false','status','--short','--branch'),'tracked_diff':tracked,'staged_diff':staged,'shutdown_note':'用Ctrl+C终止本轮两个会话，退出1是主动中断；端口已检查不监听。'})
for name in ['prepare_b_warm_boundary.py','run_b_warm_http.py','finalize_b_warm_boundary.py']:shutil.copyfile(work/name,folder/name)
# 清单将自身和审计文件也纳入；文件大小与哈希在清单落盘后另存，避免自引用哈希。
save('07-pending-files.json',{'created_at':datetime.now().astimezone().isoformat(),'pending_files':[],'note':'占位后由本脚本写入最终路径清单；不是实验结果。'})
save('08-private-file-scan.json',{'created_at':datetime.now().astimezone().isoformat(),'note':'待本脚本最终扫描登记。'})
save('09-new-files.json',{'new_files':[rel(p) for p in sorted(folder.rglob('*')) if p.is_file()]+[rel(folder/'09-new-files.json')]})
paths=subprocess.check_output([git,'ls-files','--others','--exclude-standard','-z'],cwd=repo).decode('utf-8').split('\0')
paths=sorted(p for p in paths if p)
unexpected=[p for p in paths if not (p.startswith('进阶/runs/') or p in facts['new_code_files'])]
assert not unexpected,unexpected
manifest={'created_at':datetime.now().astimezone().isoformat(),'count':len(paths),'files':[{'path':p,'status':'新增'} for p in paths],'modified_count':0,'added_count':len(paths),'staged_count':0}
(folder/'07-pending-files.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
filename_bad=[];pattern_hits=[]
patterns={'private_key':re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
          'api_key':re.compile(r'\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|AKIA[A-Z0-9]{16})\b'),
          'secret_assignment':re.compile(r'[\"\'](?:api_key|access_token|password|secret)[\"\']\s*:\s*[\"\'](?![\"\']|null|none|placeholder|example)[^\"\']{6,}[\"\']',re.I)}
for p in paths:
    path=repo/p
    if path.name in ['config.local.json','.env'] or path.suffix.lower() in ['.gguf','.safetensors','.pth','.pt','.pyc'] or '__pycache__' in path.parts:filename_bad.append(p)
    if path.suffix.lower() in ['.json','.jsonl','.py','.html','.md','.diff','.txt']:
        content=path.read_text(encoding='utf-8-sig')
        for name,pattern in patterns.items():
            if pattern.search(content):pattern_hits.append({'path':p,'pattern':name})
scan={'checked_at':datetime.now().astimezone().isoformat(),'pending_count':len(paths),'private_configs_weights_caches':filename_bad,'common_secret_pattern_hits':pattern_hits,'unrelated_paths':unexpected,'limitation':'常见模式与文件路径离线扫描，不构成保证不存在任何秘密。','private_config_ignored':command('check-ignore','基础/config.local.json')}
assert not filename_bad and not pattern_hits
(folder/'08-private-file-scan.json').write_text(json.dumps(scan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
sizes=[{'path':p,'bytes':(repo/p).stat().st_size,'sha256':hashlib.sha256((repo/p).read_bytes()).hexdigest()} for p in paths]
inventory={'checked_at':datetime.now().astimezone().isoformat(),'count':len(paths),'total_bytes':sum(p['bytes'] for p in sizes),'files':sizes,'note':'计量时的待提交文件清单，不含本计量文件本身；它也是本轮新增文件，最终全清单见outputs中的库存。'}
save('10-pending-size-snapshot.json',inventory)
paths=sorted(p for p in subprocess.check_output([git,'ls-files','--others','--exclude-standard','-z'],cwd=repo).decode().split('\0') if p)
final={'checked_at':datetime.now().astimezone().isoformat(),'count':len(paths),'modified_count':0,'added_count':len(paths),'total_bytes':sum((repo/p).stat().st_size for p in paths),'total_MiB':sum((repo/p).stat().st_size for p in paths)/1048576,'files':[{'path':p,'status':'新增','bytes':(repo/p).stat().st_size,'sha256':hashlib.sha256((repo/p).read_bytes()).hexdigest()} for p in paths],'repo_size_snapshot_path':rel(folder/'10-pending-size-snapshot.json'),'self_reference_note':'精确最终库存保存于仓库外outputs，避免清单把自身大小重复纳入。'}
(out/'pending-files-final.json').write_text(json.dumps(final,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for name in ['03-page-log-closure.json','04-requirement-coverage.json','05-delivery-facts.json','06-preservation-checks.json','08-private-file-scan.json','09-new-files.json']:shutil.copyfile(folder/name,out/name)
print(json.dumps({'new_directory':rel(folder),'pending_count':final['count'],'total_bytes':final['total_bytes'],'total_MiB':final['total_MiB'],'new_files_count':len(read(folder/'09-new-files.json')['new_files'])+1,'counts':facts['counts'],'scan':scan,'ports_stopped':ports},ensure_ascii=False,indent=2))
