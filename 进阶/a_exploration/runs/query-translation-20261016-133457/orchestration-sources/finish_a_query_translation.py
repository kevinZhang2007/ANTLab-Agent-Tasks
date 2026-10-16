from pathlib import Path
import sys,json,shutil,difflib,subprocess,socket
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
from engine import Corpus,retrieve,neighbors,terms,public
out=Path(Path('a-query-translation-out.txt').read_text(encoding='utf-8').strip());phase=out/'automatic-translations'
runtime=load(phase/'runtime.json');assert runtime['confirmed_generations']==runtime['dispatches']==3 and runtime['model_stopped'] and 'error' not in runtime
prior=load(out/'offline-retrieval-replay.json');prior_audit=load(out/'offline-gate-review.json');corpus=Corpus(load(ROOT/'进阶/materials/sections.json'))
required={x['id']:x['scores']['old_keywords']['improved']['required_blocks'] for x in prior_audit['rows']}
fidelity={
 'AD01':{'fully_faithful':'partial','direction_preserved':True,'basis':'cannot be avoided、as long as及no record required保留了条件、充分性和否定。data files被泛化为file；manual modifications未明确数据对象，记录对象仍为modification object，具体对象有遗漏，不能称逐项完全忠实。','alignment':[{'zh':'手工修改或移动数据文件','actual_en':'manual modifications or file movement','assessment':'数据限定遗漏，操作大体保留'},{'zh':'确实无法避免时','actual_en':'cannot be avoided','assessment':'无法避免条件保留，确实语气略弱'},{'zh':'只要保存最终文件','actual_en':'as long as the final file is saved','assessment':'充分性方向保留'},{'zh':'无需记录修改对象和目的','actual_en':'no record of the modification object and purpose is required','assessment':'否定方向及两类记录内容保留'}]},
 'AD02':{'fully_faithful':False,'direction_preserved':False,'basis':'原文但仅此不足以让他人执行被译为but only this is sufficient...，把不充分反转为充分，门禁失败。不得因检索仍命中同段而忽略语义反转。','alignment':[{'zh':'可以帮助他人阅读','actual_en':'helps others read it','assessment':'可以被轻度强化为直接helps'},{'zh':'但仅此不足以让他人执行原计算','actual_en':'but only this is sufficient for them to perform the original calculation','assessment':'不足反转为sufficient；关键方向错误'}]},
 'AD03':{'fully_faithful':'partial','direction_preserved':True,'basis':'only、final image、after data conversion保留了主要对象与限制；原来这是一个满足建议的陈述，被改成only retain...to meet...的祈使/目的表达，并增加preserving措辞，不称完全忠实。没有把原主张改成反对只留图，但实际译文未复现人工理想译文的检索收益。','alignment':[{'zh':'绘图过程中做过数据转换时','actual_en':'When drawing ... after data conversion','assessment':'大体保留绘图与已转换条件'},{'zh':'只保留最终图片就满足作者关于图底层数据的建议','actual_en':"only retain the final image ... to meet the author's suggestion of preserving the underlying data",'assessment':'断言改为祈使/目的，增加preserving措辞；非逐项完整等价'}]}
}
rows=[];raws=[];md=['# 完整英文检索译文：自动验证停止记录','本轮仅三次翻译生成，未生成判断回答。译文不作事实证据，未人工修正。','Codex辅助对照复核，尚待本人确认。']
for n,f in enumerate(sorted(phase.glob('item-*.json')),1):
    entry=load(f);r=load(phase/entry['raw_record']);v=load(phase/f'validation-{n:02}.json');assert v['valid'];old=next(x for x in prior['rows'] if x['id']==entry['id']);query=v['translation'];scope=corpus.scope(old['doc_ids'],old['snapshot'])
    seeds,scores=retrieve(query,scope);improved,reasons=neighbors(seeds,scope);by_score={z['block_id']:z['score'] for z in scores};ranked=sorted(scope,key=lambda b:(-by_score[b['block_id']],b['heading'],b['text'],b['paragraph_index']))
    assert all(b['doc_id'] in old['doc_ids'] and b['snapshot']==old['snapshot'] for b in seeds+improved)
    assert len({b['block_id'] for b in improved})==len(improved)
    for link in reasons:
        seed=next(b for b in seeds if b['block_id']==link['seed']);neighbor=next(b for b in improved if b['block_id']==link['added'])
        assert (seed['doc_id'],seed['snapshot'],seed['section_id'])==(neighbor['doc_id'],neighbor['snapshot'],neighbor['section_id']) and abs(seed['paragraph_index']-neighbor['paragraph_index'])==1
    coverage={}
    for name,used in [('baseline',seeds),('improved',improved)]:coverage[name]={'required_blocks':required[entry['id']],'present_required':[b for b in required[entry['id']] if b in {z['block_id'] for z in used}],'complete':set(required[entry['id']])<={z['block_id'] for z in used}}
    row={'at':now(),'id':entry['id'],'claim':old['claim'],'old_query':old['old_query'],'manual_translation':old['manual_translation'],'actual_automatic_translation':query,'fidelity':fidelity[entry['id']],'translation_raw_record':(phase/entry['raw_record']).relative_to(ROOT).as_posix(),'translation_run_id':r['run_id'],'translation_raw_content':r['content'],'translation_seconds':r['elapsed_seconds'],'usage':r['usage'],'finish_reason':r['finish_reason'],'translation_input_tokens':r['input_tokens'],'truncated':r['truncated'],'query_tokens':terms(query),'full_ranking':[{'rank':i+1,'score':by_score[b['block_id']],**public(b)} for i,b in enumerate(ranked)],'baseline':[public(b) for b in seeds],'improved':[public(b) for b in improved],'neighbors':reasons,'coverage':coverage,'scope_and_section_boundaries':True,'no_manual_repair':True,'label_correct':'not_run','source_authenticity_of_model_selected_citations':'not_run','citation_support':'not_run','strict_success':'not_run','judgment_source':'unverified','reviewer':'Codex原文辅助复核，尚待本人确认'}
    rows.append(row);write(out/('automatic-retrieval-'+entry['id']+'.json'),row)
    raws.append({'id':entry['id'],'run_id':r['run_id'],'messages':r['messages'],'actual_http_request_raw':r['actual_http_request_raw'],'raw_response':r['raw_response'],'content':r['content'],'usage':r['usage'],'finish_reason':r['finish_reason'],'client_seconds':r['elapsed_seconds']})
    md+=['\n## '+entry['id'],'中文主张：'+old['claim'],'原始转换响应：','```json',r['content'],'```',fidelity[entry['id']]['basis'],'baseline：'+', '.join(b['block_id'] for b in seeds),'improved：'+', '.join(b['block_id'] for b in improved),f"翻译耗时 {r['elapsed_seconds']:.3f} 秒；后续回答未执行。"]
direction_fail=[r['id'] for r in rows if r['fidelity']['direction_preserved'] is False]
auto_improvements=[r['id'] for r in rows if not next(x for x in prior_audit['rows'] if x['id']==r['id'])['scores']['old_keywords']['improved']['complete'] and r['coverage']['improved']['complete']]
regressions=[r['id'] for r in rows if next(x for x in prior_audit['rows'] if x['id']==r['id'])['scores']['old_keywords']['improved']['complete'] and not r['coverage']['improved']['complete']]
assert direction_fail and not auto_improvements
decision={'at':now(),'allow_answers':False,'reason':'AD02关键否定/充分性反转，自动译文未通过忠实度门禁；此外AD03的指定核心段仅排第3，未进入top2或其同章节邻段，自动检索无必要覆盖改善。','direction_changed':direction_fail,'other_fidelity_omissions':['AD01数据文件限定泛化','AD03陈述改祈使/目的表达'],'manual_ideal_improvement':['AD03'],'actual_automatic_improvements':auto_improvements,'actual_automatic_regressions':regressions,'coverage_denominators':{'baseline':3,'improved':3},'coverage_counts':{'old_keywords_baseline':1,'old_keywords_improved':2,'manual_translation_baseline':2,'manual_translation_improved':3,'actual_automatic_baseline':1,'actual_automatic_improved':2},'answer_calls_executed':0,'answer_calls_not_executed':6,'answer_metrics':'not_run，不计为模型判断错误或成功。','not_adopted':True,'retained':'现有关键词转换、共同判断提示和句子选择机制保持不变。','limits':['人工译文提升仅支持理想译文条件下检索可能改善，不是自动成绩。','长译文也引入中间结果/模块化段；覆盖/干扰变化不能单独归于长度或某个关键词。','TF-IDF不验证逻辑方向，错误译文仍可命中同一段。','AD03原S09有相邻底层值论述，指定S08覆盖与其他可能的部分依据分开；本轮未用缺失S08补模型回答。'],'stop':'不追加搜索或生成；七道评测未读取。','new_generations':3,'cumulative':585,'A_used':51,'A_cap':90,'A_remaining':39,'cap_adjusted_by_user_before_execution':True,'technical_request_failures':0}
write(out/'automatic-translation-review.json',{'at':now(),'allow_answers':False,'rows':rows,'decision':decision})
write(out/'three-raw-translation-responses.json',{'at':now(),'count':3,'responses':raws,'fact_evidence':False})
write(out/'stopped-before-answers.json',decision)
(out/'translations-and-retrieval-review.md').write_text('\n\n'.join(md)+'\n\n'+json.dumps(decision,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
protected=load(out/'protected-before.json');changed=[p for p,h in protected.items() if sha(ROOT/p)!=h];assert not changed,changed
for p,h in load(phase/'intervention-plan.json')['code_hashes'].items():assert sha(ROOT/p)==h,p
generations=[]
for p in (HERE/'runs').rglob('run-*.json'):
    r=load(p)
    if r.get('generation_dispatched') and (r.get('usage') or {}).get('completion_tokens',0)>0:generations.append((p,r['run_id']))
assert len(generations)==len({rid for p,rid in generations})==51
with socket.socket() as sock:sock.settimeout(1);port_closed=sock.connect_ex(('127.0.0.1',8080))!=0
assert port_closed
git=r'C:\Users\86186\AppData\Local\Programs\Git\cmd\git.exe'
def g(*args):
    r=subprocess.run([git,'--no-optional-locks','-c','core.quotepath=false',*args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8');return {'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
resources={'load_seconds':runtime['load_seconds'],'before_GiB':runtime['memory_before']['available_bytes']/2**30,'after_load_GiB':runtime['memory_after_load']['available_bytes']/2**30,'minimum_sampled_GiB':min(x['available_bytes'] for x in runtime['memory_samples'])/2**30,'after_stop_GiB':runtime['memory_after_stop']['available_bytes']/2**30,'model_stopped':runtime['model_stopped'],'port8080_closed':port_closed}
write(out/'completion-audit.json',{'at':now(),'old_files_checked':len(protected),'changed':changed,'actual_code_hashes_match_plan':True,'A_unique_generation_count':51,'A_run_ids':[{'path':p.relative_to(ROOT).as_posix(),'run_id':rid} for p,rid in generations],'new_generation_count':3,'baseline_cumulative':582,'cumulative':585,'A_cap':90,'A_remaining':39,'B_offline_replay_not_added':88,'resources':resources,'git_status':g('status','--short','--branch'),'git_diff_check':g('diff','--check'),'staged_diff':g('diff','--cached','--stat'),'AT_read':False,'answer_capacity':'not_checked：答案门禁未通过，不准备或执行回答','no_formal_freeze':True})
diff=''
for name in ['query_translation.py','diagnose_query_translation.py']:
    p=HERE/name;diff+=''.join(difflib.unified_diff([],p.read_text(encoding='utf-8').splitlines(keepends=True),fromfile='/dev/null',tofile='b/'+p.relative_to(ROOT).as_posix()))
(out/'complete-code.diff').write_text(diff,encoding='utf-8')
orch=out/'orchestration-sources';orch.mkdir()
for name in ['prepare_a_query_translation.py','resume_a_query_translation.py','prepare_a_query_automatic.py','finish_a_query_translation.py']:shutil.copy2(name,orch/name)
write(out/'file-manifest.json',{'at':now(),'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.rglob('*') if p.is_file() and not {'slot-cache','__pycache__'}&set(p.parts)],'new_runtime_files':['进阶/a_exploration/query_translation.py','进阶/a_exploration/diagnose_query_translation.py'],'manifest_self_excluded':True})
print(json.dumps({'decision':decision,'rows':[{'id':x['id'],'translation':x['actual_automatic_translation'],'fidelity':x['fidelity']['fully_faithful'],'seconds':x['translation_seconds'],'coverage':x['coverage']} for x in rows],'resources':resources,'old_files_unchanged':len(protected),'git_diff_check':g('diff','--check')},ensure_ascii=False,indent=2))
