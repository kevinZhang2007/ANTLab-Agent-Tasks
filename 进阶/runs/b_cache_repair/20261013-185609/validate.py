"""缓存移除的原Engine配对验证；合成资料离线重放，不调用模型。"""
from pathlib import Path
from datetime import datetime
import ast,copy,difflib,hashlib,inspect,json,os,random,subprocess,sys,time
repo=next(p for p in Path(__file__).resolve().parents if (p/'进阶/challenge_b/challenge.py').is_file())
folder=Path(__file__).resolve().parent;source=repo/'进阶/challenge_b'
assert not (folder/'02-validation-plan.json').exists(),'已有计划或结果，不覆盖、不自动重跑'
def now():return datetime.now().astimezone().isoformat()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as s:return hashlib.file_digest(s,'sha256').hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
def save(name,value):
    p=folder/name;assert not p.exists()
    with p.open('w',encoding='utf-8') as s:json.dump(value,s,ensure_ascii=False,indent=2);s.flush();os.fsync(s.fileno())
git=Path.home()/'AppData/Local/Programs/Git/cmd/git.exe'
head=subprocess.run([str(git),'-C',str(repo),'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
original=(source/'challenge.py').read_bytes();fixed=(source/'no_cache_engine.py').read_bytes()
protected={p.relative_to(repo).as_posix():sha(p) for p in (repo/'基础').rglob('*') if p.is_file()}
protected.update({n:sha(repo/n) for n in ['report.md','README.md','基础/开发记录.md']})
protected.update({p.relative_to(repo).as_posix():sha(p) for p in (repo/'进阶/runs').rglob('*') if p.is_file() and folder not in p.parents})
protected.update({p.relative_to(repo).as_posix():sha(p) for p in source.glob('*') if p.is_file()})
save('00-protected-hashes.json',protected)
(folder/'original-engine.py').write_bytes(original);(folder/'no-cache-engine.py').write_bytes(fixed)
diff=''.join(difflib.unified_diff(original.decode().splitlines(keepends=True),fixed.decode().splitlines(keepends=True),fromfile='a/进阶/challenge_b/challenge.py',tofile='b/进阶/challenge_b/no_cache_engine.py'))
(folder/'engine-full.diff').write_text(diff,encoding='utf-8')
def body(raw):
    module=ast.parse(raw.decode('utf-8-sig'))
    cls=next(n for n in module.body if isinstance(n,ast.ClassDef) and n.name=='Engine')
    return next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='evaluate')
oldnode=body(original);newnode=body(fixed)
def equal(a,b):return ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)
assert equal(oldnode.args,newnode.args)
assert all(equal(a,b) for a,b in zip(oldnode.body[:2],newnode.body[:2]))
assert len(oldnode.body[3].orelse[:-1])==len(newnode.body[2:9])==7
assert all(equal(a,b) for a,b in zip(oldnode.body[3].orelse[:-1],newnode.body[2:9]))
update=copy.deepcopy(oldnode.body[4])
next(k for k in update.value.keywords if k.arg=='cache_hit').value=ast.Constant(False)
assert equal(update,newnode.body[9]) and equal(oldnode.body[5],newnode.body[10])
save('01-implementation.json',{'recorded_at':now(),'code_base_commit':head,'original_path':'进阶/challenge_b/challenge.py','fixed_path':'进阶/challenge_b/no_cache_engine.py',
 'original_sha256':sha(source/'challenge.py'),'fixed_sha256':sha(source/'no_cache_engine.py'),'full_diff':'engine-full.diff',
 'only_cache_logic_changed_by_AST':True,'compatibility':'evaluate(request,corpus,draft)签名相同；保留空cache属性兼容server reset，但evaluate不读写缓存。',
 'functional_tradeoff':'移除缓存功能，重复请求重新执行原检索与判断，可能增加开销，不声称保留缓存性能。',
 'unchanged':'全库top-k后scope过滤、固定draft、ID有效即supported的逻辑保留。'})
data=load(source/'data.json');cases={c['id']:c for c in data['cases']}
def frame(cid,corpus=None,draft=None):
    c=cases[cid]
    return {'fixture_case':cid,'request':copy.deepcopy(c['request']),'corpus':copy.deepcopy(data['corpus'] if corpus is None else corpus),'draft':copy.deepcopy(c['draft'] if draft is None else draft),'draft_origin':'original_synthetic_fixture' if draft is None else 'explicit_self_constructed_boundary_fixed_draft'}
def expected_blocks(f):
    request=f['request'];terms=set(request['query'].strip().lower().split())
    scope=[b for b in f['corpus'] if b['doc_id'] in request['doc_ids'] and b['snapshot']==request['snapshot']]
    scope.sort(key=lambda b:(-len(terms & set(b['tags'])),b['id']))
    return [b for b in scope if terms & set(b['tags'])][:request['k']]
shuffled=copy.deepcopy(data['corpus']);random.Random(20261013).shuffle(shuffled)
assert shuffled!=data['corpus'] and sorted(shuffled,key=lambda b:b['id'])==sorted(data['corpus'],key=lambda b:b['id'])
mapping={b['id']:'block%03d'%(101+i) for i,b in enumerate(sorted(data['corpus'],key=lambda b:b['id']))}
remapped=copy.deepcopy(data['corpus'])
for b in remapped:b['id']=mapping[b['id']]
def mapped_frame(cid):
    draft=copy.deepcopy(cases[cid]['draft']);draft['citations']=[mapping[i] for i in draft['citations']]
    f=frame(cid,remapped,draft);f['draft_origin']='equivalent_id_remapping_of_original_fixture';return f
changed_draft=copy.deepcopy(cases['R01']['draft']);changed_draft['answer']='第一版客户端请求超时阈值为30秒。'
changed_corpus=copy.deepcopy(data['corpus']);target_id=expected_blocks(frame('R01'))[0]['id']
next(b for b in changed_corpus if b['id']==target_id)['text']+=' 本页补记：请求阈值单位为秒。'
scenarios=[
 {'name':'switch_snapshot','frames':[frame('R01'),frame('R02')],'cold_reference':frame('R02'),'prediction':'修复后目标结果与冷R02一致，不复用v1；原Engine可能返回旧缓存。'},
 {'name':'switch_document','frames':[frame('R01'),frame('R03')],'cold_reference':frame('R03'),'prediction':'修复后不返回alpha旧缓存且与冷beta一致；beta冷漏证预计仍存在，不能算完整正确。'},
 {'name':'normal_cold','frames':[frame('R05')],'prediction':'原/修复冷请求内容、范围、定位与结构相同，期望取到范围内元数据证据。'},
 {'name':'normal_repeat','frames':[frame('R01'),frame('R01')],'prediction':'同范围重复内容保持一致；修复每次cache_hit=false，不能称缓存命中。request_id唯一。'},
 {'name':'equivalent_corpus_order','frames':[frame('R01',shuffled),frame('R02',shuffled)],'prediction':'只打乱corpus顺序，固定id并列规则；修复目标内容等价于原始顺序的修复R02。'},
 {'name':'equivalent_block_ids','frames':[mapped_frame('R01'),mapped_frame('R02')],'mapping':mapping,'prediction':'同步改块ID及draft引用；保留字典序以免改变并列规则，逆映射后修复结果与原ID修复R02一致。'},
 {'name':'boundary_draft_changed','frames':[frame('R01'),frame('R01',draft=changed_draft)],'prediction':'只变同scope固定draft的答案表述；修复使用新draft，原Engine可能复用旧响应。不是替换主故障draft凑通过。'},
 {'name':'boundary_corpus_changed','frames':[frame('R01'),frame('R01',changed_corpus)],'prediction':'只更新同query/scope的证据正文；修复返回新原文，原Engine可能返回旧证据正文。draft不变。'}]
planned=sum((len(s['frames'])+(1 if 'cold_reference' in s else 0))*2 for s in scenarios)
assert planned==34
save('02-validation-plan.json',{'planned_at':now(),'code_base_commit':head,'original_sha256':sha(source/'challenge.py'),'fixed_sha256':sha(source/'no_cache_engine.py'),
 'data_sha256':sha(source/'data.json'),'run_kind':'offline_replay','model_generations':0,'planned_engine_evaluations':planned,
 'main_success':'修复Engine暖目标响应与同输入冷响应一致，不复用历史不同范围/快照缓存；不把beta冷漏证算完整回答正确。',
 'separate_metrics':['history_independent/cache_pollution_eliminated','evidence_retrieval_success','current_draft_used','evidence_matches_current_corpus','request_id_unique','evidence_in_scope','locator_consistent_with_actual_evidence','response_structure'],
 'normal_regressions':'冷请求R05、同范围重复R01；比较非时间/非request_id/非cache_hit字段，缓存功能已移除。',
 'equivalence_justification':'资料列表置换不改变query/tags/id并列规则；块ID重映射保持字典序且同步draft引用，证据正文、scope及语义关系不变。',
 'boundaries':'draft-only与corpus-text-only各一次单因素变更，保留完整初始/变更输入，不改题包data.json。',
 'execution_order':'按scenarios顺序，每个场景先原Engine再修复Engine；各场景独立实例，帧内保留状态；前两个场景另用新实例测冷参考。',
 'scenarios':scenarios,'stop_rule':'执行异常或原件/代码哈希变化保存后停止；普通判据失败保留并继续已定场景，不追加修复或临时重试。',
 'known_limitations':['beta范围内漏证由未修检索逻辑造成，预期保留。','supported仍只是旧ID判断，不能充当独立语义验证。','离线固定draft不是模型输出，耗时不与基础模型比较，不声称保留缓存性能。','HTTP/UI闭环本轮未验证。']})
print('VALIDATION PLAN SAVED',now(),'planned=',planned,flush=True)
sys.path.insert(0,str(source))
from challenge import Engine as Original
from no_cache_engine import Engine as Fixed
assert inspect.signature(Original.evaluate)==inspect.signature(Fixed.evaluate)
def stable(response):return {k:copy.deepcopy(v) for k,v in response.items() if k not in ['request_id','elapsed_ms','cache_hit']}
records=[];summary=[];groups={};failure=False
def evaluate(cls,f,scenario,variant,role):
    index=len(records)+1
    r={'order':index,'recorded_at':now(),'scenario':scenario,'variant':variant,'role':role,'run_kind':'offline_replay','model_generated':False,
      'code_base_commit':head,'engine_sha256':sha(source/('challenge.py' if variant=='original' else 'no_cache_engine.py')),
      'input':copy.deepcopy(f),'input_sha256':digest(f),'cache_before':copy.deepcopy(cls.cache)}
    request=copy.deepcopy(f['request']);corpus=copy.deepcopy(f['corpus']);draft=copy.deepcopy(f['draft']);before=copy.deepcopy((request,corpus,draft))
    try:
        assert sha(source/'challenge.py')==sha(folder/'original-engine.py') and sha(source/'no_cache_engine.py')==sha(folder/'no-cache-engine.py')
        start=time.perf_counter();response=cls.evaluate(request,corpus,draft);elapsed=(time.perf_counter()-start)*1000
        assert (request,corpus,draft)==before
        expected=expected_blocks(f);actual=response['evidence'];visible={b['id'] for b in actual}
        valid=bool(response['citations']) and set(response['citations']).issubset(visible)
        r.update(response=copy.deepcopy(response),client_function_elapsed_ms=elapsed,cache_after=copy.deepcopy(cls.cache),status='completed',
          checks={'response_structure':set(response)=={'answer','citations','evidence','locator_status','support_status','judgment_source','status','request_id','request','cache_hit','elapsed_ms','run_kind'},
          'evidence_in_scope':all(b['doc_id'] in request['doc_ids'] and b['snapshot']==request['snapshot'] for b in actual),
          'evidence_retrieval_success':actual==expected,'expected_evidence_ids':[b['id'] for b in expected],
          'current_draft_used':response['answer']==draft['answer'] and response['citations']==draft['citations'],
          'evidence_matches_current_corpus':all(b in corpus for b in actual),
          'locator_consistent_with_actual_evidence':response['locator_status']==('valid' if valid else 'invalid'),
          'locator_valid':valid,'request_echo_matches':response['request']==request,'fixed_cache_disabled':variant!='fixed' or (not response['cache_hit'] and cls.cache=={}),
          'semantic_support_independently_checked':False})
    except Exception as e:r.update(status='execution_error',error=type(e).__name__,detail=str(e))
    save('03-run-%02d.json'%index,r);records.append(r)
    if r['status']!='completed':raise RuntimeError('离线执行错误，已保存；停止')
    return r
try:
    for scenario in scenarios:
        name=scenario['name'];groups[name]={}
        for variant,engine_class in [('original',Original),('fixed',Fixed)]:
            engine=engine_class();warm=[]
            for i,f in enumerate(scenario['frames']):warm.append(evaluate(engine,f,name,variant,'frame_%d'%(i+1)))
            cold=evaluate(engine_class(),scenario['cold_reference'],name,variant,'cold_reference') if 'cold_reference' in scenario else None
            groups[name][variant]={'frames':warm,'cold':cold}
        b=groups[name]['original']['frames'][-1];p=groups[name]['fixed']['frames'][-1]
        item={'scenario':name,'original_target_order':b['order'],'fixed_target_order':p['order'],'original_answer':b['response']['answer'],'fixed_answer':p['response']['answer'],
          'original_cache_hit':b['response']['cache_hit'],'fixed_cache_hit':p['response']['cache_hit'],
          'original_evidence_ids':[x['id'] for x in b['response']['evidence']],'fixed_evidence_ids':[x['id'] for x in p['response']['evidence']],
          'original_retrieval_success':b['checks']['evidence_retrieval_success'],'fixed_retrieval_success':p['checks']['evidence_retrieval_success'],
          'fixed_checks':p['checks'],'prediction':scenario['prediction']}
        if name.startswith('switch_'):
            cold=groups[name]['fixed']['cold']
            item['cache_pollution_eliminated']=stable(p['response'])==stable(cold['response']) and p['checks']['evidence_in_scope'] and not p['response']['cache_hit']
            item['original_history_independent']=stable(b['response'])==stable(groups[name]['original']['cold']['response'])
            item['full_answer_verified']=False if name=='switch_document' else 'not_checked_semantically'
        elif name=='normal_cold':item['regression_passed']=stable(b['response'])==stable(p['response']) and p['checks']['evidence_retrieval_success']
        elif name=='normal_repeat':
            first=groups[name]['fixed']['frames'][0]
            item['regression_passed']=stable(first['response'])==stable(p['response'])==stable(b['response']) and first['response']['request_id']!=p['response']['request_id'] and not p['response']['cache_hit']
        elif name=='equivalent_corpus_order':
            reference=groups['switch_snapshot']['fixed']['cold']['response']
            item['equivalent_passed']=stable(p['response'])==stable(reference)
        elif name=='equivalent_block_ids':
            inverted={v:k for k,v in mapping.items()};response=stable(p['response'])
            response['citations']=[inverted[i] for i in response['citations']]
            for block in response['evidence']:block['id']=inverted[block['id']]
            item['equivalent_passed']=response==stable(groups['switch_snapshot']['fixed']['cold']['response'])
        else:item['boundary_passed']=p['checks']['current_draft_used'] and p['checks']['evidence_matches_current_corpus'] and p['checks']['fixed_cache_disabled']
        save('04-'+name+'.json',item);summary.append(item)
        print('SCENARIO',name,'fixed_retrieval=',item['fixed_retrieval_success'],'verdict=',{k:v for k,v in item.items() if k in ['cache_pollution_eliminated','regression_passed','equivalent_passed','boundary_passed']},flush=True)
except Exception as error:failure=True;save('execution-failure.json',{'recorded_at':now(),'error':type(error).__name__,'detail':str(error),'completed_evaluations':len(records)})
ids=[r['response']['request_id'] for r in records if 'response' in r]
assert len(ids)==len(set(ids))
assert all(sha(repo/n)==v for n,v in protected.items())
save('05-summary.json',{'completed_at':now(),'planned_evaluations':34,'executed_evaluations':len(records),'stopped_on_error':failure,'unique_request_ids':len(ids),'scenarios':summary,
 'cache_fix_scope':'只移除缓存；保留空cache属性兼容reset，每个请求重新执行原逻辑。','remaining_failures':['beta冷请求仍漏证；与冷请求一致不是完整回答成功。','ID有效仍被原逻辑标supported，语义未修。','未知范围和页面闭环本轮未实现。'],
 'timing_limit':'只记录原Engine和修复Engine的离线函数时间，不与基础模型比较；移除缓存可能增加重复请求开销，不声称保留缓存性能。',
 'model_generations':0,'base_generation_count_unchanged':124})
save('06-index.json',{'recorded_at':now(),'items':[{'order':r['order'],'scenario':r['scenario'],'variant':r['variant'],'role':r['role'],'request_id':r.get('response',{}).get('request_id'),'path':(folder/('03-run-%02d.json'%r['order'])).relative_to(repo).as_posix()} for r in records]})
save('07-audit.json',{'checked_at':now(),'protected_unchanged':len(protected),'original_engine_unchanged':True,'base_code_and_records_unchanged':True,'original_signature_preserved':True,'only_cache_logic_changed':True,'new_model_calls':0})
files=[p.relative_to(repo).as_posix() for p in sorted(folder.glob('*')) if p.is_file()]+['进阶/challenge_b/no_cache_engine.py',(folder/'08-files.json').relative_to(repo).as_posix()]
save('08-files.json',{'new_files':files,'modified_existing_files':[]})
print('FINAL',json.dumps({'folder':folder.relative_to(repo).as_posix(),'evaluations':len(records),'stopped':failure,'new_files':len(files),'protected':len(protected)},ensure_ascii=False))
