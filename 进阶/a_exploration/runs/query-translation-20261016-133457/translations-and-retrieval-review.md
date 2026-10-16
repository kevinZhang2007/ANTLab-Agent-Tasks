# 完整英文检索译文：自动验证停止记录

本轮仅三次翻译生成，未生成判断回答。译文不作事实证据，未人工修正。

Codex辅助对照复核，尚待本人确认。


## AD01

中文主张：当手工修改或移动数据文件确实无法避免时，只要保存最终文件，无需记录修改对象和目的。

原始转换响应：

```json

{"translation":"When manual modifications or file movement cannot be avoided, as long as the final file is saved, no record of the modification object and purpose is required."}

```

cannot be avoided、as long as及no record required保留了条件、充分性和否定。data files被泛化为file；manual modifications未明确数据对象，记录对象仍为modification object，具体对象有遗漏，不能称逐项完全忠实。

baseline：P1-S03-p01, P1-S06-p01

improved：P1-S03-p01, P1-S06-p01

翻译耗时 1.454 秒；后续回答未执行。


## AD02

中文主张：把Notebook导出为静态HTML或PDF，可以帮助他人阅读，但仅此不足以让他人执行原计算。

原始转换响应：

```json

{"translation":"Exporting the Notebook as static HTML or PDF helps others read it, but only this is sufficient for them to perform the original calculation."}

```

原文但仅此不足以让他人执行被译为but only this is sufficient...，把不充分反转为充分，门禁失败。不得因检索仍命中同段而忽略语义反转。

baseline：P2-S05-p01, P2-S10-p02

improved：P2-S05-p01, P2-S05-p02, P2-S10-p01, P2-S10-p02, P2-S10-p03

翻译耗时 1.293 秒；后续回答未执行。


## AD03

中文主张：绘图过程中做过数据转换时，只保留最终图片就满足作者关于图底层数据的建议。

原始转换响应：

```json

{"translation":"When drawing, only retain the final image after data conversion to meet the author's suggestion of preserving the underlying data."}

```

only、final image、after data conversion保留了主要对象与限制；原来这是一个满足建议的陈述，被改成only retain...to meet...的祈使/目的表达，并增加preserving措辞，不称完全忠实。没有把原主张改成反对只留图，但实际译文未复现人工理想译文的检索收益。

baseline：P1-S02-p01, P1-S09-p01

improved：P1-S02-p01, P1-S02-p02, P1-S09-p01

翻译耗时 1.101 秒；后续回答未执行。

{
  "at": "2026-10-16T16:49:28.418399+08:00",
  "allow_answers": false,
  "reason": "AD02关键否定/充分性反转，自动译文未通过忠实度门禁；此外AD03的指定核心段仅排第3，未进入top2或其同章节邻段，自动检索无必要覆盖改善。",
  "direction_changed": [
    "AD02"
  ],
  "other_fidelity_omissions": [
    "AD01数据文件限定泛化",
    "AD03陈述改祈使/目的表达"
  ],
  "manual_ideal_improvement": [
    "AD03"
  ],
  "actual_automatic_improvements": [],
  "actual_automatic_regressions": [],
  "coverage_denominators": {
    "baseline": 3,
    "improved": 3
  },
  "coverage_counts": {
    "old_keywords_baseline": 1,
    "old_keywords_improved": 2,
    "manual_translation_baseline": 2,
    "manual_translation_improved": 3,
    "actual_automatic_baseline": 1,
    "actual_automatic_improved": 2
  },
  "answer_calls_executed": 0,
  "answer_calls_not_executed": 6,
  "answer_metrics": "not_run，不计为模型判断错误或成功。",
  "not_adopted": true,
  "retained": "现有关键词转换、共同判断提示和句子选择机制保持不变。",
  "limits": [
    "人工译文提升仅支持理想译文条件下检索可能改善，不是自动成绩。",
    "长译文也引入中间结果/模块化段；覆盖/干扰变化不能单独归于长度或某个关键词。",
    "TF-IDF不验证逻辑方向，错误译文仍可命中同一段。",
    "AD03原S09有相邻底层值论述，指定S08覆盖与其他可能的部分依据分开；本轮未用缺失S08补模型回答。"
  ],
  "stop": "不追加搜索或生成；七道评测未读取。",
  "new_generations": 3,
  "cumulative": 585,
  "A_used": 51,
  "A_cap": 90,
  "A_remaining": 39,
  "cap_adjusted_by_user_before_execution": true,
  "technical_request_failures": 0
}
