# 同1024预算：关闭/开启思考的全部最终结果

仅三道开发题固定自动improved证据重放；本轮不重新检索。Codex辅助原文复核，尚待本人确认。

思考文本是模型输出，不作事实证据、不替最终答案判分，也不作为内部因果机制的直接证明。


## AD01 off

原始最终content：

```json

{
  "label": "supported",
  "reason": "The passages provided support the claim that when manual modifications or file movements are unavoidable, saving the final file and specifying the full analysis workflow in an executable form ensures the specification matches the analysis and can be reproduced by others.",
  "sentence_ids": [
    "sent-0001",
    "sent-0002",
    "sent-0003",
    "sent-0004",
    "sent-0005",
    "sent-0006",
    "sent-0007",
    "sent-0008",
    "sent-0009",
    "sent-0010",
    "sent-0011"
  ]
}

```

总输出tokens=165；客户端耗时=23.262766秒；结束=stop；实际reasoning字段=False。

理由改成最终文件加完整可执行流程，而原主张说无需记录。全选11句包含末句明确要求记录文件及目的的反证，不支持实际supported。

思考文本文件：None（未返回则为None，不虚构空字段）。


## AD01 on

原始最终content：

```json

{
  "label": "supported",
  "reason": "资料中明确指出当手工操作不可避免时，应通过流程描述替代记录修改对象和目的，且未发现反对该主张的证据。",
  "sentence_ids": [
    "sent-0002",
    "sent-0003",
    "sent-0004"
  ]
}

```

总输出tokens=341；客户端耗时=30.266204秒；结束=stop；实际reasoning字段=True。

最终理由声称流程描述可替代记录文件和目的，原文没有这个豁免；实际末句仍明确要求记录。只选可执行流程及最低限度流程细节3句，漏掉直接记录要求，supported与理由表面一致但事实和引用支持失败。

思考文本文件：reasoning-02-AD01-on.txt（未返回则为None，不虚构空字段）。


## AD02 on

原始最终content：

```json

{
  "label":"supported",
  "reason":"资料明确指出导出静态HTML/PDF可帮助他人阅读（通过代码仓库或Nbviewer等工具），同时提及使用Binder运行笔记本以支持执行。两者均满足用户主张中的两个核心需求，因此足以支持该主张。",
  "sentence_ids": [
    "sent-0002",
    "sent-0011",
    "sent-0013"
  ]
}

```

总输出tokens=502；客户端耗时=44.964288秒；结束=stop；实际reasoning字段=True。

最终supported符合公开参考。理由区分静态HTML/PDF阅读和Binder执行环境，与支持原主张方向相容，但把仅此不足概括为两个核心需求，否定限定解释仍不充分。最终只选引言问句、Binder和容器环境sent-0002/0011/0013，缺少Read静态导出来源；理由提及了原段事实不等于实际引用已覆盖，因此必要覆盖和引用集合支持失败。

思考文本文件：reasoning-03-AD02-on.txt（未返回则为None，不虚构空字段）。


## AD02 off

原始最终content：

```json

{
  "label": "contradicted",
  "reason": "The passage explicitly states that 'only this' (the method of exporting as HTML/PDF) is insufficient for others to run and explore the notebooks, which directly contradicts the original claim.",
  "sentence_ids": [
    "sent-0002",
    "sent-0011"
  ]
}

```

总输出tokens=85；客户端耗时=19.865424秒；结束=stop；实际reasoning字段=False。

原主张说仅此不足执行，理由也说不足却给contradicted。选引言问句和Binder环境句，未覆盖静态阅读来源。

思考文本文件：None（未返回则为None，不虚构空字段）。


## AD03 off

原始最终content：

```json

{
  "label": "supported",
  "reason": "The passage supports the claim that in graphic design, data transformations are essential for producing accurate results, and archiving exact program versions ensures future usability. The text emphasizes the necessity of storing programs at their exact versions to maintain compatibility and avoid issues.",
  "sentence_ids": [
    "sent-0001",
    "sent-0002",
    "sent-0003",
    "sent-0004",
    "sent-0005",
    "sent-0006",
    "sent-0007",
    "sent-0008"
  ]
}

```

总输出tokens=147；客户端耗时=28.121892秒；结束=stop；实际reasoning字段=False。

理由把绘图数据转换变成graphic design和程序版本归档，前8句程序版本/依赖不足以支持只留图满足数据建议。

思考文本文件：None（未返回则为None，不虚构空字段）。


## AD03 on

原始最终content：

```json

{
  "label": "insufficient",
  "reason": "资料中未提及绘图过程中数据转换后仅保留最终图片是否满足作者关于图底层数据的建议，且无直接证据表明这一操作与作者要求相关。",
  "sentence_ids": []
}

```

总输出tokens=438；客户端耗时=45.595625秒；结束=stop；实际reasoning字段=True。

实际未输入指定S08的绘图变换直接依据，拒判比无据支持更保守，但不符合公开开发参考contradicted。S09仍有详细值及有条件保留数据的相关论述，不能宣称全部输入无关；其替代反证的充分性保留边界。空引用不算必要来源覆盖或引用支持成功。

思考文本文件：reasoning-06-AD03-on.txt（未返回则为None，不虚构空字段）。

{
  "groups": {
    "off": {
      "denominator": 3,
      "format_complete": 3,
      "label_correct": 0,
      "reason_label_consistent": 0,
      "nonempty_source_authenticity_passed": 3,
      "empty_selection": 0,
      "necessary_coverage": 1,
      "citation_support": 0,
      "strict_complete_success": 0,
      "budget_exhausted": 0,
      "no_valid_final": 0,
      "reasoning_produced": 0,
      "input_tokens": 7843,
      "total_output_tokens": 397,
      "client_seconds": 71.2500823000446
    },
    "on": {
      "denominator": 3,
      "format_complete": 3,
      "label_correct": 1,
      "reason_label_consistent": 3,
      "nonempty_source_authenticity_passed": 2,
      "empty_selection": 1,
      "necessary_coverage": 0,
      "citation_support": 0,
      "strict_complete_success": 0,
      "budget_exhausted": 0,
      "no_valid_final": 0,
      "reasoning_produced": 3,
      "input_tokens": 7831,
      "total_output_tokens": 1281,
      "client_seconds": 120.82611659984104
    }
  },
  "decision": {
    "at": "2026-10-16T17:47:58.015151+08:00",
    "retain_as_pending_judgment_candidate": "thinking_on",
    "current_entry_modified": false,
    "basis": "按事前严格成功优先、其次标签正确：严格均0/3，开启标签1/3优于关闭0/3，且没有已正确或严格成功项退步。因此本轮开启在次级指标胜出，保留为待接入独立候选，不把它写成整体引用质量提高。",
    "main_limit": "AD02最终标签虽正确，引用缺Read；AD01继续错误，AD03拒判且空引用。必要覆盖从1/3降0/3，非空来源核验从3条降2条，这些风险与次级指标收益并列，不自动补证。",
    "no_thought_scoring": "不以思考里的说法抵消最终错误；reasoning文字也不是对内部机制的直接证明。",
    "not_generalization": "仅三道开发题、固定历史自动证据及本轮配置。与旧512预算是历史比较，不能把预算变化当作纯模式效果。",
    "new_generations": 6,
    "cumulative": 609,
    "A_used": 75,
    "original_plan_budget": 90,
    "original_plan_remaining": 15,
    "future_reserved_additional": 30,
    "future_reservation_used": 0,
    "future_reservation_authorizes_execution": false,
    "budget_note": "原计划余额与另行未来预留分列，本轮6次不消耗后续30次预留；未执行七题/变体/反事实。",
    "technical_request_failures": 0,
    "quality_retries": 0,
    "stop": "服务已停止，本轮不追加调用；不修改当前入口或五份文档。"
  }
}
