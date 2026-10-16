"""Rebuild the A delivery export from explicit archived sources; no model calls.

Requires an untouched pre-A results snapshot. This is an export writer;
recalculate.py remains the separate read-only verification command.
"""
from pathlib import Path
from datetime import datetime
import argparse, json, hashlib, importlib.util, collections
ROOT=Path(__file__).resolve().parents[2]
NOW=datetime.now().astimezone().isoformat()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p):return p.relative_to(ROOT).as_posix()
def export(root,history,out):
    spec=importlib.util.spec_from_file_location('scoring',root/'results/scoring/recalculate.py');sc=importlib.util.module_from_spec(spec);spec.loader.exec_module(sc)
    manifest=read(history/'scoring/manifest.json');old_records=json.dumps(manifest['records'],sort_keys=True)
    for n,h in manifest['source_hashes'].items():assert sha(root/n)==h,n
    cache={};a=root/'进阶/a_exploration';runs={};copies=collections.defaultdict(list);docs={}
    for p in sorted(a.rglob('*.json')):
        if '__pycache__' in p.parts:continue
        d=read(p)
        if not isinstance(d,dict):continue
        docs[rel(p)]=d;response=d.get('response');usage=d.get('usage') or (response.get('usage') if isinstance(response,dict) else {}) or {}
        if d.get('run_id') and isinstance(d.get('messages'),list) and isinstance(response,dict) and usage.get('completion_tokens',0)>0:
            rid=d['run_id'];copies[rid].append(rel(p))
            if rid in runs:
                prior=docs[runs[rid]]
                assert prior.get('messages')==d.get('messages') and prior.get('response')==d.get('response'),rid
            if rid not in runs or (len(p.parts),len(str(p)))<(len(Path(runs[rid]).parts),len(runs[rid])):runs[rid]=rel(p)
    assert len(runs)==144,len(runs)
    # A-specific metrics remain separate from foundation answer correctness.
    additions={'a_label_correct':['label_correct'],'a_source_authenticity':['source_authenticity'],'a_reason_consistent':['reason_consistent','reason_label_consistent']}
    code=(history/'scoring/recalculate.py').read_bytes();text=code.decode('utf-8');line='METRICS = {'
    assert text.count(line)==1
    nl='\r\n' if '\r\n' in text else '\n'
    text=text.replace(line,line+nl+''.join('    '+repr(k)+': '+repr(v)+','+nl for k,v in additions.items()),1)
    extra_fields=['label','sentence_ids','review_acknowledgment']
    anchor=' + list(METRICS)';assert text.count(anchor)==1
    text=text.replace(anchor,' + '+repr(extra_fields)+anchor,1)
    (root/'results/scoring/recalculate.py').write_bytes(text.encode())
    spec=importlib.util.spec_from_file_location('scoring_new',root/'results/scoring/recalculate.py');sc=importlib.util.module_from_spec(spec);spec.loader.exec_module(sc)
    ack=rel(out/'review-acknowledgment.json')
    def remember(n):manifest['source_hashes'][n]=sha(root/n)
    def nearest(n):
        parent=(root/n).parent
        while parent!=root:
            for name in ['final-freeze.json','freeze.json']:
                p=parent/name
                if p.exists():remember(rel(p));return rel(p)
            parent=parent.parent
        return ''
    def add(n,ptr,d,kind,source,extra=None,labels=None):
        m={k:'' for k in sc.FIELDS if k not in sc.METRICS};rid=d.get('run_id','');rawpath=runs.get(rid,'');raw=docs.get(rawpath,{})
        f=nearest(n);resp=raw.get('response') or {};content=raw.get('content',raw.get('raw_content',''))
        if not content and isinstance(resp,dict):content=next(iter(resp.get('choices',[])),{}).get('message',{}).get('content','')
        config=raw.get('config') or {};value=d.get('expanded_response',d.get('parsed_internal',{})) or {}
        if not isinstance(value,dict):value={}
        m.update(row_id='A:'+kind+':'+n+'#'+ptr,row_kind=kind,experiment_class='A_frozen_evaluation' if '/evaluation/' in n else 'A_validation' if '/variants/' in n or '/counterfactual/' in n else 'A_development',version=str(Path(n).parent).replace('\\','/'),freeze_path=f,freeze_sha256=manifest['source_hashes'].get(f,'not_saved'),case_id=d.get('id',d.get('task_id',raw.get('case_id','not_saved'))),condition='A_claim_verification',variant=d.get('arm',d.get('variant','not_saved')),main_task_id=d.get('parent_request_id',d.get('main_task_id','not_saved')),run_id=rid or 'not_saved',request_id=d.get('request_id',raw.get('request_id','not_saved')),stage=raw.get('stage','not_saved'),attempt=raw.get('attempt','not_saved'),retry_of=raw.get('retry_of','not_saved'),model=config.get('model',resp.get('model','not_saved') if isinstance(resp,dict) else 'not_saved'),configuration_ref=rawpath+'#/config' if rawpath else 'not_saved',result_source=source,output_origin=source,status=d.get('status',raw.get('status','not_saved')),http_status=raw.get('http_status','not_saved'),elapsed_seconds=d.get('http_seconds',d.get('answer_http_seconds',raw.get('elapsed_seconds','not_saved'))),elapsed_scope='answer_http_request' if kind=='assessment' else 'single_model_request' if kind=='model_generation' else 'not_saved',raw_content=content,answer='not_applicable_A_uses_label',citations='not_applicable_A_uses_evidence',usage=json.dumps(raw.get('usage') or {},ensure_ascii=False),usage_source=rawpath,judgment_reason=json.dumps(d.get('basis',d.get('review_basis',d.get('reason','not_checked'))),ensure_ascii=False),run_kind='live_api' if kind=='model_generation' else 'local_rule' if kind=='program_expansion' else 'offline_review',judgment_source='model' if kind=='model_generation' else 'rule' if kind=='program_expansion' else 'AI_assisted_original_text_review',count_as_generation=kind=='model_generation',count_as_b_replay=False,scoring_view=n+'#A' if kind=='assessment' else '',raw_record_path=rawpath,assessment_path=n if kind=='assessment' else '',ambiguity=json.dumps(d.get('ambiguity','see_original_basis'),ensure_ascii=False),label=d.get('model_label',d.get('label',value.get('label','not_saved'))),sentence_ids=json.dumps(value.get('sentence_ids',d.get('sentence_ids','not_saved')),ensure_ascii=False),review_acknowledgment=ack)
        if extra:m.update(extra)
        manifest['records'].append({'source_path':n,'source_pointer':ptr,'metadata':m,'labels':labels or {}});remember(n)
        return m['row_id']
    for rid,n in sorted(runs.items()):add(n,'',docs[n],'model_generation','model_raw_internal',{'raw_record_path':n})
    excluded=lambda n:any(('snapshot' in x.lower() or x in ('frozen-code','engineering-history')) for x in Path(n).parts)
    for n,d in docs.items():
        if excluded(n):continue
        if Path(n).name.startswith('expansion-'):
            rid=Path(n).stem.removeprefix('expansion-');add(n,'',{**d,'run_id':rid},'program_expansion','model_selection_program_quote_expansion')
        elif 'stop' in Path(n).name.lower() and not d.get('run_id'):
            add(n,'',d,'preparation_or_stop','preserved_failure_record',{'run_kind':'not_applicable'})
    aliases={'a_label_correct':['label_correct','answer_correct','public_reference_label_correct','external_label_correct'],'a_source_authenticity':['source_authenticity','quote_authenticity_all'],'a_reason_consistent':['reason_consistent','reason_label_consistent','reason_label_consistency','reason_relation_or_baseline_label_consistent'],'format_complete':['format_complete','json_complete'],'necessary_input_coverage':['input_coverage','necessary_input_coverage','input_necessary_coverage'],'necessary_coverage':['necessary_coverage','necessary_citation_coverage','necessary_evidence_coverage','necessary_quoted_coverage'],'support_actual_answer':['citation_support','citation_support_actual_label','citation_support_actual_judgment'],'has_unrelated_references':['unrelated','unrelated_citations','has_unrelated_evidence','has_unrelated_citations'],'strict_complete_success':['strict','strict_complete_success']}
    added_reviews=[]
    for n,d in docs.items():
        if excluded(n) or Path(n).name not in ['review.json','review-summary.json']:continue
        rs=d.get('rows')
        if not isinstance(rs,list):continue
        for i,row in enumerate(rs):
            if not isinstance(row,dict) or not any(k in row for k in aliases['a_label_correct']):continue
            ptr='/rows/'+str(i);bindings={}
            for metric,keys in aliases.items():
                k=next((k for k in keys if k in row),None)
                if k:bindings[metric]={'path':n,'pointer':ptr+'/'+k,**({'list_presence':True} if metric=='has_unrelated_references' and isinstance(row[k],list) else {})}
            source='model_relation_mapped_to_external_label' if 'external_label_origin' in row else 'model_judgment_with_selected_evidence'
            rowid=add(n,ptr,row,'assessment',source,labels=bindings);added_reviews.append(rowid)
        # Explicit comparisons only when the archive supplies integer group counts.
        groups=d.get('groups',{})
        if isinstance(groups,dict):
            for arm,g in groups.items():
                if not isinstance(g,dict) or not isinstance(g.get('denominator'),int):continue
                members=[r['metadata']['row_id'] for r in manifest['records'] if r['source_path']==n and r['metadata']['row_kind']=='assessment' and r['metadata']['variant']==arm]
                if not members:continue
                ga={'a_label_correct':['label_correct'],'strict_complete_success':['strict','strict_complete_success'],'format_complete':['format_complete','json_complete'],'necessary_input_coverage':['input_coverage'],'necessary_coverage':['necessary_coverage','necessary_citation_coverage'],'support_actual_answer':['citation_support','citation_support_actual_label'],'has_unrelated_references':['unrelated','unrelated_citations'],'a_reason_consistent':['reason_consistent','reason_label_consistent']}
                for metric,keys in ga.items():
                    key=next((k for k in keys if type(g.get(k)) is int),None)
                    if key:manifest.setdefault('new_group_summary_checks',[]).append({'summary_path':n,'summary_pointer':'/groups/'+arm,'saved_numerator_field':key,'saved_denominator_field':'denominator','row_ids':members,'metric':metric})
    remember(ack)
    manifest.update(created_at=NOW,expected_counts={'model_generations':678,'b_offline_executions':88},expected_generation_ids=sorted(set(manifest['expected_generation_ids'])|set(runs)),seed_manifest=rel(history/'scoring/manifest.json'),A_current_review_acknowledgment=ack,A_storage_duplicates={k:v for k,v in copies.items() if len(v)>1})
    assert json.dumps(manifest['records'][:json.loads(old_records).__len__()],sort_keys=True)==old_records
    write(root/'results/scoring/manifest.json',manifest)
    (root/'results/results.csv').write_text(sc.csv_text(sc.make_rows(root,manifest)),encoding='utf-8',newline='')
    result=sc.run(root);assert result['all_compared_summaries_equal'],[x for x in result['summary_comparisons'] if not x['equal']]
    write(out/'export-verification.json',{'at':NOW,'counts':result['counts'],'csv_rows':result['csv_rows'],'row_kinds':result['row_kinds'],'comparisons':len(result['summary_comparisons']),'all_compared_summaries_equal':True,'A_unique_generation_ids':len(runs),'old_record_specs_preserved':len(json.loads(old_records)),'A_assessment_rows':len(added_reviews),'three_documents_missing_approved_text':True})

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history',required=True,help='Repository-relative pre-A results snapshot directory')
    parser.add_argument('--audit-output',required=True,help='Existing repository-relative audit directory with review-acknowledgment.json')
    args=parser.parse_args()
    history=(ROOT/args.history).resolve();out=(ROOT/args.audit_output).resolve()
    if not history.is_relative_to(ROOT) or not out.is_relative_to(ROOT):raise ValueError('Repository-relative directories required')
    if not (out/'review-acknowledgment.json').is_file():raise ValueError('Missing explicit current review acknowledgment')
    export(ROOT,history,out)
