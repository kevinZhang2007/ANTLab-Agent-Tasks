from pathlib import Path
import sys
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');sys.path.insert(0,str(ROOT/'进阶/a_exploration'))
from runtime import load,write,now
out=Path(Path('a-health-resume-out.txt').read_text(encoding='utf-8').strip());rt=load(out/'runtime.json');assert rt['confirmed_generations']==6 and rt['model_stopped']
manual={
 'AD01':{
  'original':{'consistent':False,'necessary':True,'support':False,'unrelated':False,'attribution':False,'basis':'实际0011明确要求无法避免手工操作时记录哪些文件修改/移动及目的，0004要求最低程序细节。两项已覆盖直接反证，但模型给insufficient；理由承认需详细记录却不判反驳。理由将0004说成P1-S02-p02，实际为P1-S02-p03。来源展开真实不消除这些错误。'},
  'revised':{'consistent':True,'necessary':True,'support':True,'unrelated':False,'attribution':True,'basis':'0011的“If manual operations cannot be avoided ... note down which data files ... and for what purpose”直接反驳无需记录；0004及0005—0010是手工操作与可复现流程的同段背景。后者冗余但与当前手工操作记录主题和条件相关，沿用此前相关冗余不等于无关的口径，不能因片段多而临时判无关。contradicted、理由及引用集合成立；reason仍重复来源ID，另记提示遵从问题，不添加严格门槛。'}},
 'AD02':{
  'original':{'consistent':False,'necessary':True,'support':True,'unrelated':True,'attribution':'not_checked','basis':'0006/0007/0010说明静态HTML/PDF可读档案及重建环境所需依赖，0011—0013说明Binder执行和容器/依赖环境。集合支持“可阅读但仅此不足执行”，标签supported正确。reason却说主张与资料矛盾因此被支持，内在矛盾另列；0004是开源许可/仓库，没有该判断的必要支持作用，属于无关引用，因此严格失败。'},
  'revised':{'consistent':True,'necessary':True,'support':False,'unrelated':True,'attribution':False,'basis':'0006/0007已有静态可读档案与需依赖重建环境的区分，0013又给出重新运行所需环境，0009补充静态浏览，仍覆盖关键Read/Run依据。给insufficient是已有正确项退步，不能将缺少逐字“不能执行”的句子当作组合证据不足；reason形式上解释其缺证判断，但实际关系判断错误。0004许可引用仍无关；reason将静态HTML/PDF指向P2-S10-p01，实际相关原句在p02。'}},
 'AD03':{
  'original':{'consistent':True,'necessary':'ambiguous','support':'ambiguous','unrelated':False,'attribution':'not_checked','basis':'实际没有公开参考指定的S08绘图数据变换直接依据；0009描述最终图表高度汇总，0013在存储条件允许时建议永久保留全部底层数据。这些既可能作为可见范围的缺证检查来源，也可能提供有条件反证，沿用覆盖及支持ambiguous；不引入未发送S08，不移出分母。insufficient不符合公开contradicted，严格失败。'},
  'revised':{'consistent':False,'necessary':'ambiguous','support':False,'unrelated':True,'attribution':'not_checked','basis':'0004只谈归档程序版本，与仅留最终图片是否满足底层数据建议没有直接支持，属于无关片段。0013条件性建议保存全部底层数据，0016要求至少一次生成、检查和验证详细值，不支持“只保留最终图片就满足”；reason自己强调完整数据而非仅最终结果却称原主张一致，方向矛盾。S08仍未输入，必要覆盖的边界保留ambiguous；supported无论公开标签还是当前引用集合均不通过。'}}
}
assert not (out/'semantic-review-basis.json').exists();write(out/'semantic-review-basis.json',manual)
write(out/'review-boundaries.json',{'at':now(),'reviewer':'Codex辅助原文复核，尚待本人确认','all_calls_completed_before_reference_evaluation':True,'AD03_direct_S08_not_supplied':True,'reason_quality_separate_from_strict_formula':True,'related_redundancy_not_unrelated':True,'AD01_candidate_source_ID_in_reason':'未遵从不重复ID提示，单列，不新增综合评分门槛。','AD02_candidate_consistency':'其理由形式上为insufficient提供缺证解释，因此一致性true不代表实际语义正确；仍判错误拒判和引用不支持。','no_semantic_label_or_citation_repair':True})
print('semantic evidence saved')
