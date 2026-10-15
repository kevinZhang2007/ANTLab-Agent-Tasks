"""第四轮：现有自造回归与补充稳健性检查，无模型调用。"""
from pathlib import Path
from datetime import datetime
import copy,hashlib,importlib.util,json,os,shutil,subprocess,sys
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
F=ROOT/'基础/runs/final_five/20261015-210223'
L=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
N=lambda:datetime.now().astimezone().isoformat()
def W(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as o:json.dump(v,o,ensure_ascii=False,indent=2)
def main():
    assert L(ROOT/'基础/runs/delivery_robustness/20261015-213832/counterexample-summary.json')['passed']
    out=ROOT/'基础/runs/delivery_robustness/20261015-213832/retained-regressions';out.mkdir(exist_ok=False)
    W(out/'plan.json',{'saved_at':N(),'run_kind':'local_rule','judgment_source':'rule','generation_limit':0,'prediction':'既有保守解析器可能对措辞不适用；不以未知强行证明。','selection':'只修反例证明且能安全泛化的缺陷；旧回归不得删除。未发现安全缺陷则保留现版也算完成一轮。','scope':'自造数值、单位、范围、否定、次序、编号与ID；不读取T题记录。','retained_regressions':534})
    env=dict(os.environ);env['PYTHONPATH']=str(F)+os.pathsep+str(ROOT/'基础/tests');env['PYTHONDONTWRITEBYTECODE']='1'
    drivers=[('association','check_association_compat.py','association-compat-self-tests.json',78),('citation','check_general_citation_proof.py','self-check.json',130),('project','check_project_scope_resolution.py','boundary-check.json',83),('ratio','check_ratio_calculation_proof.py','ratio-check.json',146),('calculation','check_calculation_compat.py','calculation-compat-self-tests.json',97)]
    summaries=[]
    for name,script,result,expected in drivers:
        folder=out/name;folder.mkdir();shutil.copyfile(F/script,folder/script)
        command=[sys.executable,'-X','utf8','-B',str(folder/script)]
        proc=subprocess.run(command,env=env,capture_output=True,text=True,encoding='utf-8')
        (folder/'stdout.txt').write_text(proc.stdout,encoding='utf-8');(folder/'stderr.txt').write_text(proc.stderr,encoding='utf-8')
        actual=L(folder/result) if (folder/result).is_file() else None
        count=actual.get('total',actual.get('count')) if actual else None
        row={'group':name,'command':command,'returncode':proc.returncode,'expected':expected,'count':count,'passed':bool(proc.returncode==0 and actual and actual['passed'] and count==expected),'result':(folder/result).relative_to(ROOT).as_posix()}
        W(folder/'execution.json',row);summaries.append(row)
        if not row['passed']:
            W(out/'summary.json',{'checked_at':N(),'passed':False,'retained':summaries,'reason':'既有回归失败，阻断最终运行，保留本轮不采用任何修复','generation_calls':0});return 1
    sys.path.insert(0,str(F));import explicit_state_checker as states
    cases=[('解析失败',['explicit_defect']),('不存在失败',['explicit_absence']),('偏移为0',['explicit_absence']),('未关闭问题为零',['explicit_absence']),('三项检查通过',['explicit_pass']),('三项中两项通过',['unknown']),('三项未全部通过',['unknown']),('零项通过',['unknown']),('并非解析失败，但恢复失败',['explicit_absence','explicit_defect']),('定位偏移为0，恢复失败2项',['explicit_absence','explicit_defect']),('未说明恢复失败',['unknown']),('失败率未知',['unknown'])]
    rows=[]
    for text,expected in cases:
        for variant in [text,text.replace('，','；').replace('，','。').replace('但','但是')]:
            events=[]
            for start,end in states.item_spans(variant):events.extend(states.inspect_item(variant,start,end))
            actual=[e['status'] for e in events]
            rows.append({'input':variant,'expected':expected,'actual':actual,'events':events,'passed':actual==expected})
    # 多候选归属与编号/ID重映射：不按前缀推断对象身份。
    for numbers in [('Mark82','Note73'),('Obj951','Trace645')]:
        for pid in ['source','renamed-source']:
            text=f'记录{numbers[0]}恢复失败；记录{numbers[1]}解析通过。'
            ps=[{'id':pid,'source':'自造','text':text}];candidates=[]
            for n in numbers:
                start=text.index(n);candidates.append({'snapshot':n,'sources':[{'passage_index':0,'passage_id':pid,'start':start,'end':start+len(n)}]})
            before=copy.deepcopy((ps,candidates));actual=states.inspect_explicit_states(ps,candidates)
            passed=[r['observed_state'] for r in actual]==['explicit_defect','explicit_pass_only'] and (ps,candidates)==before
            rows.append({'input':ps,'candidates':candidates,'actual':actual,'passed':passed,'expected':'各自子句归属不交叉'})
    W(out/'additional-synthetic.json',{'rows':rows,'passed':all(r['passed'] for r in rows),'total':len(rows),'passed_count':sum(r['passed'] for r in rows),'generation_calls':0})
    from offline_gate import after_offline_success
    blocked=[]
    try:after_offline_success(lambda:{'passed':False,'returncode':1},lambda:blocked.append('unsafe_start'))
    except RuntimeError:pass
    gate=not blocked
    W(out/'failure-gate.json',{'passed':gate,'simulated_failed_check_blocks_start':gate,'service_started':False,'generation_calls':0})
    passed=all(r['passed'] for r in rows) and gate
    for name,h in L(F/'baseline-verification.json')['modules'].items():assert H(F/name)==h
    summary={'checked_at':N(),'passed':passed,'returncode':0 if passed else 1,'old_tests':534,'old_passed':534,'additional_total':len(rows),'additional_passed':sum(r['passed'] for r in rows),'retained':summaries,'rule_changes':[],'decision':'未发现可安全修复且需要改变现有规则的缺陷，保留原规则。' if passed else '补充检查存在失败，保留失败，不采用修复并阻断最终运行。','generation_calls':0,'failed_examples':[r for r in rows if not r['passed']]}
    W(out/'summary.json',summary);print(json.dumps(summary,ensure_ascii=False));return summary['returncode']
if __name__=='__main__':raise SystemExit(main())
