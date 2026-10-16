# 自动improved证据的共同判断候选对照

复核时间：2026-10-16T12:40:48.252666+08:00

Codex辅助原文复核，尚待本人确认。历史自动证据重放，不是重新检索或端到端成绩。残缺JSON不剥围栏、不补字段、不提取前缀当完整结果。


## AD01 original

原始content（结束处保持原样）：

```text

{
  "label": "insufficient",
  "reason": "The passage does not provide sufficient evidence to confirm or deny the claim. The evidence includes rules about documentation requirements and avoiding manual data manipulation, but there is no explicit statement that addresses whether manual modifications are avoided or if saving files without recording details is acceptable.",
  "evidence": []
}

```

完整输入已含P1-S03-p01末句：人工操作无法避免也须记录哪些文件及目的。回复仍insufficient并空引用，声称缺少明确说明，与实际原文不符；理由与拒判标签表面一致但事实错误。

客户端耗时 5.449 秒；finish_reason=stop；截断标记=False。


## AD01 revised

原始content（结束处保持原样）：

```text

{
  "label": "supported",
  "reason": "The text supports the claim that when manually modifying or moving data files is unavoidable, it is sufficient to save the final file without recording specific modifications or purposes. The evidence includes Rule 1 and Rule 2 which emphasize avoiding manual operations and specifying workflows for reusability.",
  "evidence": [
    {
      "block_id": "P1-S02-p03",
      "quote": "As a minimum, you should at least record sufficient details on programs, parameters, and manual procedures to allow yourself, in a year or so, to approximately reproduce the results."
    },
    {
      "block_id": "P1-S02-p01",
      "quote": "Whenever possible, rely on the execution of programs instead of manual procedures to modify data. Such manual procedures are not only inefficient and error-prone..."
    }
  ]
}

```

supported与其错误理由表面一致；真实quote1要求record sufficient details，不能支持无需记录。quote2标成P1-S02-p01，不在实际输入[P1-S02-p02,P1-S02-p03,P1-S03-p01]；摘录还添加...。不得把ID改成P1-S03-p01或补缺句来算成功。

客户端耗时 9.690 秒；finish_reason=stop；截断标记=False。


## AD03 revised

原始content（结束处保持原样）：

```text

{
  "label": "supported",
  "reason": "根据P1-S04段落，作者建议在绘图过程中保留最终图片以满足图底层数据的建议。同时，P1-S09段落提到生成层次化分析输出并提供链接以便查阅详细值，这符合绘图过程中只保留最终图片的要求。",
  "evidence": [
    {
      "block_id": "P1-S04-p01",
      "quote": "In order to exactly reproduce a given result, it may be necessary to use programs in the exact versions used originally. Also, as both input and output formats may change between versions, a newer version of a program may not even run without modifying its inputs. Even having noted which version was used of a given program, it is not always trivial to get hold of a program in anything but the current version. Archiving the exact versions of programs actually may save a lot of hassle at later stages."
    },
    {
      "block_id": "P1-S09-p01",
      "quote": "We find hypertext (i.e., html file output) to be particularly useful for this purpose. This allows summarized results to be generated along with links that can

```

finish_reason=length，JSON在第二个quote中途结束，格式失败且不得补齐。可见reason前缀仍把程序版本和层次输出说成图数据要求的支持；第一条完整摘录主题是软件版本而非图底层数据。只记部分输出风险，完整字段均not_checked。

客户端耗时 11.639 秒；finish_reason=length；截断标记=False。


## AD03 original

原始content（结束处保持原样）：

```text

{
  "label": "supported",
  "reason": "资料明确支持绘图过程中保留最终图片来满足作者关于图底层数据的建议，且强调了存储完整程序或虚拟机图像以确保未来可用性。",
  "evidence": [
    {
      "block_id": "P1-S04-p01",
      "quote": "In some cases, all that is needed is to store a single executable or source code file."
    },
    {
      "block_id": "P1-S09-p01",
      "quote": "We find hypertext (i.e., html file output) to be particularly useful for this purpose."
    }
  ]
}

```

输入只有外部程序版本/P1-S04与层次结果/P1-S09，不含图底层数据章节；不支持仅存最终图，两个真实摘录是无关依据。按实际输入应insufficient；公开全文参考contradicted另列，不用不可见P1-S08补证。

客户端耗时 7.493 秒；finish_reason=stop；截断标记=False。


## AD02 original

原始content（结束处保持原样）：

```text

{
  "label": "insufficient",
  "reason": "The claim cannot be fully supported by the given passages, as they primarily discuss how to support others’ reuse of notebooks but do not explicitly state that static HTML/PDF or static views via GitHub are sufficient for execution.",
  "evidence": []
}

```

原主张是静态导出有助阅读但仅此不足执行；回复却要求原文明示静态视图足以执行，否定方向有误，空引用。Read/Run原文齐全，不应借缺少逐字充分保证拒判。

客户端耗时 5.473 秒；finish_reason=stop；截断标记=False。


## AD02 revised

原始content（结束处保持原样）：

```text

{
  "label": "supported",
  "reason": "The claim states that exporting notebooks to static HTML/PDF or PDF helps others read and explore them, but it is insufficient for them to execute the original computation. The passages provided support this point by mentioning options like storing notebooks in code repositories, using GitHub's Nbviewer, and creating portable environments (e.g., Docker). These actions not only help with reading but also allow execution, making the claim partially supported.",
  "evidence": [
    {
      "block_id": "P2-S10-p01",
      "quote": "If you have followed the previous rules, your notebooks should capture your entire process and be easy to read. But how will others access, run, and explore them? There are a number of ways you can support others’ reuse of your notebooks."
    },
    {
      "block_id": "P2-S10-p02",
      "quote": "Read: Beyond granting permission to reuse your notebook, consider how you can leverage the unique structure of notebooks to support reading. At the very least, leave static HTML/PDF versions of all notebooks stored in the final version of the repository accompanying a publication."
    },
    {
      "block_id": "

```

finish_reason=length，256输出token，JSON在第三个block_id的字符串中结束。不得从前缀supported推成完整结构化结果；reason前缀将原主张扩大为read and explore，并说partially supported却用supported，记录为可观察风险，不替代最终字段判分。

客户端耗时 12.247 秒；finish_reason=length；截断标记=False。

{
  "groups": {
    "original": {
      "denominator": 3,
      "format_complete": 3,
      "public_reference_label_correct": 0,
      "public_reference_label_not_checked": 0,
      "visible_input_label_correct": 0,
      "visible_input_label_not_checked": 0,
      "reason_label_surface_consistency": 3,
      "reason_label_not_checked": 0,
      "outputs_with_continuous_quotes": 1,
      "necessary_coverage": 0,
      "citation_support": 0,
      "support_not_checked": 0,
      "strict_complete_success": 0,
      "budget_exhausted": 0,
      "client_seconds_total": 18.415180299896747
    },
    "revised": {
      "denominator": 3,
      "format_complete": 1,
      "public_reference_label_correct": 0,
      "public_reference_label_not_checked": 2,
      "visible_input_label_correct": 0,
      "visible_input_label_not_checked": 2,
      "reason_label_surface_consistency": 1,
      "reason_label_not_checked": 2,
      "outputs_with_continuous_quotes": 0,
      "necessary_coverage": 0,
      "citation_support": 0,
      "support_not_checked": 2,
      "strict_complete_success": 0,
      "budget_exhausted": 2,
      "client_seconds_total": 33.575583900325
    }
  },
  "decision": {
    "adopt": false,
    "pending_integration": false,
    "reason": "两侧严格成功均0/3；旧侧完整有效标签正确0/3，候选正确0/3且2条not_checked。无选择指标改善，候选格式由3/3降至1/3，并出现未知ID/非连续摘录；保留旧流程，不追加搜索。",
    "no_previous_success_regression_claim": "旧侧三题无严格成功或公开参考标签成功，不能把0项成功的退步检查写成稳定性已证；格式和预算结果有明确退步。",
    "mechanism_limit": "显式检查步骤不是内部执行证据。新提示在同一256预算下产生更长摘录并两次耗尽预算，这是实际配置失败；不单独归因于提示长度、推理能力或模型上限。",
    "validation_limit": "确定性检查有效标记ID/连续摘录错误，未纠正或反转label，不能判语义支持。",
    "AD03_boundary": "未输入图底层数据章节。公开完整文档参考与按可见输入的合理拒判分开；没有借不可见原文判模型引用成功。",
    "future": "本轮结束，不追加调用，七题评测继续取消。"
  }
}
