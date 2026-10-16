from pathlib import Path
import sys,json,copy,shutil,ast
from datetime import datetime
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
from engine import Corpus,retrieve,neighbors,terms,public
out=Path('C:\\Users\\86186\\Projects\\ANTLab-Agent-Tasks\\进阶\\a_exploration\\runs\\query-translation-20261016-133457')
translations_path=HERE/'runs/claim-language-20261016-123016/translations.json'
source=HERE/'runs/development-20261016-115250'
tr=load(translations_path);pairs=[(p,load(p)) for p in sorted(source.glob('pair-*.json'))];corpus=Corpus(load(ROOT/'进阶/materials/sections.json'));rows=[]
for t in tr:
    pf,pair=next((p,x) for p,x in pairs if x['claim']==t['claim_zh']);scope=corpus.scope(pair['doc_ids'],pair['snapshot']);assert [public(b) for b in scope]==pair['scope_blocks']
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
