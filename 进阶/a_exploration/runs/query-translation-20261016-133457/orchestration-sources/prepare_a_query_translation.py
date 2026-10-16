from pathlib import Path
import sys,json,copy,shutil,ast
from datetime import datetime
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
from engine import Corpus,retrieve,neighbors,terms,public
out=HERE/'runs'/('query-translation-'+datetime.now().strftime('%Y%m%d-%H%M%S'));out.mkdir();Path('a-query-translation-out.txt').write_text(str(out),encoding='utf-8')
protected={p.relative_to(ROOT).as_posix():sha(p) for p in HERE.rglob('*') if p.is_file() and out not in p.parents and not {'slot-cache','__pycache__'}&set(p.parts)}
for name in ['README.md','report.md','decisions.md','declaration.md','基础/开发记录.md','基础/starter/student.py','进阶/challenge_b/challenge.py','进阶/challenge_b/no_cache_engine.py']:protected[name]=sha(ROOT/name)
write(out/'protected-before.json',protected)
translations_path=HERE/'runs/claim-language-20261016-123016/translations.json'
source=HERE/'runs/development-20261016-115250'
write(out/'plan.json',{'at':now(),'status':'offline_gate_before_any_generation','scope':'仅三道开发题与自造样例；不读取七道评测题。','hypothesis':'忠实完整译文保留对象、操作及限定，可能使原文词项覆盖更充分，改善必要证据检索。','competing_explanation':'TF-IDF忽略否定的逻辑作用，长译文加入常见词也可能稀释关键项；翻译忠实不保证检索改善。','fixed':'不改共同判断提示、句子机制、TF-IDF公式或同章节邻段算法。','phase1':'复用已保存人工译文对现有实际关键词查询做零生成回放；不是自动流程成绩。','offline_continue_rule':'先核对完整排名、实际必要段/依据覆盖；至少一题必要覆盖改善且其余题不退步才进入自动翻译。若覆盖无改善则停止，不因排名略变继续。','phase2':'最多3次自动翻译，不给证据或参考；人工核对忠实度后，用实际译文检索。主张方向变化或必要覆盖退步停止，不改写译文。','phase3_gate':'三题译文均忠实，必要覆盖至少一题改善且其余不退步，才执行三题baseline/improved各一次，共6次回答；实际自动检索，句子机制512预算。','calls_cap':9,'baseline_cumulative':582,'A_used_before':48,'previous_A_cap':54,'new_A_cap':90,'remaining_before':42,'cap_revision_reason':'本人本轮授权将总上限调整为90，预留后续对照/变体/反事实；不是要求用满，也不恢复已取消评测执行。','technical_failure':'模型技术请求失败停止不自动重发；准备工程错误可离线修复留档。','quality_failure':'原样保留，不修答案/译文/引用，不重试。','comparison':'新旧查询回放为历史对照；回答若执行只比较同一实际自动翻译下的两检索方案，不将收益归因单个词或长度。','sources':{'manual_translations':translations_path.relative_to(ROOT).as_posix(),'historical_pairs':source.relative_to(ROOT).as_posix()},'code_hashes':{p.relative_to(ROOT).as_posix():sha(p) for p in HERE.glob('*.py')},'data_hash':sha(ROOT/'进阶/materials/sections.json'),'generations_so_far':0})
tr=load(translations_path);pairs=[(p,load(p)) for p in sorted(source.glob('pair-*.json'))];corpus=Corpus(load(ROOT/'进阶/materials/sections.json'));rows=[]
for t in tr:
    pf,pair=next((p,x) for p,x in pairs if x['claim']==t['claim_zh']);scope=corpus.scope(pair['doc_ids'],pair['snapshot']);assert scope==pair['scope_blocks']
    old=pair['retrieval_terms'];assert old==json.loads(pair['shared_query']['content'])['terms']
    result={'id':t['id'],'claim':t['claim_zh'],'doc_ids':pair['doc_ids'],'snapshot':pair['snapshot'],'manual_translation':t['claim_en'],'alignment':t['alignment'],'old_query':old,'historical_pair':pf.relative_to(ROOT).as_posix(),'translation_source':translations_path.relative_to(ROOT).as_posix(),'automatic_pipeline_score':False,'arms':{}}
    for variant,q in [('old_keywords',old),('manual_translation',t['claim_en'])]:
        seeds,scores=retrieve(q,scope);improved,reasons=neighbors(seeds,scope);score_map={s['block_id']:s['score'] for s in scores}
        ranked=sorted(scope,key=lambda b:(-score_map[b['block_id']],b['heading'],b['text'],b['paragraph_index']))
        fullrank=[{'rank':i+1,'score':score_map[b['block_id']],**public(b)} for i,b in enumerate(ranked)]
        assert all(b['doc_id'] in pair['doc_ids'] for b in seeds+improved)
        assert len({b['block_id'] for b in improved})==len(improved)
        assert all(any(a['seed']==s['block_id'] and a['added']==b['block_id'] and (s['doc_id'],s['snapshot'],s['section_id'])==(b['doc_id'],b['snapshot'],b['section_id']) and abs(s['paragraph_index']-b['paragraph_index'])==1 for s in seeds) for b in improved if b['block_id'] not in {s['block_id'] for s in seeds} for a in reasons if a['added']==b['block_id'])
        if variant=='old_keywords':assert [s['block_id'] for s in seeds]==pair['seed_ids']
        result['arms'][variant]={'query':q,'tokens':terms(q),'full_ranking':fullrank,'baseline':[public(b) for b in seeds],'improved':[public(b) for b in improved],'neighbors':reasons,'scope_and_boundary_passed':True}
    rows.append(result);write(out/('offline-'+t['id']+'.json'),result)
write(out/'offline-retrieval-replay.json',{'at':now(),'generation_calls':0,'rows':rows,'scope':'理想人工翻译检索诊断，不是自动端到端成绩；必要覆盖与无关程度需原文辅助复核。'})
shutil.copy2(__file__,out/'prepare_a_query_translation.py')
print(json.dumps({'out':str(out),'rows':[{'id':x['id'],'old_query':x['old_query'],'translation':x['manual_translation'],'arms':{k:{'baseline':[b['block_id'] for b in a['baseline']],'improved':[b['block_id'] for b in a['improved']],'top6':[(b['rank'],b['block_id'],round(b['score'],5)) for b in a['full_ranking'][:6]]} for k,a in x['arms'].items()}} for x in rows],'generated':0},ensure_ascii=False,indent=2))
