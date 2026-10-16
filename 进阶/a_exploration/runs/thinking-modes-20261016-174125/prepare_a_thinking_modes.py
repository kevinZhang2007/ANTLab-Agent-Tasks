from pathlib import Path
import sys,json,copy,shutil,subprocess,ast,hashlib
from datetime import datetime
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
from preflight import native_tokenizer
out=HERE/'runs'/('thinking-modes-'+datetime.now().strftime('%Y%m%d-%H%M%S'));out.mkdir();Path('a-thinking-modes-out.txt').write_text(str(out),encoding='utf-8')
protected={p.relative_to(ROOT).as_posix():sha(p) for p in HERE.rglob('*') if p.is_file() and out not in p.parents and not {'slot-cache','__pycache__'}&set(p.parts)}
for n in ['README.md','report.md','decisions.md','declaration.md','基础/开发记录.md','基础/starter/student.py','进阶/challenge_b/challenge.py','进阶/challenge_b/no_cache_engine.py']:protected[n]=sha(ROOT/n)
write(out/'protected-before.json',protected)
write(out/'plan-before-checks.json',{'at':now(),'status':'独立模板审计适配已起草，尚未执行检查/启动/生成','hypothesis':'在相同1024总输出预算下，真实思考模式可能改变原主张理解及引用判断，但也可能耗尽预算而没有最终结果。','competing_explanation':'reasoning可能重复错误判断或挤占最终JSON预算；正确思考句不能抵消最终错误，也不证明内部因果机制。','fixed':'原重复输入、原判断system、同句子Schema、同0.6B模型、采样与presence1.5、repeat1.0；不重新查询、不用人工充分证据。','mode_control':'统一支持推理解析的服务；每请求chat_template_kwargs.enable_thinking布尔false/true。只有该请求开关不同，不将解析格式字符串当开关证据。','service_common_adjustment':'相对前轮共同服务仅--reasoning off改on以支持解析；本轮两侧完全共用该服务，off由显式false渲染关闭分支。其余启动参数不变。','selection':'严格成功优先，其次最终标签正确；已有成功项不得退步，同分保留关闭思考。','evaluation':'全部生成结束后读取开发参考；最终JSON、标签、理由一致、非空来源真实、必要覆盖、支持、严格、预算耗尽、总输出tokens和完整请求耗时分列，残缺和无最终答案保留3题分母。','generation_cap':6,'baseline_cumulative':603,'A_used_before':69,'original_plan_budget':90,'original_plan_remaining_before':21,'future_reserved_additional':30,'future_reservation_used':0,'future_reservation_authorizes_execution':False,'reservation_note':'本人本轮另行要求为后续七题对照、变体与反事实预留30次；与原90计划及本轮6次授权分列，未恢复七题执行，不把预留计入真实调用。','stopping':'完整输入+1024须<=4096；不截断。准备错误可离线修复留档；请求技术失败停止不自动重发；质量错误不重试；2GiB加载门槛，连续3个2秒低于1GiB样本停止自有服务。','no_AT_read':True})
srcdir=ROOT/'基础/runs/prompts/qwen06_short_budget_r0';official=load(srcdir/'official-evidence.json');source_rows=[]
for filename,first,last in [('official-server-common.cpp.txt',1396,1408),('official-chat-auto-parser-generator.cpp.txt',105,155)]:
    p=srcdir/filename;record=next(x for x in official if x['saved_file']==filename);raw=p.read_bytes();normal=hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest();assert record['sha256'] in [sha(p),normal]
    lines=p.read_text(encoding='utf-8').splitlines();source_rows.append({'path':p.relative_to(ROOT).as_posix(),'official_url':record['url'],'source_commit':record['source_commit'],'recorded_sha256':record['sha256'],'actual_byte_sha256':sha(p),'LF_normalized_in_memory_sha256':normal,'lines':[first,last],'excerpt':'\n'.join(lines[first-1:last])})
write(out/'template-parser-source-evidence.json',{'at':now(),'reused_history':'基础/runs/thinking_pair/20261014-125513/resume-20261014-130150/source-template-parser-evidence.json','sources':source_rows,'reading':'请求kwargs布尔值覆盖enable_thinking；parser将reasoning parser与最终JSON Schema parser组合。实际本机Jinja只在false时补空think块，true不必预填think。','not_echoed':['内部enable_thinking布尔状态','本请求编译grammar与PEG对象'],'no_network_or_download':True})
target=HERE/'thinking_modes.py';assert not target.exists();ast.parse(Path('a_thinking_modes.py').read_text(encoding='utf-8'));shutil.copy2('a_thinking_modes.py',target)
from thinking_modes import offline_checks
from sentence_selection import offline_checks as sentence_checks,schema
from sentence_interface import offline_checks as interface_checks
from checks_extended import run as old_checks
checks={'modes':offline_checks(),'sentence':sentence_checks(),'interface':interface_checks(),'existing':old_checks(out)};assert all(x['passed'] for x in checks.values())
previous=HERE/'runs/compact-penalty-20261016-172222';base_inputs=load(previous/'diagnostic-inputs.json');oldplan=load(previous/'intervention-plan.json');inputs=[];requests=[];order=[]
for i,item in enumerate(base_inputs):
    ms=copy.deepcopy(item['messages']['repeated_15']);conf0=copy.deepcopy(item['configs']['repeated_15']);assert conf0['parameters']['presence_penalty']==1.5;conf0['parameters']['max_tokens']=1024
    x={'id':item['id'],'claim':item['claim'],'doc_ids':item['doc_ids'],'snapshot':item['snapshot'],'blocks':item['blocks'],'sentence_index':item['sentence_index'],'messages':{},'configs':{},'origin':item['origin']}
    for mode in ['off','on']:
        conf=copy.deepcopy(conf0);conf['parameters']['chat_template_kwargs']={'enable_thinking':mode=='on'};x['configs'][mode]=conf;x['messages'][mode]=copy.deepcopy(ms)
        assert conf['parameters']['response_format']['json_schema']['schema']==schema(item['sentence_index'])
        body={'model':conf['model'],'messages':ms,'stream':False,**conf['parameters']};requests.append({'id':item['id'],'mode':mode,'actual_body_planned':body,'serialized':json.dumps(body,ensure_ascii=False)})
    assert {k:v for k,v in x['configs']['off']['parameters'].items() if k!='chat_template_kwargs'}=={k:v for k,v in x['configs']['on']['parameters'].items() if k!='chat_template_kwargs'}
    inputs.append(x);order.extend({'id':item['id'],'variant':v} for v in (['off','on'] if i%2==0 else ['on','off']))
write(out/'diagnostic-inputs.json',inputs);write(out/'serialized-request-plan.json',requests)
runner=HERE/'diagnose_thinking_modes.py';assert not runner.exists();src=(HERE/'diagnose_sentence_selection.py').read_text(encoding='utf-8')
src=src.replace('from runtime import Engine,TechnicalStop,','from thinking_modes import ThinkingEngine as Engine\nfrom runtime import TechnicalStop,')
src=src.replace('原输出/句子选择对照','同预算开关思考对照')
src=src.replace("    assert load(out/'interface-adapter-check.json')['passed']","    assert load(out/'mode-offline-checks.json')['passed']\n    assert sha(out/'serialized-request-plan.json')==plan['serialized_requests_sha256']")
begin=src.index('    for item in inputs:');end=src.index('    with socket.socket()',begin)
src=src[:begin]+"    from sentence_selection import schema,build_index\n    for item in inputs:\n        assert item['sentence_index']==build_index(item['blocks'],item['doc_ids'],item['snapshot'])\n        assert item['messages']['off']==item['messages']['on']\n        for mode in ['off','on']:\n            conf=item['configs'][mode];assert conf['parameters']['max_tokens']==1024\n            assert conf['parameters']['chat_template_kwargs']=={'enable_thinking':mode=='on'}\n            assert conf['parameters']['presence_penalty']==1.5\n            assert conf['parameters']['response_format']['json_schema']['schema']==schema(item['sentence_index'])\n"+src[end:]
src=src.replace("        record.update(load_seconds=time.perf_counter()-start,memory_after_load=memory());phase='template_preflight'","        assert props['default_generation_settings']['params']['repeat_penalty']==1.0\n        record.update(load_seconds=time.perf_counter()-start,memory_after_load=memory());phase='template_preflight'")
src=src.replace("for variant in ['original','revised']:","for variant in ['off','on']:")
needle="        phase='generation'"
src=src.replace(needle,"        pairs=[]\n        for item in inputs:\n            a=load(out/('capacity-before-'+item['id']+'-off.json'));b=load(out/('capacity-before-'+item['id']+'-on.json'))\n            checks={'same_messages':a['actual_request_body']['messages']==b['actual_request_body']['messages'],'only_false_branch_padding_differs':a['rendered_prompt']==b['rendered_prompt']+'<think>\\n\\n</think>\\n\\n','both_fit':a['fits'] and b['fits']}\n            pairs.append({'id':item['id'],'checks':checks})\n            write(out/'paired-template-verification.json',{'at':now(),'pairs':pairs,'generation_calls':0})\n            if not all(checks.values()):raise TechnicalStop('两侧模板差异不符，已保存完整证据')\n        phase='generation'")
begin=src.index("            if variant=='revised':");end=src.index("            write(out/f'item-",begin)
src=src[:begin]+"            expected=next(x for x in load(out/'serialized-request-plan.json') if x['id']==entry['id'] and x['mode']==variant)\n            params=raw['slot_after'][0].get('params',{})\n            verified={'actual_serialization_matches':raw['actual_http_request_raw']==expected['serialized'],'explicit_boolean_switch':raw['actual_http_request_body']['chat_template_kwargs']=={'enable_thinking':variant=='on'},'request_budget_1024':raw['actual_http_request_body']['max_tokens']==1024,'slot_budget_1024':params.get('max_tokens')==1024,'presence_echo_1_5':params.get('presence_penalty')==1.5,'repeat_echo_1':params.get('repeat_penalty')==1.0}\n            message=raw['response']['choices'][0]['message']\n            write(out/f'mode-observation-{n+1:02}.json',{'at':now(),'verified':verified,'raw_message':message,'reasoning_field_present':'reasoning_content' in message,'reasoning_content':message.get('reasoning_content'),'content':message.get('content'),'usage':raw['usage'],'finish_reason':raw['finish_reason'],'not_echoed':['内部enable_thinking状态','编译grammar与PEG parser对象'],'response_schema_not_inferred_from_format_flags':True})\n            if not all(verified.values()):raise TechnicalStop('实际模式请求或参数不符')\n            from sentence_selection import expand\n            expansion=expand(raw['content'],item['blocks'],item['sentence_index'],item['doc_ids'],item['snapshot'])\n            write(out/f'expansion-{n+1:02}.json',expansion)\n"+src[end:]
ast.parse(src);runner.write_text(src,encoding='utf-8')
launch=copy.deepcopy(oldplan['service_arguments']);assert launch[launch.index('--reasoning')+1]=='off';launch[launch.index('--reasoning')+1]='on'
parts=[]
for x in inputs:
    for mode in ['off','on']:
        m=x['messages'][mode];parts.append('<|im_start|>system\n'+m[0]['content']+'<|im_end|>\n<|im_start|>user\n'+m[1]['content']+'<|im_end|>\n<|im_start|>assistant\n'+('<think>\n\n</think>\n\n' if mode=='off' else ''))
base=Path.home()/'AppData/Local/ANTLabLocalModel';marker='<|endoftext|>';tokens,cmd=native_tokenizer(base/'llama-b11429/llama-tokenize.exe',base/'models/Qwen3-0.6B-Q8_0.gguf',marker+marker.join(parts)+marker,out,'offline-capacity');counts=[];n=0
for token in tokens[1:]:
    if token==tokens[0]:counts.append(n);n=0
    else:n+=1
assert len(counts)==6 and all(n+1024<=4096 for n in counts)
write(out/'mode-offline-checks.json',{'at':now(),'passed':True,'checks':checks,'scope':'只检查构造、映射与来源，真实开关/模板在服务启动后以实际响应核对。'})
write(out/'offline-checks.json',{'at':now(),'passed':True,'checks':checks,'capacity_off_on_each_task':counts,'output_budget_both':1024,'generation_calls':0,'native_schema':'Schema与前轮已验证对象逐字相同；本轮不改Schema。','actual_template_preflight_required':True})
plan={**load(out/'plan-before-checks.json'),'saved_at':now(),'status':'dev_fixed_evidence_diagnostic_not_formal_freeze','order':order,'cumulative_baseline':603,'input_sha256':sha(out/'diagnostic-inputs.json'),'serialized_requests_sha256':sha(out/'serialized-request-plan.json'),'code_hashes':{p.relative_to(ROOT).as_posix():sha(p) for p in HERE.glob('*.py')},'data_hashes':oldplan['data_hashes'],'model_hash':oldplan['model_hash'],'executable_hash':oldplan['executable_hash'],'service_arguments':launch,'prior_common_service_arguments':oldplan['service_arguments'],'output_budget':1024,'no_query_generation':True,'reserve_consumed_this_round':0}
write(out/'intervention-plan.json',plan)
snap=out/'new-code-snapshot';snap.mkdir()
for p in [target,runner]:shutil.copy2(p,snap/p.name)
shutil.copy2(__file__,out/Path(__file__).name)
print(json.dumps({'out':str(out),'checks':{k:v.get('count',v['passed']) for k,v in checks.items()},'capacity_off_on_each_task':counts,'order':order,'generation_calls':0,'additional_future_reserve':30},ensure_ascii=False))
