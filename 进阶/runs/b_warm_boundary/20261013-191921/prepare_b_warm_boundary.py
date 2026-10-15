from pathlib import Path
import json, hashlib, subprocess
from datetime import datetime

repo=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
work=Path(__file__).parent
at=datetime.now().astimezone()
folder=repo/'进阶/runs/b_warm_boundary'/at.strftime('%Y%m%d-%H%M%S')
folder.mkdir(parents=True,exist_ok=False)
def save(name,value):
    (folder/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
protected={p.relative_to(repo).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in repo.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts}
save('00-protected-hashes.json',protected)
sha=subprocess.check_output([r'C:\Users\86186\AppData\Local\Programs\Git\cmd\git.exe','rev-parse','HEAD'],cwd=repo,text=True).strip()
save('01-plan.json',{'planned_at':at.isoformat(),'code_base_commit':sha,'run_kind':'offline_replay','new_model_calls':0,
    'services':{'original':{'engine':'challenge:Engine','port':8876},'fixed':{'engine':'no_cache_engine:Engine','port':8877}},
    'sequence':[{'case_id':'R01','reset':True,'override':{},'role':'preheat_unknown_document'},
                {'case_id':'R01','reset':False,'override':{'doc_ids':['missing']},'role':'unknown_document'},
                {'case_id':'R01','reset':True,'override':{},'role':'independent_preheat_unknown_snapshot'},
                {'case_id':'R01','reset':False,'override':{'snapshot':'missing'},'role':'unknown_snapshot'}],
    'predictions':['原版query缓存忽略scope；两项暖未知范围预计返回alpha/v1的旧b01，原定位valid和supported也可能沿用。',
                   '修复版重新检索，未知范围预计证据为空；仍返回固定draft及ok，不把它称为合格未知范围处理。',
                   '展示层scope_status应为invalid_scope、locator_status=invalid、support_status=not_checked；原版旧证据应明确显示范围冲突。'],
    'pass_criteria':['原Engine原始响应保留且与同request_id日志一致。','修复版未知范围不复用旧证据。','页面不将旧范围证据标为有效、不暗示语义已支持。','页面截图、提交正文、响应及日志request_id能闭环。'],
    'execution':['直接HTTP各4次，共8次；页面同序列各4次，共8次。两组分别重置预热。','原/修复同query、corpus、固定R01 draft；只改变doc_ids或snapshot。','第二项边界前独立reset=true，不能沿用第一项缓存作为预热。'],
    'stop_rules':['技术请求失败保存后停止；质量缺陷不重试、不改逻辑。','结束停止本轮服务。'],
    'limits':['不做检索、语义及Engine未知范围处理修复。','HTTP、页面均是offline_replay；页面请求也是HTTP请求，计数不重复相加。','不修改三个说明文档或基础冻结材料。'],
    'code_hashes':{n:hashlib.sha256((repo/'进阶/challenge_b'/n).read_bytes()).hexdigest() for n in ['challenge.py','no_cache_engine.py','server_review.py','review.html','data.json']}})
(work/'b_warm_folder.txt').write_text(str(folder),encoding='utf-8')
print(folder)
