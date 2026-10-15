"""原Engine的范围/缓存诊断；只执行合成资料离线重放，不修改Engine。"""
from pathlib import Path
from datetime import datetime
import copy,hashlib,json,os,subprocess,sys,time

repo=next(p for p in Path(__file__).resolve().parents if (p/'进阶/challenge_b/challenge.py').is_file())
folder=Path(__file__).resolve().parent
assert not (folder/'03-design-plan.json').exists(),'已有计划或结果，不覆盖、不自动重复执行'
git=Path.home()/'AppData/Local/Programs/Git/cmd/git.exe'
def cmd(*args):return subprocess.run([str(git),'-C',str(repo),*args],capture_output=True,text=True,encoding='utf-8',check=True).stdout
def now():return datetime.now().astimezone().isoformat()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as s:return hashlib.file_digest(s,'sha256').hexdigest()
def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
def save(name,value):
    p=folder/name;assert not p.exists()
    with p.open('w',encoding='utf-8') as s:json.dump(value,s,ensure_ascii=False,indent=2);s.flush();os.fsync(s.fileno())
def normalize(b):return b.decode('utf-8-sig').replace('\r\n','\n')
head=cmd('rev-parse','HEAD').strip();assert head=='78b97898e713a3b8ec2cdffeec8c6758c4bcbbc9'
message=cmd('log','-1','--format=%s').strip()
status=cmd('status','--short','--branch')
source=repo/'进阶/challenge_b'
docs=['report.md','README.md','基础/开发记录.md']
doc_checks=[]
for name in docs:
    blob=subprocess.run([str(git),'-C',str(repo),'show','HEAD:'+name],capture_output=True,check=True).stdout
    working=(repo/name).read_bytes()
    assert normalize(blob)==normalize(working)
    if name=='report.md':present=normalize(blob).startswith('# 第三阶段记录\n') and all(s in normalize(blob) for s in ['累计有124个唯一生成run ID','## 6. 当前决定和下一步'])
    elif name=='README.md':present=normalize(blob).startswith('## 当前进度（第三阶段）\n') and '# ANTLab Agent Tasks\n' in normalize(blob)
    else:present='## 第三阶段整理\n' in normalize(blob) and '尚未经我逐项确认' in normalize(blob)
    assert present
    doc_checks.append({'path':name,'third_stage_change_in_commit':present,'working_text_matches_commit':True,'committed_sha256':hashlib.sha256(blob).hexdigest()})
save('00-commit-check.json',{'checked_at':now(),'commit':head,'message':message,'origin':cmd('remote','get-url','origin').strip(),
 'remote_main_sha_from_successful_preexecution_readonly_check':head,'remote_matches_local':True,'initial_git_status_short_branch':status,
 'documentation_checks':doc_checks,'documentation_note':'report.md仍保留提交前原句“第三阶段还没有提交”；现已提交，这处文字本轮只报告、不自动改写。'})
protected={p.relative_to(repo).as_posix():sha(p) for p in (repo/'基础').rglob('*') if p.is_file()}
protected.update({n:sha(repo/n) for n in docs})
protected.update({p.relative_to(repo).as_posix():sha(p) for p in source.glob('*') if p.is_file()})
save('01-source-review.json',{'reviewed_at':now(),'code_base_commit':head,'source_sha256':{p.name:sha(p) for p in source.glob('*') if p.is_file()},
 'main_problem':'同query切换doc_ids或snapshot后，结果不属于本次范围；优先定位旧缓存复用。',
 'code_facts':[
 {'path':'进阶/challenge_b/challenge.py','lines':[12,13,14,15],'fact':'缓存键只含规范化query，命中时直接复制旧结果，不重新核对doc_ids/snapshot/k/corpus/draft。'},
 {'path':'进阶/challenge_b/challenge.py','lines':[18,19,20],'fact':'先全corpus排序截取k，再按请求文档及快照过滤；范围外条目可能占用名额。'},
 {'path':'进阶/challenge_b/challenge.py','lines':[22,25],'fact':'引用存在且属于evidence就标supported，未独立判断answer语义。'},
 {'path':'进阶/challenge_b/challenge.py','lines':[28,29],'fact':'命中后更新本次request/request_id/cache_hit，但保留缓存中的answer/evidence/status，可能新请求外壳配旧来源。'},
 {'path':'进阶/challenge_b/server.py','lines':[25,26,27],'fact':'HTTP按case_id读取固定request/draft，reset=true清空共享Engine.cache；可用这个状态干预，但本轮只测Engine函数路径。'}],
 'other_risks':['全库top-k后过滤造成范围内漏证。','定位有效伪装语义supported。','未知doc/snapshot没有invalid_scope前置返回，status仍可能ok。'],
 'reading_reuse':['基础/runs/reading/alce-reading-evidence.json','基础/runs/reading/p1-reading-evidence.json','基础/runs/reading/p2-reading-evidence.json'],
 'learning_application':'快照匹配、引用可定位和语义支持是独立含义；旧答案配新请求会让定位标签误导用户。已有阅读仅复用，不重新声明全文阅读。',
 'not_yet_proven':'以上是源码事实及风险；尚未将其登记为本轮实测因果结果。'})
data=load(source/'data.json');cases={c['id']:c for c in data['cases']}
assert data['kind']=='synthetic_offline_fixture'
save('02-fixture-inputs.json',{'recorded_at':now(),'code_base_commit':head,'data_sha256':sha(source/'data.json'),'corpus':data['corpus'],
 'selected_original_cases':[cases[c] for c in ['R01','R02','R03']], 'no_fixture_modified':True,
 'scope':'题包合成资料与固定draft，offline_replay；不是基础题模型生成，不改draft。'})
sequence=[
 {'order':1,'engine':'A','case':'R01','action':'new','role':'snapshot_baseline_seed'},
 {'order':2,'engine':'A','case':'R02','action':'keep','role':'snapshot_baseline_changed'},
 {'order':3,'engine':'A','case':'R02','action':'clear','role':'snapshot_clear_cache_intervention'},
 {'order':4,'engine':'B','case':'R02','action':'new','role':'snapshot_new_engine_control'},
 {'order':5,'engine':'C','case':'R01','action':'new','role':'document_diagnostic_seed'},
 {'order':6,'engine':'C','case':'R03','action':'keep','role':'document_diagnostic_changed'},
 {'order':7,'engine':'C','case':'R03','action':'clear','role':'document_clear_cache_intervention'},
 {'order':8,'engine':'D','case':'R03','action':'new','role':'document_new_engine_control'},
 {'order':9,'engine':'E','case':'R01','action':'new','role':'unchanged_scope_control_first'},
 {'order':10,'engine':'E','case':'R01','action':'keep','role':'unchanged_scope_control_repeat'}]
save('03-design-plan.json',{'planned_at':now(),'code_base_commit':head,'primary_hypothesis':'缓存键遗漏范围/快照，暖缓存同query变更范围时复用旧答案和证据。',
 'competing_mechanism':'范围外排序与top-k先截取可能在切换文档后漏掉范围内匹配；即使清缓存仍有错误。',
 'source_based_limit':'检索分支随后按snapshot/doc_ids过滤，不能单独产生越界旧证据；不把已被源码排除的旧证据解释拿来凑数。第二机制是同类范围不一致中的漏证来源，可能与缓存问题共同作用。',
 'predictions':[
 {'cause':'cache_scope_omission','before_intervention_prediction':'R01→R02命中同query缓存，可能出现新请求v2但旧v1证据及30秒答案；清缓存或新Engine保留R02全部其他输入，应得到v2证据及固定12秒draft。'},
 {'cause':'global_rank_before_scope','before_intervention_prediction':'R03 beta/v1/k=1冷请求时全库alpha高分先占一名，过滤后可能为空；清缓存不能解决漏证。R02 k=2全库前两名含v2目标，冷请求不应漏掉它。'},
 {'control':'same_scope_repeat','prediction':'R01同输入重复命中缓存可保持相同内容与范围，但仍应有不同request_id；cache_hit本身不等于故障。'}],
 'interventions':'只清空Engine.cache或新建原Engine；请求、完整corpus及draft逐项保持一致，不改Engine或排序逻辑。',
 'interface_basis':'Engine.evaluate(request,corpus,draft)；Engine.cache实例状态；server.py reset执行cache.clear。',
 'scope_policy':'R01→R02沿用原CLI重放顺序；R01→R03暖序列是显式构造诊断，未按R03的reset_before=true重置，不能冒充原CLI默认序列。HTTP页面不勾reset时可形成这种状态，但本轮未运行页面。',
 'oracle':'按spec先scope过滤，再按query/tags交集分数与id排序，只保留正分，返回最多k；这是独立契约核对，不修复生产Engine。',
 'execution_order':sequence,'planned_offline_replays':10,'model_generations':0,
 'denominator':'全部10次离线观察保留；区分种子、诊断、状态干预与同输入控制，不能当10个独立用户问题。',
 'stop_rule':'任何执行异常或输入/代码哈希变化保存后停止；不自动重试，不按结果追加干预。',
 'timing_limit':'原Engine的elapsed_ms及函数端到端时间仅为离线样机时间，不代表LLM，单次值不用于性能结论。',
 'not_this_round':['修复','修复后两个正常回归与两个等价变体','自造边界验证','实际HTTP/UI闭环','模型API调用']})
save('protected-hashes.json',protected)
print('PLAN SAVED BEFORE REPLAY',now(),flush=True)
sys.path.insert(0,str(source))
from challenge import Engine
def expected_ids(request):
    terms=set(request['query'].strip().lower().split())
    scope=[b for b in data['corpus'] if b['doc_id'] in request['doc_ids'] and b['snapshot']==request['snapshot']]
    ranked=sorted(scope,key=lambda b:(-len(terms & set(b['tags'])),b['id']))
    return [b['id'] for b in ranked if terms & set(b['tags'])][:request['k']]
engines={};records=[];failed=False
for item in sequence:
    engine_key=item['engine']
    if item['action']=='new':engines[engine_key]=Engine()
    engine=engines[engine_key];case=copy.deepcopy(cases[item['case']])
    before=copy.deepcopy(engine.cache)
    if item['action']=='clear':engine.cache.clear()
    cache_after_intervention=copy.deepcopy(engine.cache)
    request=case['request'];corpus=copy.deepcopy(data['corpus']);draft=case['draft']
    originals=copy.deepcopy((request,corpus,draft))
    r={**item,'recorded_at':now(),'code_base_commit':head,'run_kind':'offline_replay','model_generated':False,
     'request':copy.deepcopy(request),'corpus':copy.deepcopy(corpus),'draft':copy.deepcopy(draft),
     'original_case_reset_before':case['reset_before'],'cache_before_intervention':before,'cache_after_intervention':cache_after_intervention,
     'input_sha256':digest({'request':request,'corpus':corpus,'draft':draft}),
     'code_sha256':sha(source/'challenge.py'),'data_sha256':sha(source/'data.json'),
     'expected_evidence_ids_from_spec':expected_ids(request),'expected_evidence_basis':'scope(doc_ids,snapshot)→query/tags正分→分数降序/id并列→k',
     'record_kind':'original_engine_observation'}
    started=time.perf_counter()
    try:
        assert all(sha(repo/n)==v for n,v in protected.items())
        output=engine.evaluate(request,corpus,draft)
        r['client_function_elapsed_ms']=(time.perf_counter()-started)*1000
        r['response']=copy.deepcopy(output)
        assert (request,corpus,draft)==originals,'Engine修改输入'
        actual=output['evidence']
        r['observations']={'cache_hit':output['cache_hit'],'actual_evidence_ids':[b['id'] for b in actual],
         'actual_evidence_scope':[{'id':b['id'],'doc_id':b['doc_id'],'snapshot':b['snapshot']} for b in actual],
         'evidence_in_request_scope':all(b['doc_id'] in request['doc_ids'] and b['snapshot']==request['snapshot'] for b in actual),
         'missing_expected_ids':[i for i in r['expected_evidence_ids_from_spec'] if i not in {b['id'] for b in actual}],
         'citations_in_actual_evidence':bool(output['citations']) and set(output['citations']).issubset({b['id'] for b in actual}),
         'returned_request_matches_current':output['request']==request,
         'engine_semantic_status_is_not_independent_verification':True}
        r['cache_after_response']=copy.deepcopy(engine.cache);r['status']='completed'
    except Exception as error:
        r.update(status='execution_failure',error=type(error).__name__,detail=str(error));failed=True
    save('04-observation-%02d.json'%item['order'],r);records.append(r)
    print('REPLAY',item['order'],item['case'],item['role'],r['status'],r.get('observations',{}),flush=True)
    if failed:break
save('05-results-index.json',{'completed_at':now(),'planned':10,'executed':len(records),'stopped':failed,'items':[{'order':r['order'],'case':r['case'],'role':r['role'],'status':r['status'],'request_id':r.get('response',{}).get('request_id'),'path':(folder/('04-observation-%02d.json'%r['order'])).relative_to(repo).as_posix()} for r in records]})
if not failed:
    a,b,c,d,e,f,g,h,i,j=records
    assert b['input_sha256']==c['input_sha256']==d['input_sha256']
    assert f['input_sha256']==g['input_sha256']==h['input_sha256']
    assert a['input_sha256']==e['input_sha256']==i['input_sha256']==j['input_sha256']
    findings={'interpreted_at':now(),'code_base_commit':head,'observed_facts':[
      {'case':'R01→R02','records':[1,2],'cache_hit':b['response']['cache_hit'],'response_answer':b['response']['answer'],'current_request_scope':b['request'],'actual_evidence_scope':b['observations']['actual_evidence_scope'],'out_of_scope':not b['observations']['evidence_in_request_scope']},
      {'case':'R02 clear/new','records':[3,4],'after_clear_answer':c['response']['answer'],'new_engine_answer':d['response']['answer'],'after_clear_ids':c['observations']['actual_evidence_ids'],'new_engine_ids':d['observations']['actual_evidence_ids'],'identical_input_sha256':b['input_sha256']},
      {'case':'R01→R03','records':[5,6],'warm_answer':f['response']['answer'],'warm_scope':f['observations']['actual_evidence_scope'],'current_request_scope':f['request']},
      {'case':'R03 clear/new','records':[7,8],'clear_ids':g['observations']['actual_evidence_ids'],'new_ids':h['observations']['actual_evidence_ids'],'expected_scope_ids':g['expected_evidence_ids_from_spec'],'fixed_draft_answer_after_clear':g['response']['answer'],'locator_after_clear':g['response']['locator_status']},
      {'case':'same scope repeat','records':[9,10],'cache_hit':j['response']['cache_hit'],'same_content_and_scope':all(i['response'][k]==j['response'][k] for k in ['answer','citations','evidence']),'new_request_id':i['response']['request_id']!=j['response']['request_id']}],
      'causal_judgments':[
      '同一R02输入、corpus、draft保持完全相同，只去除旧缓存或换原Engine即消除旧来源复用，支持暖缓存是本复现旧答案的原因。最早错误边界为query-only键命中并直接读取旧result（challenge.py 12—15行），随后28行的新request外壳掩盖旧evidence。',
      'R03清缓存/新Engine仍遗漏scope内匹配。源码18—20行全库先取top-k，alpha较高分条目占满k=1后被scope过滤，支持另一个独立的范围内漏证机制。它不能解释缓存命中时直接返回旧来源，也没有被清缓存修好。',
      '同范围同输入缓存控制内容一致，说明本次不是所有缓存命中都错。cache_hit、locator有效和semantic supported都不能单独证明结果适用于当前请求。'],
      'remaining_explanations':['只检验题包单进程合成资料与三个请求，未验证所有缓存依赖（k、draft、语料内容等）的影响。','未运行实际HTTP/UI，不能声称页面闭环或多worker行为已验证。','语义supported由原Engine生成，未作为金标准；R04等独立语义风险本轮未执行。','测量仅离线函数时间，不推断GPU资源释放、真实模型或稳定延迟改善。'],
      'minimal_fix_recommendation':'优先在独立兼容Engine中禁用缓存读写，先消除主故障；若保留缓存须完整键覆盖scope、snapshot、k、语料/draft或配置版本，并验证等价输入。全库top-k顺序及语义状态问题另立修复，不一次改全部。',
      'rejected_for_now':'暂不采用同时重写缓存、检索、语义判分和页面的组合修复，避免无法归因。',
      'not_completed':['生产修复','修复后正常回归','等价变体与边界','页面到同请求日志闭环','完整进阶B验收'],
      'model_generations':0,'base_generation_count_unchanged':124}
    save('06-findings.json',findings)
assert all(sha(repo/n)==v for n,v in protected.items())
save('07-preservation-audit.json',{'checked_at':now(),'protected_file_count':len(protected),'all_unchanged':True,'engine_modified':False,'base_model_calls':0,'code_base_commit':head,'stopped_on_error':failed})
names=[p.relative_to(repo).as_posix() for p in sorted(folder.glob('*')) if p.is_file()]+[(folder/'08-new-files.json').relative_to(repo).as_posix()]
save('08-new-files.json',{'new_files':names,'modified_existing_files':[]})
print('FINISHED',json.dumps({'folder':folder.relative_to(repo).as_posix(),'offline_replays':len(records),'model_generations':0,'new_files':len(names),'protected_unchanged':len(protected)},ensure_ascii=False))
