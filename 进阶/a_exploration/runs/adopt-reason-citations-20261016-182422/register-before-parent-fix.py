"""登记当前本人决定并复用离线检查；不启动服务或调用模型。"""
from pathlib import Path
import sys,json,copy,ast,difflib,shutil
from datetime import datetime
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
from engine import answer_messages
from sentence_selection import adapt_messages,build_index,schema,expand,CANDIDATE_PROMPT,offline_checks as sentence_checks
from compact_factorial import compact_messages,audit,offline_checks as compact_checks
from reason_citations import adapt,NOTE
from thinking_modes import offline_checks as thinking_checks
from sentence_interface import offline_checks as interface_checks
from audited_health import offline_checks as health_checks
from checks_extended import run as old_checks

source=HERE/'runs/reason-citations-resume-20261016-181123';plan=load(source/'intervention-plan.json');review=load(source/'review.json')
resume='--resume' in sys.argv
out=Path(Path('a-reason-choice-out.txt').read_text(encoding='utf-8').strip()) if resume else HERE/'runs'/('adopt-reason-citations-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
if not resume:out.mkdir();Path('a-reason-choice-out.txt').write_text(str(out),encoding='utf-8')
protected={p.relative_to(ROOT).as_posix():sha(p) for p in HERE.rglob('*') if p.is_file() and out not in p.parents and not {'slot-cache','__pycache__'}&set(p.parts)}
for n in ['README.md','report.md','decisions.md','declaration.md','基础/开发记录.md','基础/starter/student.py','进阶/challenge_b/challenge.py','进阶/challenge_b/no_cache_engine.py']:protected[n]=sha(ROOT/n)
if resume:protected=load(out/'protected-before.json')
else:write(out/'protected-before.json',protected)
decision={'at':now(),'source':'本人本轮明确决定','status':'current_development_choice_not_formal_freeze','decision':'采用紧凑输入＋开启思考＋句子选择＋理由／引用提示候选，统一作为后续开发版本。','post_hoc_priority_adjustment':True,'reason':'上一轮候选严格成功1/3，高于旧流程0/3；标签正确均1/3。本人接受AD02标签退步的代价，本次优先选择严格成功较高的整体方案。','prior_non_adoption_preserved':(source/'review.json').relative_to(ROOT).as_posix(),'prior_review_sha256':sha(source/'review.json'),'does_not_overwrite_prior_rule_or_evaluation':True,'does_not_claim全面更好':True,'tradeoffs':['AD01标签及严格成功改善。','AD02已有正确标签退步，引用支持失败；该代价由本人明确接受。','AD03仍错且出现无关引用，缺少S08直接依据边界保留。','候选三题客户端总耗时64.057秒，高于旧流程61.946秒。'],'future_selection_rules':'本次为事后选择，不追溯改写上轮标准；后续实验取舍需在各轮开始前另行登记。','unexecuted_disagreement_review':'按本轮指令取消，不启动或补跑。','scope':'三道开发题固定自动检索证据重放；尚非新端到端成绩或七题评测。','model_generation_baseline':621,'new_generations':0,'no_per_task_version_selection':True}
if not (out/'decision.json').exists():write(out/'decision.json',decision)

hash_checks=[]
for path,h in plan['code_hashes'].items():
    actual=sha(ROOT/path);hash_checks.append({'path':path,'expected':h,'actual':actual,'matches':actual==h});assert actual==h,path
model=Path(plan['service_arguments'][plan['service_arguments'].index('-m')+1]);executable=Path(plan['service_arguments'][0]);assert sha(model)==plan['model_hash'] and sha(executable)==plan['executable_hash']
for path,h in plan['data_hashes'].items():assert sha(ROOT/path)==h,path
checks={'health':health_checks(),'compact':compact_checks(),'thinking':thinking_checks(),'sentence':sentence_checks(),'interface':interface_checks(),'existing':old_checks(out/'offline-recheck' if resume else out)};assert all(x['passed'] for x in checks.values())
write(out/'offline-checks.json',{'at':now(),'passed':True,'groups':checks,'count':sum(x.get('count',len(x.get('checks',[]))) for x in checks.values()),'no_network':True,'generation_calls':0,'limits':'已有程序、接口及自造定义检查，不是语义正确率或新原生Schema服务验证。'})

xs=load(source/'diagnostic-inputs.json');entries=[load(p) for p in sorted(source.glob('item-*.json'))];resolved=[];wiring=[]
for x in xs:
    idx=build_index(x['blocks'],x['doc_ids'],x['snapshot']);assert idx==x['sentence_index']
    original=adapt_messages(answer_messages(x['claim'],x['blocks']),idx)
    compact=compact_messages(original,x['blocks'],idx,x['doc_ids'],x['snapshot']);selected=adapt(compact)
    assert compact==x['messages']['original'] and selected==x['messages']['revised']
    assert selected[0]['content']==CANDIDATE_PROMPT+NOTE and selected[1:]==compact[1:]
    assert audit(selected,x['blocks'],idx,x['doc_ids'],x['snapshot'])['passed']
    config=copy.deepcopy(x['configs']['revised']);assert config==x['configs']['original']
    assert config['parameters']['response_format']['json_schema']['schema']==schema(idx)
    assert config['parameters']['chat_template_kwargs']=={'enable_thinking':True} and config['parameters']['max_tokens']==1024
    e=next(e for e in entries if e['id']==x['id'] and e['variant']=='revised');raw=load(source/e['raw_record']);assert raw['messages']==selected and raw['config']==config
    body={'model':config['model'],'messages':selected,'stream':False,**config['parameters']};assert body==raw['actual_http_request_body'] and json.dumps(body,ensure_ascii=False)==raw['actual_http_request_raw']
    observation=load(source/f'mode-observation-{entries.index(e)+1:02}.json');assert all(observation['verified'].values())
    expansion=expand(raw['content'],x['blocks'],idx,x['doc_ids'],x['snapshot']);assert expansion==load(source/f'expansion-{entries.index(e)+1:02}.json')
    f=out/'resolved-configs'/f'{x["id"]}.json';write(f,config)
    resolved.append({'fixture_id':x['id'],'path':f.relative_to(ROOT).as_posix(),'sha256':sha(f),'source_run_id':raw['run_id'],'source_record':(source/e['raw_record']).relative_to(ROOT).as_posix(),'note':'开发请求的完整已解析Schema配置，仅用于核对；通用入口按当前句子索引派生enum，不按题号选版本。'})
    wiring.append({'fixture_id':x['id'],'messages_equal_saved_real_request':True,'system_only_append':True,'user_unchanged':True,'config_equal_saved_real_request':True,'schema_equal_current_index':True,'actual_slot_checks_passed_historically':True,'expansion_equal_historical':True,'byte_reconstruction':True,'support_status':'not_checked','new_model_request':False})

config_base=copy.deepcopy(xs[0]['configs']['revised']);config_base['parameters'].pop('response_format')
for x in xs:
    other=copy.deepcopy(x['configs']['revised']);other['parameters'].pop('response_format');assert other==config_base
schema_base=schema([])
configuration={'at':now(),'status':'personally_selected_development_configuration_not_new_formal_freeze','scope':'共同判断流程；不改查询转换、TF-IDF或同章节邻段方法。','entry':{'prompt_adapter':'进阶/a_exploration/reason_citations.py::adapt','message_pipeline':['进阶/a_exploration/engine.py::answer_messages','进阶/a_exploration/sentence_selection.py::adapt_messages','进阶/a_exploration/compact_factorial.py::compact_messages','进阶/a_exploration/reason_citations.py::adapt'],'schema_factory':'进阶/a_exploration/sentence_selection.py::schema','expansion':'进阶/a_exploration/sentence_selection.py::expand','audited_generation':'进阶/a_exploration/thinking_modes.py::ThinkingEngine，生成继承runtime.Engine.generate','verified_comparison_runner':'进阶/a_exploration/diagnose_reason_citations_resume.py','runner_warning':'上述运行器仍为两侧对照工具，不能当作只执行当前候选的单侧端到端启动命令；本轮仅登记和核对，没有创建或启动新运行器。'},'request_common':config_base,'response_format_factory':{'type':'json_schema','json_schema':{'schema_factory':'sentence_selection.schema(current_sentence_index)'},'structure_when_empty':schema_base,'dynamic_rule':'有句子时sentence_ids.items.enum为当前实际句子索引全部ID；无句子时maxItems=0。不使用题号或开发答案构造enum。','complete_resolved_development_configs':resolved},'system':CANDIDATE_PROMPT+NOTE,'system_utf8_sha256':__import__('hashlib').sha256((CANDIDATE_PROMPT+NOTE).encode('utf-8')).hexdigest(),'input_organization':'紧凑输入，完整原文由句子片段逐字节重建，claim在证据之后且只出现一次。','thinking':'请求chat_template_kwargs.enable_thinking=true；服务reasoning=on；1024总预算含思考及最终输出。','service_arguments':plan['service_arguments'],'service_limits':{'context':4096,'parallel':1,'threads':4,'batch':128,'ubatch':64,'cpu_only':True,'context_shift':False,'warmup':False,'repeat_penalty':1.0,'default_predict':256,'request_max_tokens_overrides_default':1024,'load_available_GiB_min':2,'runtime_available_GiB_min':1,'low_sample_stop':'连续3个2秒样本低于1GiB，仅停止自有PID'},'code_hashes':plan['code_hashes'],'model':{'path':str(model),'sha256':plan['model_hash']},'executable':{'path':str(executable),'sha256':plan['executable_hash']},'data_hashes':plan['data_hashes'],'same_configuration_for_all_current_inputs':True,'not_new_generation':True}
write(out/'configuration.json',configuration);(out/'system.txt').write_text(CANDIDATE_PROMPT+NOTE,encoding='utf-8',newline='')
write(out/'wiring-checks.json',{'at':now(),'passed':True,'rows':wiring,'code_hash_checks':hash_checks,'model_and_executable_hashes_match':True,'data_hashes_match':True,'schema_note':'仅enum按当前索引变化，不改结构/标签定义；本轮未启动原生服务。','all_three_use_same_candidate':True})
(out/'prompt.diff').write_text(''.join(difflib.unified_diff((CANDIDATE_PROMPT+'\n').splitlines(True),(CANDIDATE_PROMPT+NOTE+'\n').splitlines(True),fromfile='previous-system',tofile='selected-system')),encoding='utf-8')

allruns=[]
for p in (HERE/'runs').rglob('run-*.json'):
    r=load(p)
    if r.get('generation_dispatched') and (r.get('usage') or {}).get('completion_tokens',0)>0:allruns.append({'path':p.relative_to(ROOT).as_posix(),'run_id':r['run_id']})
assert len(allruns)==len({r['run_id'] for r in allruns})==87
changed=[p for p,h in protected.items() if sha(ROOT/p)!=h];assert not changed,changed
write(out/'completion-audit.json',{'at':now(),'protected_files_unchanged':len(protected),'changed':changed,'new_generations':0,'A_unique_generations':87,'cumulative':621,'A_run_ids':allruns,'old_evaluations_unchanged':True,'runtime_code_modified':False,'model_service_started':False,'AT_read':False,'no_git_mutation':True})
shutil.copy2(__file__,out/Path(__file__).name)
files=[out/'decision.json',out/'configuration.json',out/'system.txt',*sorted((out/'resolved-configs').glob('*.json'))];diff=''
for p in files:diff+=''.join(difflib.unified_diff([],p.read_text(encoding='utf-8').splitlines(True),fromfile='/dev/null',tofile='b/'+p.relative_to(ROOT).as_posix()))
(out/'registration.diff').write_text(diff,encoding='utf-8')
write(out/'file-manifest.json',{'at':now(),'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.rglob('*') if p.is_file()],'self_excluded':True,'runtime_code_diff':'empty，未修改已有运行代码；prompt.diff展示所选候选相对旧提示的原有追加文字，非本轮再次修改。'})
print(json.dumps({'out':str(out),'checks':85,'code_hashes_matched':len(hash_checks),'protected_unchanged':len(protected),'new_generations':0,'cumulative':621,'entry':configuration['entry'],'resolved_configs':resolved},ensure_ascii=False,indent=2))
