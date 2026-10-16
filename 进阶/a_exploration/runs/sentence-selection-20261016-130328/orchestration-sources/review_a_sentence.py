from pathlib import Path
import sys,json,subprocess,time,shutil,difflib
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
from sentence_selection import expand,build_index
from sentence_interface import interface_response
from locator import Locator
from common_judgment_candidate import validate_raw
out=Path(Path('a-sentence-out.txt').read_text().strip());plan=load(out/'intervention-plan.json');items=load(out/'diagnostic-inputs.json');rt=load(out/'runtime.json')
assert rt['confirmed_generations']==6 and rt['model_stopped']
entries=[load(p) for p in sorted(out.glob('item-*.json'))];runs=[load(out/x['raw_record']) for x in entries];assert len({r['run_id'] for r in runs})==6
refs={r['id']:r for r in load(ROOT/'进阶/materials/a_dev_answers.json')};locator=Locator(load(ROOT/'进阶/materials/page_words.json'))
manual={
 ('AD01','original'):{'reason_label_consistency':True,'reason_factual_correct':False,'necessary_coverage':False,'citation_support':False,'unrelated':False,'basis':'原输入已有P1-S03末句对不可避免手工操作仍要求记录文件及目的；回复insufficient与缺说明理由表面一致，但事实基础错误，空引用不支持拒判。'},
 ('AD01','revised'):{'reason_label_consistency':False,'reason_factual_correct':False,'necessary_coverage':True,'citation_support':False,'unrelated':False,'basis':'模型选全部11个片段，包含P1-S03末句的明确记录要求；来源真且必要反证覆盖，但实际label为supported，reason改成保存最终文件加完整可执行流程这一不同主张。其他手工流程片段多为相关冗余，不把全部冗余一概标成无关；不能用直接反证支持无需记录。'},
 ('AD02','original'):{'reason_label_consistency':True,'reason_factual_correct':False,'necessary_coverage':False,'citation_support':False,'unrelated':False,'basis':'已有Read/Run完整原段，原主张仅此不足执行，回复却要求原文明示静态导出足以执行才支持，否定方向错误；空引用。'},
 ('AD02','revised'):{'reason_label_consistency':False,'reason_factual_correct':False,'necessary_coverage':False,'citation_support':False,'unrelated':False,'basis':'sentence_ids选中的是怎样访问/运行/探索这一问句，以及Binder运行环境句；没有选静态HTML/PDF用于Read的句子。理由称仅此不足与原主张冲突，但原主张恰为仅此不足，方向判断自相矛盾；contradicted及引用支持均失败。'},
 ('AD03','original'):{'reason_label_consistency':True,'reason_factual_correct':False,'necessary_coverage':False,'citation_support':False,'unrelated':True,'basis':'真实引用为程序归档及HTML层次结果，不支持只存最终图。实际输入没有图底层数据章节，应保留缺证边界；不能借不可见参考原文补证。'},
 ('AD03','revised'):{'reason_label_consistency':False,'reason_factual_correct':False,'necessary_coverage':False,'citation_support':False,'unrelated':True,'basis':'选中8个片段均来自程序版本/依赖归档P1-S04，不是图底层数据证据。理由将科学绘图变成graphic design及版本可用性另一主张。所选文本真实不代表支持原始只存最终图断言。'}
}
rows=[];raws=[];md=['# 句子选择固定证据诊断：原始内部响应与展开分开','复核时间：'+now(),'Codex辅助原文复核，尚待本人确认。新侧quote由程序依模型所选sentence_id逐字展开，不是模型生成，不构成语义证明。']
for n,(entry,r) in enumerate(zip(entries,runs),1):
    inp=next(x for x in items if x['id']==entry['id']);v=entry['variant'];assert r['messages']==inp['messages'][v] and r['config']==inp['configs'][v]
    rawpath='run-'+r['run_id']+'.json';expanded=None;selected=[];mapping_ms=None;internal=None
    if v=='revised':
        expansion=load(out/f'expansion-{n:02}.json');assert expansion==expand(r['content'],inp['blocks'],inp['sentence_index'],inp['doc_ids'],inp['snapshot'])
        internal=expansion['parsed_internal'];valid=expansion['valid'];parsed=expansion['expanded_response'];selected=expansion['selected_sources'];expanded=parsed
        format_complete=isinstance(internal,dict) and set(internal)=={'label','reason','sentence_ids'} and isinstance(internal['sentence_ids'],list) and isinstance(internal['reason'],str) and internal['label'] in ('supported','contradicted','insufficient')
        source_valid=valid and all(next(b for b in inp['blocks'] if b['block_id']==s['block_id'])['text'][s['start']:s['end']]==s['text'] for s in selected)
        mapping=interface_response(entry['request_id'],inp['claim'],inp['doc_ids'],inp['snapshot'],r['run_id'],expansion,r['elapsed_seconds'],locator=locator,actual_input_blocks=inp['blocks'])
        assert mapping['answer']==internal['label'] and mapping['support_status']=='not_checked' and all(e['model_generated_quote'] is False for e in mapping['evidence'])
        write(out/f'interface-response-{n:02}.json',mapping);mapping_ms=mapping['offline_interface_mapping_ms']
    else:
        validation=validate_raw(r['content'],inp['blocks']);assert validation==load(out/f'old-validation-{n:02}.json')
        parsed=validation['parsed'];format_complete=validation['format_complete'];valid=validation['passed'];source_valid=valid and bool(parsed['evidence']);internal=parsed
    label=internal['label'] if format_complete else None;correct=label==refs[entry['id']]['label'] if format_complete else 'not_checked';m=manual[(entry['id'],v)]
    strict=bool(format_complete and valid and correct is True and m['necessary_coverage'] and m['citation_support'] and not m['unrelated'])
    row={**entry,'raw_record':rawpath,'raw_internal_content':r['content'],'parsed_internal':internal,'expanded_response':expanded,'interface_response_file':f'interface-response-{n:02}.json' if v=='revised' else None,'format_complete':format_complete,'selection_or_old_source_validation_passed':valid,'source_authenticity_for_nonempty_evidence':source_valid,'selected_sentence_count':len(selected) if v=='revised' else None,'selected_sources':selected,'label':label,'public_reference_label':refs[entry['id']]['label'],'label_correct':correct,'reason_label_consistent_for_original_claim':m['reason_label_consistency'],'reason_factual_correct':m['reason_factual_correct'],'necessary_evidence_coverage':m['necessary_coverage'],'citation_support_actual_label':m['citation_support'],'has_unrelated_evidence':m['unrelated'],'strict_complete_success':strict,'review_basis':m['basis'],'client_seconds':r['elapsed_seconds'],'offline_interface_mapping_ms':mapping_ms,'input_tokens':r['input_tokens'],'usage':r['usage'],'finish_reason':r['finish_reason'],'truncated':r['truncated'],'output_origin':'model_selection_program_expansion' if v=='revised' else 'model_generated_evidence','judgment_source':'unverified','reviewer':'Codex原文辅助复核，尚待本人确认'}
    rows.append(row);raws.append({'id':entry['id'],'variant':v,'run_id':r['run_id'],'actual_http_request_body':r['actual_http_request_body'],'raw_response':r['raw_response'],'content':r['content'],'usage':r['usage'],'elapsed_seconds':r['elapsed_seconds'],'finish_reason':r['finish_reason']})
    md+=['\n## '+entry['id']+' '+v,'模型原始输出：','```json',r['content'],'```',f'客户端耗时{r["elapsed_seconds"]:.3f}秒；输入{r["input_tokens"]} tokens；输出{r["usage"]["completion_tokens"]} tokens；结束{r["finish_reason"]}。']
    if expanded is not None:md+=['程序展开的接口内容（local_rule；label/reason原样，quote不是模型抄写）：','```json',json.dumps(expanded,ensure_ascii=False,indent=2),'```']
    md+=[m['basis']]
groups={}
for v in ['original','revised']:
    rs=[r for r in rows if r['variant']==v];groups[v]={'denominator':3,'format_complete':sum(r['format_complete'] for r in rs),'budget_exhausted':sum(r['finish_reason']=='length' for r in rs),'label_correct':sum(r['label_correct'] is True for r in rs),'label_not_checked':sum(r['label_correct']=='not_checked' for r in rs),'nonempty_source_authenticity':sum(r['source_authenticity_for_nonempty_evidence'] for r in rs),'necessary_evidence_coverage':sum(r['necessary_evidence_coverage'] for r in rs),'citation_support':sum(r['citation_support_actual_label'] for r in rs),'strict_complete_success':sum(r['strict_complete_success'] for r in rs),'model_request_seconds':sum(r['client_seconds'] for r in rs),'output_tokens':sum(r['usage']['completion_tokens'] for r in rs)}
decision={'adopt':False,'reason':'两侧完整JSON均3/3，无预算耗尽；标签正确与严格成功均0/3。句子ID展开保证已选引用来源真实，新侧3/3来源验证通过，但未改善语义判断且调用更慢，按同分保留旧流程。','limits':['新增句子索引使输入变长；同256预算不意味着总token或时延相同，不能归因于纯输出长度。','AD01把全部11片段选入，不是精确必要证据选择；含正确反证不等于支持当前错误label。','程序没有添加未选句子，没有改label或reason，没有语义补证。','对外接口记录由离线适配生成，未做新页面/HTTP端到端接入验证。','不能把源码要求的步骤声称为模型确实执行了内部核对。'],'future':'本轮停止，不追加调用；七道评测仍取消。'}
write(out/'review.json',{'at':now(),'reviewer':'Codex原文辅助复核，尚待本人确认','run_kind':'local_rule','judgment_source':'unverified','rows':rows,'groups':groups,'decision':decision,'new_generations':6,'A_used':42,'A_remaining':12,'cumulative':576,'technical_failures':0,'quality_retries':0})
write(out/'six-raw-http-responses.json',{'at':now(),'count':6,'responses':raws,'no_repair':True})
(out/'raw-and-expanded-results.md').write_text('\n\n'.join(md)+'\n\n'+json.dumps({'groups':groups,'decision':decision},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
diffs=[]
for item in items:
    old=next(r for r in runs if r['stage'].endswith(item['id']+'-original'));new=next(r for r in runs if r['stage'].endswith(item['id']+'-revised'))
    a=json.loads(old['actual_http_request_raw']);b=json.loads(new['actual_http_request_raw']);ua=json.loads(a['messages'][1]['content']);ub=json.loads(b['messages'][1]['content'])
    assert ub=={**ua,'sentence_index':item['sentence_index']}
    aa={k:v for k,v in a.items() if k not in ['messages','response_format']};bb={k:v for k,v in b.items() if k not in ['messages','response_format']};assert aa==bb
    diffs.append({'id':item['id'],'original_body':a,'new_body':b,'same_original_passages_and_claim':True,'changed':['necessary_output_format_in_system','append_sentence_index','internal_output_schema'],'model_sampling_budget_equal':True,'no_new_query':True})
write(out/'actual-request-differences.json',diffs)
protected=load(out/'protected-before.json');changed=[p for p,h in protected.items() if sha(ROOT/p)!=h];assert not changed,changed
for p,h in plan['code_hashes'].items():assert sha(ROOT/p)==h
all_runs=[]
for p in (HERE/'runs').rglob('run-*.json'):
    r=load(p)
    if r.get('generation_dispatched') and (r.get('usage') or {}).get('completion_tokens',0)>0:all_runs.append((p,r))
assert len(all_runs)==len({r['run_id'] for p,r in all_runs})==42
git=r'C:\Users\86186\AppData\Local\Programs\Git\cmd\git.exe'
def g(*args):
    r=subprocess.run([git,'--no-optional-locks','-c','core.quotepath=false',*args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8');return {'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
resources={'load_seconds':rt['load_seconds'],'before_GiB':rt['memory_before']['available_bytes']/2**30,'after_load_GiB':rt['memory_after_load']['available_bytes']/2**30,'minimum_GiB':min(x['available_bytes'] for x in rt['memory_samples'])/2**30,'model_stopped':rt['model_stopped']}
write(out/'completion-audit.json',{'at':now(),'old_files_checked':len(protected),'changed':changed,'actual_code_matches_final_plan':True,'input_max_tokens':max(r['input_tokens'] for r in runs),'all_fit_with_256':all(r['input_tokens']+256<=4096 for r in runs),'truncated_flags':[r['truncated'] for r in runs],'unique_new_runs':[r['run_id'] for r in runs],'A_unique_generations':42,'A_remaining':12,'cumulative':576,'resources':resources,'git_status':g('status','--short','--branch'),'tracked_diff_check':g('diff','--check'),'staged_diff':g('diff','--cached','--stat'),'formal_freeze_created':False,'AT_read':False})
diff=''
for name in ['sentence_selection.py','sentence_interface.py','diagnose_sentence_selection.py']:
    p=HERE/name;diff+=''.join(difflib.unified_diff([],p.read_text(encoding='utf-8').splitlines(keepends=True),fromfile='/dev/null',tofile='b/'+p.relative_to(ROOT).as_posix()))
(out/'complete-code.diff').write_text(diff,encoding='utf-8')
orch=out/'orchestration-sources';orch.mkdir()
for name in ['prepare_a_sentence.py','complete_a_sentence_preflight.py','finalize_a_sentence_preflight.py','review_a_sentence.py']:shutil.copy2(name,orch/name)
write(out/'file-manifest.json',{'at':now(),'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.rglob('*') if p.is_file() and 'slot-cache' not in p.parts],'new_runtime_files':['进阶/a_exploration/sentence_selection.py','进阶/a_exploration/sentence_interface.py','进阶/a_exploration/diagnose_sentence_selection.py'],'manifest_self_excluded':True})
print(json.dumps({'groups':groups,'decision':decision,'resources':resources,'times':[(r['id'],r['variant'],round(r['client_seconds'],3),r['selected_sentence_count']) for r in rows],'old_files_unchanged':len(protected),'cumulative':576,'remaining':12},ensure_ascii=False,indent=2))
