from pathlib import Path
from datetime import datetime
import ast,copy,hashlib,json,sys
R=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');F=R/'基础/runs/delivery_robustness/20261015-213832';BEST=R/'基础/runs/final_five/20261015-210223'
L=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
N=lambda:datetime.now().astimezone().isoformat()
def W(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2)
def main():
    result=L(F/'recalculation-final.json');assert result['all_compared_summaries_equal'] and result['counts']=={'model_generations':534,'b_offline_executions':88}
    (R/'results/scoring/reconciliation.json').write_text(json.dumps({'recorded_at':N(),**result},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    sys.path.insert(0,str(R/'基础/tests'));sys.path.insert(0,str(BEST));import bounded_candidate as candidate
    frozen=L(BEST/'round5/freeze.json');dependencies=[]
    for name,module in list(sys.modules.items()):
        file=getattr(module,'__file__',None)
        if not file:continue
        path=Path(file).resolve()
        if path.is_file() and path.is_relative_to(R):
            relative=path.relative_to(R).as_posix();expected=frozen['code_hashes'].get(relative)
            dependencies.append({'module':name,'path':relative,'sha256':H(path),'in_frozen_code_manifest':expected is not None,'hash_matches':H(path)==expected if expected else 'not_in_manifest'})
    assert all(d['hash_matches'] is True for d in dependencies if d['in_frozen_code_manifest'])
    W(F/'actual-import-dependencies.json',{'checked_at':N(),'entry':(BEST/'bounded_candidate.py').relative_to(R).as_posix(),'active_policy':candidate.POLICY,'dependencies':dependencies,'model_and_executable_verification':{'command':'python -X utf8 -B '+(BEST/'reproduce_final.py').relative_to(R).as_posix()+' --output 基础/runs/delivery_check_unused --verify-only','exit_code':0,'source_freeze_sha256':H(BEST/'round5/freeze.json'),'no_generation':True}})
    page_source=R/'基础/runs/repeat_integrated/20261015-171741'
    page_identical={name:H(page_source/name)==H(BEST/name) for name in L(BEST/'baseline-verification.json')['modules']}
    W(F/'entry-mapping.json',{'checked_at':N(),'original_entry':'基础/starter/runner.py + 基础/starter/student.py；保留首次主实验原方案，不是最新系统探索入口','final_generic_entry':(BEST/'bounded_candidate.py').relative_to(R).as_posix()+' execute(question, passages, variant, answer_config, selection_config, dispatch, save)','final_proof_pipeline':(BEST/'proof_pipeline_candidate.py').relative_to(R).as_posix(),'configuration_paths':[(BEST/'round5/freeze.json').relative_to(R).as_posix(),(BEST/'answer.prepared.json').relative_to(R).as_posix(),(BEST/'selection.prepared.json').relative_to(R).as_posix(),(BEST/'settings.prepared.json').relative_to(R).as_posix()],'page_entry':'基础/starter/server_exploration.py','page_actual_freeze':(page_source/'freeze.json').relative_to(R).as_posix(),'page_core_and_configs_equal':page_identical,'page_closure_reference':'基础/runs/page_closure/20261015-173656/closure-audit.json','page_limits':'页面硬绑定较早冻结路径、一次会话和允许题目；核心规则及配置字节一致，但没有直接使用第五轮freeze引用。仅D03实测一次，不能声称全部题型或baseline真实页面配对均已验证。','runtime_requirement':'实际验证为Python3.14；冻结运行器使用hashlib.file_digest，未实测Python3.10兼容性。模型与llama.cpp按冻结SHA放仓库外。','public_example_limit':'基础/config.local.example.json是较早简化配置，没有当前JSON Schema；复现最新方案应读冻结answer/selection/settings，不把旧示例称为完整最新配置。'})
    coverage=L(R/'进阶/runs/b_warm_boundary/20261013-191921/04-requirement-coverage.json')
    missing=[p for row in coverage for p in row['paths'] if not (R/p).exists()];assert not missing
    W(F/'b-requirement-audit.json',{'checked_at':N(),'existing_coverage':coverage,'all_listed_paths_exist':True,'concurrency_update':{'path':'进阶/runs/b_concurrency_plan/20261013-193110/plan.md','state':'planned_not_run','plan_exists':True,'requirement':'题目要求可执行方案与停止条件；不要求本周完成分布式系统。未执行不写通过。','limits':'HTTPServer串行，独立客户端不是权限隔离；没有用户认证或worker管理。'},'causal_limit':'现有材料已区分缓存污染与top-k漏证；源码排除top-k单独导致旧范围复用，不能将其包装成同一窄症状下仍成立的第二解释。需在报告明确机制作用范围及排除时间，不补造预测。','remaining_engine_contracts':['未知范围原Engine仍status=ok及固定draft；页面映射invalid_scope不等于修复Engine契约。','top-k先截取后范围过滤导致beta漏证。','Engine按ID标supported，页面语义not_checked；未实现独立语义支持器。'],'required_delivery_missing':['三项关键决定的本人判断、替代、AI影响及证据链接待本人确认归档。','README启动/接口映射及报告进阶B证据与未完成边界尚未更新。']})
    pending=[
      {'priority':1,'item':'主评分授权边界','status':'需澄清','basis':'results/scoring/scoring-policy.md：规则计算改答/引用组装未获明确主评分授权，继续仅列系统探索，不把7/8当首次主评分或独立泛化成绩。'},
      {'priority':1,'item':'最终声明与关键决定','status':'缺根目录decisions.md及declaration.md','exists':{'decisions.md':(R/'decisions.md').exists(),'declaration.md':(R/'declaration.md').exists()},'basis':'进阶/00_共同规则与接口.md和进阶/05_提交与报告格式.md；只能由本人确认实际判断与核验，不由Codex代签。'},
      {'priority':1,'item':'整合文档进度过时','status':'按本轮授权未修改','basis':'report.md第9行及README第5行仍124次，且写进阶B未实施；需另行提供确认文本更新至实际534次及B已有证据。旧开发记录时间和历史内容保留。'},
      {'priority':1,'item':'最终仓库与登记','status':'未完成/未联网核验','basis':'最终变更尚未提交，最终SHA、收集表、私有仓库评审权限需后续确认；本轮没有提交、推送或权限检查。'},
      {'priority':2,'item':'复现配置和入口','status':'有冻结入口；公共简化示例不能代表完整最终方案','basis':'entry-mapping.json；最终目录已有运行保护，必须新目录；weights、exe、环境及版本按哈希核对。Python3.10和新机完整流程未验证。'},
      {'priority':2,'item':'B因果结论边界','status':'需说明','basis':'b-requirement-audit.json；不得把被源码排除的解释说成同一窄症状下有效竞争解释，不能声称整个系统修复。'},
      {'priority':3,'item':'未验证限制','status':'保留','basis':'D01指标定义绑定、T01资格歧义；B检索、语义、未知范围契约仍有限制；并发/多用户仅有计划，题目不要求补做分布式实测。'}]
    W(F/'pending-delivery.json',{'recorded_at':N(),'items':pending,'no_model_calls':True,'evaluation_note':'已接触题上的探索或重复测试不是独立泛化成绩；辅助语义暂判尚未经本人逐项确认。'})
    policy=R/'results/scoring/scoring-policy.md';text=policy.read_text(encoding='utf-8-sig')
    text=text.replace('1010行不等于1010次调用','1457行不等于1457次调用').replace('428','534').replace('这19份通知','这20份通知')
    old='build_export.py只用于显式重建新导出层，不是只读入口。默认拒绝覆盖已有manifest；--refresh-export会重写results导出文件，不能用于实验重跑。本次干净副本只执行recalculate.py。'
    new='build_export.py只用于显式更新导出，不是只读入口；必须传入已保留的旧manifest作为--seed和--expected-generations 534。当前种子为results/history/20261015-214234/scoring/manifest.json，旧1010条spec保持不变，新增各轮独立视图。该命令会重写当前导出，不运行模型。干净副本仅执行recalculate.py。'
    assert old in text;text=text.replace(old,new)
    old='真实模型基础页面闭环尚未补齐，见page-integration-plan.md。本轮不启动服务。最终AI使用声明、本人实际核验项、关键决策归档、仓库权限和最终SHA登记仍需另行完成；本层不代为声明。B并发、多客户端及多worker材料只有计划，不能写成执行通过。'
    new='基础D03真实页面闭环已有基础/runs/page_closure/20261015-173656/closure-audit.json及截图、同请求日志；page-integration-plan.md保留为此前计划，不再代表当前完成状态。页面绑定较早但模块/配置相同的冻结版本，仅验证一题。最新入口、复现限制和交付缺项见delivery-status.json。最终AI声明、本人核验、关键决定、文档更新、权限及最终SHA仍待完成；不代为声明。B并发/多worker计划已存在，未执行；题目要求方案，不要求本周做分布式实测。'
    assert old in text;text=text.replace(old,new);policy.write_text(text,encoding='utf-8',newline='\n')
    norm=R/'results/scoring/normalization.json';data=L(norm);data.update(updated_at=N(),expected_counts=result['counts'],previous_snapshot='results/history/20261015-214234',new_views_note='保留种子全部原spec；新增raw/final/system_review结构独立视图，按dataset及arm分组，不拼接轮次。');norm.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (R/'results/scoring/delivery-status.json').write_text(json.dumps({'updated_at':N(),'audit_folder':F.relative_to(R).as_posix(),'checks':{'independent_counterexamples':30,'retained_regressions':534,'retained_state_checks':28,'all_passed':True,'generations_added':0,'cumulative':534,'b_offline_replays':88,'csv_rows':1457,'summary_comparisons':len(result['summary_comparisons']),'all_summaries_match':True},'pending':pending,'actual_entry_reference':(F/'entry-mapping.json').relative_to(R).as_posix()},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    assert all((R/p).is_file() and H(R/p)==h for p,h in L(F/'protected-hashes.json').items())
    W(F/'protected-file-audit.json',{'checked_at':N(),'all_old_runs_and_three_documents_unchanged':True,'protected_count':len(L(F/'protected-hashes.json')),'no_generation_calls':True,'no_model_started':True})
    print(json.dumps({'counts':result['counts'],'comparisons':len(result['summary_comparisons']),'all_equal':True,'dependencies':len(dependencies),'pending_count':len(pending),'old_records_unchanged':True},ensure_ascii=False))
if __name__=='__main__':main()
