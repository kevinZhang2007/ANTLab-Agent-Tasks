# 已有记录事实摘录（不含报告正文）

耗时为客户端完整非流式请求时间，单位秒；展示保留3位小数。

| 条件 | 数量 | 中位数 | 最小值 | 最大值 |
|---|---:|---:|---:|---:|
| R0 baseline | 8 | 14.982 | 14.230 | 16.850 |
| R1 baseline | 8 | 14.271 | 12.494 | 15.372 |
| R2 baseline | 8 | 15.647 | 14.015 | 17.499 |
| K baseline | 8 | 5.183 | 4.575 | 6.151 |
| R0 improved | 8 | 14.436 | 13.016 | 16.286 |

| 题号 | R0 baseline | R0 improved |
|---|---:|---:|
| T01 | 15.117 | 13.993 |
| T02 | 15.253 | 14.755 |
| T03 | 14.789 | 14.341 |
| T04 | 14.847 | 13.016 |
| T05 | 14.230 | 16.286 |
| T06 | 16.850 | 14.340 |
| T07 | 14.718 | 14.532 |
| T08 | 15.394 | 15.257 |

累计唯一生成124次（此前84＋正式40）；本次新增0次。

冻结时间：2026-10-13T13:19:11.920418+08:00

准确相对路径：

- freeze：`基础/runs/formal/round1/freeze.json`
- frozen_request_config：`基础/runs/formal/round1/freeze.json#complete_request_config`
- config_source：`基础/runs/formal_preparation/20261013-131201/config.candidate.json`
- service_parameters：`基础/runs/formal/round1/freeze.json#service_arguments`
- generation_entry：`基础/tests/run_formal_round1.py`
- actual_executed_command：`python -X utf8 -B 基础/tests/run_formal_round1.py`
- run_list：`基础/runs/formal_preparation/20261013-131201/run-list.json`
- results_index：`基础/runs/formal/round1/result-index.json`
- original_raw_results：`基础/runs/formal/round1/run-<run_id>.json`
- effective_evaluations：`基础/runs/formal_review/round1/effective-reviews.json`
- evaluation_summary：`基础/runs/formal_review/round1/summary.json`
- evaluation_rules：`基础/runs/formal_preparation/20261013-131201/evaluation-rules.json`
- original_case_evidence：`基础/runs/formal_review/round1/evidence-T01.json 至 evidence-T08.json`
- original_case_evaluations：`基础/runs/formal_review/round1/review-T01.json 至 review-T08.json`
- evaluation_adjustments：`基础/runs/formal_review/round1/review-adjustments.json`
- paired_evaluation：`基础/runs/formal_review/round1/paired-comparison.json`
- order_evaluation：`基础/runs/formal_review/round1/order-comparison.json`
- K_evaluation：`基础/runs/formal_review/round1/K-visibility-review.json`
- evaluation_summary_entry：`基础/tests/summarize_formal_review.py`

执行入口有已有round1目录即停止保护；这里只登记已执行命令，不授权重新生成。JSON字段定位用#字段名说明，不是磁盘文件名。

只提取已有观测，单次逐题耗时不证明稳定性能改善；不新增报告正文。
