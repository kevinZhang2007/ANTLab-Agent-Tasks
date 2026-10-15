"""显式更新交付层；以保留的旧manifest为种子，不改历史响应或评价。"""
import argparse,copy,hashlib,json
from collections import Counter
from datetime import datetime
from pathlib import Path
import recalculate as scoring

def escape(v):return str(v).replace('~','~0').replace('/','~1')
def main(root,seed,expected):
    root=root.resolve();seed=scoring.safe_path(root,seed)
    old=scoring.read_json(seed);manifest=copy.deepcopy(old)
    for rel,h in old['source_hashes'].items():
        if hashlib.sha256(scoring.safe_path(root,rel).read_bytes()).hexdigest()!=h:raise ValueError('旧归档改变：'+rel)
    files={};parse_errors=[]
    for base in ['基础/runs','进阶/runs']:
        for p in sorted((root/base).rglob('*.json')):
            if any('snapshot' in part.lower() and 'code' in part.lower() for part in p.parts):continue
            try:files[p.relative_to(root).as_posix()]=scoring.read_json(p)
            except (ValueError,UnicodeError) as error:parse_errors.append({'path':p.relative_to(root).as_posix(),'error':str(error)})
    if parse_errors:raise ValueError('归档JSON解析失败：'+str(parse_errors))
    records=manifest['records'];seen={r['metadata']['row_id'] for r in records};old_generation={r['metadata']['run_id']:r['source_path'] for r in records if r['metadata']['count_as_generation']}
    generation_paths={};duplicates=[]
    for path,data in files.items():
        if not path.startswith('基础/runs/') or not isinstance(data,dict) or not data.get('run_id'):continue
        response=data.get('response');usage=data.get('usage') or (response.get('usage') if isinstance(response,dict) else {}) or {}
        if usage.get('completion_tokens',0)<=0:continue
        rid=data['run_id']
        if rid in generation_paths:
            prior=files[generation_paths[rid]]
            if prior.get('response')!=data.get('response') or prior.get('messages')!=data.get('messages'):raise ValueError('同ID内容冲突：'+rid)
            duplicates.append({'run_id':rid,'paths':[generation_paths[rid],path]})
        else:generation_paths[rid]=path
    if len(generation_paths)!=expected:raise ValueError('生成数不符：'+str(len(generation_paths)))
    if not old_generation.keys()<=generation_paths.keys():raise ValueError('旧生成记录丢失')
    generation_paths.update(old_generation)
    def remember(path):manifest['source_hashes'][path]=hashlib.sha256(scoring.safe_path(root,path).read_bytes()).hexdigest()
    def freeze_of(path):
        parent=(root/path).parent
        while parent!=root and parent.is_relative_to(root):
            if (parent/'freeze.json').is_file():
                rel=(parent/'freeze.json').relative_to(root).as_posix();remember(rel);return parent.relative_to(root).as_posix(),rel
            parent=parent.parent
        return str(Path(path).parent).replace('\\','/'),''
    def add(path,ptr,data,kind,source,labels=None,labelptr=None,extra=None):
        rowid=f'{kind}:{path}#{ptr}'
        if rowid in seen:return
        rid=data.get('run_id','');ids=data.get('stage_run_ids',data.get('run_ids',[]))
        if isinstance(ids,list) and ids:rid=next((i for i in reversed(ids) if i in generation_paths),rid)
        task=data.get('task_path')
        if isinstance(task,str) and task in files:
            saved=files[task];remember(task)
            rid=next((s['run_id'] for s in reversed(saved.get('stages',[])) if s.get('run_id') in generation_paths),rid)
            data={**saved,**data}
        rawpath=generation_paths.get(rid,'');rawdata=files.get(rawpath,{})
        response=rawdata.get('response') or {};choices=response.get('choices',[]) if isinstance(response,dict) else []
        rawcontent=rawdata.get('raw_content') or (choices[0].get('message',{}).get('content','') if choices else '')
        value=data.get('actual_final_output',data.get('system_final_response',data.get('candidate_response'))) if source=='system_final' else None
        if not isinstance(value,dict):
            try:value=json.loads(rawcontent)
            except (ValueError,TypeError):value={}
        if not isinstance(value,dict):value={}
        origin=data.get('output_source',data.get('actual_final_output_source','not_saved'))
        version,freeze=freeze_of(rawpath or path)
        timing=data.get('timing',data.get('timing_summary',{})) or {}
        elapsed=data.get('elapsed_seconds',data.get('end_to_end_seconds',timing.get('end_to_end_seconds','not_saved')))
        derived=source in ['local_rule_trace','local_rule_derived'] or source=='system_final' and str(origin).startswith('local_rule')
        meta={k:'' for k in scoring.FIELDS if k not in scoring.METRICS}
        meta.update(row_id=rowid,row_kind=kind,experiment_class='system_exploration' if derived else 'subsequent_exploration',version=version,freeze_path=freeze,freeze_sha256=manifest['source_hashes'].get(freeze,'not_saved'),case_id=data.get('case_id',rawdata.get('case_id','not_saved')),condition=data.get('condition',rawdata.get('condition','not_saved')),variant=data.get('variant',rawdata.get('variant','not_saved')),main_task_id=data.get('main_task_id',rawdata.get('main_task_id','not_saved')),run_id=rid or 'not_saved',stage=rawdata.get('stage','not_saved'),attempt=rawdata.get('attempt','not_saved'),retry_of=rawdata.get('retry_of','not_saved'),model=rawdata.get('config',{}).get('model',response.get('model','not_saved')),configuration_ref=rawpath+'#/config' if rawpath else 'not_saved',result_source=source,output_origin=origin,status=data.get('status',rawdata.get('status','not_saved')),http_status=rawdata.get('http_status','not_saved'),elapsed_seconds=elapsed,elapsed_scope='end_to_end_or_answer_replay_as_archived' if timing else 'single_model_request',raw_content=rawcontent or 'not_saved',answer=json.dumps(value.get('answer','not_saved'),ensure_ascii=False),citations=json.dumps(value.get('citations','not_saved'),ensure_ascii=False),usage=json.dumps(rawdata.get('usage') or response.get('usage') or 'not_saved',ensure_ascii=False),usage_source=rawpath or 'not_saved',judgment_reason=json.dumps((labels or {}).get('reasons',data.get('reason','not_checked')),ensure_ascii=False),run_kind='local_rule' if derived else rawdata.get('run_kind','not_saved'),judgment_source='rule' if derived else 'unverified',count_as_generation=kind=='model_generation',count_as_b_replay=False,scoring_view='',raw_record_path=rawpath,assessment_path=path if kind=='assessment' else '',ambiguity=json.dumps((labels or {}).get('ambiguity','not_checked'),ensure_ascii=False))
        if extra:meta.update(extra)
        bindings={}
        if labels is not None:
            for metric,aliases in scoring.METRICS.items():
                key=next((k for k in aliases if k in labels),None)
                if key:bindings[metric]={'path':path,'pointer':(ptr if labelptr is None else labelptr)+'/'+escape(key),**({'list_presence':True} if metric=='has_unrelated_references' and isinstance(labels[key],list) else {})}
        records.append({'source_path':path,'source_pointer':ptr,'metadata':meta,'labels':bindings});seen.add(rowid);remember(path)
        if rawpath:remember(rawpath)
    for rid,path in generation_paths.items():
        if rid not in old_generation:add(path,'',files[path],'model_generation','model_raw',extra={'count_as_generation':True,'raw_record_path':path,'elapsed_scope':'single_model_request'})
    accepted={'effective-reviews.json','effective-semantic-review.json','semantic-review.json','evaluations.json','evaluation.json','comparison-review.json','defect-review.json','local-reading-review.json','local-and-final-review.json','qualification-review.json','review-summary.json','evaluation-summary.json'}
    old_assessments={r['source_path'] for r in records if r['metadata']['row_kind']=='assessment'}
    sides={'raw_review':'model_raw','system_final_review':'system_final','raw':'model_raw','final':'system_final','system_review':'system_final','before_system_review':'before_system_review','after_system_review':'after_system_review'}
    scalar_checks=[]
    for path,document in files.items():
        if not path.startswith('基础/runs/') or Path(path).name not in accepted or path in old_assessments:continue
        def walk(node,ptr='',inherited=None):
            if isinstance(node,list):
                for i,child in enumerate(node):walk(child,ptr+'/'+str(i),inherited)
            elif isinstance(node,dict):
                context={**(inherited or {}),**{k:node[k] for k in ['case_id','condition','variant','main_task_id','run_id','run_ids','stage_run_ids','dataset','arm','comparison_arm','task_path'] if k in node}}
                found=[s for s in sides if isinstance(node.get(s),dict) and any(k in node[s] for k in scoring.METRICS)]
                if found and context.get('case_id'):
                    for side in found:
                        dataset=context.get('dataset','development' if Path(path).name=='evaluation-summary.json' else '')
                        arm=context.get('arm',context.get('comparison_arm',''))
                        view=path+'#'+side+'#'+str(dataset)+'#arm='+str(arm)
                        add(path,ptr+'/'+side,{**node,**context},'assessment',sides[side],node[side],ptr+'/'+side,{'scoring_view':view})
                    return
                for key in ['evaluation','final_evaluation','rows','items','tasks','results','final_answers','reviews']:
                    if key in node:walk(node[key],ptr+'/'+escape(key),context)
        before=len(records);walk(document)
        newrows=records[before:]
        summary_path=str(Path(path).with_name('summary.json')).replace('\\','/')
        summary=files.get(summary_path,{})
        # 两次完整重复运行的逐条评价与其原有dataset汇总逐项对照。
        if Path(path).name=='effective-reviews.json' and isinstance(summary,dict) and isinstance(summary.get('datasets'),dict):
            for dataset,group in summary['datasets'].items():
                for side,metrics in group.get('metrics',{}).items():
                    source=sides.get(side)
                    matches=[r['metadata'] for r in newrows if r['metadata']['scoring_view']==path+'#'+side+'#'+dataset+'#arm=']
                    if not matches:raise ValueError('原汇总没有对应逐条评价：'+summary_path+' '+dataset+' '+side)
                    keys={(m['scoring_view'],m['condition'],m['variant'],m['result_source']) for m in matches}
                    if len(keys)!=1:raise ValueError('原汇总对应多个分组：'+summary_path)
                    view,condition,variant,result_source=next(iter(keys))
                    for metric,saved in metrics.items():
                        if metric in scoring.METRICS and isinstance(saved,dict) and 'numerator' in saved:
                            manifest['summary_checks'].append({'path':summary_path,'pointer':'/datasets/'+escape(dataset)+'/metrics/'+escape(side)+'/'+escape(metric),'view':view,'condition':condition,'variant':variant,'result_source':result_source,'metric':metric})
                    remember(summary_path)
        # 最近轮次的明确整数汇总也检查，绝不通过修改标签配平。
        groups=document.get('groups',document.get('metrics',{})) if isinstance(document,dict) else {}
        aliases={'raw_answer_correct':('model_raw','answer_correct'),'raw_strict':('model_raw','strict_complete_success'),'final_answer_correct':('system_final','answer_correct'),'final_strict':('system_final','strict_complete_success'),'system_answer_correct':('system_final','answer_correct'),'system_strict':('system_final','strict_complete_success')}
        if isinstance(groups,dict):
            for name,group in groups.items():
                if not isinstance(group,dict):continue
                for savedkey,(source,metric) in aliases.items():
                    if not isinstance(group.get(savedkey),int):continue
                    members=[r for r in newrows if r['metadata']['result_source']==source and ('#arm='+name==r['metadata']['scoring_view'][r['metadata']['scoring_view'].rfind('#arm='):] or '#'+name+'#arm=' in r['metadata']['scoring_view'])]
                    if not members:continue
                    scalar_checks.append({'summary_path':path,'summary_pointer':'/'+('groups' if 'groups' in document else 'metrics')+'/'+escape(name),'saved_numerator_field':savedkey,'saved_denominator_field':'denominator','row_ids':[r['metadata']['row_id'] for r in members],'metric':metric})
    for path,data in files.items():
        if not isinstance(data,dict) or not path.startswith('基础/runs/'):continue
        if Path(path).name.startswith('task-'):
            for key in ['proof_record','ratio_proof','difference_proposal']:
                if isinstance(data.get(key),dict) and data[key]:add(path,'/'+key,{**data,**data[key]},'rule_trace','local_rule_trace',extra={'run_kind':'local_rule','judgment_source':'rule'})
        if 'stop' in Path(path).name and not data.get('run_id'):add(path,'',data,'preparation_or_stop','preserved_failure_record',extra={'status':data.get('status','see_original'),'run_kind':'not_applicable'})
    manifest.update(created_at=datetime.now().astimezone().isoformat(),expected_counts={'model_generations':expected,'b_offline_executions':88},seed_manifest=seed.relative_to(root).as_posix(),expected_generation_ids=sorted(generation_paths),duplicate_storage=duplicates,new_group_summary_checks=scalar_checks)
    manifest['record_counts']=dict(Counter(r['metadata']['row_kind'] for r in records));manifest['source_hashes']=dict(sorted(manifest['source_hashes'].items()))
    output=root/'results';(output/'scoring/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    rows=scoring.make_rows(root,manifest,files);(output/'results.csv').write_text(scoring.csv_text(rows),encoding='utf-8',newline='')
    return {'row_counts':manifest['record_counts'],'csv_rows':len(rows),'new_summary_checks':len(scalar_checks),'model_ids':len(generation_paths),'old_record_specs_retained':len(old['records']),'all_old_specs_unchanged':manifest['records'][:len(old['records'])]==old['records']}
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);parser.add_argument('--seed',required=True);parser.add_argument('--expected-generations',required=True,type=int)
    args=parser.parse_args();print(json.dumps(main(args.root,args.seed,args.expected_generations),ensure_ascii=False))
