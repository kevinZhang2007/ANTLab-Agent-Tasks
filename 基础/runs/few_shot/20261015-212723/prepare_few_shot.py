from pathlib import Path
from datetime import datetime
from decimal import Decimal
import ast,copy,difflib,hashlib,json,shutil,sys
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
P=ROOT/'基础/runs/final_five/20261015-210223'
L=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
N=lambda:datetime.now().astimezone().isoformat()
def W(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2)
def main():
    F=ROOT/'基础/runs/few_shot'/datetime.now().strftime('%Y%m%d-%H%M%S');F.mkdir(parents=True,exist_ok=False)
    examples=[
      {'question':'绮叶项目这份徽章清单的蓝标率是多少？只输出百分数。','passages':[{'id':'例证萤','source':'自造徽章清单','text':'绮叶项目清单有48枚徽章。蓝标率定义为蓝标枚数除以清单总枚数，条纹标不计入蓝标。'},{'id':'例证苔','source':'自造徽章点数','text':'上述清单有18枚蓝标徽章，其余均为无标徽章。'}],'response':{'answer':'37.5%','citations':['例证萤','例证苔']},'verification':'18 / 48 × 100 = 37.5；定义、分母及分子来源齐全。'},
      {'question':'苇舟项目应接收哪个箱？只输出箱名。','passages':[{'id':'例证珀','source':'自造箱检记录','text':'苇舟项目：箱桔封签破损、防潮检查通过；箱梨封签完好、防潮检查通过。'},{'id':'例证霁','source':'自造接收规则','text':'本清单只接收封签完好且防潮检查通过的箱；仅一箱合格时选该箱。'}],'response':{'answer':'箱梨','citations':['例证珀','例证霁']},'verification':'箱桔明示违反封签条件；箱梨两项明确满足，且唯一合格。'},
      {'question':'山葵项目能确认清单玉可以归档吗？无法确认时回答证据不足。','passages':[{'id':'例证汀','source':'自造办理记录','text':'山葵项目的清单玉已签章，未记录校对状态。'},{'id':'例证岚','source':'自造归档规则','text':'本项目归档必须已签章且校对通过。'}],'response':{'answer':'证据不足','citations':['例证汀','例证岚']},'verification':'签章已说明，校对未知，不能将未知当通过。'}]
    assert Decimal(18)/Decimal(48)*100==Decimal('37.5')
    prefix='以下三个简短自造示例只演示方法。示例事实、数值、对象及引用ID仅属于示例，不能作为当前问题的证据，也不能替当前资料补缺失定义。\n'
    addition=prefix+'\n'.join('示例'+str(i)+'：'+json.dumps({k:e[k] for k in ['question','passages','response']},ensure_ascii=False,separators=(',',':')) for i,e in enumerate(examples,1))
    W(F/'examples.json',{'saved_at':N(),'examples':examples,'system_appendix':addition,'synthetic_only':True,'not_from_development_or_evaluation_answers':True})
    freeze=L(P/'round5/freeze.json');diff=[]
    for p,h in {**freeze['code_hashes'],**freeze['data_hashes']}.items():
        if H(ROOT/p)!=h:diff.append(p)
    W(F/'parent-verification.json',{'checked_at':N(),'parent_freeze':(P/'round5/freeze.json').relative_to(ROOT).as_posix(),'sha256':H(P/'round5/freeze.json'),'differences':diff,'previous_cumulative':526})
    assert not diff
    names=list(L(P/'baseline-verification.json')['modules'])
    for name in names:shutil.copyfile(P/name,F/name)
    for name in ['prepare_final_five.py','development_evaluator.py']:shutil.copyfile(P/name,F/name)
    original=(P/'bounded_candidate.py').read_text(encoding='utf-8-sig')
    marker="    if 'temperature' in policy:config['parameters']['temperature']=policy['temperature']"
    assert original.count(marker)==1
    changed=original.replace(marker,"    if policy.get('few_shot'):\n        messages[0]['content']+='\\n\\n'+EXAMPLE_APPENDIX\n"+marker)
    changed=changed.replace('import copy,json','import copy,json\nfrom pathlib import Path\nEXAMPLE_APPENDIX=json.loads(Path(__file__).with_name(\'examples.json\').read_text(encoding=\'utf-8\'))[\'system_appendix\']',1)
    ast.parse(changed);(F/'bounded_candidate.py').write_text(changed,encoding='utf-8',newline='\n')
    (F/'few-shot.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),changed.splitlines(True),fromfile='frozen/bounded_candidate.py',tofile='few_shot/bounded_candidate.py')),encoding='utf-8')
    driver=(P/'run_bounded_round.py').read_text(encoding='utf-8-sig')
    driver=driver.replace("'bounded_candidate.py','run_bounded_round.py','prepare_final_five.py'","'bounded_candidate.py','run_bounded_round.py','prepare_final_five.py','examples.json','prepare_few_shot.py'")
    driver=driver.replace("'denominator':'先开发4题再评测8题R0，分母分别4/8；最多24次生成；质量错误不重试。'","'denominator':'4道开发题各对照/少样例候选一次；每侧分母4，共8次回答生成；定位只历史重放，不计新调用。'")
    driver=driver.replace("'round':plan['round'],'bounded_five_round_design':plan","'round':'few_shot_answer_replay','few_shot_design':plan")
    driver=driver.replace('"""评测后资格证明完整流程：指定候选评测8题R0重复测试，最多16次生成，证明与引用组装离线。"""','"""复用已验证运行器：开发4题少样例回答对照，最多8次生成。"""',1)
    ast.parse(driver);(F/'run_bounded_round.py').write_text(driver,encoding='utf-8',newline='\n')
    (F/'runner-reuse.diff').write_text(''.join(difflib.unified_diff((P/'run_bounded_round.py').read_text(encoding='utf-8-sig').splitlines(True),driver.splitlines(True),fromfile='frozen/run_bounded_round.py',tofile='few_shot/run_bounded_round.py')),encoding='utf-8')
    shutil.copyfile(Path(__file__),F/'prepare_few_shot.py')
    W(F/'baseline-verification.json',{'checked_at':N(),'source':P.relative_to(ROOT).as_posix(),'modules':{n:H(F/n) for n in names},'all_rule_modules_unchanged':True})
    run=F/'round1';run.mkdir()
    for name in ['settings.prepared.json','answer.prepared.json','selection.prepared.json']:shutil.copyfile(F/name,run/name)
    for name in ['parent-freeze-verification.json','version-verification.json']:shutil.copyfile(P/'round5'/name,run/name)
    prediction={'saved_at':N(),'hypothesis':'定义、资格和缺证示例可能改善回答与引用；可能无效，也可能把示例数值、ID或业务定义套入当前题。','competition':'更长提示可能分散注意、增加漏引或使既有成功退步；规则后处理也可能掩盖原答变化。','unique_change':'最终system末尾追加三个示例；当前user、最终原段落与顺序、Schema、采样、256预算及规则后处理保持不变。','selection':'先系统最终严格成功数，再系统答案正确数；同分保留原方案。任何示例污染或既有成功项退步均不采用；不追加第二候选。','regression_veto':'逐题核对原始/系统答案正确和严格成功；同时对比本轮对照及最新冻结运行。已通过的格式、ID检查、必要覆盖、支持发生退步亦列为否决依据。','contamination':'示例独有项目、对象、引用ID进入当前回答/引用，或示例特有数值充当当前结论却无当前原文依据，记录污染；正常的证据不足分支不算污染。不能仅凭未发现字面污染证明不存在隐性迁移。','definition_boundary':'D01缺失定义绑定仍不得由示例补充；本轮不读取T题或处理T01歧义。','timing':'开发题与正式题均已接触；本轮仅开发题回答阶段历史最终输入重放，不是完整流程。','failure':'最多8次回答生成；质量不重试；请求技术失败先核查是否发送并停止，不自动重发；每项即存，结束停止自有服务。','after_improvement':'若有改善只保存并报告，不自动运行T题或完整流程。'}
    jobs=[]
    for i in range(1,5):
        for arm in (['control','candidate'] if i%2 else ['candidate','control']):
            jobs.append({'sequence':len(jobs)+1,'case_id':f'D{i:02d}','dataset':'development','condition':'R0','variant':'improved','comparison_arm':arm,'policy':{} if arm=='control' else {'few_shot':True},'historical_task':(P/'round5'/f'task-{i:02d}.json').relative_to(ROOT).as_posix()})
    W(run/'execution-plan.prepared.json',{'experiment':'few_shot_final_answer','round':1,'saved_at':N(),'items':jobs,'generation_limit':8,'previous_cumulative':526,'design':prediction})
    sys.path.insert(0,str(ROOT/'基础/tests'));sys.path.insert(0,str(F));import bounded_candidate as candidate
    conf=L(run/'answer.prepared.json');checks=[];message_checks=[]
    prompt=candidate.student.prepare_messages('',[])[0]['content']
    W(F/'complete-prompts.json',{'saved_at':N(),'control':prompt,'candidate':prompt+'\n\n'+addition,'examples':examples})
    for i in range(1,5):
        task=L(P/'round5'/f'task-{i:02d}.json');before=copy.deepcopy(task)
        messages,config,_=candidate.core.answer_request(task['question'],task['used_passages'],conf,universe=task['original_passages'])
        old,oc=candidate.apply_policy(messages,config,{});new,nc=candidate.apply_policy(messages,config,{'few_shot':True})
        assert old[0]['content']==prompt and new[0]['content']==prompt+'\n\n'+addition
        assert old[1:]==new[1:] and oc==nc and task==before
        assert json.loads(old[1]['content'])=={'question':task['question'],'passages':task['used_passages']}
        assert old==task['stages'][-1]['messages'] and config==task['stages'][-1]['config']
        message_checks.append({'case_id':task['case_id'],'control_messages':old,'candidate_messages':new,'config':config,'only_system_appendix_changed':True,'actual_input_source':(P/'round5'/f'task-{i:02d}.json').relative_to(ROOT).as_posix()})
    for e in examples:
        assert all(pid in {p['id'] for p in e['passages']} for pid in e['response']['citations'])
    for name,h in L(F/'baseline-verification.json')['modules'].items():assert H(F/name)==h
    for path in F.glob('*.py'):ast.parse(path.read_text(encoding='utf-8-sig'))
    W(run/'execution-offline-check.json',{'checked_at':N(),'passed':True,'returncode':0,'only_system_changed':True,'example_ratio_recomputed':'18/48*100=37.5','examples_self_consistent':True,'all_rule_hashes_unchanged':True,'prior_regressions':{'old':534,'additional':28,'source':(P/'round4/summary.json').relative_to(ROOT).as_posix()},'message_checks':message_checks,'generation_calls':0})
    W(F/'preparation.json',{'saved_at':N(),'passed':True,'generation_calls':0,'model_calls_not_started':True,'source_freeze':(P/'round5/freeze.json').relative_to(ROOT).as_posix(),'hashes':{p.name:H(p) for p in F.iterdir() if p.is_file()}})
    print(str(F))
if __name__=='__main__':main()
