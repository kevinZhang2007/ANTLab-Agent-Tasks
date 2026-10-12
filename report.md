# 第一阶段记录

更新时间：2026-10-12 14:07:20 +0800。这是第一阶段记录，还不是最终报告。

## 1. 完成概览
我已经准备了Git 2.56.0.windows.2和Python 3.14.6，满足骨架Python 3.10+要求。解释器位于 `%LOCALAPPDATA%/Programs/Python/Python314/python.exe`。环境详情来自此前检查，本次未重复检查硬件。
目前我已实现了基础/starter/student.py的prepare_messages()，完成自造样例和D01 E条件的无模型输入检查。目前选择进阶B，先完成基础题和B，A只在时间允许时考虑补充。真实模型请求、正式评测和改进配对还没运行。
当前可核验的三项证据：输入组织代码 `基础/starter/student.py`；检查脚本 `基础/tests/check_student.py`；本次记录 `基础/runs/e3b3ce3a-f88b-4168-93b3-98ca6fdec97e.json`。

## 2. 阅读到命题
我已经通过阅读了解了入口、基础题目、数据说明、进阶共同规则和提交格式。输入组织按这些规则实现：问题与可见段落分开序列化，保留了id/source/text和顺序；引用存在与引用支持答案应分开判断。但是目前代码只完成前者的输入组织，还没有实现语义判断。
论文原文核对和公开系统比较还没有开展，研究命题与对照预期也还没有确定。
这次检查只核对自造样例和D01，并没有查看正式题内容或运行正式评测。检查脚本和runner会在内存中解析包含各题的数据文件，但是没有输出或评估正式题内容。聊天助手已阅读公开评测输入，所以不属于完全盲测。

## 3. 实验设计
当前只有输入检查：自造样例覆盖中文、引号、换行、反斜杠、空正文和空段落列表；D01固定使用E条件、baseline和config.example.json，不调用模型。
主假设、竞争解释、正式指标、参数冻结、失败分母和停止条件尚未确定。32次基线、8次改进及正式判分还没运行。历史dry-run记录保留，不作为模型质量或耗时结果。

## 4. 实现与复现
源码上游：https://github.com/Shiina413/ANTLab-Agent-Tasks 。个人Fork：https://github.com/kevinZhang2007/ANTLab-Agent-Tasks 。原始源码基点commit：`b028d90f43f44585cf085a3f607516a94f485e88`。第一阶段版本以包含这份文件的Git提交为准，最终考核版本我会在完成后登记。查看已跟踪文件改动：`git diff b028d90f43f44585cf085a3f607516a94f485e88`；新增文件可以在 `git status --short --untracked-files=all`看到。
prepare_messages()返回system和user两条Chat Completions消息。统一提示词要求核对版本、批次、指标口径和签署状态；answer遵守问题要求的表达形式，citations保存支持答案的段落ID。user使用JSON保存question和完整passages。函数不读答案文件，不按题号或条件生成答案；improve()仍原样返回。

从仓库的根目录执行：

```powershell
python -X utf8 -B 基础/tests/check_student.py
```

脚本会运行D01 E dry-run，并生成新的基础/runs/<run_id>.json。实际messages与输入逐项核对，包括问题、ID、来源、正文和顺序。不需要密钥或本地私人配置。浏览器到后端再到真实模型的完整请求链还没运行。

## 5. 结果与诊断
这次检查脚本退出码0，语法、自造样例和D01核对全部通过。这次的run ID：`e3b3ce3a-f88b-4168-93b3-98ca6fdec97e`；mode为dry，status为dry_run，段落顺序为P312446、P898100，response和elapsed_seconds均为null。
保留的dry-run记录：

- `基础/runs/46eef393-1778-4952-b9f8-e0bb6f7eaac0.json`
- `基础/runs/a93a378c-5f0a-4690-af00-387bee4f5ba4.json`
- `基础/runs/e3b3ce3a-f88b-4168-93b3-98ca6fdec97e.json`

`git check-ignore -- 基础/runs/e3b3ce3a-f88b-4168-93b3-98ca6fdec97e.json` 无输出、退出码1，表示未被忽略；git status将该文件列为??，表示未跟踪且可加入版本控制。
普通 `git diff --check` 退出码2，报告新增行尾空白；`git -c core.whitespace=cr-at-eol diff --check` 退出码0。检查确认报告来自CRLF中的回车，没有额外空格或制表符；两种结果分别保留，未修改Git配置。
dry-run只证明输入组织可运行，不能证明回答正确、引用语义支持或提示词能抵抗资料中的指令。真实模型质量、费用、耗时、诊断对照、变体和改进配对还没运行。现有provider强制HTTPS和Bearer密钥，本地模型服务尚未接入；运行记录仍沿用基础骨架接口，进阶接口尚未补齐。

## 6. 决定与未来的计划

我当前保留了统一提示词、JSON序列化和原始运行记录，暂不改变improve、检索、provider或记录接口。下一步我先核对提示词和输入记录，再选择模型服务，继续基础题和进阶B。用户核验结果尚未记录。
下一步核对论文原文并比较公开系统，接通真实请求链，确定参数和费用边界，再开展逐题评价。进阶B先检查样机代码和接口，保留故障复现、修复前后对照和关键决定依据。
