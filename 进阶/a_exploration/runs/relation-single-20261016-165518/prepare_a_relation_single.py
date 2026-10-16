from pathlib import Path
import sys,json,copy,subprocess,shutil,ast,difflib
from datetime import datetime
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
from preflight import native_tokenizer
out=HERE/'runs'/('relation-single-'+datetime.now().strftime('%Y%m%d-%H%M%S'));out.mkdir();Path('a-relation-single-out.txt').write_text(str(out),encoding='utf-8')
protected={p.relative_to(ROOT).as_posix():sha(p) for p in HERE.rglob('*') if p.is_file() and out not in p.parents and not {'slot-cache','__pycache__'}&set(p.parts)}
for name in ['README.md','report.md','decisions.md','declaration.md','基础/开发记录.md','基础/starter/student.py','进阶/challenge_b/challenge.py','进阶/challenge_b/no_cache_engine.py']:protected[name]=sha(ROOT/name)
write(out/'protected-before.json',protected)
write(out/'plan-before-checks.json',{'at':now(),'baseline_cumulative':585,'A_used_before':51,'A_cap':90,'A_remaining_before':39,'generation_cap':6,'hypothesis':'取消第二次label生成、固定映射能消除关系标签矛盾；能否改善语义需另行评价。','competing_explanation':'关系本身可能错误，确定性映射会忠实传播错误；理由也可能与关系冲突，程序不作语义修正。','selection':'严格成功优先，其次外部标签正确；既有成功项不得退步，同分保留当前句子流程。','stopping':'技术请求失败停止不自动重发；质量失败保留不重试。加载前2GiB，连续3个2秒样本低于1GiB停止本轮自有服务。','evidence':'同一已归档自动improved证据、原中文主张、句子索引；不查询、不用人工充分证据，不是端到端检索成绩。','historical':'先零生成回放历史relation-first三条，不覆盖旧评价。','semantic_evaluation':'模型原始关系正确、映射标签正确、理由关系一致、来源真实、必要覆盖、引用支持、严格成功分列；只原文辅助评价，不用程序映射正确替代语义判断。','no_AT_read':True})
target=HERE/'relation_single.py';assert not target.exists();ast.parse(Path('a_relation_single.py').read_text(encoding='utf-8'));shutil.copy2('a_relation_single.py',target)
from relation_single import PROMPT,RELATION_TO_LABEL,schema,messages,expand,offline_checks
from sentence_selection import offline_checks as sentence_checks
from sentence_interface import offline_checks as interface_checks
from relation_first import offline_checks as old_relation_checks
from checks_extended import run as existing_checks
checks={'candidate':offline_checks(),'sentence':sentence_checks(),'interface':interface_checks(),'previous_relation':old_relation_checks(),'existing':existing_checks(out)}
assert all(x['passed'] for x in checks.values())
common=ROOT/'进阶/00_共同规则与接口.md';task=ROOT/'进阶/01_A_研究机制迁移.md'
write(out/'interface-adaptation-evidence.json',{'at':now(),'sources':[{'path':common.relative_to(ROOT).as_posix(),'sha256':sha(common),'lines':'13-20','original':['接口路径自由，README给出映射。','- judgment_source：rule / model / human / unverified。人工评测标签不得伪装为系统输出，模型自评不能作为唯一金标准。','- run_kind：live_api / offline_replay / dry_run / local_rule。成本、延迟按类型分别报告。']},{'path':task.relative_to(ROOT).as_posix(),'sha256':sha(task),'line':27,'original':'判定类别为supported/contradicted/insufficient；系统尚不能判断可用not_checked。系统结果、人工评价、模型裁判分开。'}],'conclusion':'未发现内部relation再适配外部规定类别的明确冲突；外部仍为label/reason/evidence及共同字段。只记录接口技术兼容，不宣称A+B或本地服务验收边界已获认可。','mapping_provenance':'模型只生成relation；外部标签由local_rule固定映射，语义support_status保持not_checked，模型请求run_kind=live_api；两者分别保存。','no_semantic_rule_claim':True})
previous=HERE/'runs/relation-first-20261016-131824';old_inputs=load(previous/'diagnostic-inputs.json');old_review=load(previous/'review.json');hist=[]
for n,e in enumerate([load(p) for p in sorted(previous.glob('item-*.json')) if load(p)['variant']=='revised'],1):
    raw=load(previous/e['raw_record']);obj=json.loads(raw['content']);inp=next(x for x in old_inputs if x['id']==e['id'])
    projected={'relation':obj['relation'],'reason':obj['explanation'],'sentence_ids':obj['sentence_ids']};mapped=expand(json.dumps(projected,ensure_ascii=False),inp['blocks'],inp['sentence_index'],inp['doc_ids'],inp['snapshot']);old=next(x for x in old_review['rows'] if x['run_id']==e['run_id'])
    assert mapped['valid'] and mapped['mapped_label']==RELATION_TO_LABEL[obj['relation']]
    row={'at':now(),'id':e['id'],'source_raw_path':(previous/e['raw_record']).relative_to(ROOT).as_posix(),'source_raw_sha256':sha(previous/e['raw_record']),'original_response':raw['raw_response'],'original_content':raw['content'],'original_relation':obj['relation'],'original_label':obj['label'],'original_explanation':obj['explanation'],'projection_note':'历史explanation逐字投影为reason，不改变文字；原始四字段响应完整保留。','mapping':mapped,'derived_response':mapped['expanded_response'],'derived_label_origin':'local_rule_mapping_from_historical_model_relation','mapping_consistent':True,'relation_correct':old['relation_correct_from_actual_input'],'external_label_correct':mapped['mapped_label']==old['public_reference_label'],'original_label_correct':old['label_correct'],'necessary_coverage':old['necessary_evidence_coverage'],'citation_support_after_mapping':False,'strict_success_after_mapping':False,'basis':{'AD01':'关系entails仍错，映射后仍supported；所选直接反证不能支持无需记录。','AD02':'entails映射supported后外部标签符合参考，但原先只选两个泛泛引言，没有Read与Run关键证据。映射未修正解释事实或补证，不算严格成功。','AD03':'entails映射仍supported，所选程序版本及检查详细值不支持只留图足够。'}[e['id']],'generation_calls':0,'reviewer':'Codex原文辅助复核，尚待本人确认'}
    hist.append(row);write(out/f'historical-map-{n:02}.json',row)
write(out/'historical-mapping-summary.json',{'at':now(),'rows':hist,'mapping_consistency':3,'denominator':3,'original_label_correct':0,'mapped_external_label_correct':1,'relation_correct':1,'strict_success':0,'new_generations':0,'historical_evaluation_unchanged':True,'not_new_model_accuracy':'新增的是程序映射标签，不能当成模型重新生成label或本轮同步对照成绩。'})
inputs=[];cases=[]
for item in old_inputs:
    current=copy.deepcopy(item['messages']['original']);conf=copy.deepcopy(item['configs']['original']);assert conf['parameters']['max_tokens']==512
    newconf=copy.deepcopy(conf);newconf['parameters']['response_format']['json_schema']['schema']=schema(item['sentence_index'])
    x={'id':item['id'],'claim':item['claim'],'doc_ids':item['doc_ids'],'snapshot':item['snapshot'],'blocks':item['blocks'],'sentence_index':item['sentence_index'],'messages':{'original':current,'revised':messages(current)},'configs':{'original':conf,'revised':newconf},'origin':item['origin']};inputs.append(x)
    for variant in ['original','revised']:
        sch=x['configs'][variant]['parameters']['response_format']['json_schema']['schema'];fixtures=[];sid=item['sentence_index'][0]['sentence_id']
        def value(rel='entails',ids=None):return {'relation':rel,'reason':'self-made structure check','sentence_ids':[sid] if ids is None else ids} if variant=='revised' else {'label':RELATION_TO_LABEL.get(rel,rel),'reason':'self-made structure check','sentence_ids':[sid] if ids is None else ids}
        for rel in RELATION_TO_LABEL:fixtures.append({'name':rel+'_valid','response':value(rel),'accept':True})
        for name,val,accept in [('unknown_id',value(ids=['missing']),False),('illegal_value',value('undefined'),False),('duplicate_id_program_rejects',value(ids=[sid,sid]),True),('empty_valid',value(ids=[]),True),('extra_field',{**value(),'extra':1},False)]:fixtures.append({'name':name,'response':val,'accept':accept})
        cases.append({'name':item['id']+'-'+variant,'schema':sch,'fixtures':fixtures})
write(out/'diagnostic-inputs.json',inputs);write(out/'schema-cases.json',cases)
cmd=[sys.executable,'-X','utf8','-B',str(HERE/'check_id_enum_native.py'),str(out)];r=subprocess.run(cmd,capture_output=True);(out/'native.stdout.txt').write_bytes(r.stdout);(out/'native.stderr.txt').write_bytes(r.stderr);write(out/'native-command.json',{'at':now(),'command':cmd,'exit_code':r.returncode,'generation_calls':0});assert r.returncode==0 and load(out/'native-id-enum-validation.json')['passed']
runner=HERE/'diagnose_relation_single.py';assert not runner.exists();src=(HERE/'diagnose_relation_first.py').read_text(encoding='utf-8');src=src.replace('from relation_first import','from relation_single import').replace("assert load(out/'relation-offline-checks.json')['passed']","assert load(out/'single-offline-checks.json')['passed']").replace("    assert load(out/'schema-order-compilation-corrected.json')['all_forced']\n",'');ast.parse(src);runner.write_text(src,encoding='utf-8')
write(out/'single-offline-checks.json',{'at':now(),'passed':True,'checks':checks,'interface_checked':True,'historical_mapping_saved':True})
oldplan=load(previous/'intervention-plan.json');launch=oldplan['service_arguments'];parts=[]
for x in inputs:
    for v in ['original','revised']:
        m=x['messages'][v];parts.append('<|im_start|>system\n'+m[0]['content']+'<|im_end|>\n<|im_start|>user\n'+m[1]['content']+'<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n')
base=Path.home()/'AppData/Local/ANTLabLocalModel';marker='<|endoftext|>';ids,command=native_tokenizer(base/'llama-b11429/llama-tokenize.exe',base/'models/Qwen3-0.6B-Q8_0.gguf',marker+marker.join(parts)+marker,out,'offline-capacity');counts=[];n=0
for token in ids[1:]:
    if token==ids[0]:counts.append(n);n=0
    else:n+=1
assert len(counts)==6 and all(n+512+64<=4096 for n in counts)
write(out/'offline-checks.json',{'at':now(),'passed':True,'checks':checks,'native_cases':len(load(out/'native-id-enum-validation.json')['tests']),'capacity':counts,'output_budget_both':512,'extra_margin':64,'generation_calls':0,'scope':'结构和来源门禁不代表语义正确。'})
plan={**load(out/'plan-before-checks.json'),'saved_at':now(),'status':'development_diagnostic_not_formal_freeze','baseline_prompt':inputs[0]['messages']['original'][0]['content'],'candidate_prompt':PROMPT,'mapping':RELATION_TO_LABEL,'order':[{'id':x['id'],'variant':v} for i,x in enumerate(inputs) for v in (['original','revised'] if i%2==0 else ['revised','original'])],'cumulative_baseline':585,'input_sha256':sha(out/'diagnostic-inputs.json'),'code_hashes':{p.relative_to(ROOT).as_posix():sha(p) for p in HERE.glob('*.py')},'data_hashes':oldplan['data_hashes'],'model_hash':oldplan['model_hash'],'executable_hash':oldplan['executable_hash'],'service_arguments':launch,'output_budget_both':512,'no_query_generation':True,'evaluation_note':'baseline无relation记not_applicable；新侧relation模型原始、label程序派生，理由关系冲突人工记质量失败不翻转。外部标签正确与映射正确分开。'}
write(out/'intervention-plan.json',plan)
write(out/'planned-request-differences.json',[{'id':x['id'],'same_user_and_original_evidence_index':x['messages']['original'][1:]==x['messages']['revised'][1:],'same_sampling':{k:v for k,v in x['configs']['original']['parameters'].items() if k!='response_format'}=={k:v for k,v in x['configs']['revised']['parameters'].items() if k!='response_format'},'baseline_messages':x['messages']['original'],'candidate_messages':x['messages']['revised'],'baseline_schema':x['configs']['original']['parameters']['response_format'],'candidate_schema':x['configs']['revised']['parameters']['response_format']} for x in inputs])
snap=out/'code-snapshot';snap.mkdir()
for p in HERE.glob('*.py'):shutil.copy2(p,snap/p.name)
shutil.copy2(__file__,out/Path(__file__).name)
print(json.dumps({'out':str(out),'checks':{k:v.get('count',v['passed']) for k,v in checks.items()},'native_cases':len(load(out/'native-id-enum-validation.json')['tests']),'capacity':counts,'historical_mapped_labels_correct':1,'generated':0,'ready':True},ensure_ascii=False))
