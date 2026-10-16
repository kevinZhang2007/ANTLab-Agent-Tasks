from pathlib import Path
import sys,json,copy,shutil,subprocess,ast,itertools
from datetime import datetime
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
from sentence_selection import CANDIDATE_PROMPT as CURRENT_PROMPT
from preflight import native_tokenizer
from checks_extended import run as old_checks
out=HERE/'runs'/('relation-first-'+datetime.now().strftime('%Y%m%d-%H%M%S'));out.mkdir();Path('a-relation-out.txt').write_text(str(out),encoding='utf-8')
protected={p.relative_to(ROOT).as_posix():sha(p) for p in HERE.rglob('*') if p.is_file() and out not in p.parents and not {'__pycache__','slot-cache'}&set(p.parts)}
for n in ['README.md','report.md','decisions.md','declaration.md','基础/开发记录.md','基础/starter/student.py','进阶/challenge_b/challenge.py','进阶/challenge_b/no_cache_engine.py']:protected[n]=sha(ROOT/n)
write(out/'protected-before.json',protected)
previous=HERE/'runs/sentence-selection-20261016-130328'
write(out/'current-user-decision.json',{'at':now(),'source':'本轮本人明确指示','decision':'接受额外耗时，保留句子选择机制的来源可靠性收益，作为当前开发基础机制。','prior_conclusion_preserved':{'path':(previous/'review.json').relative_to(ROOT).as_posix(),'sha256':sha(previous/'review.json'),'conclusion':'按此前严格成功优先、标签其次且同分保留旧的标准，句子机制未胜出。该结论不覆盖。'},'not_claimed':'未提高答案正确率或严格成功率，不把当前取舍追溯成过去标准下胜出。','new_selection_rule':'本轮标签正确优先，既有正确项不得退步，同分再比较严格成功与引用质量；生成前登记，不改历史。','budget':{'original_A_cap':54,'A_used_before':42,'remaining_before':12,'this_round_cap':6,'cumulative_before':576,'cap_increase_now':0,'reason':'本轮6次仍在原54内，无需扩额；超额许可未提前算作已使用调用。'}})
p=HERE/'relation_first.py';assert not p.exists();ast.parse(Path('a_relation_first.py').read_text(encoding='utf-8'));shutil.copy2('a_relation_first.py',p)
from relation_first import PROMPT,schema,messages,offline_checks
checks=offline_checks();assert checks['passed'];prior=old_checks(out);assert prior['passed']==35
prior_inputs=load(previous/'diagnostic-inputs.json');inputs=[];cases=[]
for item in prior_inputs:
    baseline=copy.deepcopy(item['messages']['revised']);assert baseline[0]['content']==CURRENT_PROMPT
    new=messages(baseline);old_conf=copy.deepcopy(item['configs']['revised']);old_conf['parameters']['max_tokens']=512;new_conf=copy.deepcopy(old_conf);new_conf['parameters']['response_format']['json_schema']['schema']=schema(item['sentence_index'])
    inputs.append({'id':item['id'],'claim':item['claim'],'doc_ids':item['doc_ids'],'snapshot':item['snapshot'],'blocks':item['blocks'],'sentence_index':item['sentence_index'],'messages':{'original':baseline,'revised':new},'configs':{'original':old_conf,'revised':new_conf},'origin':item['origin']})
    sample={'relation':'undetermined','explanation':'synthetic structure test','sentence_ids':[],'label':'insufficient'}
    fixtures=[]
    for order in itertools.permutations(sample):fixtures.append({'name':'order_'+'_'.join(order),'response':{k:sample[k] for k in order},'accept':list(order)==['relation','explanation','sentence_ids','label']})
    mismatch={'relation':'conflicts','explanation':'synthetic mismatch must not be grammar-corrected','sentence_ids':[],'label':'supported'}
    fixtures.append({'name':'inconsistent_labels_still_schema_valid','response':mismatch,'accept':True})
    fixtures.append({'name':'unknown_sentence_rejected','response':{'relation':'entails','explanation':'synthetic','sentence_ids':['foreign-id'],'label':'supported'},'accept':False})
    cases.append({'name':item['id'],'schema':schema(item['sentence_index']),'fixtures':fixtures})
write(out/'diagnostic-inputs.json',inputs);write(out/'schema-cases.json',cases)
# 先实际编译根规则；不凭properties顺序推断。
native_source=(HERE/'check_id_enum_native.py').read_text(encoding='utf-8');prefix=native_source[:native_source.index("cases=json.loads((folder/'schema-cases.json')")]
compile_source=prefix+"\ncases=json.loads((folder/'schema-cases.json').read_text(encoding='utf-8'))\nrows=[]\nfor item in cases:\n    grammar=native_convert(item['schema']);(folder/('compiled-'+item['name']+'.gbnf')).write_text(grammar,encoding='utf-8')\n    root_line=next(line for line in grammar.splitlines() if line.startswith('root ::='))\n    fields=['relation','explanation','sentence_ids','label'];positions=[root_line.find(k+'-kv') for k in fields]\n    forced=all(x>=0 for x in positions) and positions==sorted(positions) and root_line.count('-kv')==4 and '|' not in root_line\n    rows.append({'case':item['name'],'root':root_line,'positions':positions,'forced':forced})\nsave('schema-order-compilation.json',{'at':datetime.now().astimezone().isoformat(),'rows':rows,'all_forced':all(x['forced'] for x in rows),'generation_calls':0})\nhandles.close()\n"
cp=out/'compile_schema_order.py';cp.write_text(compile_source,encoding='utf-8');ast.parse(compile_source)
cmd=[sys.executable,'-X','utf8','-B',str(cp),str(out)];r=subprocess.run(cmd,capture_output=True);(out/'compile.stdout.txt').write_bytes(r.stdout);(out/'compile.stderr.txt').write_bytes(r.stderr);assert r.returncode==0
order=load(out/'schema-order-compilation.json')
if not order['all_forced']:
    write(out/'order-not-forced-stop.json',{'at':now(),'reason':'实际Schema根规则未保证所需顺序，尚未生成；不自动换协议，不声称关系先于label。','generation_calls':0,'compilation':order});print(json.dumps({'out':str(out),'order_forced':False,'generated':0},ensure_ascii=False));sys.exit(0)
cmd=[sys.executable,'-X','utf8','-B',str(HERE/'check_id_enum_native.py'),str(out)];r=subprocess.run(cmd,capture_output=True);(out/'native-order.stdout.txt').write_bytes(r.stdout);(out/'native-order.stderr.txt').write_bytes(r.stderr)
write(out/'native-order-command.json',{'at':now(),'command':cmd,'exit':r.returncode,'generation_calls':0});assert r.returncode==0 and load(out/'native-id-enum-validation.json')['passed']
write(out/'relation-offline-checks.json',checks)
runner=HERE/'diagnose_relation_first.py';assert not runner.exists();src=(HERE/'diagnose_sentence_selection.py').read_text(encoding='utf-8')
begin=src.index('        from sentence_selection import build_index,adapt_messages,schema');end=src.index('    with socket.socket()',begin)
src=src[:begin]+"        from sentence_selection import build_index\n        from relation_first import messages,schema\n        assert item['sentence_index']==build_index(item['blocks'],item['doc_ids'],item['snapshot'])\n        assert item['messages']['revised']==messages(item['messages']['original'])\n        assert item['configs']['revised']['parameters']['response_format']['json_schema']['schema']==schema(item['sentence_index'])\n        assert {k:v for k,v in item['configs']['original']['parameters'].items() if k!='response_format'}=={k:v for k,v in item['configs']['revised']['parameters'].items() if k!='response_format'}\n"+src[end:]
src=src.replace("    assert load(out/'interface-adapter-check.json')['passed']","    assert load(out/'relation-offline-checks.json')['passed']\n    assert load(out/'native-id-enum-validation.json')['passed']\n    assert load(out/'schema-order-compilation.json')['all_forced']")
begin=src.index("            if variant=='revised':");end=src.index("            write(out/f'item-",begin)
src=src[:begin]+"            if variant=='revised':\n                from relation_first import expand\n            else:\n                from sentence_selection import expand\n            expansion=expand(raw['content'],item['blocks'],item['sentence_index'],item['doc_ids'],item['snapshot'])\n            write(out/f'expansion-{n+1:02}.json',expansion)\n"+src[end:]
ast.parse(src);runner.write_text(src,encoding='utf-8')
launch_plan=load(previous/'intervention-plan.json');launch=launch_plan['service_arguments'];parts=[]
for item in inputs:
    for v in ['original','revised']:
        ms=item['messages'][v];parts.append('<|im_start|>system\n'+ms[0]['content']+'<|im_end|>\n<|im_start|>user\n'+ms[1]['content']+'<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n')
marker='<|endoftext|>';base=Path.home()/'AppData/Local/ANTLabLocalModel';ids,cmd=native_tokenizer(base/'llama-b11429/llama-tokenize.exe',Path(launch[launch.index('-m')+1]),marker+marker.join(parts)+marker,out,'native-relation-capacity');sep=ids[0];counts=[];n=0
for x in ids[1:]:
    if x==sep:counts.append(n);n=0
    else:n+=1
assert len(counts)==6 and all(n+512+64<=4096 for n in counts)
definitions=[{'text':'All changes must be documented.','claim':'Changes need not be documented.','expected_relation':'conflicts','scope':'自造定义例，不进真实请求。'},{'text':'The file is readable; execution is not described.','claim':'The file can execute the analysis.','expected_relation':'undetermined','scope':'未提到不当反证。'},{'text':'Retaining a summary is recommended, not mandatory.','claim':'A summary is recommended.','expected_relation':'entails','scope':'不将建议强化为强制。'}]
write(out/'offline-checks.json',{'at':now(),'passed':True,'prior_regression':prior,'relation_checks':checks,'native_order_cases':len(load(out/'native-id-enum-validation.json')['tests']),'definitions':definitions,'capacity_tokens':counts,'output_budget_both':512,'extra_margin':64,'generation_calls':0,'scope':'模型关系语义是否正确仍须调用后原文复核；原生顺序只保证输出字段次序，不证明内部思维顺序。'})
plan={'saved_at':now(),'status':'development_diagnostic_not_formal_freeze','hypothesis':'把关系显式放在label之前可能减少否定方向与标签不一致。','competing_explanation':'模型可能先形成错误判断再生成一致关系/理由；强制字段次序不证明真实认知流程，索引缺证或语义错误仍可能存在。','current_user_decision':'current-user-decision.json','selection':'标签正确数优先且不得损害已有正确项，同分再比较严格成功与引用质量；生成前固定，仅用于本轮，不改历史选择结论。','baseline_prompt':CURRENT_PROMPT,'candidate_prompt':PROMPT,'schema_order_forced_by_native_grammar':True,'relation_label_independent_in_schema':True,'mismatch_policy':'保存真实relation和label，标quality_failure，不按relation自动改label；展开仅所选片段，不新增证据。','evidence_origin':'同一批首轮自动improved证据、原中文主张、同一完整句子索引；不重新检索/人工替换，不是端到端成绩。','order':[{'id':x['id'],'variant':v} for i,x in enumerate(inputs) for v in (['original','revised'] if i%2==0 else ['revised','original'])],'generation_cap':6,'cumulative_baseline':576,'A_used_before':42,'A_remaining_before':12,'A_original_cap':54,'budget_cap_revision_this_round':0,'output_budget_both':512,'historical_budget':256,'budget_comparison_limit':'本轮两侧512相同；与历史256比较不是单一关系因素对照。','evaluation':'标签正确、关系正确、关系标签一致、理由原文事实、引用来源/必要覆盖/支持/无关引用、严格成功和耗时分列。baseline无relation记not_applicable，不由label反推关系充当独立正确关系。3题分母保持；AD03不可见目标原文不得补模型证据。','stopping':'加载前2GiB；运行连续3个2秒样本低于1GiB停自有PID；完整模板检查通过才生成。技术失败停止不自动重发；质量失败不重试。','input_sha256':sha(out/'diagnostic-inputs.json'),'code_hashes':{p.relative_to(ROOT).as_posix():sha(p) for p in HERE.glob('*.py')},'data_hashes':launch_plan['data_hashes'],'model_hash':launch_plan['model_hash'],'executable_hash':launch_plan['executable_hash'],'service_arguments':launch,'no_AT_read':True}
write(out/'intervention-plan.json',plan)
write(out/'planned-request-differences.json',[{'id':x['id'],'baseline_messages':x['messages']['original'],'candidate_messages':x['messages']['revised'],'same_user_full_evidence_sentence_index':x['messages']['original'][1:]==x['messages']['revised'][1:],'baseline_schema':x['configs']['original']['parameters']['response_format'],'candidate_schema':x['configs']['revised']['parameters']['response_format'],'same_numeric_parameters':{k:v for k,v in x['configs']['original']['parameters'].items() if k!='response_format'}=={k:v for k,v in x['configs']['revised']['parameters'].items() if k!='response_format'}} for x in inputs])
snap=out/'code-snapshot';snap.mkdir()
for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'));shutil.copy2(p,snap/p.name)
print(json.dumps({'out':str(out),'native_order_forced':True,'native_cases':len(load(out/'native-id-enum-validation.json')['tests']),'checks':35+checks['count'],'capacity':counts,'budget_both':512,'generated':0,'plan_saved':True},ensure_ascii=False))
