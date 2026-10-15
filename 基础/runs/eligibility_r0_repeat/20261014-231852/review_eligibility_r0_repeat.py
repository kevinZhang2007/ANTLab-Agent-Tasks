"""全部生成结束后复用原文依据，另存辅助暂判；不供生成入口导入。"""
import json
import statistics
from datetime import datetime
from pathlib import Path

ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
PARENT=ROOT/'基础/runs/eligibility_r0_repeat/20261014-231852'
FULL=PARENT/'full';SMALL=PARENT/'small';OUT=FULL/'review'
now=lambda:datetime.now().astimezone().isoformat()
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))

def write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as out:
        json.dump(value,out,ensure_ascii=False,indent=2);out.write('\n')

def parse(raw):
    try:
        value=json.loads(raw)
        ok=isinstance(value,dict) and set(value)=={'answer','citations'} and isinstance(value['answer'],str) and isinstance(value['citations'],list) and all(isinstance(i,str) for i in value['citations'])
        return value,ok
    except (ValueError,TypeError):return {},False

def main():
    execution=load(FULL/'execution-summary.json')
    assert execution['completed_main_tasks']==8 and not execution['technical_stop'] and execution['service_stopped']
    assert not OUT.exists();OUT.mkdir()
    note='Codex辅助原文复核，尚未经本人逐项确认；非官方成绩或独立人工判分。'
    tasks=[load(p) for p in sorted(FULL.glob('task-*.json'))]
    assert len(tasks)==8 and all(t['condition']=='R0' and t['variant']=='improved' for t in tasks)
    rows=[]
    for task in tasks:
        cid=task['case_id'];basis=load(ROOT/('基础/runs/formal_review/round1/evidence-'+cid+'.json'))
        original={p['id']:p for p in task['original_passages']}
        assert all(e['quote'] in original[e['id']]['text'] for e in basis['required_evidence'])
        assert basis['source_sha256']==load(FULL/'freeze.json')['data_hashes']['基础/data/cases.json']
        visible={p['id']:p for p in task.get('used_passages',[])}
        raw=task.get('raw_answer','');value,format_ok=parse(raw)
        answer=value.get('answer','');citations=value.get('citations',[]) if format_ok else []
        required={e['id'] for e in basis['required_evidence']}
        excluded={e['id']:e['reason'] for e in basis['excluded_evidence']}
        acceptable=basis.get('accepted_equivalent_forms',[basis['derived_answer']])
        if cid=='T04':acceptable=['流程乙','乙']
        if cid=='T07':acceptable=['方案丙','丙']
        correct=answer in acceptable;semantic=correct
        if cid=='T03' and answer in ['2.6秒','2.6 秒']:semantic=True
        if cid=='T07' and answer in ['选择方案丙','采用方案丙','最终选择方案丙']:semantic=True
        ids=bool(format_ok and citations and all(i in visible for i in citations))
        coverage=required.issubset(citations)
        input_coverage=required.issubset(visible)
        irrelevant=[i for i in citations if i in excluded]
        support=bool(semantic and ids and coverage)
        answer_reason=basis['derivation']+' 实际answer='+repr(answer)+'；不改写原回答。'
        support_reason='引用集合必须支持实际答案；数据与选择/发布规则分别核对，ID存在不等于支持。'
        ambiguity=None
        if cid=='T05':
            coverage=bool(set(citations)&required);input_coverage=bool(set(visible)&required)
            support=bool(correct and ids and coverage)
            support_reason='沿用澄清：目标校内组的采集边界或明确缺能耗段均可作有效缺证来源；不要求固定ID，不推出现实中绝对无采集。'
        if cid=='T01':
            ambiguity='S24完成三项有条件推导与未关闭问题为零未明示的严格字面边界保留。'
            answer_reason+=' '+ambiguity
            if answer in ['S24','证据不足']:
                correct=semantic='ambiguous'
                support='ambiguous' if ids and coverage else False
                ambiguity+=' 两种解释下答案评价不同，无法合并为无条件正确；待本人确认。'
            elif answer=='S23':
                answer_reason+=' S23明确缺坐标映射，与三项完成要求冲突；不依赖S24争议即可判该选择失败。'
            elif answer=='S25':
                answer_reason+=' S25有三项未关闭问题，与禁止未关闭定位问题冲突。'
        if answer=='证据不足' and cid in ['T02','T06']:
            answer_reason+=' 主任务完整R0资料可推导；最终漏选或拒答不能计端到端成功。'
        strict=bool(correct is True and format_ok and ids and coverage and support is True and not irrelevant)
        row={'reviewed_at':now(),'reviewer_note':note,'status':'provisional_not_personally_confirmed',
             'case_id':cid,'main_task_id':task['main_task_id'],'run_ids':[s['run_id'] for s in task.get('stages',[])],
             'raw_content':raw,'answer':answer,'citations':citations,'pipeline_status':task['status'],
             'answer_correct':correct,'semantic_consistent':semantic,'format_complete':format_ok,
             'citation_ids_exist':ids,'necessary_input_coverage':input_coverage,'necessary_coverage':coverage,
             'support_actual_answer':support,'irrelevant_ids':irrelevant,'has_unrelated_references':bool(irrelevant),
             'strict_complete_success':strict,'end_to_end_seconds':task.get('end_to_end_seconds'),
             'initial_input_ids':list(original),'final_input_ids':list(visible),
             'qualification_rule':task.get('eligibility_rule_audit'), 'ambiguity':ambiguity,
             'reasons':{'answer':answer_reason,'coverage':'必要来源='+','.join(sorted(required))+'；实际引用='+','.join(citations),
                        'support':support_reason,'unrelated':[{'id':i,'reason':excluded[i]} for i in irrelevant]},
             'basis_path':('基础/runs/formal_review/round1/evidence-'+cid+'.json'),
             'source_evidence':[{'id':e['id'],'quote':e['quote'],'text':original[e['id']]['text'],'cited':e['id'] in citations,'visible':e['id'] in visible} for e in basis['required_evidence']]}
        write(OUT/('review-'+cid+'.json'),{'basis':basis,'row':row});rows.append(row)
    metrics=['answer_correct','semantic_consistent','format_complete','citation_ids_exist','necessary_input_coverage','necessary_coverage','support_actual_answer','has_unrelated_references','strict_complete_success']
    sums={m:{'true':sum(r[m] is True for r in rows),'false':sum(r[m] is False for r in rows),
             'ambiguous':sum(r[m]=='ambiguous' for r in rows),'denominator':8,
             'percent':sum(r[m] is True for r in rows)*100/8} for m in metrics}
    write(OUT/'effective-reviews.json',{'reviewed_at':now(),'reviewer_note':note,'rows':rows})
    write(OUT/'summary.json',{'reviewed_at':now(),'reviewer_note':note,'denominator':8,'metrics':sums,
        'selection_failures_count_in_denominator':True,'end_to_end_seconds':{'median':statistics.median(r['end_to_end_seconds'] for r in rows),'min':min(r['end_to_end_seconds'] for r in rows),'max':max(r['end_to_end_seconds'] for r in rows)},
        'qualification_enabled_tasks':sum(bool(r.get('qualification_rule',{}).get('qualification_enabled')) for r in rows),
        'scope':'评测后R0完整流程重复测试；非独立泛化评价，未自动采用。'})
    small_reviews=[]
    for path in SMALL.glob('run-*.json'):
        r=load(path);value,ok=parse(r['raw_content']);citations=value['citations'];answer=value['answer']
        inputs={p['id']:p for p in r['used_passages']}
        data=next(p for p in inputs.values() if '区域定位4项偏移' in p['text'])
        rule=next(p for p in inputs.values() if '三项检查全部通过' in p['text'])
        cover={data['id'],rule['id']}.issubset(citations)
        correct=answer=='K17'
        ids=bool(citations and all(i in inputs for i in citations))
        small_reviews.append({'sequence':r['sequence'],'variant':r['variant'],'run_id':r['run_id'],'raw_content':r['raw_content'],
              'answer_correct':correct,'citation_ids_exist':ids,'citation_coverage':cover,'support':correct and cover and ids,'strict_complete_success':correct and ok and cover and ids,
              'elapsed_seconds':r['elapsed_seconds'],'reviewer_note':note,
              'basis':'K16定位4项偏移、K18恢复2项失败；K17三项通过。发布规则要求三项全部通过；选择正确仍须引用数据与发布条件。'})
    write(SMALL/'evaluations.json',{'reviewed_at':now(),'rows':sorted(small_reviews,key=lambda r:r['sequence'])})
    generated={}
    for path in (ROOT/'基础/runs').rglob('*.json'):
        value=load(path)
        if not isinstance(value,dict):continue
        usage=value.get('usage')
        if not isinstance(usage,dict) and isinstance(value.get('response'),dict):usage=value['response'].get('usage')
        if isinstance(usage,dict) and usage.get('completion_tokens',0)>0 and value.get('run_id'):
            generated.setdefault(value['run_id'],[]).append(path.relative_to(ROOT).as_posix())
    write(PARENT/'generation-count.json',{'checked_at':now(),'unique_generated_run_ids':len(generated),
          'this_round_small':2,'this_round_full':execution['confirmed_generation_calls'],'previous':316,'run_id_sources':generated})
    print(json.dumps({'small':sorted(small_reviews,key=lambda r:r['sequence']),
        'rows':[{'case_id':r['case_id'],'answer':r['answer'],'citations':r['citations'],'correct':r['answer_correct'],'semantic':r['semantic_consistent'],
                 'coverage':r['necessary_coverage'],'support':r['support_actual_answer'],'unrelated':r['has_unrelated_references'],'strict':r['strict_complete_success'],
                 'seconds':round(r['end_to_end_seconds'],3)} for r in rows], 'summary':sums,'unique_generated':len(generated)},ensure_ascii=False))

if __name__=='__main__':main()
