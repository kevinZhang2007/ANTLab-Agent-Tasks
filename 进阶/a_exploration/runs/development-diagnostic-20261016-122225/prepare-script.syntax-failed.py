from pathlib import Path
import json,sys,shutil,ast
from datetime import datetime
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration'
sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now,config
from engine import Corpus,public,answer_messages,parse_answer
from checks_extended import run as checks
from preflight import native_tokenizer
old=HERE/'runs/development-20261016-115250'
out=HERE/'runs'/('development-diagnostic-'+datetime.now().strftime('%Y%m%d-%H%M%S'));out.mkdir()
Path('a-diagnostic-out.txt').write_text(str(out),encoding='utf-8')
target=HERE/'diagnose_development.py';assert not target.exists();shutil.copy2('a_diagnostic_runner.py',target)
corpus=Corpus(load(ROOT/'进阶/materials/sections.json'))
tasks=load(old/'development-inputs.json');refs=load(ROOT/'进阶/materials/a_dev_answers.json')
appendix='\n先核对完整主张的对象、条件、量词与否定方向，再将它和原文的要求或限制比较。reason应说明原文与主张是同向、冲突还是缺少关键依据，label必须与reason一致。原文没有逐字复述主张，不等于证据不足；用途不同、仅部分条件成立，也不能当作支持完整主张。'
chosen=[['P1-S03-p01'],['P2-S10-p02','P2-S10-p03'],['P1-S08-p01']]
analysis=[{'retrieval':'两侧均含必要原文，无检索遗漏。','qualifiers':'原文有人工操作无法避免时的例外及最低记录要求；主张把无需记录说成足够。','judgment':'baseline支持却在理由中复述要记录；improved声称没有明确说明，均未正确对照否定方向。','citations':'baseline摘录真实，但没有引用句末直接冲突条件；improved为空。','reference_limit':'contradicted针对无需记录，不把原文解读为绝对禁止人工操作。','ambiguity':'未发现影响标签的实质歧义。'},{'retrieval':'baseline缺Run段，improved已含Read与Run。','qualifiers':'静态可读记录与执行环境是两种用途；主张含仅此不足这一限制。','judgment':'improved理由把待验证内容改成静态HTML足以执行，出现否定方向改变。','citations':'两侧均无引用，不能算支持成功。','reference_limit':'原文区分Read/Run并提出执行环境；不是证明静态导出在任何附带条件下都绝对不能参与执行。','ambiguity':'不足以独自保证运行来自Read/Run用途及环境条件的组合解释，非逐字原句；保留推导边界。'},{'retrieval':'两侧都漏P1-S08；命中P1-S04的virtual machine image及P1-S09的HTML用途。','qualifiers':'原文建议保留底层数据、处理值，最低要求注明图依据哪些数据及如何重建；不是所有图都必须保留所有中间值。','judgment':'把虚拟机/HTML用途当作图底层数据建议，出现对象混淆；缺检索与生成判断同时存在。','citations':'两条摘录真实且可定位，但与判断所需图数据依据无关。','reference_limit':'contradicted针对仅保留最终图满足建议；can be useful是建议，不强化为无例外强制存储每项数据。','ambiguity':'建议强度有限，但仅存图片无法满足末句最低数据重建说明；本次参考标签可由完整段落支持。'}]
inputs=[];dossier=[];md=['# 三道开发题离线诊断','实际核对时间：'+now(),'只使用开发材料；以下原始输出未改写。参考只用于诊断与评价。']
for i,t in enumerate(tasks):
    h=next(load(p) for p in old.glob('http-*.json') if load(p)['task_id']==t['id']);pair=h['response'];ref=refs[i]
    reference=[public(b) for b in corpus.blocks if b['section_id'] in ref['evidence_sections']]
    blocks=[b for b in corpus.blocks if b['block_id'] in chosen[i]]
    assert len(blocks)==len(chosen[i]) and all(b['doc_id'] in t['doc_ids'] for b in blocks+reference)
    messages=answer_messages(t['claim'],blocks);revised=json.loads(json.dumps(messages));revised[0]['content']+=appendix
    inputs.append({'id':t['id'],'claim':t['claim'],'doc_ids':t['doc_ids'],'snapshot':t['snapshot'],'blocks':blocks,'messages':{'original':messages,'revised':revised},'config':config('answer'),'origin':'开发阶段Codex依据原文指定充分证据，尚待本人核对；不是自动检索'})
    entry={'id':t['id'],'claim':t['claim'],'doc_ids':t['doc_ids'],'shared_terms':pair['retrieval_terms'],'reference':ref,'full_reference_passages':reference,'analysis':analysis[i],'diagnostic_evidence':[public(b) for b in blocks],'arms':{}}
    md+=['\n## '+t['id'],'主张：'+t['claim'],'doc_ids：'+json.dumps(t['doc_ids']),'共享检索词：'+pair['retrieval_terms']
    for arm in ['baseline','improved']:
        a=pair['arms'][arm];used=a['actual_input_passages']
        entry['arms'][arm]={'full_actual_passages':used,'raw_content':a['raw_record']['content'],'run_id':a['raw_record']['run_id'],'reference_section_present':{s:any(b['section_id']==s for b in used) for s in ref['evidence_sections']}}
        md+=['\n### '+arm+'实际完整证据','```json',json.dumps(used,ensure_ascii=False,indent=2),'```','模型原始输出：','```json',a['raw_record']['content'],'```']
    md+=['\n### 公开参考原文与限定','```json',json.dumps(reference,ensure_ascii=False,indent=2),'```','参考标签：'+ref['label']]+[k+'：'+v for k,v in analysis[i].items()]
    dossier.append(entry)
write(out/'offline-diagnosis.json',{'at':now(),'reviewer':'Codex依据开发原文辅助核对，尚待本人确认','reference_scope_verified':True,'wiring_error_found':False,'cases':dossier,'hypotheses_not_model_internal_proof':True})
(out/'offline-diagnosis.md').write_text('\n\n'.join(md)+'\n',encoding='utf-8')
write(out/'diagnostic-inputs.json',inputs)
result=checks(out);assert result['passed']==35
synthetic=[]
for label,claim,text in [('negation','The lab need not record edits.','Record every unavoidable edit.'),('partial','This package alone guarantees execution.','The package provides a readable record.'),('unknown','The archive includes source files.','The archive contains diagrams.')]:
    b={'block_id':'made-up','doc_id':'imaginary','snapshot':'published','section_id':'one','heading':'synthetic','paragraph_index':0,'text':text,'_order':(0,0)}
    m=answer_messages(claim,[b]);r=json.loads(json.dumps(m));r[0]['content']+=appendix
    assert m[1:]==r[1:] and json.loads(m[1]['content'])['passages'][0]['text']==text
    synthetic.append({'name':label,'claim':claim,'text':text,'passed':'只检查消息与原文保留，不冒充模型语义验证'})
base=Path.home()/'AppData/Local/ANTLabLocalModel';pre=load(old/'offline-preflight.json');launch=load(old/'runtime.json')['service_arguments']
assert sha(launch[0])==pre['executable_hash'] and sha(launch[launch.index('-m')+1])==pre['model_hash']
parts=[]
for item in inputs:
    for v in ['original','revised']:parts.append('<|im_start|>system\n'+item['messages'][v][0]['content']+'<|im_end|>\n<|im_start|>user\n'+item['messages'][v][1]['content']+'<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n')
marker='<|endoftext|>';ids,command=native_tokenizer(base/'llama-b11429/llama-tokenize.exe',Path(launch[launch.index('-m')+1]),marker+marker.join(parts)+marker,out,'native-diagnostic-capacity')
sep=ids[0];counts=[];n=0
for x in ids[1:]:
    if x==sep:counts.append(n);n=0
    else:n+=1
assert len(counts)==6 and all(n+256+64<=4096 for n in counts)
write(out/'offline-checks.json',{'at':now(),'passed':True,'existing_synthetic_checks':result,'additional_message_checks':synthetic,'offline_template_token_counts':counts,'output_budget':256,'extra_safety':64,'capacity_requires_actual_template_recheck':True,'native_tokenizer_command':command,'generation_calls':0})
order=[{'id':t['id'],'variant':v} for i,t in enumerate(tasks) for v in (['original','revised'] if i%2==0 else ['revised','original'])]
plan={'saved_at':now(),'status':'registered_before_generation','diagnostic_not_method_win':True,'input_origin':'manual_verified_development_evidence','prior_exposure':'已看三题错误和公开开发参考；未读AT题','primary_failure':'必要证据存在时仍未按完整主张的否定/用途限制判定','explanations':[{'name':'检索遗漏或干扰导致有效证据没有被使用','evidence':'AD03必要段落漏检，AD02 baseline缺Run；AD01已有关键段但包含长说明，注意分配仍未知','prediction':'给足且缩减到必要完整段落后，原提示即可恢复；修订提示相对原提示增益小。'},{'name':'完整主张的极性、用途或label/reason映射错误','evidence':'AD01支持标签与要记录理由不一致；AD02改成足以执行的命题；不能观测模型内部原因','prediction':'相同充分证据下原提示仍错，而显式主张核对提示可能纠正；若两侧仍错，不能据此唯一归因。'}],'intervention':'三题各一组核实的完整充分原段；同题两侧只追加统一system文字。相对历史的证据替换是非同步诊断，不作端到端改进或单因素历史因果结论。','prompt_appendix':appendix,'original_prompt':inputs[0]['messages']['original'][0]['content'],'revised_prompt':inputs[0]['messages']['revised'][0]['content'],'config':config('answer'),'order':order,'generation_cap':6,'cumulative_baseline':543,'A_used_before':9,'A_total_cap':54,'selection':'先比较三题判断正确和严格成功；同分保留原提示。诊断不能自动宣布正式方法胜出，任何共同提示决定须开发阶段披露并两方案统一。','evaluation':'分别记录格式、完整主张判断、关键限定、引用ID、摘录真实性、引用支持；人工指定证据不计检索或端到端成绩，保留推荐强度和组合解释边界。','stopping':'加载前2GiB；运行连续3次2秒样本低于1GiB停止自有PID；全部实际模板检查通过后生成。技术失败停止不重发；质量失败继续不重试；最多6次。','code_hashes':{p.relative_to(ROOT).as_posix():sha(p) for p in HERE.glob('*.py')},'data_hashes':{(ROOT/'进阶/materials/sections.json').relative_to(ROOT).as_posix():sha(ROOT/'进阶/materials/sections.json')},'model_hash':pre['model_hash'],'executable_hash':pre['executable_hash'],'service_arguments':launch,'input_sha256':sha(out/'diagnostic-inputs.json'),'inference_reads_reference_answers':False}
write(out/'intervention-plan.json',plan)
snap=out/'code-snapshot';snap.mkdir()
for p in HERE.glob('*.py'):shutil.copy2(p,snap/p.name)
shutil.copy2(HERE/'config.json',snap/'config.json')
for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
print(json.dumps({'out':str(out),'checks':35,'capacity':counts,'plan_saved':True,'generation_calls':0},ensure_ascii=False))
