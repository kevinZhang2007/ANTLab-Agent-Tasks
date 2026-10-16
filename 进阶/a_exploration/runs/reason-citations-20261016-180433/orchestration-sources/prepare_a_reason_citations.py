from pathlib import Path
import sys,json,copy,ast,shutil,difflib
from datetime import datetime
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
from compact_factorial import audit,offline_checks as compact_checks
from thinking_modes import offline_checks as thinking_checks
from sentence_selection import offline_checks as sentence_checks,build_index,schema,CANDIDATE_PROMPT
from sentence_interface import offline_checks as interface_checks
from checks_extended import run as old_checks
from preflight import native_tokenizer
previous=HERE/'runs/thinking-compact-20261016-175212';oldplan=load(previous/'intervention-plan.json')
out=HERE/'runs'/('reason-citations-'+datetime.now().strftime('%Y%m%d-%H%M%S'));out.mkdir();Path('a-reason-citations-out.txt').write_text(str(out),encoding='utf-8')
protected={p.relative_to(ROOT).as_posix():sha(p) for p in HERE.rglob('*') if p.is_file() and out not in p.parents and not {'slot-cache','__pycache__'}&set(p.parts)}
for n in ['README.md','report.md','decisions.md','declaration.md','基础/开发记录.md','基础/starter/student.py','进阶/challenge_b/challenge.py','进阶/challenge_b/no_cache_engine.py']:protected[n]=sha(ROOT/n)
write(out/'protected-before.json',protected)
note='\nreason直接说明证据为何支持、反驳或不足以判断原主张，不重新改写主张；若reason声称原主张与原文冲突，label不能同时表示supported。sentence_ids只选择判断所需片段，不能因同主题就加入；可组合多个必要片段，不要求引用越少越好。reason不重复段落ID，来源由句子索引展开。'
module=HERE/'reason_citations.py';assert not module.exists()
module.write_text('"""独立共同判断提示候选；仅追加说明，不修改模型输出。"""\nimport copy\nNOTE='+repr(note)+'\ndef adapt(messages):\n    result=copy.deepcopy(messages)\n    assert result[0]["role"]=="system"\n    result[0]["content"]+=NOTE\n    return result\n',encoding='utf-8')
from reason_citations import adapt
formula='format_complete AND selection_valid AND label_correct AND necessary_evidence_coverage_is_true AND citation_support_actual_label_is_true AND NOT has_unrelated_evidence'
write(out/'current-personal-decision.json',{'at':now(),'source':'本轮本人明确决定','decision':'将紧凑输入＋开启思考作为后续开发基础，接受覆盖和本轮成本收益；不宣称严格成功提高。','preserved_previous_decision':'进阶/a_exploration/runs/thinking-compact-20261016-175212/review.json','previous_sha256':sha(previous/'review.json'),'does_not_overwrite_previous':True})
write(out/'strict-formula-provenance.json',{'at':now(),'formula':formula,'reason_quality_in_formula':False,'original_evidence':'进阶/a_exploration/runs/sentence-selection-20261016-130328/review_a_sentence.py','original_expression':'format_complete and valid and correct is True and necessary_coverage and citation_support and not unrelated','later_drift':'thinking-compact评价脚本加入reason一致性门槛；本轮使用最初口径，理由另列，不覆盖旧评价。','previous_six_strict_remain_zero':'AD01/AD03标签错；AD02重复缺覆盖、紧凑含无关引用，均不因移除理由门槛变成功。','ambiguous':'保留三题分母，必要覆盖或支持为ambiguous不视为true。'})
write(out/'plan-before-checks.json',{'at':now(),'hypothesis':'短追加说明可能减少理由与label矛盾及无关引用，亦可能只是增加文字或损害已有正确判断。','competing_explanation':'错误可能来自否定理解和必要证据识别，说明检查要求不能保证模型执行。','selection':'严格成功优先，其次标签正确；已有正确AD02不得退步；同分保留当前流程。','strict_formula':formula,'reason_quality_separate':True,'scope':'三道开发题固定自动improved证据重放，不重新查询，不人工补AD03直接依据。','generation_cap':6,'baseline_cumulative':615,'A_used_before':81,'original_plan_budget':90,'future_reserved_additional':30,'future_reservation_used':0,'stopping':'所有离线及实际模板检查通过才调用；2GiB加载门槛，连续三个2秒样本低于1GiB停止自有服务；技术失败不重发，质量错误不重试。','no_AT_read':True,'original_system':CANDIDATE_PROMPT,'candidate_system':CANDIDATE_PROMPT+note})
checks={'compact':compact_checks(),'thinking':thinking_checks(),'sentence':sentence_checks(),'interface':interface_checks(),'existing':old_checks(out)}
assert all(x['passed'] for x in checks.values())
inputs=[];requests=[];order=[];audits=[]
for i,x in enumerate(load(previous/'diagnostic-inputs.json')):
    ms=copy.deepcopy(x['messages']['compact']);conf=copy.deepcopy(x['configs']['compact']);new=adapt(ms)
    assert ms[0]['content']==CANDIDATE_PROMPT and new[0]['content']==ms[0]['content']+note and new[1:]==ms[1:]
    before=copy.deepcopy(ms);assert adapt(ms)==new and ms==before
    assert conf['parameters']['max_tokens']==1024 and conf['parameters']['presence_penalty']==1.5 and conf['parameters']['chat_template_kwargs']=={'enable_thinking':True}
    assert conf['parameters']['response_format']['json_schema']['schema']==schema(x['sentence_index'])
    for messages in [ms,new]:assert audit(messages,x['blocks'],x['sentence_index'],x['doc_ids'],x['snapshot'])['passed']
    item={**x,'messages':{'original':ms,'revised':new},'configs':{'original':copy.deepcopy(conf),'revised':copy.deepcopy(conf)}};inputs.append(item);audits.append({'id':x['id'],'same_user':True,'same_configuration':True,'only_system_append':True,'byte_scope_audit':True})
    for variant in ['original','revised']:
        body={'model':conf['model'],'messages':item['messages'][variant],'stream':False,**conf['parameters']};requests.append({'id':x['id'],'mode':variant,'body':body,'serialized':json.dumps(body,ensure_ascii=False)})
    order.extend({'id':x['id'],'variant':v} for v in (['original','revised'] if i%2==0 else ['revised','original']))
write(out/'diagnostic-inputs.json',inputs);write(out/'serialized-request-plan.json',requests);write(out/'byte-and-scope-audit.json',{'at':now(),'passed':True,'rows':audits})
runner=HERE/'diagnose_reason_citations.py';assert not runner.exists();oldsrc=(HERE/'diagnose_thinking_compact.py').read_text(encoding='utf-8');src=oldsrc.replace('开启思考下重复/紧凑输入对照','紧凑思考下理由和引用提示对照').replace("'repeated'","'original'").replace("'compact'","'revised'").replace('-repeated.json','-original.json').replace('-compact.json','-revised.json')
src=src.replace('from compact_factorial import compact_messages,audit','from compact_factorial import audit\n    from reason_citations import adapt')
src=src.replace("assert item['messages']['revised']==compact_messages(item['messages']['original'],item['blocks'],item['sentence_index'],item['doc_ids'],item['snapshot'])","assert item['messages']['revised']==adapt(item['messages']['original'])")
src=src.replace("'same_system':a['actual_request_body']['messages'][0]==b['actual_request_body']['messages'][0]","'only_system_append':b['actual_request_body']['messages']==adapt(a['actual_request_body']['messages'])")
ast.parse(src);assert 'compact_messages(' not in src;runner.write_text(src,encoding='utf-8')
parts=[]
for x in inputs:
    for v in ['original','revised']:
        m=x['messages'][v];parts.append('<|im_start|>system\n'+m[0]['content']+'<|im_end|>\n<|im_start|>user\n'+m[1]['content']+'<|im_end|>\n<|im_start|>assistant\n')
base=Path.home()/'AppData/Local/ANTLabLocalModel';marker='<|endoftext|>';tokens,command=native_tokenizer(base/'llama-b11429/llama-tokenize.exe',base/'models/Qwen3-0.6B-Q8_0.gguf',marker+marker.join(parts)+marker,out,'offline-capacity');counts=[];n=0
for token in tokens[1:]:
    if token==tokens[0]:counts.append(n);n=0
    else:n+=1
assert len(counts)==6 and all(n+1024<=4096 for n in counts)
for name in ['mode-offline-checks.json','offline-checks.json']:write(out/name,{'at':now(),'passed':True,'checks':checks,'capacity_original_revised':counts,'generation_calls':0,'adapter_assertions':18,'actual_http_template_check_required':True})
plan={**load(out/'plan-before-checks.json'),'saved_at':now(),'status':'fixed_dev_evidence_diagnostic_not_formal_freeze','order':order,'cumulative_baseline':615,'input_sha256':sha(out/'diagnostic-inputs.json'),'serialized_requests_sha256':sha(out/'serialized-request-plan.json'),'code_hashes':{p.relative_to(ROOT).as_posix():sha(p) for p in HERE.glob('*.py')},'data_hashes':oldplan['data_hashes'],'model_hash':oldplan['model_hash'],'executable_hash':oldplan['executable_hash'],'service_arguments':oldplan['service_arguments'],'output_budget':1024,'no_new_query':True}
write(out/'intervention-plan.json',plan);snap=out/'new-code-snapshot';snap.mkdir()
for p in [runner,module]:shutil.copy2(p,snap/p.name)
shutil.copy2(__file__,out/Path(__file__).name)
(out/'runner-full.diff').write_text(''.join(difflib.unified_diff(oldsrc.splitlines(True),src.splitlines(True),fromfile='diagnose_thinking_compact.py',tofile='diagnose_reason_citations.py')),encoding='utf-8')
print(json.dumps({'out':str(out),'passed':True,'capacity':counts,'order':order,'generations':0},ensure_ascii=False))
