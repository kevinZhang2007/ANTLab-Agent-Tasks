from pathlib import Path
import sys,json,copy,hashlib
from datetime import datetime
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,now,sha
from engine import Corpus,neighbors,public
from bounded_candidate import BoundedEngine
from sentence_selection import expand,build_index
from checks_extended import run as previous_checks
batch=Path(Path('a-bounded-root.txt').read_text(encoding='utf-8').strip());retained='--retained' in sys.argv;out=batch/('round5-retained' if retained else 'round5');out.mkdir()
if datetime.now().hour*60+datetime.now().minute>=22*60+35:
    write(out/'not-started.json',{'at':now(),'reason':'22:35截止，不启动新开发轮次','generation_calls':0});sys.exit(0)
profile=load(batch/('final-profile.json' if retained else 'chosen-profile.json'));cfg=load(batch/'configuration.json');write(out/'plan.json',{'at':now(),'goal':'排除固定ID、顺序依赖及程序展开错误；不扩展语义猜测。','changes':'不改算法、提示或参数，只有自造机制验证。','prediction':'编号和输入列表顺序改变后，按内容对应的检索和邻段一致；语义同义改写只验证消息保真，不能由离线程序证明模型标签不变。','counterexamples':['外文档邻段','跨章节邻段','未知或重复句子ID','缺证空数组','同义措辞的词法变化'],'selection':'全部程序检查通过才冻结当前方案；失败不删除，不为目标样例加分支。','new_generations':0})
e=BoundedEngine.__new__(BoundedEngine);e.profile=profile;e.answer_base=cfg['request_common'];cases=[]
def test(name,value,basis):
    cases.append({'name':name,'passed':bool(value),'basis':basis})
    write(out/'mechanism-checks.json',{'at':now(),'passed':all(c['passed'] for c in cases),'cases':cases,'generation_calls':0})
    assert value,name
sections=[{'id':'made-section-a','doc_id':'made-doc-a','heading':'Checkpoint preservation','paragraphs':['A checkpoint must be retained.','The record identifies its origin.','Use precise names.']},{'id':'made-section-b','doc_id':'made-doc-a','heading':'Other operation','paragraphs':['This operation has no checkpoint.']},{'id':'made-section-c','doc_id':'made-doc-b','heading':'Checkpoint preservation','paragraphs':['A foreign checkpoint record.']}]
c=Corpus(sections);scope=c.scope(['made-doc-a'],'published');before=copy.deepcopy(scope);seeds,_=e.retrieve('checkpoint retained origin',scope);expanded,reasons=neighbors(seeds,scope)
test('scope_excludes_foreign',all(b['doc_id']=='made-doc-a' for b in scope),'仅指定doc_ids；不借邻文档。')
test('neighbors_section_local',all(next(b for b in scope if b['block_id']==r['seed'])['section_id']==next(b for b in scope if b['block_id']==r['added'])['section_id'] for r in reasons),'同章节±1，去重。')
mapping={b['block_id']:'renamed-'+hashlib.sha256(b['block_id'].encode()).hexdigest()[:10] for b in scope};remap=[{**b,'block_id':mapping[b['block_id']]} for b in scope];rs,_=e.retrieve('checkpoint retained origin',list(reversed(remap)));rx,_=neighbors(rs,list(reversed(remap)))
test('id_and_input_order_retrieval',[b['text'] for b in seeds]==[b['text'] for b in rs],'按内容对应，ID和输入列表顺序不作得分。')
test('id_and_order_neighbors',[b['text'] for b in expanded]==[b['text'] for b in rx],'保留原段_order而非传入列表偶然顺序。')
test('input_not_mutated',scope==before,'检索与补段不改原文。')
for n,claim in enumerate(['Checkpoints need preservation.','Preserve the checkpoints.','Some checkpoints need preservation.','Not every checkpoint is retained.']):
    ms,conf,idx,audit=e.build_answer(claim,seeds,['made-doc-a'],'published');u=json.loads(ms[1]['content']);test('claim_preserved_'+str(n),u['claim']==claim and audit['passed'],'仅验证改写/否定/量词原样进入输入，不判语义正确。')
ms,conf,idx,audit=e.build_answer('Checkpoints need preservation.',seeds,['made-doc-a'],'published');raw=json.dumps({'reason':'synthetic','sentence_ids':[idx[0]['sentence_id']],'label':'supported'});ex=expand(raw,[public(b) for b in seeds],idx,['made-doc-a'],'published')
test('selected_quote_origin',ex['valid'] and ex['selected_sources'][0]['text']==idx[0]['text'],'程序只展开模型选句。')
for name,ids in [('unknown',['not-existing']),('duplicate',[idx[0]['sentence_id']]*2)]:
    bad=expand(json.dumps({'reason':'synthetic','sentence_ids':ids,'label':'supported'}),[public(b) for b in seeds],idx,['made-doc-a'],'published');test(name+'_refused',not bad['valid'] and bad['expanded_response'] is None,'不修补、不翻转label。')
empty=expand(json.dumps({'reason':'synthetic','sentence_ids':[],'label':'insufficient'}),[public(b) for b in seeds],idx,['made-doc-a'],'published');test('empty_is_not_semantic_success',empty['valid'] and empty['semantic_support']=='not_checked','合法空选择不自动支持缺证结论。')
old=previous_checks(out);assert old['passed'];write(out/'old-regression.json',old)
write(out/'decision.json',{'at':now(),'retain_current':True,'new_generations':0,'mechanism_cases':len(cases),'existing_checks':old['passed'],'all_passed':True,'limits':['没有执行模型语义变体；将在最终冻结后按预先设计独立执行。','TF-IDF可能对同义措辞敏感，不因离线ID顺序不变就宣称同义理解稳健。','来源真实、PDF位置及语义支持仍分开。'],'stop_candidate_search':True,'profile_sha256':sha(batch/('final-profile.json' if retained else 'chosen-profile.json'))})
print(json.dumps({'checks':len(cases),'existing':old['passed'],'generations':0,'profile':profile['name']},ensure_ascii=False))
