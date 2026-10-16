from pathlib import Path
import sys,json,math
from collections import Counter
from datetime import datetime
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
from engine import Corpus,terms,retrieve,neighbors,public
def sha_text(text):
    import hashlib
    return hashlib.sha256(text.encode('utf-8')).hexdigest()
out=HERE/'runs'/('retrieval-short-enum-'+datetime.now().strftime('%Y%m%d-%H%M%S'));out.mkdir()
Path('a-round-out.txt').write_text(str(out),encoding='utf-8')
protected={p.relative_to(ROOT).as_posix():sha(p) for p in HERE.rglob('*') if p.is_file() and out not in p.parents and not {'__pycache__','slot-cache'}&set(p.parts)}
for n in ['README.md','report.md','decisions.md','declaration.md','基础/开发记录.md','基础/starter/student.py','进阶/challenge_b/challenge.py','进阶/challenge_b/no_cache_engine.py']:protected[n]=sha(ROOT/n)
write(out/'protected-before.json',protected)
corpus=Corpus(load(ROOT/'进阶/materials/sections.json'));old=HERE/'runs/development-20261016-115250';refs={x['id']:x for x in load(ROOT/'进阶/materials/a_dev_answers.json')};rows=[]
for h in sorted([load(p) for p in old.glob('http-*.json')],key=lambda x:x['task_id']):
    pair=h['response'];blocks=corpus.scope(pair['doc_ids'],pair['snapshot']);counts=[Counter(terms(b['text'])) for b in blocks];df=Counter(t for c in counts for t in c)
    idf={t:math.log((1+len(blocks))/(1+d))+1 for t,d in df.items()};qraw=Counter(terms(pair['retrieval_terms']));q={t:(1+math.log(n))*idf[t] for t,n in qraw.items() if t in idf};qn=math.sqrt(sum(v*v for v in q.values()));ranked=[]
    for b,c in zip(blocks,counts):
        vector={t:(1+math.log(n))*idf[t] for t,n in c.items()};norm=math.sqrt(sum(v*v for v in vector.values()));parts={t:q[t]*vector.get(t,0)/(qn*norm) if qn and norm else 0 for t in q};score=sum(parts.values())
        ranked.append({'block_id':b['block_id'],'section_id':b['section_id'],'heading':b['heading'],'paragraph_index':b['paragraph_index'],'doc_id':b['doc_id'],'text_sha256':sha_text(b['text']),'text_tokens':terms(b['text']),'token_counts':dict(c),'score':score,'query_term_contributions':parts,'matched_query_terms':[t for t in q if t in vector],'reference_section_audit_only':b['section_id'] in refs[h['task_id']]['evidence_sections'],'text':b['text']})
    ranked.sort(key=lambda r:(-r['score'],r['heading'],r['text'],r['paragraph_index']))
    for i,r in enumerate(ranked,1):r['rank']=i
    actual_seeds,scores=retrieve(pair['retrieval_terms'],blocks);actual_neighbors,trace=neighbors(actual_seeds,blocks)
    score_map={s['block_id']:s['score'] for s in scores};assert all(math.isclose(r['score'],score_map[r['block_id']],rel_tol=1e-12,abs_tol=1e-12) for r in ranked)
    assert [x['block_id'] for x in actual_seeds]==pair['seed_ids']
    assert [public(x) for x in actual_neighbors]==pair['arms']['improved']['actual_input_passages']
    rows.append({'id':h['task_id'],'doc_ids':pair['doc_ids'],'query_terms':pair['retrieval_terms'],'query_tokens':list(qraw.elements()),'query_tokens_absent_from_scope_vocabulary':[t for t in qraw if t not in idf],'query_idf':{t:idf.get(t) for t in qraw},'ranked':ranked,'seeds_original_order':pair['seed_ids'],'neighbors_trace':trace,'independent_score_recomputation_matches':True,'scope_and_serialization_matches':True,'chapter_boundary_checked':True})
write(out/'retrieval-audit.json',{'at':now(),'formula':'idf=log((1+N)/(1+df))+1; tf=1+log(count); cosine; positive top2, tie heading/text/index; neighbors only same doc/snapshot/section ±1, no multi-hop','stemming':False,'algorithm_bug_found':False,'cases':rows,'notes':'词面覆盖不足和较长段落的余弦归一化会影响排名；质量问题不登记为代码bug。参考章节标记仅审计使用，不进推理。'})
print(json.dumps({'out':str(out),'AD03':[{'rank':r['rank'],'id':r['block_id'],'score':r['score'],'matched':r['matched_query_terms'],'contributions':r['query_term_contributions']} for c in rows if c['id']=='AD03' for r in c['ranked'] if r['rank']<=3 or r['reference_section_audit_only']],'bugs':False},ensure_ascii=False,indent=2))
