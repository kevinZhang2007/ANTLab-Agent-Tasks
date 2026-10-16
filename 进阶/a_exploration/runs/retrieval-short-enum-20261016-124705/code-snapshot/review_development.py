"""仅离线评价：所有调用完成后读取公开开发参考。推理模块不得导入本文件。"""
from pathlib import Path
from collections import Counter
import argparse,json,hashlib,re
from runtime import ROOT,HERE,load,write,now

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();folder=a.out.resolve()
    runs=[load(x) for x in folder.glob('run-*.json')]
    assert len(runs)==9 and len({r['run_id'] for r in runs})==9 and all(r.get('generation_dispatched') and r.get('usage',{}).get('completion_tokens',0)>0 for r in runs),'全部9次生成保存后才读取开发参考'
    assert not (folder/'review.json').exists()
    references={x['id']:x for x in load(ROOT/'进阶/materials/a_dev_answers.json')}
    records=sorted([load(x) for x in folder.glob('http-*.json') if not x.name.startswith('http-error')],key=lambda r:r['task_id'])
    sections=load(ROOT/'进阶/materials/sections.json')
    def paragraph(section,index):return next(x for x in sections if x['id']==section)['paragraphs'][index]
    basis={
      'AD01':{'necessary_blocks':['P1-S03-p01'],'original_sources':[{'section':'P1-S03','paragraph_index':0,'text':paragraph('P1-S03',0)}],'key_original':'If manual operations cannot be avoided, you should as a minimum note down which data files were modified or moved, and for what purpose.','judgment':'原文对无法避免的手工操作仍要求记录哪些文件被修改/移动及目的，反对无需记录；不等于绝对禁止手工操作。','error':'两侧最终输入都有完整例外条件。baseline把应记录的原文当成无需记录的支持；improved改为拒判，也与已提供原文不符。','input_coverage':{'baseline':True,'improved':True}},
      'AD02':{'necessary_blocks':['P2-S10-p02','P2-S10-p03'],'original_sources':[{'section':'P2-S10','paragraph_index':i,'text':paragraph('P2-S10',i)} for i in [1,2]],'key_original':'Read与Run分开：静态HTML/PDF供阅读归档；运行还讨论Binder、容器或依赖描述。','judgment':'结合两个用途说明可以支持“有助阅读但仅此不足执行”；不把原文没有保证充分执行误读成该主张缺证。','error':'baseline缺少Run段，存在选证不足；improved补入Run完整段后仍insufficient，其英文理由把“仅此不足执行”读成“足以执行”。','input_coverage':{'baseline':False,'improved':True}},
      'AD03':{'necessary_blocks':['P1-S08-p01'],'original_sources':[{'section':'P1-S08','paragraph_index':0,'text':paragraph('P1-S08',0)}],'key_original':'In cases where plotting involves more than a direct visualization of underlying numbers, it can be useful to store both the underlying data and the processed values that are directly visualized.','judgment':'原文要求保留图形底层数据/处理值及可重建信息，最终图片不足。','error':'检索词仅为data conversion, final image；命中外部程序版本和分层结果，不含绘图底层数据章节。两个种子章节都只有一段，无邻段可补，两侧完整请求相同，均以无关资料错误支持。','input_coverage':{'baseline':False,'improved':False}}
    }
    rows=[];pairs=[]
    for record in records:
        cid=record['task_id'];pair=record['response'];base=pair['arms']['baseline'];imp=pair['arms']['improved'];b=basis[cid]
        for src in b['original_sources']:
            src['text_sha256']=hashlib.sha256(src['text'].encode()).hexdigest();src['start']=0;src['end']=len(src['text'])
        for arm_name,arm in pair['arms'].items():
            parsed=arm.get('parsed',{});checks=arm.get('reference_checks',[]);evidence=parsed.get('evidence',[])
            correct=parsed.get('label')==references[cid]['label']
            row={'task_id':cid,'variant':arm_name,'request_id':arm['main_task_id'],'pair_request_id':pair['request_id'],'run_id':arm['raw_record']['run_id'],'shared_query_run_id':pair['shared_query']['run_id'],'raw_content':arm['raw_record']['content'],'actual_label':parsed.get('label'),'reference_label':references[cid]['label'],'format_complete':arm.get('format_complete',False),'answer_correct':correct,'semantic_consistent':False,'reason_language_chinese':bool(re.search('[一-鿿]',parsed.get('reason',''))),'id_membership_check':all(c['id_valid'] for c in checks),'nonempty_references':bool(evidence),'quote_authenticity':[c['quote_continuous_original'] for c in checks],'necessary_input_coverage':b['input_coverage'][arm_name],'necessary_cited_coverage':False,'citation_support_actual_judgment':False,'has_unrelated_citations':cid=='AD03','strict_complete_success':False,'locator_status':arm['locator_status'],'locator_valid_references':sum(e['location']['locator_status']=='valid' for e in arm['evidence']),'reference_count':len(evidence),'actual_input_ids':[x['block_id'] for x in arm['actual_input_passages']],'answer_client_seconds':arm['raw_record']['elapsed_seconds'],'answer_stage_wall_seconds':arm['answer_stage_wall_seconds'],'shared_query_cost_fraction':0.5,'allocated_total_seconds':arm['allocated_total_seconds'],'usage':arm['raw_record']['usage'],'finish_reason':arm['raw_record']['finish_reason'],'basis':b,'judgment_note':'Codex辅助原文复核，尚待本人确认；非官方成绩。id集合检查允许空引用，但空引用不算证据/定位/支持成功。','semantic_support_reason':'该次判断错误或拒判与原文不符；原文片段真实/可定位不能支持错误判断。'}
            rows.append(row)
        baseline_ids={x['block_id'] for x in base['actual_input_passages']}
        added=[x['block_id'] for x in imp['actual_input_passages'] if x['block_id'] not in baseline_ids]
        same=base['raw_record']['actual_http_request_body']==imp['raw_record']['actual_http_request_body']
        pairs.append({'task_id':cid,'pair_request_id':pair['request_id'],'shared_terms':pair['retrieval_terms'],'actual_added_ids':added,'raw_neighbor_trace_note':'原added_neighbors记录邻接关系，包含已是种子的邻段；actual_added_ids才是净新增，不改旧轨迹。','actual_requests_identical':same,'pair_elapsed_seconds':pair['pair_elapsed_seconds'],'query_elapsed_seconds':pair['shared_query']['elapsed_seconds'],'query_usage':pair['shared_query']['usage'],'query_run_id_counted_once':pair['shared_query']['run_id'],'baseline_final_label':base.get('parsed',{}).get('label'),'improved_final_label':imp.get('parsed',{}).get('label')})
    groups={}
    for variant in ['baseline','improved']:
        rs=[r for r in rows if r['variant']==variant]
        groups[variant]={'denominator':3,**{key:sum(r[key] is True for r in rs) for key in ['format_complete','answer_correct','semantic_consistent','id_membership_check','nonempty_references','necessary_input_coverage','necessary_cited_coverage','citation_support_actual_judgment','has_unrelated_citations','strict_complete_success']},'locator_valid_tasks':sum(r['locator_status']=='valid' for r in rs),'answer_http_total_seconds':sum(r['answer_client_seconds'] for r in rs),'allocated_total_seconds':sum(r['allocated_total_seconds'] for r in rs)}
    write(folder/'review.json',{'reviewed_at':now(),'run_kind':'local_rule','judgment_source':'unverified','reviewer':'Codex辅助原文复核，尚待本人确认','evaluation_after_all_generations_saved':True,'public_reference_source':'进阶/materials/a_dev_answers.json','public_reference_sha256':hashlib.sha256((ROOT/'进阶/materials/a_dev_answers.json').read_bytes()).hexdigest(),'rows':rows,'pairs':pairs,'groups':groups,'technical_generation_failures':0,'quality_retry_count':0,'length_finish_count':sum(r.get('finish_reason')=='length' for r in runs),'A_confirmed_generations':9,'cumulative_confirmed_generations':543,'A_total_budget':54,'A_remaining':45,'decision':'开发判断正确和严格成功均未改善；按同分保留简单基线，不自动采用邻段补全，也不追加优化。是否继续固定候选正式比较由本人决定。','limits':['仅三道开发题，不是评测或泛化成绩','原生PDF插件空白，保留失败；本地渲染物理页查看和字段适配另做零生成回放验证','没有读取AT正文或开展AT生成']})
    print(json.dumps({'groups':groups,'pairs':pairs,'A_generations':9,'cumulative':543,'remaining':45},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
