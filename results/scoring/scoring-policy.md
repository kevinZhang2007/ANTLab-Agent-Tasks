# 结果总表与只读复算

本层是交付整理，不是新实验。评价为Codex辅助原文复核及聊天助手澄清，尚未经本人逐项确认，不是官方成绩。

## 读法与计数

- `results/results.csv`包含调用账本、独立评价视图、规则轨迹和准备停止记录。1457行不等于1457次调用。
- `model_generation`按根级run_id及实际completion_tokens>0核对，共534个唯一ID。定位、诊断、思考但没有最终答案的生成也计入；下载、准备失败、dry-run和模板分词不计入。`count_as_generation`只有这534行是true。
- `b_offline_replay`是固定draft离线重放，共88次Engine执行：直接Engine44次、直接HTTP22次、页面提交22次。页面也是HTTP入口；44条HTTP记录与44条同request_id日志是一组执行，不再加44。不能把B重放当成真实模型生成。
- `assessment`不计调用。每个归档评价文件及其模型原始/系统最终侧为独立`scoring_view`，重复复核是不同视图，不能相加、挑最好或冒充新请求。原始评价与effective评价均保留。
- `rule_trace`不计调用；记录证明、拒绝或计算轨迹，不把proof=true直接转成语义通过。
- `preparation_or_stop`不计生成。它只是保存的停止通知，不推断该轮发过请求，也不能把这20份通知当成19次独立模型失败。

## 主结果与探索

首次主实验仅为`基础/runs/formal/round1/`的40次：32次baseline与8次R0 improved，以其freeze.json为版本依据。其评价在`基础/runs/formal_review/round1/`，后来的口径澄清另存，不能冒充冻结前规则。

后续模型、提示词、规则和已接触T题上的重复测试单列探索。每行保留版本目录、可定位的冻结文件及哈希；没有保存冻结的旧记录不补造时间。`not_saved`表示该字段或关联没有确认，不能凭现在的配置回填。

各视图按condition、variant、result_source分别汇总。题目才是配对单位，同题不同条件不是独立样本。R0/R1/R2对照顺序；K同时改变资料选择与数量，不能解释为纯位置效应。不同模型、预算、调用次数或配置的结果不拼成一轮。

## 评价口径

- answer_correct：指定表达形式下答案是否成立；semantic_consistent独立记录语义一致。
- format_complete：结构完整，不代表事实正确。
- citation_ids_exist：ID属于实际输入，不代表原文支持。
- necessary_input_coverage：最终模型输入是否含必要证据。necessary_coverage：模型实际引用是否覆盖必要证据，二者不混用。
- support_actual_answer：引用集合是否支持实际answer。相关却支持不了错误答案的资料不能判为支持。
- has_unrelated_references：是否夹带无关或范围冲突引用，与有效支持子集分别记录；相关冗余不自动算无关。
- strict_complete_success：开发阶段选定的综合标签，直接复算已保存标签，不冒充任务唯一官方评分标准，也不在本脚本中自动重新推导。
- not_checked与ambiguous单列，保留在分母。首次失败、无答案、非法输出和未执行最终阶段的主任务不得因没有最终run ID而删除。总表保留这些评价行；未知条件只在同目录、同题已归档生成记录给出唯一条件时补关联，不依赖题号推断运行逻辑。
- `missing_evidence_response_compliant`与事实正确性不同。K可见证据不足但输出确定结果时，事实可能无法核验，而缺证应答不合规；不能借不可见资料判K。

依据：`基础/01_考核题目.md`第17、25、31、33、37、47行；`基础/03_提交要求.md`第5、11行；`进阶/00_共同规则与接口.md`第15—18、24—30行。行号以本次归档版本为准。

## 规则结果的计分边界

local_rule计算改答与local_rule引用组装是系统派生结果，不能冒充模型原始输出。现有任务原文没有明确授权将这些结果计入主评分，因此仅列系统探索结果。`system_final`视图包含未改动的原答与实际派生结果；output_origin区分二者。未改动的原答保留live_api来源，实际规则派生映射为local_rule/rule。

归档辅助语义评价的来源不能因为系统规则产生了输出就改称独立人工核验。总表中派生结果的judgment_source=rule指派生处理来源；其正确性仍是旁列的辅助暂判，不代表程序证明自动等于事实正确。

规则事实与引用是否只来自最终模型输入，须查看各条material_scope/proof_fact_sources；较早的离线探索不能与后来收紧边界的版本混称。保留原记录定位，复算不替它们消除限制。

## 只读复算命令

从仓库根目录执行：

```powershell
python -X utf8 -B results/scoring/recalculate.py
```

只使用标准库，从脚本位置确定仓库根目录。读取manifest.json中明确列出的仓库内文件和JSON指针，核对哈希、CSV、调用计数及已有汇总，结果只写标准输出。没有网络、服务启动、模型调用或实验代码导入，不读私人配置，不写旧文件，也不新增实验记录。它复算已保存评价，不自动证明语义判断正确。

返回码0表示复算及已比较汇总一致；汇总差异返回2；缺文件、哈希改变或CSV不符会报错并非零退出。不存在的评价字段保留not_checked，原始值及其路径/指针保存在original_values列。

build_export.py只用于显式更新导出，不是只读入口；必须传入已保留的旧manifest作为--seed和--expected-generations 534。当前种子为results/history/20261015-214234/scoring/manifest.json，旧1010条spec保持不变，新增各轮独立视图。该命令会重写当前导出，不运行模型。干净副本仅执行recalculate.py。

## 仍缺的交付事项

基础D03真实页面闭环已有基础/runs/page_closure/20261015-173656/closure-audit.json及截图、同请求日志；page-integration-plan.md保留为此前计划，不再代表当前完成状态。页面绑定较早但模块/配置相同的冻结版本，仅验证一题。最新入口、复现限制和交付缺项见delivery-status.json。最终AI声明、本人核验、关键决定、文档更新、权限及最终SHA仍待完成；不代为声明。B并发/多worker计划已存在，未执行；题目要求方案，不要求本周做分布式实测。
