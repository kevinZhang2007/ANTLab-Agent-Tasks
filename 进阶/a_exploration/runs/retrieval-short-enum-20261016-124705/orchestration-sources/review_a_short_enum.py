from pathlib import Path
import sys,json,shutil,subprocess,difflib,math
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
from engine import Corpus,retrieve,neighbors,public,terms
from short_enum_candidate import QUERY_PROMPT,ANSWER_PROMPT,answer_schema
from common_judgment_candidate import validate_raw
out=Path(Path('a-round-out.txt').read_text().strip());rt=load(out/'runtime.json');assert rt['confirmed_generations']==9 and rt['model_stopped'] and rt['page_stopped']
records=sorted([load(p) for p in out.glob('http-*.json')],key=lambda x:x['task_id']);assert len(records)==3
refs={x['id']:x for x in load(ROOT/'进阶/materials/a_dev_answers.json')};old=HERE/'runs/development-20261016-115250';old_review=load(old/'review.json');old_map={(r['task_id'],r['variant']):r for r in old_review['rows']}
corpus=Corpus(load(ROOT/'进阶/materials/sections.json'));events=[json.loads(line) for line in (out/'events.jsonl').read_text(encoding='utf-8').splitlines()];rows=[];pairs=[];raw_rows=[];ids=[];md=['# 整体候选九条原始响应及复核','实际复核时间：'+now(),'仅三道开发题自动流程；Codex辅助原文复核，尚待本人确认。残缺JSON原样保留，不补字段或从前缀计标签成功。']
for h in records:
    pair=h['response'];tid=h['task_id'];scope=corpus.scope(pair['doc_ids'],pair['snapshot']);seeds,scores=retrieve(pair['retrieval_terms'],scope);expanded,trace=neighbors(seeds,scope)
    assert pair['seed_ids']==[b['block_id'] for b in seeds]
    scoremap={x['block_id']:x['score'] for x in scores};ranked=sorted(scope,key=lambda b:(-scoremap[b['block_id']],b['heading'],b['text'],b['paragraph_index']))
    q=pair['shared_query'];ids.append(q['run_id']);assert q['messages'][0]['content']==QUERY_PROMPT
    raw_rows.append({'id':tid,'variant':'shared_query','run_id':q['run_id'],'content':q['content'],'seconds':q['elapsed_seconds'],'usage':q['usage'],'finish_reason':q['finish_reason']})
    md+=['\n## '+tid+' 共享查询','```json',q['content'],'```',f'run ID: {q["run_id"]}；{q["elapsed_seconds"]:.3f}秒。']
    for variant in ['baseline','improved']:
        arm=pair['arms'][variant];r=arm['raw_record'];ids.append(r['run_id']);used=seeds if variant=='baseline' else expanded
        assert arm['actual_input_passages']==[public(b) for b in used] and r['actual_input_passages']==arm['actual_input_passages']
        assert r['messages'][0]['content']==ANSWER_PROMPT
        assert r['config']['parameters']['response_format']['json_schema']['schema']==answer_schema(used)
        val=validate_raw(r['content'],used);assert val==arm['source_validation'];parsed=val['parsed'] if val['format_complete'] else None
        correct=parsed['label']==refs[tid]['label'] if parsed else 'not_checked'
        if tid=='AD01':
            input_coverage=True;reason_consistent=False;necessary=False;support=False;unrelated=True
            basis='两侧都含完整P1-S03末句，要求人工操作不可避免时仍记录对象和目的。模型只据避免手工操作/保存程序版本来支持无需记录；后者无关。两个摘录确属对应原文，但不支持当前label。'
        elif tid=='AD02' and variant=='baseline':
            input_coverage='ambiguous';reason_consistent=True;necessary=False;support=False;unrelated=False
            basis='label与参考一致，理由大体保持有助阅读但不足执行。第一条quote来自实际P2-S10-p02，却标为P2-S01-p04；不能修ID后算通过。基线只有Read与概览，Read也提依赖清单/重建环境，是否单段已足够支持全部运行限制有解释边界，输入覆盖单列待确认，不按固定ID强制缺证。'
        elif tid=='AD02':
            input_coverage=True;reason_consistent='not_checked';necessary='not_checked';support='not_checked';unrelated='not_checked'
            basis='补邻段取得明确执行依赖(P2-S01-p03)及Run完整原文；但输出256 token耗尽，第三个evidence后未闭合。不得抽取supported前缀判答案成功。片段还把Store与Use等改写成原句，局部风险另记，不冒充完整字段评价。'
        else:
            input_coverage=False;reason_consistent='not_checked';necessary='not_checked';support='not_checked';unrelated='not_checked'
            basis='新查询仍未出现plot/plotting等具体对象，只有data/conversion/final/image及author\'s recommendation；必要图数据章节仍未命中，无同章节邻段。两侧请求及原始输出相同，均在第二个quote中途耗尽256预算，完整语义字段not_checked。可见前缀仍用程序版本/层次输出解释只存图，不能用不可见图数据原文补证。'
        quote_locations=[]
        if parsed:
            for e in parsed['evidence']:
                quote_locations.append({'reported_id':e['block_id'],'quote':e['quote'],'continuous_in_reported_block':any(b['block_id']==e['block_id'] and e['quote'] in b['text'] for b in used),'other_actual_input_ids_containing_exact_quote':[b['block_id'] for b in used if b['block_id']!=e['block_id'] and e['quote'] in b['text']]})
        row={'id':tid,'variant':variant,'request_id':arm['main_task_id'],'pair_request_id':pair['request_id'],'run_id':r['run_id'],'raw_content':r['content'],'parsed':parsed,'format_complete':val['format_complete'],'public_reference_label':refs[tid]['label'],'label_correct':correct,'necessary_input_coverage':input_coverage,'reason_label_consistent':reason_consistent,'id_membership':val['id_membership_check'],'continuous_quotes':val['continuous_quote_checks'],'quoted_source_audit':quote_locations,'quote_authenticity_all':all(c['quote_continuous_original'] for c in val['continuous_quote_checks']) if parsed else 'not_checked','necessary_citation_coverage':necessary,'citation_support':support,'has_unrelated_citations':unrelated,'strict_complete_success':False,'review_basis':basis,'client_seconds':r['elapsed_seconds'],'stage_wall_seconds':arm['answer_stage_wall_seconds'],'allocated_total_seconds':arm['allocated_total_seconds'],'usage':r['usage'],'input_tokens':r['input_tokens'],'finish_reason':r['finish_reason'],'truncated':r['truncated'],'old_result':{k:old_map[(tid,variant)][k] for k in ['actual_label','format_complete','answer_correct','strict_complete_success','necessary_input_coverage']},'reviewer':'Codex原文辅助复核，尚待本人确认'}
        rows.append(row);raw_rows.append({'id':tid,'variant':variant,'run_id':r['run_id'],'content':r['content'],'seconds':r['elapsed_seconds'],'usage':r['usage'],'finish_reason':r['finish_reason']})
        md+=['\n### '+variant+' 原始content','```text',r['content'],'```',basis,f'run ID: {r["run_id"]}；客户端{r["elapsed_seconds"]:.3f}秒；结束{r["finish_reason"]}。']
        assert any(e.get('run_id')==r['run_id'] and e.get('request_id')==arm['main_task_id'] and e['event']=='model_response' for e in events)
    pairs.append({'id':tid,'pair_request_id':pair['request_id'],'query_run_id':q['run_id'],'query_terms':pair['retrieval_terms'],'query_tokens':terms(pair['retrieval_terms']),'seed_ids':pair['seed_ids'],'ranked':[{'rank':i+1,'block_id':b['block_id'],'section':b['section_id'],'score':scoremap[b['block_id']],'reference_section_audit_only':b['section_id'] in refs[tid]['evidence_sections']} for i,b in enumerate(ranked)],'added_trace':trace,'same_actual_request':pair['arms']['baseline']['raw_record']['actual_http_request_body']==pair['arms']['improved']['raw_record']['actual_http_request_body'],'pair_elapsed_seconds':pair['pair_elapsed_seconds'],'query_seconds':q['elapsed_seconds'],'query_cost_share_each':.5})
assert len(ids)==len(set(ids))==9
groups={}
for v in ['baseline','improved']:
    rs=[r for r in rows if r['variant']==v];groups[v]={'denominator':3,'definite_input_coverage':sum(r['necessary_input_coverage'] is True for r in rs),'ambiguous_input_coverage':sum(r['necessary_input_coverage']=='ambiguous' for r in rs),'format_complete':sum(r['format_complete'] for r in rs),'label_correct':sum(r['label_correct'] is True for r in rs),'label_not_checked':sum(r['label_correct']=='not_checked' for r in rs),'id_valid_complete_outputs':sum(r['format_complete'] and r['id_membership'] is True for r in rs),'authentic_nonempty_quote_outputs':sum(r['format_complete'] and r['parsed']['evidence'] and r['quote_authenticity_all'] is True for r in rs),'necessary_citation_coverage':sum(r['necessary_citation_coverage'] is True for r in rs),'citation_support':sum(r['citation_support'] is True for r in rs),'semantic_support_not_checked':sum(r['citation_support']=='not_checked' for r in rs),'strict_complete_success':sum(r['strict_complete_success'] for r in rs),'budget_exhausted':sum(r['finish_reason']=='length' for r in rs),'answer_http_seconds':sum(r['client_seconds'] for r in rs),'allocated_total_seconds':sum(r['allocated_total_seconds'] for r in rs),'old_group':old_review['groups'][v]}
decision={'strict_success_improvement':False,'baseline_secondary_label_improvement':'按预先的次级指标，baseline有效标签由0/3到1/3；但这一题引用归属失败，不能算严格成功。','improved_arm':'完整有效标签正确与严格成功仍0/3且2条not_checked；同分保留旧侧，格式从3/3降至1/3。','common_flow_adoption':'两侧共同流程不能分别挑选有利结果。本轮不自动替换原入口：仅baseline次级标签改善，邻段侧无收益且格式退步；保留整体候选及负面结果供本人决定，不声称整体胜出。','quality_regressions':'完整JSON总数由6/6降至3/6，出现3次输出预算耗尽；没有输入截断。','mechanism_limits':'检索词提示、短判断和动态ID enum共同改变，不能独立归因；enum防止未知ID但没防住合法ID下的错误摘录归属、改写或语义错误。','no_more_search':True,'AT_not_read':True,'no_formal_freeze':True,'3B_cancelled':True}
write(out/'review.json',{'at':now(),'run_kind':'local_rule','judgment_source':'unverified','reviewer':'Codex辅助原文复核，尚待本人确认','rows':rows,'groups':groups,'pairs':pairs,'decision':decision,'new_generations':9,'A_used':36,'A_remaining':18,'cumulative':570,'technical_failures':0,'quality_retries':0})
write(out/'nine-raw-responses.json',{'at':now(),'raw_responses':raw_rows,'count':9,'no_repair':True})
(out/'nine-raw-responses-and-review.md').write_text('\n\n'.join(md)+'\n\n'+json.dumps({'groups':groups,'decision':decision},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
write(out/'coverage-clarification.json',{'at':now(),'scope':'当前/旧AD02 baseline输入覆盖判定的解释边界，旧评价不覆盖','basis':'Read段明确可读归档且提with a full dependences list...recreate the compute environment，可构成额外运行条件线索；完整Run或其他执行依赖段提供更明确依据。不能按固定Run ID要求覆盖。','current_baseline':'ambiguous，公开参考标签正确但引用归属明确错误，严格失败不变','old_baseline':'旧记录的输入覆盖为false；其Read段同样含依赖清单线索，本轮只登记同样待本人确认，不追溯改旧计数或制造新严格成功。'})
page=out/'page';page.mkdir()
for p in Path('a-round-ui').iterdir():shutil.copy2(p,page/p.name)
protected=load(out/'protected-before.json');changed=[p for p,h in protected.items() if sha(ROOT/p)!=h];assert not changed,changed
all_runs=[]
for p in (HERE/'runs').rglob('run-*.json'):
    r=load(p)
    if r.get('generation_dispatched') and (r.get('usage') or {}).get('completion_tokens',0)>0:all_runs.append((p,r))
assert len(all_runs)==len({r['run_id'] for p,r in all_runs})==36
new_runs=[load(p) for p in out.glob('run-*.json')];assert len(new_runs)==9
git=r'C:\Users\86186\AppData\Local\Programs\Git\cmd\git.exe'
def g(*args):
    r=subprocess.run([git,'--no-optional-locks','-c','core.quotepath=false',*args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8');return {'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
resource={'before_load_GiB':rt['memory_before']['available_bytes']/2**30,'after_load_GiB':rt['memory_after_load']['available_bytes']/2**30,'minimum_GiB':min(x['available_bytes'] for x in rt['memory_samples'])/2**30,'after_stop_GiB':rt['memory_after_stop']['available_bytes']/2**30,'load_seconds':rt['load_seconds'],'model_process_peak_working_set':'not_measured','model_stopped':rt['model_stopped'],'page_stopped':rt['page_stopped']}
write(out/'completion-audit.json',{'at':now(),'protected_files_checked':len(protected),'changed':changed,'new_unique_generations':9,'new_run_ids':ids,'A_unique_generations':36,'A_remaining':18,'cumulative':570,'resources':resource,'all_inputs_fit':all(r['input_tokens']+r['config']['parameters']['max_tokens']<=4096 for r in new_runs),'max_input':max(r['input_tokens'] for r in new_runs),'truncation_flags':[r['truncated'] for r in new_runs],'generation_finish_reasons':[r['finish_reason'] for r in new_runs],'native_enum_validation':'native-id-enum-validation.json','parameter_echo_not_claimed':['response_format','effective_max_tokens'],'page_pair_requests':[x['pair_request_id'] for x in pairs],'same_request_logs':'events.jsonl','git_status':g('status','--short','--branch'),'tracked_diff_check':g('diff','--check'),'staged_diff':g('diff','--cached','--stat')})
diff=''
for name in ['short_enum_candidate.py','launch_short_enum.py','check_id_enum_native.py']:
    p=HERE/name;diff+=''.join(difflib.unified_diff([],p.read_text(encoding='utf-8').splitlines(keepends=True),fromfile='/dev/null',tofile='b/'+p.relative_to(ROOT).as_posix()))
(out/'complete-code.diff').write_text(diff,encoding='utf-8')
orch=out/'orchestration-sources';orch.mkdir()
for name in ['audit_a_retrieval_round.py','prepare_a_short_enum.py','review_a_short_enum.py']:shutil.copy2(name,orch/name)
write(out/'file-manifest.json',{'at':now(),'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.rglob('*') if p.is_file() and 'slot-cache' not in p.parts],'new_runtime_files':['进阶/a_exploration/short_enum_candidate.py','进阶/a_exploration/launch_short_enum.py','进阶/a_exploration/check_id_enum_native.py'],'manifest_self_excluded':True})
print(json.dumps({'groups':groups,'decision':decision,'resources':resource,'times':[(r['id'],r['variant'],r['client_seconds']) for r in rows],'new':9,'cumulative':570,'remaining':18,'protected_files':len(protected)},ensure_ascii=False,indent=2))
