from pathlib import Path
from datetime import datetime
import ast,copy,hashlib,importlib.util,json,shutil,sys
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
BEST=ROOT/'基础/runs/final_five/20261015-210223'
L=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
N=lambda:datetime.now().astimezone().isoformat()
def W(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as o:json.dump(v,o,ensure_ascii=False,indent=2)
def p(text,pid):return {'id':pid,'source':'独立自造资料','text':text}
def raw(answer):return json.dumps({'answer':answer,'citations':[]},ensure_ascii=False)
def main():
    F=ROOT/'基础/runs/delivery_robustness'/datetime.now().strftime('%Y%m%d-%H%M%S');F.mkdir(parents=True,exist_ok=False)
    W(F/'plan.json',{'saved_at':N(),'generation_limit':0,'baseline_generations':534,'source_freeze':(BEST/'round5/freeze.json').relative_to(ROOT).as_posix(),'scope':'只核对入口与独立自造反例；不运行D/T、不启动模型。','failure':'先保存最小反例，安全独立修复后必须跑旧回归；冻结版本不改。证明拒绝时保留原答，不补默认值。','export':'旧results完整另存快照，再更新明确映射；不改原评价。','limits':'已接触题上的成绩不称泛化；未核验状态如实保留。'})
    protected={p.relative_to(ROOT).as_posix():H(p) for base in [ROOT/'基础/runs',ROOT/'进阶/runs'] for p in base.rglob('*') if p.is_file() and F not in p.parents}
    for name in ['report.md','README.md','基础/开发记录.md']:protected[name]=H(ROOT/name)
    W(F/'protected-hashes.json',protected)
    frozen=L(BEST/'round5/freeze.json');differences=[]
    for path,expected in {**frozen['code_hashes'],**frozen['data_hashes']}.items():
        if H(ROOT/path)!=expected:differences.append(path)
    W(F/'entry-verification.json',{'checked_at':N(),'passed':not differences,'differences':differences,'freeze_sha256':H(BEST/'round5/freeze.json'),'entry':(BEST/'bounded_candidate.py').relative_to(ROOT).as_posix(),'runner':(BEST/'run_bounded_round.py').relative_to(ROOT).as_posix(),'reproduction':(BEST/'reproduce_final.py').relative_to(ROOT).as_posix(),'core_pipeline':(BEST/'proof_pipeline_candidate.py').relative_to(ROOT).as_posix(),'model':frozen['model'],'llama_cpp':frozen['llama_cpp'],'answer_config':frozen['answer_config'],'selection_config':frozen['selection_config'],'service_arguments':frozen['service_arguments'],'code_hashes':frozen['code_hashes'],'data_hashes':frozen['data_hashes'],'kept_policy':{},'few_shot_not_adopted':L(ROOT/'基础/runs/few_shot/20261015-212723/selection.json')['selected_arm']=='control','model_binary_hash_check':'须在真实LOCALAPPDATA环境离线执行reproduce_final.py --verify-only；不启动服务。'})
    assert not differences
    sys.path.insert(0,str(ROOT/'基础/tests'));sys.path.insert(0,str(BEST))
    import general_citation_proof as cite,ratio_calculation_proof as ratio,difference_calculation_proposal as diff
    scope='绀羽项目Edition583版本在2025-11'
    dq=scope+'同机实验中，新链路的完整响应耗时中位数比旧链路少多少秒？只输出数值。'
    dm=p(scope+'的记录：顺序批次Ledger647的旧链路处理57个固定问题，客户端完整响应耗时中位数为43.75秒。','custom-data')
    de=p('批次Ledger647的复核补页：Ledger647新链路处理同样57个问题，中位数为29.125秒；两次保持输入顺序。','custom-extra')
    rq=scope+'冻结清单的完整支持率是多少？只输出百分数。'
    rm=p(scope+'的记录：冻结清单Register953固定125条主张为分母，后续复跑不能剔除无引用和格式异常主张。','ratio-count')
    re=p('批次Register953的复核补页：Register953人工复核显示45条完全支持、35条部分支持、30条矛盾、15条无引用；完整支持只计完全支持。','ratio-definition')
    sq=scope+'应发布哪个快照？只输出快照编号。'
    sm=p(scope+'的记录：复核表Document862显示Cap875签章核验通过、箱体定位通过、重放恢复通过；Cap982箱体定位9项偏移。','snapshot-data')
    se=p('批次Document862的复核补页：Document862的发布规则要求签章核验、箱体定位和重放恢复三项检查全部通过。','snapshot-rule')
    rows=[];cases=[]
    def add(name,branch,q,ps,answer,expected,explanation,universe=None):cases.append({'name':name,'branch':branch,'question':q,'passages':copy.deepcopy(ps),'raw_response':raw(answer),'expected_derived_answer':expected,'expected_basis':explanation,'audit_universe':copy.deepcopy(universe)})
    replace=lambda passage,a,b:{**passage,'text':passage['text'].replace(a,b)}
    add('difference_positive','calculation',dq,[dm,de],'证据不足','14.625','同范围、同单位、同统计量，43.75-29.125=14.625。')
    add('difference_scope_conflict','calculation',dq,[replace(dm,'Edition583','Edition584'),de],'原始保留',None,'版本冲突，不能派生。')
    add('difference_unit_conflict','calculation',dq,[dm,replace(de,'29.125秒','29.125毫秒')],'原始保留',None,'量纲单位不一致，不作默认换算。')
    add('difference_metric_missing','calculation',dq,[replace(dm,'客户端完整响应耗时中位数','未定义指标中位数'),de],'原始保留',None,'主文缺问题指定完整指标。')
    add('difference_evidence_missing','calculation',dq,[dm],'原始保留',None,'最终输入缺补充操作数，审计池有也不能补事实。',[dm,de])
    add('difference_direction_reversed','calculation',dq.replace('少多少','多多少'),[dm,de],'14.625','-14.625','改变明确运算方向，允许独立建议负差值，但旧正值不应获得引用证明。')
    add('difference_direction_unknown','calculation',dq.replace('少多少','相差多少'),[dm,de],'原始保留',None,'方向不受支持，拒绝而不猜正负。')
    add('ratio_positive','ratio',rq,[rm,re],'证据不足','36%','明确分类、分母125，45/125*100=36%。')
    add('ratio_definition_missing','ratio',rq,[rm,replace(re,'；完整支持只计完全支持','')],'原始保留',None,'没有指标到分类定义，不能补业务常识。')
    add('ratio_class_overlap','ratio',rq,[rm,replace(re,'；完整支持','；部分支持与完全支持可同时属于同一主张；完整支持')],'原始保留',None,'明确分类交叉，不能当互斥计数。')
    add('ratio_conflicting_unit','ratio',rq,[rm,replace(re,'35条部分支持','35次部分支持')],'原始保留',None,'计数单位不同。')
    add('ratio_wrong_scope','ratio',rq,[rm,replace(re,'Register953','Register954')],'原始保留',None,'批次不同，无唯一直接关联。')
    add('ratio_zero_denominator','ratio',rq,[replace(rm,'125条','0条'),re],'原始保留',None,'零分母拒绝。')
    add('ratio_incomplete_input','ratio',rq,[rm],'原始保留',None,'定义在最终模型输入外，只可审计不可用作事实。',[rm,re])
    add('ratio_duplicate_categories','ratio',rq,[rm,replace(re,'35条部分支持','35条完全支持')],'原始保留',None,'同一分类重复计数，不选一项凑结果。')
    add('snapshot_positive','qualification',sq,[sm,se],'Cap875','Cap875','所有指定检查分别明示通过，引用数据与规则。')
    add('snapshot_unknown_condition','qualification',sq,[replace(sm,'、重放恢复通过',''),se],'Cap875',None,'缺一个必要条件，不把未知当通过。')
    add('snapshot_failed_condition','qualification',sq,[replace(sm,'重放恢复通过','重放恢复失败'),se],'Cap875',None,'获选对象必要检查明确失败。')
    add('snapshot_missing_rule','qualification',sq,[sm],'Cap875',None,'缺发布规则不能出正向资格证明。')
    add('snapshot_scope_conflict','qualification',sq,[replace(sm,'Edition583','Edition584'),se],'Cap875',None,'项目版本范围冲突。')
    add('snapshot_no_positive_evidence','qualification',sq,[replace(sm,'Cap875签章核验通过、箱体定位通过、重放恢复通过','Cap875只登记创建时间'),se],'Cap875',None,'其他对象失败不证明获选对象通过。')
    add('citation_wrong_direction','citations',dq.replace('少多少','多多少'),[dm,de],'14.625',None,'原answer方向错误，不能只拼齐引用掩盖。')
    add('citation_wrong_result','citations',dq,[dm,de],'14.626',None,'结果不符不派生引用，不纠正原answer。')
    add('citation_unit_conflict','citations',dq,[dm,replace(de,'29.125秒','29.125分钟')],'14.625',None,'来源真实但单位冲突仍拒绝。')
    add('citation_incomplete_sources','citations',dq,[dm],'14.625',None,'不能从审计池补入模型未见的引用。',[dm,de])
    add('citation_positive','citations',dq,[dm,de],'14.625','14.625','只为原正确答案组装两个实际来源。')
    # 编号和ID仅由自造机制样例重映射，期待行为必须对应不变。
    basecases=copy.deepcopy(cases)
    for c in basecases:
        if c['name'] not in ['difference_unit_conflict','ratio_definition_missing','snapshot_unknown_condition','citation_positive']:continue
        c['name']+='_remapped'
        for collection in ['passages','audit_universe']:
            for index,pas in enumerate(c.get(collection) or []):pas['id']='new-id-'+str(index);pas['text']=pas['text'].replace('Ledger647','Archive731').replace('Register953','Archive832').replace('Document862','Archive934').replace('Cap875','View613').replace('Cap982','View719')
        c['raw_response']=c['raw_response'].replace('Cap875','View613')
        if c['expected_derived_answer']=='Cap875':c['expected_derived_answer']='View613'
        c['passages'].reverse();cases.append(c)
    W(F/'synthetic-cases.json',{'saved_before_execution_at':N(),'cases':cases,'source':'独立自造，未使用D/T材料或答案。'})
    for index,case in enumerate(cases,1):
        before=copy.deepcopy(case);ps=case['passages'];q=case['question'];rr=case['raw_response'];universe=case['audit_universe']
        try:
            actual=(diff.propose if case['branch']=='calculation' else ratio.propose if case['branch']=='ratio' else cite.prove_answer)(q,ps,rr,universe)
            derived=actual.get('proposed_response') if case['branch'] in ['calculation','ratio'] else actual.get('derived_response')
            expected=case['expected_derived_answer'];passed=(derived is None if expected is None else derived is not None and derived['answer']==expected)
            passed=passed and case==before
            if derived is not None:passed=passed and set(derived['citations'])<={p['id'] for p in ps}
            if derived is not None and case['branch'] in ['citations','qualification']:passed=passed and derived['answer']==json.loads(rr)['answer']
            final=derived if derived is not None else json.loads(rr)
            if expected is None:passed=passed and final==json.loads(rr)
            row={**case,'actual':actual,'derived_response':derived,'final_response':final,'passed':passed,'raw_response_preserved':rr==before['raw_response'],'checked_at':N()}
        except Exception as error:row={**case,'passed':False,'exception':repr(error),'checked_at':N()}
        W(F/f'case-{index:02d}.json',row);rows.append(row)
        if not row['passed']:W(F/f'minimal-reproduction-{index:02d}.json',row)
    W(F/'counterexample-summary.json',{'checked_at':N(),'passed':all(r['passed'] for r in rows),'total':len(rows),'passed_count':sum(r['passed'] for r in rows),'failed':[r['name'] for r in rows if not r['passed']],'model_generations':0,'repairs_applied':False})
    shutil.copyfile(Path(__file__),F/'delivery_robustness.py')
    print(json.dumps({'folder':str(F),'total':len(rows),'passed':sum(r['passed'] for r in rows),'failures':[{'name':r['name'],'reason':r.get('actual',{}).get('reason'),'derived':r.get('derived_response'),'exception':r.get('exception')} for r in rows if not r['passed']]},ensure_ascii=False))
if __name__=='__main__':main()
