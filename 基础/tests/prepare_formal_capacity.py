"""准备待确认正式清单；仅本地健康、模板与分词接口，绝不生成。"""
from pathlib import Path
from datetime import datetime
import copy, ctypes, hashlib, json, math, os, random, socket, subprocess, sys, threading, time
import urllib.request, urllib.error

repo=Path(__file__).resolve().parents[2]
base=repo/'基础'
folder=base/'runs/formal_preparation'/datetime.now().strftime('%Y%m%d-%H%M%S')
folder.mkdir(parents=True,exist_ok=False)
def now():return datetime.now().astimezone().isoformat()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def save(name,value):
    path=folder/name
    assert not path.exists(), '不覆盖已有记录'
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

# 所有旧文件只记录哈希，不修改；正式数据正文不打印也不归档。
old={p.relative_to(repo).as_posix():sha(p) for p in (base/'runs').rglob('*') if p.is_file() and folder not in p.parents}
protected_names=['report.md','README.md','基础/开发记录.md','基础/starter/student.py','基础/starter/provider.py','基础/starter/runner.py','基础/starter/server.py','基础/config.local.json','基础/config.local.example.json']
old.update({n:sha(repo/n) for n in protected_names if (repo/n).is_file()})
save('protected-hashes.json',old)
sys.path.insert(0,str(base/'starter'))
import student, runner
assert (base/'starter/student.py').read_bytes()==(base/'runs/improve/linked_r0/student-v1.py').read_bytes()
config=load(base/'runs/two_step/dev_r0/config.answer.json')
assert config['parameters']['max_tokens']==256
assert config['parameters']['seed']==42
root=Path(os.environ['LOCALAPPDATA'])/'ANTLabLocalModel'
exe=root/'llama-b11429/llama-server.exe'
model=root/'models/Qwen3-0.6B-Q8_0.gguf'
source=load(base/'runs/prompts/qwen06_abc_r0/source-validation.json')
service_args=[str(exe),'-m',str(model),'--host','127.0.0.1','--port','8080','--alias',config['model'],
 '--ctx-size','4096','--parallel','1','--batch-size','128','--ubatch-size','64','--threads','4','--gpu-layers','0',
 '--no-context-shift','--no-warmup','--temp','0.7','--top-p','0.8','--top-k','20','--min-p','0',
 '--presence-penalty','1.5','--repeat-penalty','1.0','--reasoning','off','--seed','42','--predict','256',
 '--slot-save-path',str(root/'diagnostic-cache')]
public_args=[s.replace(str(root),'%LOCALAPPDATA%/ANTLabLocalModel') for s in service_args]

# 仅程序访问正式输入，不读开发答案，不向输出写题目或段落正文。
cases=runner.cases()
formal=[c for c in cases if c['split']=='evaluation']
assert [c['id'] for c in formal]==['T%02d'%i for i in range(1,9)]
jobs=[{'case_id':c['id'],'condition':cond,'variant':'baseline'} for c in formal for cond in ['R0','R1','R2','K']]
jobs += [{'case_id':c['id'],'condition':'R0','variant':'improved'} for c in formal]
random.Random(20261013).shuffle(jobs)
for i,j in enumerate(jobs,1):j['sequence']=i
assert len(jobs)==40 and sum(j['variant']=='baseline' for j in jobs)==32
save('run-list.json',{'created_at':now(),'status':'待确认配置','frozen':False,'generation_authorized':False,'order_seed':20261013,
 'baseline_order':'各条件清单的原顺序；baseline不调用improve。','improved_order':'仅R0调用当前第一版文字排序，保留全部原段落。','items':jobs})
save('task-rule-check.json',{'checked_at':now(),'sources':[
 {'path':'基础/01_考核题目.md','section':'第三步','quote':'对T01–T08各执行R0、R1、R2、K，共32次基线请求；在R0上执行你的改进，共8次。'},
 {'path':'基础/01_考核题目.md','section':'第三、四步','quote':'统一模型、提示词、生成参数和判分口径；无法统一的差异写明。'},
 {'path':'基础/01_考核题目.md','section':'条件表及其后说明','conclusion':'R0/R1/R2同资料换顺序；K同时改变选择与数量。'},
 {'path':'基础/starter/runner.py','section':'prepare','conclusion':'baseline保留condition清单顺序；improved才调用student.improve。'}],
 'units':'8道题是配对单位，每题5个任务；40次请求不是40个独立样本。','development_reference':'基础/runs/two_step/dev_r0/summary.json，同分保留原方案，候选负面结果不删除。'})
save('config.candidate.json',config)
version=subprocess.run([str(exe),'--version'],capture_output=True,text=True,encoding='utf-8',errors='replace',check=True)
actual_model_hash=sha(model)
assert model.stat().st_size==source['bytes'] and actual_model_hash==source['sha256']
code_names=['基础/starter/student.py','基础/starter/provider.py','基础/starter/runner.py','基础/starter/server.py','基础/starter/index.html',
 '基础/tests/check_student.py','基础/tests/check_improve.py','基础/tests/run_improve_pairs.py','基础/tests/run_schema_check.py']
script_path=base/'tests/prepare_formal_capacity.py'
code_names.append(script_path.relative_to(repo).as_posix())
git=Path.home()/'AppData/Local/Programs/Git/cmd/git.exe'
head=subprocess.run([str(git),'-C',str(repo),'rev-parse','HEAD'],capture_output=True,text=True,encoding='utf-8',check=True).stdout.strip()
save('candidate-settings.json',{'recorded_at':now(),'status':'待确认配置','frozen':False,'freeze_time':None,'generation_authorized':False,
 'source_commit':head,'working_tree_hashes_are_authoritative':True,'request_config':'config.candidate.json','request_config_sha256':sha(folder/'config.candidate.json'),
 'code_sha256':{n:sha(repo/n) for n in code_names},'data_sha256':{n:sha(repo/n) for n in ['基础/data/cases.json','基础/data/manifest.json']},
 'dataset_version':load(base/'data/manifest.json')['version'],'manifest_case_hash_matches':sha(base/'data/cases.json')==load(base/'data/manifest.json')['case_sha256'],
 'model':{**source,'actual_sha256':actual_model_hash,'actual_bytes':model.stat().st_size,'external_path':'%LOCALAPPDATA%/ANTLabLocalModel/models/Qwen3-0.6B-Q8_0.gguf'},
 'llama_cpp':{'build':'b11429','commit':'d81235049','version_output':version.stdout+version.stderr,'executable_sha256':sha(exe)},
 'service_arguments':public_args,'system_prompt_sha256':hashlib.sha256(student.prepare_messages('',[])[0]['content'].encode()).hexdigest(),
 'schema':config['parameters']['response_format'],'service_controls':{'context':4096,'slots':1,'cpu_threads':4,'gpu_layers':0,'reasoning':'off','context_shift':False,'warmup':False,'repeat_penalty':1.0},
 'execution_readiness':'清单和参数仅待确认；尚无专用40项执行编排、人工逐题标签或正式结果，runner默认limit=1不能当40项全跑。'})

save('evaluation-rules.json',{'recorded_at':now(),'status':'待确认评价口径','sources':['基础/01_考核题目.md 第四步','进阶/00_共同规则与接口.md','基础/runs/reading/alce-reading-evidence.json','基础/runs/review/stage3/citation-rules.json'],
 'metrics':[
 {'name':'answer_correct','method':'根据问题指定表达形式、项目/版本/日期/批次/口径/签署状态，核对全部当前可见原文。计算逐项记录分子分母、运算方向单位；选择逐项记录资格及决策规则。证据不足须核查所需事实是否确实缺失。','unknown':'not_checked，不能编造标准答案'},
 {'name':'format_complete','method':'原始content可解析为仅含answer字符串和citations字符串数组的JSON；不补字段、不修正原响应。空数组可以格式合法。'},
 {'name':'citation_ids_exist','method':'分别记录空引用、每个ID是否属于该次实际输入、重复引用；ID存在不等于支持。'},
 {'name':'necessary_evidence_covered','method':'先按问题和实际输入独立列出所需事实及来源，再检查引用覆盖。可能有等价证据组合，不把某一唯一ID集当金标准。'},
 {'name':'citation_support','method':'将实际answer拆成可核验主张，检查引用集合是否足以推出结论；标supported/contradicted/insufficient/not_checked，并摘录原文、计算或规则依据。'},
 {'name':'irrelevant_citations','method':'逐条判断是否为任何必要主张提供实质支持；范围错误或完全无关另列。多段共同支持的部分证据不因单段不足而自动算无关；相关冗余不自动算错误。'}],
 'strict_complete_success':{'origin':'开发阶段选定的综合指标，不是任务原文唯一评分标准','definition':'格式完整、指定答法正确、非空且全部ID属于实际输入、必要依据覆盖、引用集合支持实际答案、没有无关引用；技术失败或无答案为不成功。尚未人工核验时为not_checked。'},
 'manual_review':{'no_public_formal_gold':True,'no_model_only_judge':True,'procedure':['生成前只做容量检查，不人工分析题目或编造标签。','获授权完成正式调用后，以每次实际输入为边界逐题保存核对表：问题要求、范围、必要事实、原文定位、推导、原回答与引用、各分项状态。','题目完整可见资料另查输入是否缺证；实际输入无法推出时记录不足，K遗漏与错误拒答分开解释。','若有歧义，保存竞争解释并标未核验；人工调整保留旧标签、新标签、理由和时间，不改原响应。','完成可复核标签后才汇总；同时报告总分母、已核验数量及未知项，不能用已核验子集冒充全部正确率。'],
 'reviewer_label':'human，人工评价不是系统输出','cost':'客户端完整非流式请求耗时；启动、模板检查和人工评价耗时另列。'}})
save('failure-rules.json',{'recorded_at':now(),'status':'待确认执行规则','main_tasks':40,'independent_paired_units':8,
 'first_attempt':'每个清单项attempt=1立即保存；主表保留首次尝试状态。首次技术成功响应是first_valid_attempt，即使格式错、无答案或答错也不得质量重试。',
 'denominators':{'baseline':32,'improved':8,'pairing':'8组R0 baseline/improved；8组R0/R1/R2顺序观察；K另列选择和数量变化。','not_executed':'如因技术停止，不伪造剩余结果；列实际执行分母和计划40项完成率，未执行不当作模型回答错误。','technical_success_subset':'另列首次技术成功子集及对应分母，首次失败仍保留在主任务表。'},
 'technical_failure':'HTTP非成功、超时、服务退出、请求参数失效、内存不足、容量超限或输入与清单不一致；保留请求和错误后立即停止整轮。',
 'quality_failure':'错误答案、合法证据不足、空引用、错误引用、格式错误或预算耗尽是结果，不自动重试。',
 'retry_policy':'本轮准备不授权任何生成或重试。正式执行若技术失败须先排查并另获恢复授权；若重试，使用同设置，记录attempt、retry_of及修复，不覆盖首次失败，不挑最佳。设置改变须作为独立探索，不能混入主轮次。',
 'stop_before_generation':['全部40项容量已核验且满足4096；超限保存后停止，不删段、不截断、不换设置继续。','正式执行前需确认配置并单独登记冻结时间、哈希及40项实际输入清单。','实际模型哈希、代码、数据、参数和服务设置须与确认版本一致。'],
 'no_generation_this_round':True,'capacity_only_endpoints':['health','props','apply-template','tokenize'],
 'position_limit':'R0/R1/R2同资料换顺序；K改变选择及数量；小样本不声称统计显著或稳定性能提升。'})

save('advanced-b-gaps.json',{'recorded_at':now(),'status':'计划，未实施','sources':['进阶/02_B_系统失效诊断.md','进阶/00_共同规则与接口.md','进阶/challenge_b/spec.md','进阶/challenge_b/challenge.py'],
 'existing':['B行为契约、原样机源码及页面；本轮只源码核查，没有执行样机。','P1/P2指定规则与ALCE阅读证据已归档。','基础开发失败、竞争解释和干预记录已有，但不自动替代完整B交付。'],
 'proposed_route':'题包challenge_b离线重放，避免追加模型调用；待确认，不读取或编辑合成draft来凑结果。',
 'main_fault':'同query切换doc_ids/snapshot后结果不符合当前资料范围（旧证据或遗漏）。这是待复现故障，不宣称已实测。',
 'code_confirmed':['cache键仅query.strip().lower()，未包含范围或draft；命中缓存后仅更新request等元信息。','先全corpus排序和截取k，再按doc_ids/snapshot过滤；与spec要求的scope内排序不一致。','引用ID有效直接标supported，没有独立语义核验。'],
 'competing_explanations':[
 {'cause':'缓存混淆范围','prediction':'同query先旧快照后新快照可复用旧evidence；仅换成新Engine/关闭缓存应消除旧来源复用。'},
 {'cause':'范围过滤晚于全局top-k','prediction':'即使新Engine冷启动，scope外高分条目仍可挤掉scope内证据；只改变scope外干扰条目的排名或先过滤范围可改变遗漏。'}],
 'minimal_work':[
 {'item':'原始复现','missing':True,'plan':'按原样机记录同query/不同范围的请求顺序、实际evidence、cache_hit、状态和日志，定位最早错误边界。'},
 {'item':'区分性干预','missing':True,'plan':'干预前保存预测；分别只重置缓存与只去除scope外排序干扰。保留原始输入/draft，区分共同作用；另查低延迟是否来自错误旧缓存。'},
 {'item':'最小修复','missing':True,'plan':'若缓存归因成立，优先评估禁用缓存的最小修复；舍弃扩大缓存键作为本轮替代，并说明性能取舍。若仅排序归因成立则先scope过滤再top-k；不预先承诺同时修两项。'},
 {'item':'两个正常回归','missing':True,'plan':'同一有效scope冷请求；相同输入重复请求。按spec核对证据/状态/唯一request_id，不只看200或抄函数输出。'},
 {'item':'两个等价变体','missing':True,'plan':'同步重映射文档/证据ID及请求/draft引用；打乱corpus顺序而保持语义、范围、tags和稳定并列规则。保留可逆映射与预期。'},
 {'item':'一个自造边界','missing':True,'plan':'未知snapshot或doc_id应明确invalid_scope，不回退旧快照；记录剩余局限。'},
 {'item':'页面到日志闭环','missing':True,'plan':'展示当前请求、实际来源快照、证据原文、locator/support/judgment来源、修复前后差异与request_id；支持回溯同请求日志。尚未语义核验须显示not_checked。'},
 {'item':'另外两个症状及决定','missing':True,'plan':'登记scope外排序挤掉证据和ID有效伪装supported的风险；补至少三项关键决定、被舍弃方案、AI影响和剩余边界。'}],
 'limits':'源码检查能确认实现与契约不符，但本轮没有复现、因果干预、修复或页面验证；不把已有基础优化当作B已完成。'})
print('SAVED preparation parts 1,2,4,5,6:',folder.relative_to(repo).as_posix(),flush=True)

# 容量检查允许表型/分词接口；访问其他路径直接拒绝，不导入provider.call_model。
http_calls=[]
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def service(route,body=None):
    assert route in {'health','props','apply-template','tokenize'},'禁止生成接口'
    http_calls.append({'route':route,'method':'GET' if body is None else 'POST','time':now()})
    request=urllib.request.Request('http://127.0.0.1:8080/'+route,data=None if body is None else json.dumps(body,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
    with opener.open(request,timeout=20) as response:return json.loads(response.read())
class MemoryStatus(ctypes.Structure):
    _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ('total','available','total_page','available_page','total_virtual','available_virtual','extended')]
def memory():
    m=MemoryStatus();m.length=ctypes.sizeof(m)
    assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return {'time':now(),'available_bytes':m.available,'total_bytes':m.total}
runtime={'recorded_at':now(),'counts_as_generation':False,'generation_calls':0,'arguments':public_args,'before_load':memory(),'samples':[]}
proc=None;stop=threading.Event();abort=threading.Event();thread=None;rows=[]
def monitor():
    low=0
    while not stop.is_set():
        m=memory();runtime['samples'].append(m)
        low=low+1 if m['available_bytes']<1024**3 else 0
        if low>=3:
            abort.set()
            if proc and proc.poll() is None:proc.terminate()
            return
        stop.wait(2)
try:
    assert runtime['before_load']['available_bytes']>=2*1024**3,'可用内存不足2 GiB，保存后停止'
    with socket.socket() as sock:sock.bind(('127.0.0.1',8080))
    with (folder/'server-stdout.log').open('wb') as stdout,(folder/'server-log.txt').open('wb') as stderr:
        proc=subprocess.Popen(service_args,stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
    started=time.perf_counter();thread=threading.Thread(target=monitor,daemon=True);thread.start()
    while True:
        if abort.is_set():raise RuntimeError('可用内存持续低于1 GiB')
        if proc.poll() is not None:raise RuntimeError('服务加载失败')
        try:
            if service('health').get('status')=='ok':break
        except (urllib.error.URLError,TimeoutError):pass
        if time.perf_counter()-started>120:raise TimeoutError('服务启动超时')
        time.sleep(.5)
    runtime['load_seconds']=time.perf_counter()-started;runtime['after_load']=memory()
    props=service('props')
    assert props['default_generation_settings']['n_ctx']==4096 and props['total_slots']==1
    assert props['build_info']=='b11429-d81235049' and props['model_alias']==config['model']
    params=props['default_generation_settings']['params']
    numeric={k:v for k,v in config['parameters'].items() if isinstance(v,(int,float)) and k!='max_tokens'}
    assert all(math.isclose(params[k],v,rel_tol=1e-6,abs_tol=1e-6) for k,v in numeric.items())
    runtime['service_verified']={'context':4096,'slots':1,'build':props['build_info'],'sampling_defaults_match':True,'max_tokens_checked_in_body':256,'max_tokens_default_not_used_as_request_echo':True,'chat_template_sha256':hashlib.sha256(props['chat_template'].encode()).hexdigest()}
    for job in jobs:
        if abort.is_set():raise RuntimeError('内存不足')
        case,original,selected,messages=runner.prepare(job['case_id'],job['condition'],job['variant'])
        before=copy.deepcopy(original)
        if job['variant']=='baseline':assert selected==original
        else:
            assert len(selected)==len(original) and sorted(p['id'] for p in selected)==sorted(p['id'] for p in original)
            assert all(p in original for p in selected)
        assert original==before
        assert json.loads(messages[1]['content'])=={'question':case['question'],'passages':selected}
        by={p['id']:p for p in case['passages']}
        assert original==[by[i] for i in case['conditions'][job['condition']]]
        assert set(case['conditions']['R0'])==set(case['conditions']['R1'])==set(case['conditions']['R2'])
        assert len(case['conditions']['K'])==2 and set(case['conditions']['K']).issubset(case['conditions']['R0'])
        body={'model':config['model'],'messages':messages,'stream':False,**config['parameters']}
        assert body['max_tokens']==256
        prompt=service('apply-template',body)['prompt']
        assert all(m['content'] in prompt for m in messages),'模板没有完整保留消息'
        assert prompt.endswith('<think>\n\n</think>\n\n'),'关闭思考模板不一致'
        tokens=service('tokenize',{'content':prompt,'add_special':True,'parse_special':True})['tokens']
        count=len(tokens)
        row={**job,'input_tokens':count,'output_budget':256,'total_required':count+256,'context_capacity':4096,'fits':count+256<4096}
        rows.append(row)
        # 每项即保存，仅长度信息；不保存题目、段落、提示渲染文本或token IDs。
        with (folder/'capacity-items.jsonl').open('a',encoding='utf-8') as stream:stream.write(json.dumps(row,ensure_ascii=False)+'\n')
        print(job['case_id'],job['condition'],job['variant'],count,count+256,row['fits'],flush=True)
        if not row['fits']:raise RuntimeError('正式输入容量超限；不截断、不修改设置继续')
    runtime['completed_items']=len(rows);runtime['all_fit']=True
except Exception as e:
    runtime.update(status='stopped',error_type=type(e).__name__,error_detail=str(e),completed_items=len(rows))
    print('STOPPED',type(e).__name__,str(e),flush=True)
finally:
    stop.set()
    if thread:thread.join(timeout=5)
    if proc and proc.poll() is None:
        proc.terminate()
        try:proc.wait(timeout=10)
        except subprocess.TimeoutExpired:proc.kill();proc.wait()
    runtime['service_stopped']=proc is None or proc.poll() is not None
    runtime['after_stop']=memory();runtime['http_calls']=http_calls
    # 日志不含正式内容，公开模型路径使用环境变量；不改任何旧日志。
    for name in ['server-log.txt','server-stdout.log']:
        path=folder/name
        if path.exists():path.write_text(path.read_text(encoding='utf-8',errors='replace').replace(str(root),'%LOCALAPPDATA%/ANTLabLocalModel'),encoding='utf-8')
    save('capacity-runtime.json',runtime)
    save('capacity-summary.json',{'checked_at':now(),'status':'待确认配置','frozen':False,'counts_as_generation':False,'generated_calls':0,
     'planned_items':40,'checked_items':len(rows),'all_fit':len(rows)==40 and all(r['fits'] for r in rows),
     'maximum_input_tokens':max((r['input_tokens'] for r in rows),default=None),'maximum_total_required':max((r['total_required'] for r in rows),default=None),
     'output_budget':256,'context_capacity':4096,'margin_at_maximum':4096-max((r['total_required'] for r in rows),default=4096),
     'fit_rule':'保守要求input_tokens+256 < 4096，不静默删段或截断。','tokenization_options':{'add_special':True,'parse_special':True},
     'message_and_order_verified':len(rows)==40,'formal_bodies_saved_or_printed':False,'items':rows,
     'not_proven':'只验证当前40项候选输入容量；不是正式生成成功、模型回答质量、已冻结或其他题可容纳。','service_stopped':runtime['service_stopped']})
    unchanged=all(sha(repo/n)==v for n,v in old.items())
    assert unchanged,'旧文件被改变'
    previous=load(base/'runs/two_step/dev_r0/generation-count.json')
    assert previous['cumulative_unique_count']==84
    save('final-audit.json',{'checked_at':now(),'protected_files_unchanged':len(old),'new_generation_calls':0,'cumulative_generation_calls':84,
     'generation_endpoints_called':False,'allowed_routes_only':all(c['route'] in {'health','props','apply-template','tokenize'} for c in http_calls),
     'formal_body_saved_or_printed':False,'frozen':False,'service_stopped':runtime['service_stopped']})
    print('FINAL',json.dumps({'folder':folder.relative_to(repo).as_posix(),'items':len(rows),'maximum':max((r['input_tokens'] for r in rows),default=None),'all_fit':len(rows)==40 and all(r['fits'] for r in rows),'generation_calls':0,'service_stopped':runtime['service_stopped']},ensure_ascii=False),flush=True)
