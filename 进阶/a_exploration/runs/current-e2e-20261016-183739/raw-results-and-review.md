# 当前采用版本：三道开发题完整配对

Codex辅助原文复核，尚待本人确认。三题分母保留；不是七题评测。

严格成功：完整JSON且选择验证通过、标签正确、必要覆盖=true、引用支持=true、无无关引用。理由一致性不属于综合公式。

## AD01 baseline

```json

{
  "label": "contradicted",
  "reason": "资料明确指出：当手工操作无法避免时，必须记录修改对象和目的（见P1-S03中的句子）。该主张与资料内容直接冲突。",
  "sentence_ids": ["sent-0003", "sent-0008"]
}

```

原始输入含P1-S03-p01最后一句“If manual operations cannot be avoided ... note down which data files ... and for what purpose”。选择sent-0008覆盖直接反证，sent-0003说明手工操作可复现风险，属于相关冗余。contradicted及其证据集合成立；理由重复来源名称另列，不新增严格门槛。

## AD01 improved

```json

{
  "label": "contradicted",
  "reason": "资料明确指出当手工操作无法避免时，必须记录修改对象和目的（如P1-S03-p01中提到的记录数据文件修改或移动及用途），与主张中的'无需记录'相矛盾。",
  "sentence_ids": ["sent-0004", "sent-0005", "sent-0006", "sent-0007", "sent-0008", "sent-0009", "sent-0010", "sent-0011"]
}

```

邻段只新增同章节P1-S02-p02，原直接反证仍在P1-S03-p01的sent-0011。0004及0005—0010均属手工流程记录的相关背景，沿用相关冗余不等于无关的口径。两侧均已完整成功，不能把本题结果说成邻段改善。

## AD02 baseline

```json

{
  "label": "supported",
  "reason": "资料明确指出：1. 导出为HTML/PDF有助于阅读（见P2-S10-p01中的文本），2. 同时提及Nbviewer/GitHub等技术手段可实现执行原计算（见P2-S10-p02中相关段落），但未直接说明静态导出仅能满足执行需求。因此，主张符合资料内容。",
  "sentence_ids": ["sent-0001", "sent-0002", "sent-0003", "sent-0004", "sent-0005", "sent-0006", "sent-0007", "sent-0008", "sent-0009", "sent-0010"]
}

```

实际未检索P2-S10-p03，但p02的0006/0007已区分静态可读档案和需完整依赖列表才能重建计算环境，允许这种有充分原文的替代支持，不要求固定Run引用ID。模型选全部十句，集合足以支持实际supported；0004仓库许可对本判断无关，严格失败。理由把Nbviewer/GitHub静态视图误写为执行原计算，且把HTML/PDF归到p01，不能用标签碰巧正确掩盖理由错误。

## AD02 improved

```json

{
  "label": "insufficient",
  "reason": "资料中提到导出静态HTML/PDF有助于阅读（P2-S10-p01），但并未直接说明其是否足以执行原计算。其他段落提及使用 Binder 或容器化环境支持执行，因此该主张部分成立，但不足以全面满足。",
  "sentence_ids": ["sent-0004", "sent-0006", "sent-0007", "sent-0009", "sent-0013"]
}

```

邻段新增P2-S10-p03（Binder、容器/依赖环境）；所选0006/0007及0013覆盖Read/Run区分，资料足够但最终insufficient为错误拒判。reason形式上解释缺证判断，却误读了否定限定，静态原句归属也写错。0004许可引用仍无关；不能因摘录真实或资料更全判成功。

## AD03 baseline

```json

{
  "label":"supported",
  "reason":"资料明确指出在程序版本管理、详细数据生成及虚拟机图像存储等环节中，需保存精确版本以确保后续可追溯性，并强调生成完整数据而非仅保留最终结果。主张与作者建议一致。",
  "sentence_ids": ["sent-0004", "sent-0013", "sent-0016"]
}

```

实际只有P1-S04-p01和P1-S09-p01，公开参考指定S08绘图变换直接依据未进入输入。S09保留有条件的底层数据建议和最低详细值检查，可形成替代反证但完整覆盖边界继续ambiguous。所选0004是程序版本归档，无关；0013/0016不能支持“仅图片足够”。理由强调完整数据却判主张一致，方向错误。

## AD03 improved

```json

{
  "label":"supported",
  "reason":"资料明确指出在程序版本管理、详细数据生成及虚拟机图像存储等环节中，需保存精确版本以确保后续可追溯性，并强调生成完整数据而非仅保留最终结果。主张与作者建议一致。",
  "sentence_ids": ["sent-0004", "sent-0013", "sent-0016"]
}

```

两种子各在单段章节，本题没有可补邻段；两侧实际messages、Schema及响应相同，但均为本轮独立真实调用。S08仍缺，不借公开参考补证；0013/0016不支持仅留最终图，0004程序归档无关，公开contradicted未命中。

{
  "groups": {
    "baseline": {
      "denominator": 3,
      "label_correct": 2,
      "json_complete": 3,
      "source_authenticity": 3,
      "input_coverage": 2,
      "input_coverage_ambiguous": 1,
      "necessary_citation_coverage": 2,
      "citation_support": 2,
      "unrelated_citations": 2,
      "reason_label_consistent": 1,
      "strict_complete_success": 1,
      "pdf_location_all_valid": 3,
      "answer_http_seconds": 62.20325309969485
    },
    "improved": {
      "denominator": 3,
      "label_correct": 1,
      "json_complete": 3,
      "source_authenticity": 3,
      "input_coverage": 2,
      "input_coverage_ambiguous": 1,
      "necessary_citation_coverage": 2,
      "citation_support": 1,
      "unrelated_citations": 2,
      "reason_label_consistent": 2,
      "strict_complete_success": 1,
      "pdf_location_all_valid": 2,
      "answer_http_seconds": 64.20189800020307
    }
  },
  "pairs": [
    {
      "task_id": "AD01",
      "baseline_label": "contradicted",
      "improved_label": "contradicted",
      "label_regressed": false,
      "strict_baseline": true,
      "strict_improved": true,
      "pair_elapsed_seconds": 32.7577398000285
    },
    {
      "task_id": "AD02",
      "baseline_label": "supported",
      "improved_label": "insufficient",
      "label_regressed": true,
      "strict_baseline": false,
      "strict_improved": false,
      "pair_elapsed_seconds": 51.023163499776274
    },
    {
      "task_id": "AD03",
      "baseline_label": "supported",
      "improved_label": "supported",
      "label_regressed": false,
      "strict_baseline": false,
      "strict_improved": false,
      "pair_elapsed_seconds": 47.58721590018831
    }
  ]
}