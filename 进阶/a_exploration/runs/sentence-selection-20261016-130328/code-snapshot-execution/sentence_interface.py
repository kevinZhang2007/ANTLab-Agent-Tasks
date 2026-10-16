"""对外证据适配；保留模型label，标明quote由程序展开。"""
import copy,time
from runtime import load,ROOT
from locator import Locator

def interface_response(request_id,claim,doc_ids,snapshot,model_run_id,expansion,model_elapsed_seconds,locator=None):
    start=time.perf_counter()
    response={'request_id':request_id,'claim':claim,'requested_doc_ids':doc_ids,'requested_snapshot':snapshot,'actual_doc_ids':[],'actual_snapshots':[],'answer':None,'evidence':[],'locator_status':'absent','support_status':'not_checked','judgment_source':'unverified','claim_judgment_source':'model','elapsed_ms':model_elapsed_seconds*1000,'elapsed_scope':'original_nonstream_model_request_only','run_kind':'live_api','model_run_id':model_run_id,'output_origin':'model_selection_program_verbatim_expansion','derivation':{'run_kind':'local_rule','judgment_source':'rule','label_changed':False,'semantic_support':'not_checked','model_generated_quote':False},'status':'selection_quality_failure','end_to_end_ms':None,'end_to_end_note':'固定证据诊断；此适配可离线复算，未测自动检索端到端耗时。'}
    if expansion['valid']:
        obj=expansion['expanded_response'];response.update(answer=obj['label'],reason=obj['reason'],status='expanded')
        for e,r in zip(obj['evidence'],expansion['selected_sources']):
            if r['doc_id'] not in doc_ids or r['snapshot']!=snapshot:raise ValueError('派生来源跨范围')
            loc=locator.locate({'doc_id':r['doc_id'],'text':r['text']},e['quote']) if locator else {'locator_status':'absent','regions':[],'reason':'未执行PDF框映射'}
            page=loc['regions'][0]['page'] if loc['regions'] else None
            response['evidence'].append({**copy.deepcopy(e),'doc_id':r['doc_id'],'snapshot':r['snapshot'],'sentence_id':r['sentence_id'],'text':r['text'],'start':r['start'],'end':r['end'],'offset_unit':r['offset_unit'],'page':page,'page_null_reason':None if page is not None else loc['reason'],'locator_status':'valid','pdf_location':loc,'support_status':'not_checked','judgment_source':'unverified','quote_origin':'local_rule_expansion_of_model_selected_sentence','model_generated_quote':False})
        response['actual_doc_ids']=sorted({r['doc_id'] for r in expansion['selected_sources']})
        response['actual_snapshots']=sorted({r['snapshot'] for r in expansion['selected_sources']})
        response['locator_status']='valid' if response['evidence'] else 'absent'
    else:response['error']=expansion.get('error','invalid_selection')
    response['offline_interface_mapping_ms']=(time.perf_counter()-start)*1000
    return response

def offline_checks():
    from sentence_selection import build_index,expand
    import json
    b={'block_id':'synthetic','doc_id':'made-up','snapshot':'published','text':'Keep this. Another sentence.'};idx=build_index([b],['made-up'],'published')
    raw=json.dumps({'label':'contradicted','reason':'synthetic','sentence_ids':[idx[0]['sentence_id']]});x=expand(raw,[b],idx,['made-up'],'published');r=interface_response('synthetic-request','synthetic claim',['made-up'],'published','synthetic-run',x,1.25)
    assert r['answer']=='contradicted' and r['support_status']=='not_checked' and r['derivation']['model_generated_quote'] is False
    assert r['evidence'][0]['text']==b['text'][idx[0]['start']:idx[0]['end']] and r['evidence'][0]['page'] is None and r['evidence'][0]['page_null_reason']
    empty=expand(json.dumps({'label':'supported','reason':'synthetic','sentence_ids':[]}),[b],idx,['made-up'],'published');er=interface_response('empty','claim',['made-up'],'published','run',empty,1)
    assert er['answer']=='supported' and er['evidence']==[] and er['support_status']=='not_checked'
    bad=expand(json.dumps({'label':'supported','reason':'synthetic','sentence_ids':['bad']}),[b],idx,['made-up'],'published');br=interface_response('bad','claim',['made-up'],'published','run',bad,1)
    assert br['status']=='selection_quality_failure' and br['answer'] is None and br['evidence']==[]
    return {'passed':True,'count':3,'generation_calls':0,'semantic_judgment':'not_checked'}
