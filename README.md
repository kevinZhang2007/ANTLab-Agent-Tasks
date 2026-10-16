## 当前交付

申请方向：Agent。主要进阶选择：B。进阶A作为附加探索。交付分支：main。

本仓库包含基础题首次正式实验、后续系统探索、进阶B缓存故障诊断与修复，以及进阶A的实现、开发比较和冻结评测。报告见[report.md](report.md)，关键取舍见[decisions.md](decisions.md)，完成范围与辅助工具说明见[declaration.md](declaration.md)。

累计保存678个唯一模型生成run ID：此前基础及探索534次，A新增144次。B另有88次offline_replay，不计入模型生成。准备失败、dry-run、分词和离线规则检查不算生成。results.csv包含评价、轨迹等记录，其1803行不等于调用次数。

### 基础实验

首次正式40项原始结果保留，没有规则改答或引用后处理。后续已接触题上的修改与重复测试单列探索，没有替换首次结果。

| 最终基础探索 | 模型原答正确 | 模型原始严格成功 | 系统最终答案正确 | 系统最终严格成功 |
|---|---:|---:|---:|---:|
| 开发4题 | 2/4 | 2/4 | 3/4 | 3/4 |
| 评测8题重复测试 | 5/8 | 1/8 | 7/8 | 7/8 |

系统结果包含规则计算改答或引用组装，不能当作模型自身成绩，也不是独立泛化成绩。规则后处理的主评分资格交由评审判断。

### 进阶结果

B已完成故障复现、缓存状态干预、独立禁用缓存修复、正常回归、等价变体、边界及页面与日志闭环。缓存污染得到修复，检索漏证、Engine语义误标和未知范围返回契约仍有问题，多客户端与多worker只有未执行计划。

A比较正文TF-IDF取两段与同章节邻段补全，两侧共享查询，统一使用紧凑输入、开启思考和句子选择。程序只展开模型所选原句，不自动证明语义。

| A七题评测 | baseline | 邻段补全 |
|---|---:|---:|
| 标签正确 | 5/7 | 5/7 |
| 必要引用覆盖 | 2/7 | 4/7 |
| 引用支持 | 2/7 | 2/7 |
| 严格成功 | 2/7 | 2/7 |
| 回答阶段HTTP总耗时 | 109.528秒 | 176.731秒 |

邻段未提高严格成功，且本轮成本更高，因此不推荐替代简单基线。等义改写暴露不稳定性；空检索题的ID变体不能证明非空引用鲁棒性。A作为附加探索，双题验收及本地服务是否满足A的API要求尚未得到组织方明确确认。

本人已审阅全部实验资料。评价采用AI辅助原文复核，不是官方成绩或独立人工评分。

### 记录与复现

- [首次基础冻结](基础/runs/formal/round1/freeze.json)
- [首次40项结果](基础/runs/formal/round1/result-index.json)
- [基础最终探索冻结](基础/runs/final_five/20261015-210223/round5/freeze.json)
- [基础最终候选](基础/runs/final_five/20261015-210223/bounded_candidate.py)
- [阅读索引](基础/runs/reading/technical-evidence-index.json)
- [A最终冻结](进阶/a_exploration/runs/bounded-final-20261016-215730/final-freeze.json)
- [A五轮取舍](进阶/a_exploration/runs/bounded-final-20261016-215730/five-rounds-summary.json)
- [A七题评价](进阶/a_exploration/runs/bounded-final-20261016-215730/evaluation/review.json)
- [A调用清单](进阶/a_exploration/runs/bounded-final-20261016-215730/generation-ledger.json)
- [A复现入口](进阶/a_exploration/runs/bounded-final-20261016-215730/reproduce.py)
- [逐例导出](results/results.csv)

从仓库根目录只读复算：

    python -X utf8 -B results/scoring/recalculate.py

该命令不调用模型、不重新判断语义。当前及隔离副本复算通过，678个唯一生成ID、88次B离线执行和546项汇总比较一致。

基础最终版本只读核对：

    python -X utf8 -B 基础/runs/final_five/20261015-210223/reproduce_final.py --output 基础/runs/delivery_check_unused --verify-only

基础页面启动：

    python -X utf8 -B 基础/tests/run_page_closure.py --out 基础/runs/page_closure/new-run --case D03 --port 8765

打开http://127.0.0.1:8765/。页面提交会新增最多两次真实模型生成，仅历史D03已实测，必须使用不存在的新目录。

B原版和修复版在两个终端分别启动：

    python -X utf8 -B 进阶/challenge_b/server_review.py --engine challenge:Engine --port 8876 --log-dir 进阶/runs/b_demo_original/new-run
    python -X utf8 -B 进阶/challenge_b/server_review.py --engine no_cache_engine:Engine --port 8877 --log-dir 进阶/runs/b_demo_fixed/new-run

打开http://127.0.0.1:8876/或http://127.0.0.1:8877/。B只做离线重放，不调用模型，日志目录必须为新目录。

A复现入口默认只准备新目录，添加--run才会新增调用；先查看入口--help，配置以冻结文件为准。帮助命令通过不等于重新执行完整生成。

本机环境为Windows x64、Python 3.14.6、llama.cpp b11429及CPU模型。模型和可执行文件位于仓库外，私人配置不提交。Python 3.10、其他操作系统和新机器安装尚未验证。基础使用关闭思考的配置，A最终回答开启思考，不能混用。

提交基点为60617b5e2e6c082771b92b1f5dae5bd11efc4955；本轮最终SHA待提交后登记，可通过git rev-parse HEAD核对。不把基点误称为本轮最终提交。

来源为https://github.com/Shiina413/ANTLab-Agent-Tasks，题包源码基点为b028d90f43f44585cf085a3f607516a94f485e88，可使用git diff b028d90f43f44585cf085a3f607516a94f485e88 HEAD查看相对改动。简历与联系方式只放收集表，不放仓库。

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
