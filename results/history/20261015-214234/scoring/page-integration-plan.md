# 基础真实模型页面闭环：只读核查与最小方案

状态：planned_not_run。本轮没有修改服务、启动页面或调用模型。

## 当前入口

基础/starter/server.py第4行从runner导入execute；第25—30行只接受dry/mock/paid模式并调用原runner。基础/starter/runner.py第35行使用生产student，未接最新独立候选。不能把这条页面入口说成已验证最新候选，也不能用B的固定draft页面替代基础模型页面证据。

与最新已验证计算版本一致的通用入口是：
基础/runs/calculation_full_dev/20261015-160956/proof_pipeline_candidate.py 的execute(question, passages, variant, answer_config, selection_config, dispatch=None, save=None)，第37行。

版本依据为同目录freeze.json；评测重跑对应基础/runs/calculation_full_eval/20261015-161821/freeze.json。接入前再次核对冻结哈希及依赖，不复制历史正确回答或使用评价文件驱动推理。

## 最小后续实现

1. 新增独立页面适配器，明确选择原baseline或上述候选，不替换生产student或历史冻结。复用provider真实请求和既有save记录接口；定位、回答、规则处理保持已有边界。
2. 请求携带question/passages、范围及实际配置引用；服务仅监听127.0.0.1。回环模型服务是免费本地调用，页面模式应明确local live_api，不能借paid名称暗示付费或把dry/mock写成真实调用。
3. 页面提交生成主request_id，各阶段run ID归属于同一主请求；后台保存实际messages、资料顺序、配置、原始响应、失败及完整端到端耗时，页面显示同request_id供回查。
4. raw_response、规则proof、derived/proposed_response与最终显示分区；来源分别标模型/local_rule，显示答案是否改动。语义未核验明确not_checked；定位只说明ID属于实际输入，不能用绿色通过暗示语义支持。
5. evidence回到实际发送原文，显示稳定块ID、doc_id、snapshot、page；输入没有对应字段时null并说明，不能从source目录猜造文档范围。规则仅可按已验证版本使用最终模型输入；额外原始资料审计另存。
6. 后续获准后，用开发题完成页面提交→实际模型→页面结果→同ID日志→原文定位；分别检查baseline与候选、失败展示和规则拒绝。真实调用须新增独立记录并增加实际计数。本轮不执行。

尚缺：该适配器代码、真实模型页面请求/响应、截图、同ID日志及定位/语义分离的实际检查。当前只有方案，不能宣称页面闭环完成。进阶B并发/多用户/多worker亦仅计划；独立客户端不等于权限隔离。
