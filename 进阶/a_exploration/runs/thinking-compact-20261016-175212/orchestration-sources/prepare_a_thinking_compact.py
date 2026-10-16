from pathlib import Path
import sys,json,copy,shutil,ast
from datetime import datetime
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
from preflight import native_tokenizer
out=HERE/'runs'/('thinking-compact-'+datetime.now().strftime('%Y%m%d-%H%M%S'));out.mkdir();Path('a-thinking-compact-out.txt').write_text(str(out),encoding='utf-8')
protected={p.relative_to(ROOT).as_posix():sha(p) for p in HERE.rglob('*') if p.is_file() and out not in p.parents and not {'slot-cache','__pycache__'}&set(p.parts)}
for n in ['README.md','report.md','decisions.md','declaration.md','基础/开发记录.md','基础/starter/student.py','进阶/challenge_b/challenge.py','进阶/challenge_b/no_cache_engine.py']:protected[n]=sha(ROOT/n)
write(out/'protected-before.json',protected)
previous=HERE/'runs/thinking-modes-20261016-174125';oldplan=load(previous/'intervention-plan.json');oldreview=load(previous/'review.json');known_correct=[x['id'] for x in oldreview['rows'] if x['variant']=='on' and x['label_correct']]
write(out/'plan-before-checks.json',{'at':now(),'hypothesis':'开启思考时，去重并将claim置后的组织方案可能改变判断和必要证据选择，也可能只减少输入和耗时或丢失已正确判断。','competing_explanation':'模型可能在较短输入上更快地产生同样错误，或忽略跨句证据；A组织因素同时改变表示与claim位置，不能单独归因去重。','selection':'严格成功优先，其次标签正确；已有标签正确题不得退步（同时检查本轮重复侧及历史已正确题）；必要覆盖与引用支持的退步逐题报告。只有耗时下降单列效率收益，不称正确率提升；质量同分保留重复侧。','historically_correct_dev_ids_for_evaluation_only':known_correct,'scope':'仅三道开发题及自造样例；同一自动improved证据重放，不重新检索、不用人工充分证据。','fixed':'两侧Qwen3-0.6B-Q8_0、同原判断system、同句子Schema/展开、同模型和采样，presence1.5/repeat1.0、开启思考、1024共享总输出预算、4096上下文。','generation_cap':6,'baseline_cumulative':609,'A_used_before':75,'original_plan_budget':90,'original_plan_remaining_before':15,'future_reserved_additional':30,'future_reservation_used':0,'future_reservation_authorizes_execution':False,'stopping':'所有实际模板保存并检查通过才生成；超限不删原文。技术失败停止不重发，质量错误不重试。沿用2GiB加载和连续3个2秒低于1GiB的自有进程停止规则。','evaluation':'仅最终content判分，reasoning全留；标签、理由一致、非空来源真实性、必要覆盖、引用支持、严格、输出tokens和完整客户端耗时分列。AD03缺S08边界不借参考补证。','no_AT_read':True})
from compact_factorial import compact_messages,audit,offline_checks as compact_checks
from thinking_modes import offline_checks as thinking_checks
from sentence_selection import offline_checks as sentence_checks,build_index,schema
from sentence_interface import offline_checks as interface_checks
from checks_extended import run as old_checks
checks={'compact':compact_checks(),'thinking':thinking_checks(),'sentence':sentence_checks(),'interface':interface_checks(),'existing':old_checks(out)};assert all(x['passed'] for x in checks.values())
inputs=[];requests=[];order=[];audits=[]
for i,x in enumerate(load(previous/'diagnostic-inputs.json')):
    ms=copy.deepcopy(x['messages']['on']);conf=copy.deepcopy(x['configs']['on']);assert conf['parameters']['max_tokens']==1024 and conf['parameters']['presence_penalty']==1.5 and conf['parameters']['chat_template_kwargs']=={'enable_thinking':True}
    compact=compact_messages(ms,x['blocks'],x['sentence_index'],x['doc_ids'],x['snapshot']);proof=audit(compact,x['blocks'],x['sentence_index'],x['doc_ids'],x['snapshot']);assert compact[0]==ms[0]
    item={'id':x['id'],'claim':x['claim'],'doc_ids':x['doc_ids'],'snapshot':x['snapshot'],'blocks':x['blocks'],'sentence_index':x['sentence_index'],'messages':{'repeated':ms,'compact':compact},'configs':{'repeated':copy.deepcopy(conf),'compact':copy.deepcopy(conf)},'origin':x['origin']};inputs.append(item);audits.append({'id':x['id'],'byte_scope_audit':proof,'same_claim':json.loads(ms[1]['content'])['claim']==json.loads(compact[1]['content'])['claim'],'same_system':True,'same_config_schema_mode':True})
    for variant in ['repeated','compact']:
        body={'model':conf['model'],'messages':item['messages'][variant],'stream':False,**conf['parameters']};requests.append({'id':x['id'],'mode':variant,'body':body,'serialized':json.dumps(body,ensure_ascii=False)})
    order.extend({'id':x['id'],'variant':v} for v in (['repeated','compact'] if i%2==0 else ['compact','repeated']))
write(out/'diagnostic-inputs.json',inputs);write(out/'serialized-request-plan.json',requests);write(out/'byte-and-scope-audit.json',{'at':now(),'passed':True,'rows':audits})
runner=HERE/'diagnose_thinking_compact.py';assert not runner.exists();src=(HERE/'diagnose_thinking_modes.py').read_text(encoding='utf-8');src=src.replace('同预算开关思考对照','开启思考下重复/紧凑输入对照')
begin=src.index('    from sentence_selection import schema,build_index');end=src.index('    with socket.socket()',begin)
src=src[:begin]+"    from sentence_selection import schema,build_index\n    from compact_factorial import compact_messages,audit\n    assert load(out/'byte-and-scope-audit.json')['passed']\n    for item in inputs:\n        assert item['sentence_index']==build_index(item['blocks'],item['doc_ids'],item['snapshot'])\n        assert item['configs']['repeated']==item['configs']['compact']\n        assert item['messages']['compact']==compact_messages(item['messages']['repeated'],item['blocks'],item['sentence_index'],item['doc_ids'],item['snapshot'])\n        assert audit(item['messages']['compact'],item['blocks'],item['sentence_index'],item['doc_ids'],item['snapshot'])['passed']\n        for variant in ['repeated','compact']:\n            conf=item['configs'][variant];assert conf['parameters']['max_tokens']==1024\n            assert conf['parameters']['chat_template_kwargs']=={'enable_thinking':True}\n            assert conf['parameters']['presence_penalty']==1.5\n            assert conf['parameters']['response_format']['json_schema']['schema']==schema(item['sentence_index'])\n"+src[end:]
src=src.replace("for variant in ['off','on']:","for variant in ['repeated','compact']:")
begin=src.index('        pairs=[]');end=src.index("        phase='generation'",begin)
src=src[:begin]+"        pairs=[]\n        for item in inputs:\n            a=load(out/('capacity-before-'+item['id']+'-repeated.json'));b=load(out/('capacity-before-'+item['id']+'-compact.json'))\n            checks={'same_system':a['actual_request_body']['messages'][0]==b['actual_request_body']['messages'][0],'same_config':item['configs']['repeated']==item['configs']['compact'],'both_on_branch':a['actual_generation_suffix']==b['actual_generation_suffix']=='','both_fit':a['fits'] and b['fits'],'byte_scope_audit':audit(item['messages']['compact'],item['blocks'],item['sentence_index'],item['doc_ids'],item['snapshot'])['passed']}\n            pairs.append({'id':item['id'],'checks':checks})\n            write(out/'paired-template-verification.json',{'at':now(),'pairs':pairs,'generation_calls':0})\n            if not all(checks.values()):raise TechnicalStop('共同配置或紧凑原文审计不符，模板证据已保存')\n"+src[end:]
assert "{'enable_thinking':variant=='on'}" in src;src=src.replace("{'enable_thinking':variant=='on'}","{'enable_thinking':True}");ast.parse(src);runner.write_text(src,encoding='utf-8')
parts=[]
for x in inputs:
    for variant in ['repeated','compact']:
        m=x['messages'][variant];parts.append('<|im_start|>system\n'+m[0]['content']+'<|im_end|>\n<|im_start|>user\n'+m[1]['content']+'<|im_end|>\n<|im_start|>assistant\n')
base=Path.home()/'AppData/Local/ANTLabLocalModel';marker='<|endoftext|>';tokens,command=native_tokenizer(base/'llama-b11429/llama-tokenize.exe',base/'models/Qwen3-0.6B-Q8_0.gguf',marker+marker.join(parts)+marker,out,'offline-capacity');counts=[];n=0
for token in tokens[1:]:
    if token==tokens[0]:counts.append(n);n=0
    else:n+=1
assert len(counts)==6 and all(n+1024<=4096 for n in counts)
write(out/'mode-offline-checks.json',{'at':now(),'passed':True,'checks':checks,'byte_reconstruction':True,'source_compatibility_reused':'进阶/a_exploration/runs/thinking-modes-20261016-174125/template-parser-source-evidence.json','generation_calls':0})
write(out/'offline-checks.json',{'at':now(),'passed':True,'checks':checks,'capacity_repeated_compact_each_task':counts,'output_budget_both':1024,'actual_http_template_check_required':True,'generation_calls':0})
plan={**load(out/'plan-before-checks.json'),'saved_at':now(),'status':'fixed_dev_evidence_diagnostic_not_formal_freeze','order':order,'cumulative_baseline':609,'input_sha256':sha(out/'diagnostic-inputs.json'),'serialized_requests_sha256':sha(out/'serialized-request-plan.json'),'code_hashes':{p.relative_to(ROOT).as_posix():sha(p) for p in HERE.glob('*.py')},'data_hashes':oldplan['data_hashes'],'model_hash':oldplan['model_hash'],'executable_hash':oldplan['executable_hash'],'service_arguments':oldplan['service_arguments'],'output_budget':1024,'no_new_query':True}
write(out/'intervention-plan.json',plan);snap=out/'new-code-snapshot';snap.mkdir();shutil.copy2(runner,snap/runner.name);shutil.copy2(__file__,out/Path(__file__).name)
print(json.dumps({'out':str(out),'checks':{k:v.get('count',v['passed']) for k,v in checks.items()},'capacity_repeated_compact':counts,'order':order,'generated':0},ensure_ascii=False))
