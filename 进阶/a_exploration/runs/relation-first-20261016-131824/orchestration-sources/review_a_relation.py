from pathlib import Path
import sys,json,subprocess,shutil,difflib,socket
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
from sentence_interface import interface_response
from locator import Locator
out=Path(Path('a-relation-out.txt').read_text(encoding='utf-8').strip())
rt=load(out/'runtime.json');assert rt['confirmed_generations']==rt['dispatches']==6 and rt['model_stopped'] and 'error' not in rt
inputs={x['id']:x for x in load(out/'diagnostic-inputs.json')};entries=[load(p) for p in sorted(out.glob('item-*.json'))]
refs={x['id']:x for x in load(ROOT/'进阶/materials/a_dev_answers.json')}
locator=Locator(load(ROOT/'进阶/materials/page_words.json'))
manual={
 ('AD01','original'):{'relation_correct':'not_applicable','necessary':True,'support':False,'unrelated':False,'reason_consistent':False,'reason_factual':False,'basis':'原主张称无需记录；理由却换成最终文件加可执行流程这一不同主张。选中全部11句含末句明确记录要求，覆盖了反证，却不能支持实际supported。'},
 ('AD01','revised'):{'relation_correct':False,'necessary':True,'support':False,'unrelated':False,'reason_consistent':True,'reason_factual':False,'basis':'entails/supported内部一致，但解释声称原文明确无需记录，与已选sent-0011的you should as a minimum note down which data files...and for what purpose直接相反。关系与标签都错。'},
 ('AD02','original'):{'relation_correct':'not_applicable','necessary':False,'support':False,'unrelated':False,'reason_consistent':False,'reason_factual':False,'basis':'理由把仅静态导出不足执行视为反驳，原主张本来就说仅此不足；只选访问/运行问句和Binder句，漏掉Read静态导出依据。'},
 ('AD02','revised'):{'relation_correct':True,'necessary':False,'support':False,'unrelated':False,'reason_consistent':False,'reason_factual':False,'basis':'对完整实际输入，Read静态档案与Run运行环境组合支持原主张，因此entails方向正确；实际label仍contradicted，关系标签不一致。解释先称帮助read and run又称不足执行，且只选sent-0002/0003这两个泛泛问句/引言，不含静态导出与运行环境证据。不能把正确relation当成最终label成功。'},
 ('AD03','original'):{'relation_correct':'not_applicable','necessary':False,'support':False,'unrelated':True,'reason_consistent':False,'reason_factual':False,'basis':'只选程序版本/依赖归档前8句，把绘图只存最终图改成graphic design及归档程序的另一主张；真实摘录不支持原主张。'},
 ('AD03','revised'):{'relation_correct':False,'necessary':False,'support':False,'unrelated':True,'reason_consistent':True,'reason_factual':False,'basis':'entails/supported及解释一致，但选中程序归档句和S09检查详细值句；这些不证明只存最终图满足转换后数据保留建议。S09末句还是应检查详细值的依据，不是只留图足够。不可借未输入的S08补引用；即使对S09替代反证的充分性有边界，entails仍不成立。'}
}
rows=[];raws=[];md=['# 关系优先：本轮六条原始输出','Codex辅助原文复核，尚待本人确认；固定自动证据重放，不是端到端成绩。两侧预算均512。']
for n,e in enumerate(entries,1):
    r=load(out/e['raw_record']);x=inputs[e['id']];v=e['variant'];assert r['messages']==x['messages'][v] and r['config']==x['configs'][v]
    exp=load(out/f'expansion-{n:02}.json');obj=exp['parsed_internal'];sel=exp['selected_sources'];m=manual[(e['id'],v)]
    source=exp['valid'] and all(next(b for b in x['blocks'] if b['block_id']==s['block_id'])['text'][s['start']:s['end']]==s['text'] for s in sel)
    fields=['relation','explanation','sentence_ids','label'] if v=='revised' else ['label','reason','sentence_ids']
    fmt=isinstance(obj,dict) and set(obj)==set(fields) and exp['valid'];correct=obj['label']==refs[e['id']]['label']
    consistent=exp['relation_label_consistent'] if v=='revised' else 'not_applicable'
    strict=bool(fmt and correct and m['reason_consistent'] and m['reason_factual'] and m['necessary'] and m['support'] and not m['unrelated'] and consistent is not False)
    mapped=interface_response(e['request_id'],x['claim'],x['doc_ids'],x['snapshot'],r['run_id'],exp,r['elapsed_seconds'],locator=locator,actual_input_blocks=x['blocks'])
    assert mapped['answer']==obj['label'] and mapped['support_status']=='not_checked'
    if v=='revised':mapped.update(relation=obj['relation'],relation_label_consistent=consistent,quality_failure=exp.get('quality_failure'),explanation_projection='模型explanation逐字映射reason，label未改变')
    write(out/f'interface-response-{n:02}.json',mapped)
    row={**e,'raw_internal_content':r['content'],'parsed_internal':obj,'format_complete':fmt,'actual_serialized_field_order':list(obj),'native_expected_order_matches':list(obj)==fields,'relation':obj.get('relation','not_applicable'),'relation_correct_from_actual_input':m['relation_correct'],'relation_label_consistent':consistent,'label':obj['label'],'public_reference_label':refs[e['id']]['label'],'label_correct':correct,'reason_label_consistent_for_original_claim':m['reason_consistent'],'reason_factual_correct':m['reason_factual'],'source_authenticity':source,'selected_sources':sel,'selected_sentence_count':len(sel),'necessary_evidence_coverage':m['necessary'],'citation_support_actual_label':m['support'],'has_unrelated_evidence':m['unrelated'],'strict_complete_success':strict,'basis':m['basis'],'expanded_response':exp['expanded_response'],'client_seconds':r['elapsed_seconds'],'input_tokens':r['input_tokens'],'usage':r['usage'],'finish_reason':r['finish_reason'],'truncated':r['truncated'],'judgment_source':'unverified','reviewer':'Codex辅助原文复核，尚待本人确认','output_origin':'模型选择、程序逐字展开原文；未补选、未改label'}
    rows.append(row);raws.append({'id':e['id'],'variant':v,'run_id':r['run_id'],'actual_http_request_raw':r['actual_http_request_raw'],'raw_response':r['raw_response'],'content':r['content'],'usage':r['usage'],'finish_reason':r['finish_reason'],'client_seconds':r['elapsed_seconds']})
    md+=['\n## '+e['id']+' '+v,'```json',r['content'],'```',f"客户端耗时 {r['elapsed_seconds']:.3f} 秒；输出 {r['usage']['completion_tokens']} tokens；结束 {r['finish_reason']}。",m['basis'],'程序按所选句子展开的接口内容：','```json',json.dumps(exp['expanded_response'],ensure_ascii=False,indent=2),'```']
    write(out/f'review-item-{n:02}.json',row)
groups={}
for v in ['original','revised']:
    rs=[r for r in rows if r['variant']==v]
    groups[v]={'denominator':3,'format_complete':sum(r['format_complete'] for r in rs),'label_correct':sum(r['label_correct'] for r in rs),'relation_correct':sum(r['relation_correct_from_actual_input'] is True for r in rs) if v=='revised' else 'not_applicable','relation_label_consistent':sum(r['relation_label_consistent'] is True for r in rs) if v=='revised' else 'not_applicable','source_authenticity':sum(r['source_authenticity'] for r in rs),'necessary_evidence_coverage':sum(r['necessary_evidence_coverage'] for r in rs),'citation_support':sum(r['citation_support_actual_label'] for r in rs),'strict_complete_success':sum(r['strict_complete_success'] for r in rs),'budget_exhausted':sum(r['finish_reason']=='length' for r in rs),'client_seconds':sum(r['client_seconds'] for r in rs),'output_tokens':sum(r['usage']['completion_tokens'] for r in rs)}
decision={'at':now(),'adopt_relation_first':False,'retain_sentence_selection_by_current_user_decision':True,'basis':'两侧标签正确均0/3，严格成功均0/3，引用支持均0/3；新侧关系正确1/3、关系标签一致2/3，来源真实性没有额外收益，按本轮同分规则保留当前句子流程。','existing_correct_items_regressed':0,'prior_not_won_conclusion_unchanged':True,'mechanism_limit':'字段先后已强制，不代表内部思考按此执行；关系说对也不保证label跟随，程序未自动翻转。','AD03_evidence_boundary':'没有输入指定S08，但S09实际含检查详细值及有条件保存底层数据的相邻论述，不能称全无相关资料。其对原主张的替代反证充分性有解释边界；两侧实际supported/entails均没有支持。未用不可见S08补模型证据，不改旧评价。','budget_limit':'本轮同512；历史256仅作历史比较，不能当本轮纯关系因素对照。','stop':'本轮结束，不追加提示搜索或换模型；七道评测不读取。'}
write(out/'review.json',{'at':now(),'reviewer':'Codex辅助原文复核，尚待本人确认','rows':rows,'groups':groups,'decision':decision,'new_generations':6,'A_used':48,'A_remaining':6,'cumulative':582,'A_budget_cap':54,'budget_cap_increase':0,'technical_request_failures':0,'preparation_checker_failure_preserved':True,'quality_retries':0})
write(out/'six-raw-http-responses.json',{'at':now(),'count':6,'responses':raws,'no_repair':True})
(out/'raw-and-expanded-results.md').write_text('\n\n'.join(md)+'\n',encoding='utf-8')
differences=[]
for x in inputs.values():
    a=next(r for r in rows if r['id']==x['id'] and r['variant']=='original');b=next(r for r in rows if r['id']==x['id'] and r['variant']=='revised')
    ar=load(out/a['raw_record']);br=load(out/b['raw_record']);aa=json.loads(ar['actual_http_request_raw']);bb=json.loads(br['actual_http_request_raw'])
    assert aa['messages'][1:]==bb['messages'][1:]
    assert {k:v for k,v in aa.items() if k not in ['messages','response_format']}=={k:v for k,v in bb.items() if k not in ['messages','response_format']}
    assert aa['max_tokens']==bb['max_tokens']==512
    differences.append({'id':x['id'],'same_user_complete_blocks_sentence_index':True,'same_sampling_model_budget':True,'changed':['system_relationship_output_instruction','internal_schema_add_relation_explanation_and_field_order'],'actual_original_body':aa,'actual_candidate_body':bb})
write(out/'actual-request-differences.json',differences)
protected=load(out/'protected-before.json');changed=[p for p,h in protected.items() if sha(ROOT/p)!=h];assert not changed,changed
plan=load(out/'intervention-plan.json')
for p,h in plan['code_hashes'].items():assert sha(ROOT/p)==h,p
runs=[]
for p in (HERE/'runs').rglob('run-*.json'):
    r=load(p)
    if r.get('generation_dispatched') and (r.get('usage') or {}).get('completion_tokens',0)>0:runs.append((p,r))
assert len(runs)==len({r['run_id'] for p,r in runs})==48
with socket.socket() as s:s.settimeout(1);port_closed=s.connect_ex(('127.0.0.1',8080))!=0
assert port_closed
git=r'C:\Users\86186\AppData\Local\Programs\Git\cmd\git.exe'
def g(*args):
    r=subprocess.run([git,'--no-optional-locks','-c','core.quotepath=false',*args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8');return {'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
resources={'load_seconds':rt['load_seconds'],'before_GiB':rt['memory_before']['available_bytes']/2**30,'after_load_GiB':rt['memory_after_load']['available_bytes']/2**30,'minimum_GiB':min(x['available_bytes'] for x in rt['memory_samples'])/2**30,'after_stop_GiB':rt['memory_after_stop']['available_bytes']/2**30,'model_stopped':rt['model_stopped'],'port8080_closed':port_closed}
write(out/'generation-ledger.json',{'at':now(),'A_unique':48,'A_run_ids':[{'path':p.relative_to(ROOT).as_posix(),'run_id':r['run_id']} for p,r in runs],'new_run_ids':[r['run_id'] for r in rows],'new':6,'foundation_B_baseline_generations':534,'cumulative':582,'B_offline_replay_not_added':88,'A_cap':54,'A_remaining':6,'cap_increase_this_round':0,'native_schema_tokenization_checks_added':0})
write(out/'completion-audit.json',{'at':now(),'old_files_checked':len(protected),'old_files_changed':changed,'plan_code_hashes_match':True,'input_max_tokens':max(r['input_tokens'] for r in rows),'all_fit_with_512':all(r['input_tokens']+512<=4096 for r in rows),'truncated':[r['truncated'] for r in rows],'actual_field_order_all_match':all(r['native_expected_order_matches'] for r in rows),'resources':resources,'git_status':g('status','--short','--branch'),'tracked_diff_check':g('diff','--check'),'staged_diff':g('diff','--cached','--stat'),'formal_freeze_created':False,'AT_read':False})
diff=''
for name in ['relation_first.py','diagnose_relation_first.py']:
    p=HERE/name;diff+=''.join(difflib.unified_diff([],p.read_text(encoding='utf-8').splitlines(keepends=True),fromfile='/dev/null',tofile='b/'+p.relative_to(ROOT).as_posix()))
(out/'complete-code.diff').write_text(diff,encoding='utf-8')
orch=out/'orchestration-sources';orch.mkdir()
for name in ['prepare_a_relation.py','resume_a_relation.py','review_a_relation.py']:shutil.copy2(name,orch/name)
write(out/'file-manifest.json',{'at':now(),'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.rglob('*') if p.is_file() and not {'slot-cache','__pycache__'}&set(p.parts)],'new_runtime_files':['进阶/a_exploration/relation_first.py','进阶/a_exploration/diagnose_relation_first.py'],'self_excluded':True})
print(json.dumps({'groups':groups,'decision':decision,'resources':resources,'protected_files_unchanged':len(protected),'times':[(r['id'],r['variant'],round(r['client_seconds'],3)) for r in rows],'cumulative':582,'A_remaining':6},ensure_ascii=False,indent=2))
