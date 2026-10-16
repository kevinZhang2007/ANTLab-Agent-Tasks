from pathlib import Path
import sys,json,copy,shutil,subprocess,ast
from datetime import datetime
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
from preflight import native_tokenizer
out=HERE/'runs'/('compact-penalty-'+datetime.now().strftime('%Y%m%d-%H%M%S'));out.mkdir();Path('a-compact-factorial-out.txt').write_text(str(out),encoding='utf-8')
protected={p.relative_to(ROOT).as_posix():sha(p) for p in HERE.rglob('*') if p.is_file() and out not in p.parents and not {'slot-cache','__pycache__'}&set(p.parts)}
for n in ['README.md','report.md','decisions.md','declaration.md','基础/开发记录.md','基础/starter/student.py','进阶/challenge_b/challenge.py','进阶/challenge_b/no_cache_engine.py']:protected[n]=sha(ROOT/n)
write(out/'protected-before.json',protected)
names=['repeated_15','compact_15','repeated_0','compact_0']
write(out/'plan-before-checks.json',{'at':now(),'status':'此时仅已写独立紧凑函数，尚未执行离线检查或模型生成','factors':{'A':'重复原JSON/紧凑原文并把claim移到最后，属于输入组织整体因素，不能单独归因去重。','B':'请求presence_penalty明确1.5/0，其余不变，不预称修复惩罚。'},'hypothesis':'紧凑组织可能减少冗余输入成本；presence=0可能减少生成中对已出现词的惩罚。语义和引用质量均可能不改善或退步。','competing_explanation':'表示及主张位置共同改变，输出变化也可能来自提示理解、缺证或随机采样；三题每组合一次不能外推通用作用。','variants':names,'selection':'严格成功优先，其次标签正确，引用来源真实性不能退步；质量相同仅在实测输入或成本降低时可选择紧凑表示作为效率取舍，不称正确率提升。完全同分惩罚参数保留原1.5。','planned_order':'按开发题顺序，每题四组合按names左移题目序号位后依次执行；不按输出追加或调序。','baseline_cumulative':591,'A_used_before':57,'A_cap':90,'A_remaining_before':33,'generation_cap':12,'budget_both':512,'no_new_query':True,'evaluation':'标签、理由标签一致、来源、必要覆盖、支持、无关、严格成功、tokens及完整HTTP耗时分列；程序不翻转语义。','stopping':'技术请求失败立即停止，不自动重发；质量错误保留不重试；加载前2GiB，运行连续3个2秒样本低于1GiB停止本轮自有PID。','guard_architecture':'旧runtime.Engine每实例9次上限保留，独立运行器按题使用三个实例各最多4次；外层总上限12，统一服务和逐请求记录，不重置已执行记录。','AT_read':False})
target=HERE/'compact_factorial.py';assert not target.exists();ast.parse(Path('a_compact_factorial.py').read_text(encoding='utf-8'));shutil.copy2('a_compact_factorial.py',target)
from compact_factorial import compact_messages,audit,offline_checks
from sentence_selection import offline_checks as sentence_checks,schema,build_index
from sentence_interface import offline_checks as interface_checks
from checks_extended import run as old_checks
checks={'compact':offline_checks(),'sentence':sentence_checks(),'interface':interface_checks(),'existing':old_checks(out)};assert all(x['passed'] for x in checks.values())
previous=HERE/'runs/relation-single-20261016-165518';base_inputs=load(previous/'diagnostic-inputs.json');oldplan=load(previous/'intervention-plan.json');inputs=[];serialized=[];order=[];audits=[]
for i,item in enumerate(base_inputs):
    current=copy.deepcopy(item['messages']['original']);compact=compact_messages(current,item['blocks'],item['sentence_index'],item['doc_ids'],item['snapshot']);proof=audit(compact,item['blocks'],item['sentence_index'],item['doc_ids'],item['snapshot'])
    assert current[0]==compact[0] and json.loads(current[1]['content'])['claim']==json.loads(compact[1]['content'])['claim']==item['claim']
    conf0=copy.deepcopy(item['configs']['original']);assert conf0['parameters']['max_tokens']==512 and conf0['parameters']['presence_penalty']==1.5 and 'repeat_penalty' not in conf0['parameters']
    x={'id':item['id'],'claim':item['claim'],'doc_ids':item['doc_ids'],'snapshot':item['snapshot'],'blocks':item['blocks'],'sentence_index':item['sentence_index'],'messages':{},'configs':{},'origin':item['origin']}
    for name in names:
        x['messages'][name]=copy.deepcopy(compact if name.startswith('compact') else current);conf=copy.deepcopy(conf0);conf['parameters']['presence_penalty']=1.5 if name.endswith('15') else 0;x['configs'][name]=conf
        assert conf['parameters']['response_format']['json_schema']['schema']==schema(item['sentence_index'])
        assert {k:v for k,v in conf['parameters'].items() if k!='presence_penalty'}=={k:v for k,v in conf0['parameters'].items() if k!='presence_penalty'}
        body={'model':conf['model'],'messages':x['messages'][name],'stream':False,**conf['parameters']}
        serialized.append({'id':item['id'],'variant':name,'body':body,'serialized_utf8':json.dumps(body,ensure_ascii=False),'body_sha256':__import__('hashlib').sha256(json.dumps(body,ensure_ascii=False).encode('utf-8')).hexdigest()})
    inputs.append(x);audits.append({'id':item['id'],'compact':proof,'same_sentence_schema':True,'same_system':True,'source_claim_occurrences':current[1]['content'].count(item['claim']),'compact_claim_occurrences':compact[1]['content'].count(item['claim'])})
    rotated=names[i:]+names[:i];order.extend({'id':item['id'],'variant':v} for v in rotated)
write(out/'diagnostic-inputs.json',inputs);write(out/'serialized-request-plan.json',serialized);write(out/'byte-and-scope-audit.json',{'at':now(),'passed':True,'rows':audits,'source_index':'完整字符位置和分句规则仅在服务端diagnostic-inputs中留存，紧凑模型输入不含这些字段。'})
runner=HERE/'diagnose_compact_factorial.py';assert not runner.exists();src=(HERE/'diagnose_sentence_selection.py').read_text(encoding='utf-8')
src=src.replace('原输出/句子选择对照','输入组织×presence惩罚四组合对照')
src=src.replace("    assert load(out/'interface-adapter-check.json')['passed']","    assert load(out/'byte-and-scope-audit.json')['passed']")
begin=src.index('    for item in inputs:');end=src.index('    with socket.socket()',begin)
src=src[:begin]+"    from compact_factorial import compact_messages,audit\n    from sentence_selection import schema,build_index\n    for item in inputs:\n        assert item['sentence_index']==build_index(item['blocks'],item['doc_ids'],item['snapshot'])\n        expected=compact_messages(item['messages']['repeated_15'],item['blocks'],item['sentence_index'],item['doc_ids'],item['snapshot'])\n        for variant in item['messages']:\n            conf=item['configs'][variant];assert conf['parameters']['max_tokens']==512\n            assert conf['parameters']['response_format']['json_schema']['schema']==schema(item['sentence_index'])\n            assert item['messages'][variant]==(expected if variant.startswith('compact') else item['messages']['repeated_15'])\n            assert conf['parameters']['presence_penalty']==(1.5 if variant.endswith('15') else 0)\n            if variant.startswith('compact'):audit(item['messages'][variant],item['blocks'],item['sentence_index'],item['doc_ids'],item['snapshot'])\n"+src[end:]
src=src.replace('(out/\'slot-cache\').mkdir();engine=Engine(out);',"(out/'slot-cache').mkdir();engine=Engine(out);clients={};")
src=src.replace("        record.update(load_seconds=time.perf_counter()-start,memory_after_load=memory());phase='template_preflight'","        assert props['default_generation_settings']['params']['repeat_penalty']==1.0\n        record.update(load_seconds=time.perf_counter()-start,memory_after_load=memory());phase='template_preflight'")
src=src.replace("for variant in ['original','revised']:","for variant in item['messages']:")
src=src.replace("            if engine.dispatches>=6:raise TechnicalStop('达到6次上限')","            if sum(c.dispatches for c in clients.values())>=12:raise TechnicalStop('达到12次总上限')")
src=src.replace("            raw=engine.generate(","            if entry['id'] not in clients:clients[entry['id']]=Engine(out)\n            client=clients[entry['id']]\n            if client.dispatches>=4:raise TechnicalStop('达到单题4次上限')\n            raw=client.generate(")
begin=src.index("            if variant=='revised':");end=src.index("            write(out/f'item-",begin)
src=src[:begin]+"            expected=next(x for x in load(out/'serialized-request-plan.json') if x['id']==entry['id'] and x['variant']==variant)\n            params=raw['slot_after'][0].get('params',{})\n            verified={'actual_serialization_matches_plan':raw['actual_http_request_raw']==expected['serialized_utf8'],'presence_explicit_in_request':raw['actual_http_request_body']['presence_penalty']==item['configs'][variant]['parameters']['presence_penalty'],'presence_echo_matches':params.get('presence_penalty')==item['configs'][variant]['parameters']['presence_penalty'],'repeat_penalty_echo_1':params.get('repeat_penalty')==1.0,'budget_request_512':raw['actual_http_request_body']['max_tokens']==512,'slot_budget_512':params.get('max_tokens')==512}\n            write(out/f'parameter-check-{n+1:02}.json',verified)\n            if not all(verified.values()):raise TechnicalStop('请求序列化或惩罚回显不符')\n            from sentence_selection import expand\n            expansion=expand(raw['content'],item['blocks'],item['sentence_index'],item['doc_ids'],item['snapshot'])\n            write(out/f'expansion-{n+1:02}.json',expansion)\n"+src[end:]
src=src.replace('engine.dispatches','sum(c.dispatches for c in clients.values())').replace('engine.completed','sum(c.completed for c in clients.values())')
ast.parse(src);runner.write_text(src,encoding='utf-8')
parts=[]
for x in inputs:
    for variant in ['repeated_15','compact_15']:
        m=x['messages'][variant];parts.append('<|im_start|>system\n'+m[0]['content']+'<|im_end|>\n<|im_start|>user\n'+m[1]['content']+'<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n')
base=Path.home()/'AppData/Local/ANTLabLocalModel';marker='<|endoftext|>';tokens,cmd=native_tokenizer(base/'llama-b11429/llama-tokenize.exe',base/'models/Qwen3-0.6B-Q8_0.gguf',marker+marker.join(parts)+marker,out,'offline-capacity');counts=[];n=0
for token in tokens[1:]:
    if token==tokens[0]:counts.append(n);n=0
    else:n+=1
assert len(counts)==6 and all(n+512+64<=4096 for n in counts)
write(out/'offline-checks.json',{'at':now(),'passed':True,'checks':checks,'capacity':counts,'counts_order':'每题重复/紧凑，惩罚变化不改变离线模板正文；服务启动后实际12项模板逐一检查','output_budget':512,'extra_margin':64,'generation_calls':0,'schema_unchanged':'实际Schema逐项等于此前已原生验证的当前句子方案；未新增Schema结构。'})
plan={**load(out/'plan-before-checks.json'),'saved_at':now(),'status':'development_factorial_not_formal_freeze','order':order,'cumulative_baseline':591,'input_sha256':sha(out/'diagnostic-inputs.json'),'serialized_requests_sha256':sha(out/'serialized-request-plan.json'),'code_hashes':{p.relative_to(ROOT).as_posix():sha(p) for p in HERE.glob('*.py')},'data_hashes':oldplan['data_hashes'],'model_hash':oldplan['model_hash'],'executable_hash':oldplan['executable_hash'],'service_arguments':oldplan['service_arguments'],'context':4096,'repeat_penalty':1.0,'reasoning':'off','output_budget':512,'selection_tie':'质量与引用相同且紧凑实测减少输入tokens时可作效率选择；惩罚同质量保留原1.5，不把词项/时延变化称通用能力改善。'}
write(out/'intervention-plan.json',plan)
snap=out/'new-code-snapshot';snap.mkdir()
for p in [target,runner]:shutil.copy2(p,snap/p.name)
shutil.copy2(__file__,out/Path(__file__).name)
print(json.dumps({'out':str(out),'checks':{k:v.get('count',v['passed']) for k,v in checks.items()},'capacity_repeated_compact':counts,'order':order,'generated':0,'ready':True},ensure_ascii=False))
