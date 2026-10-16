# 紧凑输入与开启思考：理由和引用提示六次对照

固定自动improved证据历史重放，不是端到端检索成绩。Codex辅助原文复核，尚待本人确认。

严格成功不加入理由一致性门槛：format_complete AND selection_valid AND label_correct AND necessary_evidence_coverage_is_true AND citation_support_actual_label_is_true AND NOT has_unrelated_evidence

## AD01 original

```json

{
  "label": "insufficient",
  "reason": "资料中并未明确支持当手工修改文件时无需记录对象和目的，而是强调即使有这些操作也需详细记录程序、参数等信息（如P1-S02-p02中的sent-0004要求至少记录程序细节）。",
  "sentence_ids": ["sent-0004", "sent-0011"]
}

```

耗时18.412秒；输入1036、输出387 tokens；结束stop。

实际0011明确要求无法避免手工操作时记录哪些文件修改/移动及目的，0004要求最低程序细节。两项已覆盖直接反证，但模型给insufficient；理由承认需详细记录却不判反驳。理由将0004说成P1-S02-p02，实际为P1-S02-p03。来源展开真实不消除这些错误。

## AD01 revised

```json

{
  "label": "contradicted",
  "reason": "资料明确指出当手工操作无法避免时，必须记录修改对象和目的（如P1-S03-p01中提到的记录数据文件修改或移动及用途），与主张中的'无需记录'相矛盾。",
  "sentence_ids": ["sent-0004", "sent-0005", "sent-0006", "sent-0007", "sent-0008", "sent-0009", "sent-0010", "sent-0011"]
}

```

耗时18.287秒；输入1113、输出364 tokens；结束stop。

0011的“If manual operations cannot be avoided ... note down which data files ... and for what purpose”直接反驳无需记录；0004及0005—0010是手工操作与可复现流程的同段背景。后者冗余但与当前手工操作记录主题和条件相关，沿用此前相关冗余不等于无关的口径，不能因片段多而临时判无关。contradicted、理由及引用集合成立；reason仍重复来源ID，另记提示遵从问题，不添加严格门槛。

## AD02 revised

```json

{
  "label": "insufficient",
  "reason": "资料中提到导出静态HTML/PDF有助于阅读（P2-S10-p01），但并未直接说明其是否足以执行原计算。其他段落提及使用 Binder 或容器化环境支持执行，因此该主张部分成立，但不足以全面满足。",
  "sentence_ids": ["sent-0004", "sent-0006", "sent-0007", "sent-0009", "sent-0013"]
}

```

耗时23.409秒；输入1205、输出488 tokens；结束stop。

0006/0007已有静态可读档案与需依赖重建环境的区分，0013又给出重新运行所需环境，0009补充静态浏览，仍覆盖关键Read/Run依据。给insufficient是已有正确项退步，不能将缺少逐字“不能执行”的句子当作组合证据不足；reason形式上解释其缺证判断，但实际关系判断错误。0004许可引用仍无关；reason将静态HTML/PDF指向P2-S10-p01，实际相关原句在p02。

## AD02 original

```json

{
  "label": "supported",
  "reason": "资料中明确提到使用GitHub、Nbviewer等方法提供静态视图可帮助阅读，同时指出Binder和Docker等容器化环境能支持执行原计算。主张认为仅导出HTML/PDF不足以执行计算的表述与资料内容存在矛盾，因此被支持。",
  "sentence_ids": ["sent-0004", "sent-0006", "sent-0007", "sent-0010", "sent-0011", "sent-0012", "sent-0013"]
}

```

耗时20.626秒；输入1128、输出460 tokens；结束stop。

0006/0007/0010说明静态HTML/PDF可读档案及重建环境所需依赖，0011—0013说明Binder执行和容器/依赖环境。集合支持“可阅读但仅此不足执行”，标签supported正确。reason却说主张与资料矛盾因此被支持，内在矛盾另列；0004是开源许可/仓库，没有该判断的必要支持作用，属于无关引用，因此严格失败。

## AD03 original

```json

{
  "label": "insufficient",
  "reason": "资料中未明确提及绘图过程中仅保留最终图片满足作者关于图底层数据的建议，且相关证据（如使用HTML文件输出）支持其他做法而非直接关联。",
  "sentence_ids": ["sent-0009", "sent-0013"]
}

```

耗时22.908秒；输入1144、输出491 tokens；结束stop。

实际没有公开参考指定的S08绘图数据变换直接依据；0009描述最终图表高度汇总，0013在存储条件允许时建议永久保留全部底层数据。这些既可能作为可见范围的缺证检查来源，也可能提供有条件反证，沿用覆盖及支持ambiguous；不引入未发送S08，不移出分母。insufficient不符合公开contradicted，严格失败。

## AD03 revised

```json

{
  "label":"supported",
  "reason":"资料明确指出在程序版本管理、详细数据生成及虚拟机图像存储等环节中，需保存精确版本以确保后续可追溯性，并强调生成完整数据而非仅保留最终结果。主张与作者建议一致。",
  "sentence_ids": ["sent-0004", "sent-0013", "sent-0016"]
}

```

耗时22.361秒；输入1221、输出450 tokens；结束stop。

0004只谈归档程序版本，与仅留最终图片是否满足底层数据建议没有直接支持，属于无关片段。0013条件性建议保存全部底层数据，0016要求至少一次生成、检查和验证详细值，不支持“只保留最终图片就满足”；reason自己强调完整数据而非仅最终结果却称原主张一致，方向矛盾。S08仍未输入，必要覆盖的边界保留ambiguous；supported无论公开标签还是当前引用集合均不通过。

{
  "groups": {
    "original": {
      "denominator": 3,
      "label_correct": 1,
      "format_complete": 3,
      "reason_label_consistent": 1,
      "source_authenticity": 3,
      "necessary_coverage": 2,
      "necessary_coverage_ambiguous": 1,
      "citation_support": 1,
      "citation_support_ambiguous": 1,
      "unrelated_citations": 1,
      "strict_complete_success": 0,
      "budget_exhausted": 0,
      "input_tokens": 3308,
      "output_tokens": 1338,
      "client_seconds": 61.946068400051445
    },
    "revised": {
      "denominator": 3,
      "label_correct": 1,
      "format_complete": 3,
      "reason_label_consistent": 2,
      "source_authenticity": 3,
      "necessary_coverage": 2,
      "necessary_coverage_ambiguous": 1,
      "citation_support": 1,
      "citation_support_ambiguous": 0,
      "unrelated_citations": 2,
      "strict_complete_success": 1,
      "budget_exhausted": 0,
      "input_tokens": 3539,
      "output_tokens": 1302,
      "client_seconds": 64.05651569995098
    }
  },
  "pairs": [
    {
      "id": "AD01",
      "old_label": "insufficient",
      "new_label": "contradicted",
      "label_regressed": false,
      "historically_correct_AD02_regressed": false,
      "old_strict": false,
      "new_strict": true,
      "old_necessary": true,
      "new_necessary": true,
      "old_support": false,
      "new_support": true,
      "old_unrelated": false,
      "new_unrelated": false,
      "old_consistent": false,
      "new_consistent": true,
      "delta_client_seconds": -0.12456330005079508
    },
    {
      "id": "AD02",
      "old_label": "supported",
      "new_label": "insufficient",
      "label_regressed": true,
      "historically_correct_AD02_regressed": true,
      "old_strict": false,
      "new_strict": false,
      "old_necessary": true,
      "new_necessary": true,
      "old_support": true,
      "new_support": false,
      "old_unrelated": true,
      "new_unrelated": true,
      "old_consistent": false,
      "new_consistent": true,
      "delta_client_seconds": 2.7823634000960737
    },
    {
      "id": "AD03",
      "old_label": "insufficient",
      "new_label": "supported",
      "label_regressed": false,
      "historically_correct_AD02_regressed": false,
      "old_strict": false,
      "new_strict": false,
      "old_necessary": "ambiguous",
      "new_necessary": "ambiguous",
      "old_support": "ambiguous",
      "new_support": false,
      "old_unrelated": false,
      "new_unrelated": true,
      "old_consistent": true,
      "new_consistent": false,
      "delta_client_seconds": -0.5473528001457453
    }
  ],
  "decision": {
    "at": "2026-10-16T18:15:12.611776+08:00",
    "adopt_prompt_candidate": false,
    "existing_correct_item_regression_veto": true,
    "rule": "严格成功优先，其次标签正确；已有正确项不得退步，同分保留旧流程。",
    "retain_base": "紧凑输入＋开启思考由本人决定保留，提示候选独立取舍。",
    "strict_formula": "format_complete AND selection_valid AND label_correct AND necessary_evidence_coverage_is_true AND citation_support_actual_label_is_true AND NOT has_unrelated_evidence",
    "reason_quality_separate": true,
    "no_auto_label_flip_or_citation_removal": true,
    "AD03_missing_direct_source_preserved": true,
    "scope": "仅三题固定自动证据；没有读取七题或更新端到端成绩。",
    "new_generations": 6,
    "cumulative": 621,
    "A_used": 87,
    "original_plan_remaining": 3,
    "future_reserved_additional": 30,
    "future_reservation_used": 0,
    "technical_failures": 0,
    "quality_retries": 0
  }
}