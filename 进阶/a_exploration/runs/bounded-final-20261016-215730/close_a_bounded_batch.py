from pathlib import Path
import sys,json,copy,shutil,subprocess,socket,difflib,statistics
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
b=Path(Path('a-bounded-root.txt').read_text(encoding='utf-8').strip());freeze=load(b/'final-freeze.json');protected=load(b/'protected-before.json')
assert all(sha(ROOT/p)==h for p,h in freeze['code_hashes'].items());assert all(sha(ROOT/p)==h for p,h in freeze['data_hashes'].items());assert sha(b/'final-profile.json')==freeze['profile_sha256']
allruns=[];batchruns=[]
for p in (HERE/'runs').rglob('run-*.json'):
    x=load(p)
    if x.get('generation_dispatched') and (x.get('usage') or {}).get('completion_tokens',0)>0:
        row={'path':p.relative_to(ROOT).as_posix(),'run_id':x['run_id'],'stage':x['stage'],'usage':x['usage'],'finish_reason':x['finish_reason'],'truncated':x['truncated']};allruns.append(row)
        if b in p.parents:batchruns.append(row)
assert len(allruns)==len({x['run_id'] for x in allruns})==144
assert len(batchruns)==len({x['run_id'] for x in batchruns})==48
runtime_stages=['round1','round2','round3','round4','evaluation','variants','counterfactual'];runtime={n:load(b/n/'runtime.json') for n in runtime_stages}
assert all('error' not in x and x['model_stopped'] for x in runtime.values())
assert [runtime[n]['confirmed_generations'] for n in runtime_stages]==[6,3,3,6,21,6,3]
assert not any(x['finish_reason']=='length' or x['truncated'] is True for x in batchruns)
changes=[p for p,h in protected.items() if sha(ROOT/p)!=h];assert not changes,changes
ports={}
for port in [8080,8890]:
    with socket.socket() as s:s.settimeout(1);ports[str(port)]=s.connect_ex(('127.0.0.1',port))!=0
assert all(ports.values())
provider=ROOT/'基础/starter/provider.py';oldprovider=load(ROOT/'基础/runs/formal/round1/freeze.json')['code_hashes']['基础/starter/provider.py'];assert sha(provider)==oldprovider
write(b/'dependency-audit.json',{'at':now(),'A_code_46_hashes_match':True,'query_config_prebatch_hash':protected['进阶/a_exploration/config.json'],'query_config_now_sha256':sha(HERE/'config.json'),'query_config_unchanged':sha(HERE/'config.json')==protected['进阶/a_exploration/config.json'],'shared_provider_sha256':sha(provider),'shared_provider_matches_older_foundation_freeze':True,'older_provider_hash_source':'基础/runs/formal/round1/freeze.json','disclosure':'A冻结文件仅显式列A代码；共享传输provider的相同旧冻结哈希在此另存核对，不追溯改写A冻结。'})
write(b/'generation-ledger.json',{'at':now(),'baseline':630,'new':48,'cumulative':678,'A_before_batch':96,'A_now':144,'foundation_baseline':534,'B_offline_replays_unchanged':88,'per_stage':{n:x['confirmed_generations'] for n,x in runtime.items()},'round5_generations':0,'batch_max':60,'unused':12,'evaluation_validation_calls':30,'not_double_counted_as_old_reserved_30':True,'technical_retries':0,'unique_batch_run_ids':batchruns,'A_all_unique_run_ids':allruns})
reviews={n:load(b/n/'review.json') for n in ['round1','round2','round3','round4','evaluation','variants','counterfactual']}
old=load(HERE/'runs/current-e2e-20261016-183739/review-summary.json')
rounds=[{'round':1,'calls':6,'change':'对象保留查询＋0.75正文/0.25标题检索','strict':'0/3','labels':'0/3','adopt':False,'reason':'AD03检索补回但仍拒判，AD01丢失必要证据；回退查询和标题候选。'},{'round':2,'calls':3,'change':'直接依据/限定/背景区分与选句精简','strict':'0/3','labels':'1/3','adopt':False,'reason':'AD01退步，许可无关引用仍在。'},{'round':3,'calls':3,'change':'reason→sentence_ids→label及方向核对说明','strict':'1/3','labels':'2/3','adopt':'provisional_then_reverted','reason':'按improved指标先胜出；第4轮暴露baseline副作用。'},{'round':4,'calls':6,'change':'同一配置在三题两侧组合验证','strict':'baseline 0/3；improved 1/3','labels':'baseline 1/3；improved 2/3','adopt':False,'reason':'六输出严格1/6低于旧配置2/6；标签总数同3/6。事前未细化双侧聚合，已披露为保守收尾回退，不伪称预注册。'},{'round':5,'calls':0,'change':'ID/顺序/范围/句子展开与自造措辞检查','strict':'not_model_test','labels':'not_model_test','adopt':'retain','reason':'临时候选与最终回退配置分别13项机制＋35项既有检查；只验证程序，不证明模型语义鲁棒。'}]
write(b/'five-rounds-summary.json',{'at':now(),'rounds':rounds,'final_profile':'retained','search_stopped':True,'no_sixth_round':True,'deadline_start_compliance':True,'round5_note':'先在第4轮期间进行临时profile离线检查，回退后对最终profile重查；同一第5轮，均0生成。','old_full_development_results_source':'进阶/a_exploration/runs/current-e2e-20261016-183739/review-summary.json','do_not_mix':'最终保留方案的完整开发结果引用旧轮，不拿第3/4轮更好的单题拼接。'})
variant_summary={'at':now(),'dev_equivalence':{'source':'AD01','old_labels':['contradicted','contradicted'],'new_labels':['insufficient','supported'],'passed':False,'cause_not_isolated':'查询及检索证据随等义措辞变化，且判断方向仍错；不能只归因于模型语言或某一关键词。'},'eval_equivalence':{'source':'AT01','transform':'全部块ID一致重映射','old_labels':['insufficient','insufficient'],'new_labels':['insufficient','insufficient'],'label_invariant':True,'meaningful_nonempty_ID_test':False,'limitation':'两侧空检索，没有ID实际进入最终模型输入；不能写成已验证非空ID鲁棒。'},'counterfactual':{'source':'AD01','transform':'无需记录→仍应记录','expected':'supported','actual':['supported','supported'],'strict':[True,True],'scope':'完整流程，查询重新执行；原文条件和原始响应全部保存。'},'no_additional_calls_for_weak_variant':True}
write(b/'variants-and-counterfactual-summary.json',variant_summary)
write(b/'failure-diagnosis.json',{'at':now(),'observed':['AT01 query=fixed-seed-verification，原分词器把带连字符短语作为一个词，无词表命中，导致正确拒判但没有证据覆盖。','AT05跨章节合取需要P1文字→结果和P2推理记录，两个命中加同章节邻段仍漏P1必要部分。','AT03/AT06有反证却拒判或支持，暴露生成方向问题。','等义AD01改写改变查询和命中，端到端不稳定。'],'earlier_hypotheses':['检索遗漏导致不能判断','证据已存在但生成未正确组合或处理否定'],'distinguishing_evidence':'第1轮AD03进入完整绘图段仍拒判，表明检索遗漏不是全部解释；第4轮与主评测均保留证据足够但标签错误。只能说明并存，不能由思考文本证明内部因果机制。','repair_after_eval':False,'next_step_only':'未来可独立研究查询分词和跨章节必要证据覆盖；本批停止，不修评测错题。'})
snapshot=b/'frozen-code';snapshot.mkdir()
for name,h in freeze['code_hashes'].items():
    target=snapshot/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
target=snapshot/'基础/starter/provider.py';target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(provider,target)
diff=''
for p in [HERE/'bounded_candidate.py',HERE/'run_bounded_stage.py']:diff+=''.join(difflib.unified_diff([],p.read_text(encoding='utf-8').splitlines(True),fromfile='/dev/null',tofile='b/'+p.relative_to(ROOT).as_posix()))
(b/'complete-code.diff').write_text(diff,encoding='utf-8')
reproduce=b/'reproduce.py'
reproduce.write_text('''"""默认只准备新目录；--run才执行，将新增真实生成。"""
from pathlib import Path
import argparse,sys,copy,subprocess
SOURCE=Path(__file__).resolve().parent
ROOT=next(p for p in SOURCE.parents if (p/'进阶/a_exploration/runtime.py').is_file())
HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--stage',choices=['evaluation','variants','counterfactual'],default='evaluation');p.add_argument('--run',action='store_true');a=p.parse_args();out=a.out.resolve()
    if out.exists():raise ValueError('新输出目录必须不存在')
    freeze=load(SOURCE/'final-freeze.json')
    for n,h in {**freeze['code_hashes'],**freeze['data_hashes']}.items():
        if sha(ROOT/n)!=h:raise ValueError('冻结依赖改变：'+n)
    cfg=load(SOURCE/'configuration.json')
    for path,h in [(cfg['model']['path'],freeze['model_hash']),(cfg['executable']['path'],freeze['executable_hash'])]:
        if sha(Path(path))!=h:raise ValueError('本机模型或运行工具与冻结不符')
    out.mkdir(parents=True);write(out/'configuration.json',cfg);write(out/'final-freeze.json',freeze);write(out/'final-profile.json',freeze['profile'])
    stage=out/a.stage;stage.mkdir()
    for name in ['plan.json','tasks.json','profile.json','offline-checks.json']:write(stage/name,load(SOURCE/a.stage/name))
    write(out/'prepared-only.json',{'at':now(),'source':SOURCE.relative_to(ROOT).as_posix(),'stage':a.stage,'generations':0,'note':'复用相同代码及数据下的归档离线门禁；实际启动会重查内存、健康、阶段模板与容量。'})
    if a.run:subprocess.run([sys.executable,'-X','utf8','-B',str(HERE/'run_bounded_stage.py'),'--stage',str(stage)],check=True,cwd=ROOT)
    else:print('PREPARED_ONLY',stage)
if __name__=='__main__':main()
''',encoding='utf-8')
reproduce_record={'at':now(),'script':reproduce.relative_to(ROOT).as_posix(),'script_sha256':sha(reproduce),'default_generations':0,'run_evaluation_cap':21,'actual_engine':'BoundedEngine profile=retained，与CurrentEngine消息/检索/参数逐字节等价，见final-entry-equivalence.json。','page_entry':'进阶/a_exploration/prepare_current_run.py ＋ launch_current.py，复用已验证retained页面；本批未新增页面生成。','run_warning':'--run新增真实调用，只能用不存在的新目录；旧目录受保护。','environment':'本机Windows x64、Python 3.14.6、llama.cpp b11429；未验证全新机器、其他OS或多用户并发。'};write(b/'reproduction-entry.json',reproduce_record)
write(b/'completion-audit.json',{'at':now(),'batch_confirmed_unique_generations':48,'cumulative':678,'A_unique_generations':144,'protected_unchanged':len(protected),'changed':changes,'all_frozen_code_and_data_hashes_match':True,'all_model_services_stopped':True,'ports_closed':ports,'technical_failures':0,'technical_retries':0,'budget_exhausted':0,'truncated':False,'stage_runtime':{n:{'dispatches':x['dispatches'],'confirmed':x['confirmed_generations'],'stopped':x['model_stopped'],'min_available_GiB':min(m['available_bytes'] for m in x['memory_samples'])/2**30} for n,x in runtime.items()},'no_new_round_after_cutoff':True,'five_documents_unchanged':True,'foundation_B_unchanged':True})
facts=['# 供五份文档更新使用的事实包','记录时间：'+now()+'。仅事实整理，不是已批准文档正文。','本批五轮开发结束后停止优化，保留原关键词转换＋正文TF-IDF＋同章节邻段；共同判断为紧凑输入、开启思考、句子选择、理由/引用提示，1024预算。','唯一冻结时间：'+freeze['frozen_at']+'。代码/配置/模型/资料哈希见final-freeze.json；共享provider另与既有基础冻结核对一致，未改写旧冻结。','五轮新增6、3、3、6、0次，共18次。第1/2轮不采用；第3轮临时胜出，第4轮因baseline严格退步回退。双侧聚合细则事前未明确，记录为事后保守选择，不声称预注册。第5轮仅程序机制检查。','最终保留方案的完整开发结果来自current-e2e-20261016-183739：baseline标签2/3、严格1/3；improved标签1/3、严格1/3。本批第4轮属于另一被放弃配置：baseline标签1/3、严格0/3；improved标签2/3、严格1/3。两轮分开展示，不拼接。','冻结后七题主验证：baseline和improved标签均5/7（71.4%），严格均2/7（28.6%）；无官方答案，均为Codex原文辅助暂判，尚待本人确认。7道题为配对单位，不把14输出当14独立样本，不声称统计显著或泛化能力。','严格公式：格式完整、选择验证通过、标签正确、必要引用覆盖、引用支持、无无关引用。理由一致性、PDF区域定位另列；不是任务唯一官方评分标准。','七题输入必要覆盖均4/7；必要引用覆盖baseline2/7、improved4/7，但实际引用支持均2/7。引用来源真实的非空输出为4/7和5/7；空引用分别3和2，不算伪造，但不能因此算严格成功。','七题PDF引用区域全部可定位的输出为baseline4/7、improved4/7。没有框的片段保持absent/invalid，不伪造精确定位；来源真实、PDF定位和语义支持分开。','七题完整非流式回答HTTP时间总和：baseline109.528秒、improved176.731秒；包含查询和处理的逐侧组件和为119.066、186.312秒。共享查询只计7次，两侧成本各分摊50%，组件和不是两组独立计时。','AT02暂接受分层及processed-data共享句的组合支持，不要求固定末句；AT04同一pipeline检查上下文的冗余句暂不判无关。这些语义判断需本人确认，不写成独立人工或官方成绩。','两题等价变体新增6次：AD01改写后两侧错误，完整流程不稳健；AT01 ID映射标签相同但仍空检索，未实际测试非空ID引用，不能宣称ID模型鲁棒。反事实新增3次：无需记录→仍应记录，两侧supported且严格通过；只覆盖这个限定词变化。','本批新增48次：开发18＋主验证21＋等价6＋反事实3；累计678个生成run ID，A为144，基础既有534。B另88次offline_replay保持不变。60次上限未用12次，不继续补满。','没有请求技术失败、质量重试或预算耗尽；所有本轮自有模型服务已停止。不改基础/B、五份文档、首次结果或负面记录，不暂存提交推送。','主要未解决问题：连字符查询零匹配；跨章节合取证据漏检；否定/条件方向错误；无关或过多引文；理由错误归属；部分PDF词框匹配失败。冻结后不修评测错题。','仍需收尾：本人核对辅助评分及争议口径；聊天助手提供五份文档正文再审核落盘；A/B双提交及本地服务验收边界未获明确认可；全新环境与并发尚未实测。','入口和索引：final-freeze.json、five-rounds-summary.json、evaluation/review.json、variants/review.json、counterfactual/review.json、generation-ledger.json、reproduce.py、complete-code.diff。']
(b/'facts-for-documents.md').write_text('\n\n'.join(facts)+'\n',encoding='utf-8')
for name in ['prepare_a_bounded_batch.py','install_a_bounded_runner.py','prepare_bounded_stage.py','review_bounded_dev.py','bounded_round5_offline.py','freeze_a_bounded_final.py','save_a_evaluation_reference.py','review_a_frozen_pairs.py','close_a_bounded_batch.py']:
    shutil.copy2(name,b/name)
write(b/'file-manifest.json',{'at':now(),'new_runtime_files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in [HERE/'bounded_candidate.py',HERE/'run_bounded_stage.py']],'new_record_files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in b.rglob('*') if p.is_file() and not {'slot-cache','__pycache__'}&set(p.parts)],'self_excluded':True})
print(json.dumps({'new':48,'cumulative':678,'A_unique':144,'protected_unchanged':len(protected),'all_stopped':True,'record_files':len(load(b/'file-manifest.json')['new_record_files']),'reproducer':str(reproduce)},ensure_ascii=False))
