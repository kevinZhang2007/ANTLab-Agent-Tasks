from pathlib import Path
import sys,json,ast,copy,shutil,subprocess
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now,config
from preflight import native_tokenizer
out=Path(Path('a-query-translation-out.txt').read_text(encoding='utf-8').strip());replay=load(out/'offline-retrieval-replay.json')
audit=[]
for x in replay['rows']:
    required={'AD01':['P1-S03-p01'],'AD02':['P2-S10-p02','P2-S10-p03'],'AD03':['P1-S08-p01']}[x['id']]
    scores={}
    for variant,a in x['arms'].items():
        scores[variant]={arm:{'required_blocks':required,'present_required':[b for b in required if b in {p['block_id'] for p in a[arm]}],'complete':set(required)<={b['block_id'] for b in a[arm]}} for arm in ['baseline','improved']}
    audit.append({'id':x['id'],'scores':scores,'basis':{'AD01':'P1-S03最后一句明确要求记录修改或移动文件及目的；新旧均在。','AD02':'Read静态导出与Run环境段组合，新旧improved均在；两侧baseline仍缺Run。新译文增加Modularize code段及其邻段，为主题相关但不能代替Read/Run判断的干扰。','AD03':'公开开发指定S08中明确讨论底层数据、处理值和重建依据；旧侧缺，新译文检索第1位命中。其他流程记录段不能替代它。'}[x['id']],'unrelated_or_distractor_notes':{'AD01':'新侧加入中间结果存档段，为广义相关冗余，不代替直接手工记录要求。','AD02':'新侧加入模块化代码及交互段，不提供静态阅读与执行的关键区别。','AD03':'旧侧程序版本段不支持绘图数据结论；新侧另含通用工作流记录段，相关但非核心。'}[x['id']]})
improvements=[r['id'] for r in audit if not r['scores']['old_keywords']['improved']['complete'] and r['scores']['manual_translation']['improved']['complete']]
regressions=[r['id'] for r in audit if r['scores']['old_keywords']['improved']['complete'] and not r['scores']['manual_translation']['improved']['complete']]
assert improvements and not regressions
write(out/'offline-gate-review.json',{'at':now(),'reviewer':'Codex原文辅助复核，尚待本人确认','rows':audit,'improved_cases':improvements,'regressions':regressions,'continue_automatic_translation':True,'generation_calls':0,'coverage_basis':'此处ID列表只属于开发评价依据，不传入翻译/检索函数或模型请求，不作运行时题号映射。','scope':'人工译文理想检索回放，不是自动流程成绩。'})
target=HERE/'query_translation.py';assert not target.exists();ast.parse(Path('a_query_translation.py').read_text(encoding='utf-8'));shutil.copy2('a_query_translation.py',target)
from query_translation import messages,SCHEMA,PROMPT,offline_checks
checks=offline_checks();assert checks['passed']
phase=out/'automatic-translations';phase.mkdir();inputs=[]
for x in replay['rows']:
    conf=config('query');conf['parameters']['response_format']['json_schema']['schema']=copy.deepcopy(SCHEMA)
    inputs.append({'id':x['id'],'claim':x['claim'],'doc_ids':x['doc_ids'],'snapshot':x['snapshot'],'blocks':[],'messages':{'translation':messages(x['claim'])},'configs':{'translation':conf}})
write(phase/'diagnostic-inputs.json',inputs)
src=(HERE/'diagnose_sentence_selection.py').read_text(encoding='utf-8')
src=src.replace('原输出/句子选择对照','独立译文生成及门禁后回答')
src=src.replace("    assert load(out/'interface-adapter-check.json')['passed']","    assert plan['phase'] in ['automatic_translation','automatic_retrieval_answers']\n    assert load(out.parent/'offline-gate-review.json')['continue_automatic_translation']\n    if plan['phase']=='automatic_retrieval_answers':assert load(out.parent/'automatic-translation-review.json')['allow_answers']")
begin=src.index('    for item in inputs:');end=src.index('    with socket.socket()',begin)
src=src[:begin]+"    for item in inputs:\n        for variant in item['messages']:\n            assert item['configs'][variant]['parameters']['max_tokens']==plan['output_budget']\n        if plan['phase']=='automatic_translation':\n            from query_translation import messages,SCHEMA\n            assert item['messages']['translation']==messages(item['claim'])\n            assert item['configs']['translation']['parameters']['response_format']['json_schema']['schema']==SCHEMA\n            assert not item['blocks']\n        else:\n            from sentence_selection import answer_messages as unused\n".replace("            from sentence_selection import answer_messages as unused\n","            assert all(b['doc_id'] in item['doc_ids'] and b['snapshot']==item['snapshot'] for b in item['blocks'])\n")+src[end:]
src=src.replace("'diagnostic_input_origin':'automatic_improved_evidence_replay'","'diagnostic_input_origin':plan['phase']")
src=src.replace("            for variant in ['original','revised']:","            for variant in item['messages']:")
src=src.replace("if engine.dispatches>=6:raise TechnicalStop('达到6次上限')","if engine.dispatches>=plan['generation_cap']:raise TechnicalStop('达到本阶段上限')")
begin=src.index("            if variant=='revised':");end=src.index("            print('SAVED'",begin)
src=src[:begin]+"            if plan['phase']=='automatic_translation':\n                from query_translation import parse\n                try:validation={'valid':True,'translation':parse(raw['content']),'repair_applied':False}\n                except (ValueError,TypeError) as e:validation={'valid':False,'error':repr(e),'repair_applied':False}\n            else:\n                from sentence_selection import expand\n                validation=expand(raw['content'],item['blocks'],item['sentence_index'],item['doc_ids'],item['snapshot'])\n            write(out/f'validation-{n+1:02}.json',validation)\n            write(out/f'item-{n+1:02}.json',{'at':now(),'id':entry['id'],'variant':variant,'request_id':request_id,'run_id':raw['run_id'],'raw_record':'run-'+raw['run_id']+'.json','input_origin':plan['phase'],'not_end_to_end_score':True})\n"+src[end:]
runner=HERE/'diagnose_query_translation.py';assert not runner.exists();ast.parse(src);runner.write_text(src,encoding='utf-8')
previous=load(HERE/'runs/relation-first-20261016-131824/intervention-plan.json')
launch=previous['service_arguments'];base=Path.home()/'AppData/Local/ANTLabLocalModel';parts=[]
for x in inputs:
    m=x['messages']['translation'];parts.append('<|im_start|>system\n'+m[0]['content']+'<|im_end|>\n<|im_start|>user\n'+m[1]['content']+'<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n')
marker='<|endoftext|>';ids,cmd=native_tokenizer(base/'llama-b11429/llama-tokenize.exe',base/'models/Qwen3-0.6B-Q8_0.gguf',marker+marker.join(parts)+marker,phase,'offline-translation-capacity');counts=[];n=0
for token in ids[1:]:
    if token==ids[0]:counts.append(n);n=0
    else:n+=1
assert len(counts)==3 and all(n+128+64<=4096 for n in counts)
write(phase/'offline-checks.json',{'at':now(),'passed':True,'checks':checks,'capacity':counts,'output_budget':128,'extra_margin':64,'schema':'与原query相同的单字符串JSON结构，仅字段由terms改为translation，后续实际请求仍原生转换执行。','generation_calls':0})
plan={'saved_at':now(),'phase':'automatic_translation','output_budget':128,'generation_cap':3,'order':[{'id':x['id'],'variant':'translation'} for x in inputs],'cumulative_baseline':582,'A_used_before':48,'A_total_cap':90,'A_remaining_before':42,'prompt':PROMPT,'schema':SCHEMA,'translation_cost':'每题只转换一次，两方案共享；真生成仅计一次，若回答执行两侧各分摊50%翻译耗时和usage，另列实际翻译/回答耗时；不是各侧独立端到端计时。','fidelity_gate':'逐项对照中文对象、操作、否定、only/条件/数量/强度，方向改变停止，不人工修译文；三题均忠实且必要覆盖至少改善一题无退步才回答。','failure':'技术失败停止不自动重发；质量错误保留，最多3次转换不追加。','input_sha256':sha(phase/'diagnostic-inputs.json'),'code_hashes':{p.relative_to(ROOT).as_posix():sha(p) for p in HERE.glob('*.py')},'data_hashes':previous['data_hashes'],'model_hash':previous['model_hash'],'executable_hash':previous['executable_hash'],'service_arguments':launch}
write(phase/'intervention-plan.json',plan)
snap=phase/'code-snapshot';snap.mkdir()
for p in HERE.glob('*.py'):shutil.copy2(p,snap/p.name)
shutil.copy2(__file__,out/Path(__file__).name)
print(json.dumps({'out':str(out),'phase':str(phase),'offline_improvement':improvements,'regressions':regressions,'checks':checks,'capacity':counts,'generated':0},ensure_ascii=False))
