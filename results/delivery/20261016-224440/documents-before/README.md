## 当前交付：基础题与进阶B

这份提交包含基础题的首次正式实验、后续系统探索，以及进阶B的故障诊断与最小修复。整合报告见[report.md](report.md)，关键取舍见[decisions.md](decisions.md)，完成范围和辅助工具说明见[declaration.md](declaration.md)。

目前累计保存534个唯一模型生成run ID。进阶B另外完成88次离线重放，不计入模型生成次数。准备失败、dry-run、分词和离线规则检查也不计入生成次数。

### 结果怎么读

首次正式实验保留32项baseline和8项R0 improved，共40项原始结果，没有规则改答或引用后处理。后续修改、重复测试和规则派生单独保存，没有替换首次结果。

当前保留方案的结果如下：

| 数据集 | 模型原答正确 | 模型原始严格成功 | 系统最终答案正确 | 系统最终严格成功 |
|---|---:|---:|---:|---:|
| 开发4题 | 2/4 | 2/4 | 3/4 | 3/4 |
| 评测8题重复测试 | 5/8 | 1/8 | 7/8 | 7/8 |

“严格成功”要求答案符合指定答法、必要证据覆盖完整、引用支持结论且不夹带无关引用，是这次开发选定的综合指标。格式、答案、引用覆盖、语义支持和无关引用仍分别报告。

系统结果包含规则计算改答或引用组装，不能写成模型自身的正确率。这些结果经过AI辅助复核和本人审阅；评测题已经参与后续分析，因此重复测试不属于独立盲测或泛化成绩。规则后处理能否计入主评分，交由评审按任务要求判断。

### 主要入口

- [整合报告](report.md)
- [开发过程](基础/开发记录.md)
- [首次正式冻结](基础/runs/formal/round1/freeze.json)
- [首次40项原始结果](基础/runs/formal/round1/result-index.json)
- [最终探索版本冻结](基础/runs/final_five/20261015-210223/round5/freeze.json)
- [最终探索结果](基础/runs/final_five/20261015-210223/round5/review-summary.json)
- [最终候选入口](基础/runs/final_five/20261015-210223/bounded_candidate.py)
- [逐例导出](results/results.csv)
- [阅读证据索引](基础/runs/reading/technical-evidence-index.json)

results.csv还包含评价、规则轨迹和停止记录，行数不等于调用次数。

### 只读复算

从仓库根目录执行：

```bash
python -X utf8 -B results/scoring/recalculate.py
```

该命令复算已归档标签，不调用模型、不重新判断语义、不修改实验记录。干净副本的隔离运行已通过，322项汇总比较一致。

最终依赖、模型和配置核对：

```bash
python -X utf8 -B 基础/runs/final_five/20261015-210223/reproduce_final.py --output 基础/runs/delivery_check_unused --verify-only
```

实际模型复现必须使用不存在的新输出目录，会新增生成记录：

```bash
python -X utf8 -B 基础/runs/final_five/20261015-210223/reproduce_final.py --output 基础/runs/final_reproduction/new-run
```

包装器的verify-only分支已验证，底层运行器已完成最终实验；包装器的完整生成分支尚未另行执行。

### 页面

基础真实模型页面仅实测D03一次。启动器同时管理模型和页面，须使用新目录：

```bash
python -X utf8 -B 基础/tests/run_page_closure.py --out 基础/runs/page_closure/new-run --case D03 --port 8765
```

打开 http://127.0.0.1:8765/ 。页面提交会新增最多两次模型生成。原始回答与规则派生分开展示，页面定位有效不等于语义已经核验。

进阶B原版与修复版分别启动：

```bash
python -X utf8 -B 进阶/challenge_b/server_review.py --engine challenge:Engine --port 8876 --log-dir 进阶/runs/b_demo_original/new-run
python -X utf8 -B 进阶/challenge_b/server_review.py --engine no_cache_engine:Engine --port 8877 --log-dir 进阶/runs/b_demo_fixed/new-run
```

分别打开 http://127.0.0.1:8876/ 和 http://127.0.0.1:8877/ 。日志目录须不存在。B使用固定draft离线重放，不调用模型。

### 环境与限制

本机验证环境为Windows x64、Python 3.14.6、llama.cpp b11429及Qwen3-0.6B-Q8_0，使用CPU推理。模型权重和llama.cpp位于仓库外，私人配置不提交。完整配置以各轮冻结记录为准，不能用早期简化配置代替最终Schema。

进阶B已验证缓存污染修复，但检索漏证、Engine的语义状态误标和未知范围返回契约仍有问题；多客户端与多worker只有可执行计划，尚未实测。Python 3.10、其他操作系统及全新机器安装尚未验证。

进阶A尚未启动，本次不计入已完成内容。

# ANTLab Agent Tasks

文档阅读与信息核验方向 Agent 项目的应用层开发者招募考核：先完成基础题，再从进阶 A/B/C 中选择一套完成。

**截止时间：北京时间 2026 年 10 月 16 日 23:59（UTC+8）。**

## 从哪开始

1. 先读 [开始阅读.md](开始阅读.md)（总体规则、时间、提交方式）。
2. 基础题（必做）：[基础/README.md](基础/README.md) 与 基础/01_考核题目.md。
3. 进阶题（三选一）：[进阶/README.md](进阶/README.md)，在 A / B / C 中选一套。

## 目录结构

```text
开始阅读.md              入口：总体规则、截止时间、提交方式
基础/                    基础题：12 题（4 开发题有公开答案 + 8 评测题），
                         R0/R1/R2/K 四种输入组织条件；模型 API 自费，
                         主请求量与运行命令见 基础/README.md
进阶/                    进阶题（A/B/C 三选一）
├─ 01_A_研究机制迁移.md        A：主张→证据→支持状态机制迁移与对照
├─ 02_B_系统失效诊断.md        B：源码审查、故障归因与修复
├─ 03_C_产品假设验证.md        C：围绕自选用户任务的产品假设验证
├─ materials/                 两份 CC Attribution 公开论文（P1/P2）及抽取数据
├─ challenge_b/               B 题文档查证样机（30 行 Engine，含预埋故障）
└─ templates/                 声明与整合报告模板
```

## 规则要点

- 准备时间为一周（包含基础题和进阶题）；模型调用使用自己的 API，费用自理；实验输入、原始响应、失败和前后对照须保留在仓库中。
- AI 可辅助阅读、实现和排错；需记录它对关键决定的影响、本人如何核验，以及实际完成和未完成的内容。
- 提交：把作品推送到自己的 GitHub 仓库，并在收集表登记仓库链接与最终 commit SHA；收集表地址与仓库评审账号见 Q 群公布（详见 进阶/05_提交与报告格式.md 与 进阶/06_收集表填写说明.md）。
- 本包不含评委参考答案、评测标签、内部开发教程或商业书籍全文。
- 文件完整性：`基础/文件校验.json` 与 `进阶/文件校验.json` 提供逐文件 SHA256，可自行校验。
