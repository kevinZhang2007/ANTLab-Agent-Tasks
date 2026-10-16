from pathlib import Path
import copy,json,sys
from engine import Corpus,retrieve,neighbors,answer_messages,query_messages,parse_answer,parse_terms,QUERY_SCHEMA,ANSWER_SCHEMA
from locator import Locator,scale_box

def run():
    rows=[]
    def check(name,value):
        rows.append({'name':name,'passed':bool(value)})
        if not value:raise AssertionError(name)
    def reject(name,fn):
        try:fn()
        except (ValueError,KeyError,TypeError,json.JSONDecodeError):check(name,True)
        else:check(name,False)
    sections=[{'id':'one','doc_id':'manual','heading':'First','paragraphs':['preceding scope caveat','archive version dependencies','following exception']},{'id':'two','doc_id':'manual','heading':'Second','paragraphs':['external section barrier']},{'id':'three','doc_id':'other','heading':'Other','paragraphs':['archive version dependencies']}]
    original=copy.deepcopy(sections); c=Corpus(sections); blocks=c.scope(['manual'],'published')
    check('scope_no_leak',all(b['doc_id']=='manual' for b in blocks))
    reject('unknown_document',lambda:c.scope(['missing'],'published'))
    reject('unknown_snapshot',lambda:c.scope(['manual'],'old'))
    reject('empty_doc_ids',lambda:c.scope([],'published'))
    seeds,scores=retrieve('archive version dependencies',blocks); expanded,reasons=neighbors(seeds,blocks)
    check('positive_scores_only',all(next(x['score'] for x in scores if x['block_id']==b['block_id'])>0 for b in seeds))
    check('chapter_barrier',all(b['section_id']=='one' for b in expanded))
    check('three_neighbors',len(expanded)==3)
    twice,_=neighbors(seeds+seeds,blocks);check('duplicate_seeds_no_duplicate_output',twice==expanded)
    check('all_full_paragraphs_preserved',all(b['text'] in sections[0]['paragraphs'] for b in expanded))
    check('inputs_unchanged',sections==original)
    check('empty_query_retrieval',retrieve('zzzzzz',blocks)[0]==[])
    check('empty_corpus',retrieve('word',[])[0]==[] and neighbors([],[])[0]==[])
    check('empty_messages_no_answer_fabrication',json.loads(answer_messages('claim',[])[1]['content'])=={'claim':'claim','passages':[]})
    mapped=copy.deepcopy(blocks)
    for i,b in enumerate(mapped):b['block_id']='mapped-'+str(i)
    mapped_seeds,_=retrieve('archive version dependencies',list(reversed(mapped)));mapped_expanded,_=neighbors(mapped_seeds,mapped)
    check('id_remap_content_invariance',[b['text'] for b in mapped_expanded]==[b['text'] for b in expanded])
    obj,checks=parse_answer(json.dumps({'label':'supported','reason':'synthetic','evidence':[{'block_id':blocks[1]['block_id'],'quote':'archive version'}]}),blocks)
    check('valid_id_and_quote',checks[0]['id_valid'] and checks[0]['quote_continuous_original'])
    _,checks=parse_answer(json.dumps({'label':'supported','reason':'synthetic','evidence':[{'block_id':'unknown','quote':'invented'}]}),blocks)
    check('invalid_reference_not_repaired',not checks[0]['id_valid'])
    _,checks=parse_answer(json.dumps({'label':'supported','reason':'synthetic','evidence':[{'block_id':blocks[1]['block_id'],'quote':'not in original'}]}),blocks)
    check('fabricated_quote_not_repaired',not checks[0]['quote_continuous_original'])
    reject('invalid_json',lambda:parse_answer('[]',blocks))
    reject('invalid_query',lambda:parse_terms('{"terms":""}'))
    reject('invalid_label',lambda:parse_answer('{"label":"gold","reason":"x","evidence":[]}',blocks))
    check('answer_schema_required',set(ANSWER_SCHEMA['required'])=={'label','reason','evidence'})
    check('query_schema_required',QUERY_SCHEMA['required']==['terms'])
    check('zoom_half',scale_box([10,20,30,40],100,200,50,100)==[5,10,15,20])
    check('zoom_double',scale_box([10,20,30,40],100,200,200,400)==[20,40,60,80])
    check('nonuniform_scale',scale_box([10,20,30,40],100,200,200,100)==[20,10,60,20])
    reject('invalid_page_size',lambda:scale_box([1,2,3,4],0,100,10,10))
    block={'doc_id':'manual','snapshot':'published','text':'Original continuous quoted evidence is here.'}
    words=[{'id':'word','doc_id':'manual','snapshot':'published','page':1,'text':block['text'],'bbox':[10,20,90,30],'page_width':100,'page_height':100}]
    loc=Locator(words).locate(block,block['text']);check('whole_line_box_precision',loc['locator_status']=='valid' and loc['regions'][0]['boxes'][0]['bbox']==words[0]['bbox'])
    check('fake_quote_invalid',Locator(words).locate(block,'unseen')['locator_status']=='invalid')
    doubled=words+[dict(words[0],id='second',page=2)]
    check('ambiguous_location_rejected',Locator(doubled).locate(block,block['text'])['locator_status']=='invalid')
    check('scope_location_no_leak',Locator([dict(words[0],doc_id='other')]).locate(block,block['text'])['locator_status']=='absent')
    return {'status':'passed','passed':len(rows),'failed':0,'checks':rows,'run_kind':'local_rule','generation_calls':0,'synthetic_only':True}

if __name__=='__main__':print(json.dumps(run(),ensure_ascii=False,indent=2))
