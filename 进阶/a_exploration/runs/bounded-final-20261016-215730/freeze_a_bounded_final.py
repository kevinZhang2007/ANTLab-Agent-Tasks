from pathlib import Path
import sys,json,copy,shutil
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
from bounded_candidate import BoundedEngine
from current_candidate import build_answer,query_config
from engine import query_messages,Corpus,public
b=Path(Path('a-bounded-root.txt').read_text(encoding='utf-8').strip());cfg=load(b/'configuration.json');p=load(b/'final-profile.json');assert p==load(b/'retained-profile.json')
assert load(b/'round5-retained/decision.json')['all_passed'];assert load(b/'round4/decision.json')['final_profile']=='retained'
e=BoundedEngine.__new__(BoundedEngine);e.profile=p;e.answer_base=cfg['request_common'];corpus=Corpus(load(ROOT/'进阶/materials/sections.json'));rows=[]
for t in load(b/'retained-query-tasks.json'):
    scope=corpus.scope(t['doc_ids'],t['snapshot']);seeds,scores=e.retrieve(t['terms'],scope)
    from engine import retrieve,neighbors
    oldseeds,oldsc=retrieve(t['terms'],scope);assert seeds==oldseeds and scores==oldsc
    for mode,blocks in [('baseline',seeds),('improved',neighbors(seeds,scope)[0])]:
        assert e.build_answer(t['claim'],blocks,t['doc_ids'],t['snapshot'])==build_answer(t['claim'],blocks,t['doc_ids'],t['snapshot'],cfg['request_common'])
        assert e.query_messages(t['claim'])==query_messages(t['claim']);rows.append({'id':t['id'],'mode':mode,'byte_equal_to_current_retained_entry':True})
write(b/'final-entry-equivalence.json',{'at':now(),'passed':True,'rows':rows,'no_history_response_used':True,'generation_calls':0})
assert sha(Path(cfg['model']['path']))==cfg['model']['sha256'] and sha(Path(cfg['executable']['path']))==cfg['executable']['sha256']
run_ids=[]
for f in b.rglob('run-*.json'):
    r=load(f)
    if r.get('generation_dispatched') and (r.get('usage') or {}).get('completion_tokens',0)>0:run_ids.append(r['run_id'])
assert len(run_ids)==len(set(run_ids))==18
freeze={'frozen_at':now(),'kind':'A开发结束后的唯一冻结，七题尚未读取','profile':p,'profile_sha256':sha(b/'final-profile.json'),'configuration':cfg,'single_entry':'进阶/a_exploration/current_candidate.py::CurrentEngine.execute','batch_entry':'进阶/a_exploration/run_bounded_stage.py，BoundedEngine配置为retained；消息、Schema、查询和排序与current入口逐字节对应验证。','main_improvement':'仅同章节前后邻段，相同关键词和TF-IDF两段基线；不采用title-body或新对象查询。','thinking_and_prompt':'紧凑输入、开启思考、句子选择、理由/引用候选提示；label-first Schema，不采用解释先行版本。','strict_formula':load(b/'batch-plan.json')['strict_formula'],'reason_consistency_separate':True,'code_hashes':{p.relative_to(ROOT).as_posix():sha(p) for p in HERE.glob('*.py')},'data_hashes':cfg['data_hashes'],'model_hash':cfg['model']['sha256'],'executable_hash':cfg['executable']['sha256'],'development_generations':18,'cumulative_before_evaluation':648,'evaluation_remaining_authorization':{'main':21,'equivalence':6,'counterfactual':3},'max_batch_total':60,'variants_and_counterfactual_preplanned':'batch-plan.json','seven_task_content_read':False,'selection_disclosure':'round3曾按improved标签胜出，round4暴露baseline严格退步后回退；整体汇总细则事前未细化，另存，不追溯伪称。','scoring':'AT无公开标准答案；后续按指定doc_ids原文推导暂判，歧义和失败保留分母7。','no_further_changes_after_eval':True}
assert not (b/'final-freeze.json').exists();write(b/'final-freeze.json',freeze)
print(json.dumps({'frozen_at':freeze['frozen_at'],'profile':p,'code_hashes':len(freeze['code_hashes']),'dev_calls':18,'cumulative':648,'AT_read':False},ensure_ascii=False))
