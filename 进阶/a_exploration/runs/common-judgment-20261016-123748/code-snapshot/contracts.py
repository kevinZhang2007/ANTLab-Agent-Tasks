"""只映射已保存字段，不修正模型判断或补证据。"""
def normalize_pair(pair):
    output=[]
    for mode,arm in pair.get('arms',{}).items():
        parsed=arm.get('parsed',{})
        output.append({'request_id':arm['main_task_id'],'parent_request_id':pair['request_id'],'claim':pair['claim'],'doc_ids':pair['doc_ids'],'snapshot':pair['snapshot'],'actual_doc_ids':sorted({b['doc_id'] for b in arm['actual_input_passages']}),'actual_snapshots':sorted({b['snapshot'] for b in arm['actual_input_passages']}),'mode':mode,'answer':parsed.get('label'),'model_reason':parsed.get('reason'),'evidence':arm['evidence'],'locator_status':arm['locator_status'],'support_status':'not_checked','judgment_source':'unverified','claim_judgment_source':'model','elapsed_ms':1000*arm['raw_record']['elapsed_seconds'],'elapsed_scope':'final_model_http_request_only','pair_elapsed_ms':1000*pair['pair_elapsed_seconds'],'allocated_cost_ms':1000*arm['allocated_total_seconds'],'shared_query_cost_fraction':0.5,'run_kind':'live_api','record_origin':'archived_actual_model_response','run_id':arm['raw_record']['run_id'],'shared_query_run_id':pair['shared_query']['run_id'],'semantic_note':'模型主张判断和引用语义支持分开；不以模型自评作为金标准。'})
    return output
