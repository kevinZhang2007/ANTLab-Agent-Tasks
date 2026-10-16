from pathlib import Path
import sys,json
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,now
batch=Path(Path('a-bounded-root.txt').read_text(encoding='utf-8').strip());stage=batch/sys.argv[1];rt=load(stage/'runtime.json');assert 'error' not in rt and rt['model_stopped']
manual=load(stage/'semantic-basis.json');refs={x['id']:x for x in load(ROOT/'进阶/materials/a_dev_answers.json')};rows=[]
for item in load(stage/'result-index.json')['tasks']:
    task=load(stage/item['path'])
    for arm,v in task['arms'].items():
        r=v['raw'];ex=v['expansion'];m=manual[task['task_id']][arm];obj=ex['parsed_internal'];label=obj.get('label') if isinstance(obj,dict) else None;correct=ex['valid'] and label==refs[task['task_id']]['label']
        strict=bool(ex['valid'] and correct and m['necessary'] is True and m['support'] is True and m['unrelated'] is False)
        rows.append({'id':task['task_id'],'arm':arm,'run_id':r['run_id'],'raw_path':task['task_id']+'/run-'+r['run_id']+'.json','label':label,'label_correct':correct,'format_complete':ex['valid'],'source_authenticity':ex['valid'] and bool(ex['selected_sources']),'empty_selection':ex['valid'] and not ex['selected_sources'],'input_coverage':m['input'],'necessary_citation_coverage':m['necessary'],'citation_support':m['support'],'unrelated':m['unrelated'],'reason_consistent':m['consistent'],'strict':strict,'basis':m['basis'],'raw_content':r['content'],'http_seconds':r['elapsed_seconds'],'finish_reason':r['finish_reason'],'pdf_all_valid':bool(v['interface']['evidence']) and all(e['pdf_location']['locator_status']=='valid' for e in v['interface']['evidence'])})
groups={}
for arm in sorted({r['arm'] for r in rows}):
    rs=[r for r in rows if r['arm']==arm];groups[arm]={'denominator':3,'returned':len(rs),'label_correct':sum(r['label_correct'] for r in rs),'strict':sum(r['strict'] for r in rs),'format_complete':sum(r['format_complete'] for r in rs),'source_authenticity':sum(r['source_authenticity'] for r in rs),'input_coverage':sum(r['input_coverage'] is True for r in rs),'necessary_coverage':sum(r['necessary_citation_coverage'] is True for r in rs),'citation_support':sum(r['citation_support'] is True for r in rs),'unrelated':sum(r['unrelated'] is True for r in rs),'reason_consistent':sum(r['reason_consistent'] is True for r in rs),'pdf_all_valid':sum(r['pdf_all_valid'] for r in rs),'http_seconds':sum(r['http_seconds'] for r in rs)}
write(stage/'review.json',{'at':now(),'rows':rows,'groups':groups,'reviewer':'Codex辅助原文复核，尚待本人确认','reason_not_in_strict':True,'not_end_to_end_if_query_replay':True})
print(json.dumps({'groups':groups,'results':[(r['id'],r['arm'],r['label'],r['strict']) for r in rows]},ensure_ascii=False,indent=2))
