from pathlib import Path
import json, hashlib, subprocess, difflib
from datetime import datetime
repo=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
work=Path(__file__).parent
now=datetime.now().astimezone()
folder=repo/'进阶/runs/b_http_page'/now.strftime('%Y%m%d-%H%M%S')
folder.mkdir(parents=True,exist_ok=False)
def save(name,value):
    (folder/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
protected={p.relative_to(repo).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in repo.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts}
save('00-protected-hashes.json',protected)
sha=subprocess.check_output([r'C:\Users\86186\AppData\Local\Programs\Git\cmd\git.exe','rev-parse','HEAD'],cwd=repo,text=True).strip()
for name in ['server_review.py','review.html']:
    dest=repo/'进阶/challenge_b'/name
    if dest.exists():raise RuntimeError(str(dest))
    dest.write_bytes((work/name).read_bytes())
    (folder/name).write_bytes(dest.read_bytes())
save('01-plan.json',{'planned_at':now.isoformat(),'code_base_commit':sha,'run_kind':'offline_replay','new_model_calls':0,'services':{'original':{'engine':'challenge:Engine','port':8876},'fixed':{'engine':'no_cache_engine:Engine','port':8877}},'default_engine':'challenge:Engine','predictions':['原版R01→R02仍显示旧v1证据；展示层标范围冲突并保留原响应。','修复版相同序列显示v2/b02，不复用缓存。','修复版R03使用5秒draft但证据为空、定位invalid，检索失败。','冷R05及同范围重复内容一致；修复版重复不是缓存命中。','未知文档/快照冷请求不借范围外证据，但Engine仍返回ok及固定draft，展示invalid_scope并记录契约缺口。'],'http_sequence':[{'case_id':c,'reset':reset,'override':override} for c,reset,override in [('R01',True,{}),('R02',False,{}),('R03',False,{}),('R05',True,{}),('R05',False,{}),('R07',True,{}),('R02',True,{'snapshot':'missing'})]],'page_sequence_same_as_http':True,'rules':['原/修复服务同corpus/draft和HTTP序列，各自清空开始。','页面通过真实点击提交；每次截图、DOM状态及HTTP后端日志按request_id匹配。','原Engine响应不改；外层locator核对实际范围，support始终not_checked，judgment_source=unverified。','未知范围仅展示标注，不修检索算法，不补draft或证据。','技术错误保存后停止，质量缺陷保留；结束关闭本轮两个服务。'],'limitations':['离线函数耗时不代表LLM或端到端模型延迟。','语义状态未核验，ID有效不能代表支持。','未做并发、生产安全或多用户验证。']})
save('02-field-mapping.json',{'raw_response':'engine_response完整保留','mode':'request.mode=offline_replay','support_status':'外层not_checked，原值保留于engine_response.support_status','judgment_source':'外层unverified，原值保留','locator_status':'非空引用+证据ID存在+实际证据属于请求范围；无引用absent，否则invalid','block_id':'由固定资料id逐项映射，不改原始块ID','scope_status':'范围存在性核对；invalid_scope是展示层值，不声称Engine已修复范围契约','actual_scopes':'实际返回evidence中的doc_id/snapshot去重','elapsed_ms':'Engine真实本地函数耗时','run_kind':'HTTP传输仍为offline_replay','draft':'使用data.json中case对应固定draft；边界只改请求范围','log':'events.jsonl记录startup及每次完整HTTP正文、Engine输入、corpus、draft、缓存前后及响应'})
diff=''
for name in ['server_review.py','review.html']:
    diff+=''.join(difflib.unified_diff([], (work/name).read_text(encoding='utf-8').splitlines(True),fromfile='/dev/null',tofile='进阶/challenge_b/'+name))
(folder/'code-full.diff').write_text(diff,encoding='utf-8')
(work/'b_http_folder.txt').write_text(str(folder),encoding='utf-8')
print(folder)
