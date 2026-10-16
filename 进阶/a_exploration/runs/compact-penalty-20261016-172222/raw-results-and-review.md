# 输入组织与presence_penalty四组合：全部原始结果

本轮12次0.6B生成，仅三道开发题固定自动证据回答重放，不是端到端检索成绩。

Codex辅助原文复核，尚待本人确认。空引用可合法，但不能当作非空来源真实性通过。


## AD01 repeated_15

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

输入2332、输出165 tokens，客户端21.000838秒；结束stop。

理由改成最终文件加可执行流程，而原主张是无需记录。所选全部11句含P1-S03末句明确要求记录哪些文件和目的，必要反证在，但不支持实际supported。


## AD01 compact_15

```json

{
  "label": "insufficient",
  "reason": "The provided passage does not explicitly support the claim. The information in the passages focuses on how to produce and reproduce results, but it does not address whether manual modifications or data file movements are necessary or sufficient.",
  "sentence_ids": []
}

```

输入1040、输出63 tokens，客户端6.313166秒；结束stop。

理由把不可避免条件改成手工修改是否必要或充分的子问题；实际原段仍完整含明确记录要求，insufficient错误。空选择没有来源造假，但不能算非空引文真实性通过，也未覆盖反证。


## AD01 repeated_0

```json

{
  "label": "supported",
  "reason": "The passages provided support the claim that when manual modifications or file movements are unavoidable, the final file should be saved without recording the specific details of the modifications or purposes.",
  "sentence_ids": [
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

输入2332、输出128 tokens，客户端19.647729秒；结束stop。

理由声称不用记录修改细节，和supported表面一致，但与选中sent-0011的you should as a minimum note down...and for what purpose直接相反，惩罚归零未修语义。


## AD01 compact_0

```json

{
  "label": "insufficient",
  "reason": "提供的资料中并未明确支持该主张，也没有提供反例。",
  "sentence_ids": []
}

```

输入1040、输出36 tokens，客户端6.025935秒；结束stop。

原文明确要求记录文件及目的，回复却称没有反例；拒判理由与label表面一致但事实错误。空引用未证明缺证。


## AD02 compact_15

```json

{
  "label": "insufficient",
  "reason": "资料中提到的静态HTML/PDF版本和Nbviewer等技术手段可以辅助阅读，但并未明确说明这些手段是否足以支持执行原计算。",
  "sentence_ids": ["sent-0004", "sent-0006", "sent-0007", "sent-0008", "sent-0009"]
}

```

输入1132、输出97 tokens，客户端9.068495秒；结束stop。

sent-0006静态档案与0007在执行技术失败时仍可读、另需依赖列表重建环境，可作区分read与run的替代组合，不强制固定Run段ID；所以覆盖按实际内容成立。但回复以未明说足以执行为由拒判，忽略原主张正是仅此不足，引用不支持实际insufficient。0004的仓库许可不提供该区别，另记无关。


## AD02 repeated_0

```json

{
  "label": "contradicted",
  "reason": "The passage explicitly states that 'only this' (the method of exporting as HTML/PDF) is insufficient for others to run and explore the notebooks, which directly contradicts the original claim.",
  "sentence_ids": [
    "sent-0002",
    "sent-0007",
    "sent-0008",
    "sent-0010"
  ]
}

```

输入2628、输出103 tokens，客户端20.899105秒；结束stop。

理由与原主张同向却判contradicted。所引问句、静态档案及Nbviewer阅读句没有给完整的执行环境对比；不能只凭出处真算支持反驳。


## AD02 compact_0

```json

{
  "label": "insufficient",
  "reason": "资料中提到静态HTML或PDF版本的存储与使用有助于他人阅读，但仅此不足以让他人执行原计算。",
  "sentence_ids": ["sent-0004", "sent-0006", "sent-0007", "sent-0008", "sent-0009"]
}

```

输入1132、输出91 tokens，客户端8.003952秒；结束stop。

理由逐字语义支持仅此不足执行，却给insufficient，理由与标签不一致。同一组0006/0007替代依据可以覆盖判断，但不能支持这个拒判；0004许可来源另记无关。


## AD02 repeated_15

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

输入2628、输出85 tokens，客户端19.535897秒；结束stop。

原主张说仅此不足执行，理由也说不足，却判contradicted，否定方向仍错。引言问句和Binder句未覆盖静态阅读的必要来源。


## AD03 repeated_0

```json

{
  "label": "supported",
  "reason": "The passage supports the claim that in the process of drawing images, the author's suggestion to only retain the final image is valid.",
  "sentence_ids": [
    "sent-0001",
    "sent-0002",
    "sent-0003",
    "sent-0004",
    "sent-0005",
    "sent-0006",
    "sent-0007",
    "sent-0008",
    "sent-0010",
    "sent-0011",
    "sent-0012",
    "sent-0013",
    "sent-0014",
    "sent-0015",
    "sent-0016"
  ]
}

```

输入2883、输出188 tokens，客户端27.678030秒；结束stop。

理由直接说作者建议只留最终图，和supported表面一致但没有原文支持。选了程序归档和多数S09句；S09检查详细值及有条件保留数据不是只留图足够的依据。


## AD03 compact_0

```json

{
  "label": "insufficient",
  "reason": "缺乏直接证据支持该主张，且无法确认资料中是否明确涉及绘图过程中数据转换的保留要求。",
  "sentence_ids": []
}

```

输入1148、输出46 tokens，客户端6.883297秒；结束stop。

与紧凑1.5一样保留缺少S08直接依据的边界；不借未输入参考补证。公开参考口径标签不对，实际可见证据下的拒判充分性另记ambiguous，空引用不算支持成功。


## AD03 repeated_15

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

输入2883、输出147 tokens，客户端25.928496秒；结束stop。

理由把绘图数据转换改成graphic design与程序归档，选中前8句均为程序版本/依赖，不支持只留图足够。


## AD03 compact_15

```json

{
  "label": "insufficient",
  "reason": "缺乏直接证据支持该主张，且无法确认资料中是否明确涉及绘图过程中的数据转换与最终图片保存之间的关系。",
  "sentence_ids": []
}

```

输入1148、输出50 tokens，客户端6.716168秒；结束stop。

未输入指定S08的绘图变换直接依据，拒判比无据支持更保守，但不符合公开参考contradicted。实际S09仍有底层值相关论述，其替代反证充分性有边界，不认定所有资料都无关；空引用未覆盖可检查来源。

{
  "groups": {
    "repeated_15": {
      "denominator": 3,
      "format_complete": 3,
      "selection_valid": 3,
      "label_correct": 0,
      "reason_label_consistent": 0,
      "nonempty_source_authenticity_passed": 3,
      "empty_selection": 0,
      "source_truth_failures": 0,
      "necessary_coverage": 1,
      "citation_support": 0,
      "unrelated_citations": 1,
      "strict_complete_success": 0,
      "input_tokens": 7843,
      "output_tokens": 397,
      "client_seconds": 66.46523070009425,
      "budget_exhausted": 0
    },
    "compact_15": {
      "denominator": 3,
      "format_complete": 3,
      "selection_valid": 3,
      "label_correct": 0,
      "reason_label_consistent": 3,
      "nonempty_source_authenticity_passed": 1,
      "empty_selection": 2,
      "source_truth_failures": 0,
      "necessary_coverage": 1,
      "citation_support": 0,
      "unrelated_citations": 1,
      "strict_complete_success": 0,
      "input_tokens": 3320,
      "output_tokens": 210,
      "client_seconds": 22.097828399855644,
      "budget_exhausted": 0
    },
    "repeated_0": {
      "denominator": 3,
      "format_complete": 3,
      "selection_valid": 3,
      "label_correct": 0,
      "reason_label_consistent": 2,
      "nonempty_source_authenticity_passed": 3,
      "empty_selection": 0,
      "source_truth_failures": 0,
      "necessary_coverage": 1,
      "citation_support": 0,
      "unrelated_citations": 1,
      "strict_complete_success": 0,
      "input_tokens": 7843,
      "output_tokens": 419,
      "client_seconds": 68.2248641999904,
      "budget_exhausted": 0
    },
    "compact_0": {
      "denominator": 3,
      "format_complete": 3,
      "selection_valid": 3,
      "label_correct": 0,
      "reason_label_consistent": 2,
      "nonempty_source_authenticity_passed": 1,
      "empty_selection": 2,
      "source_truth_failures": 0,
      "necessary_coverage": 1,
      "citation_support": 0,
      "unrelated_citations": 1,
      "strict_complete_success": 0,
      "input_tokens": 3320,
      "output_tokens": 173,
      "client_seconds": 20.91318430006504,
      "budget_exhausted": 0
    }
  },
  "contrasts": [
    {
      "name": "A：惩罚1.5下组织因素",
      "old": "repeated_15",
      "new": "compact_15",
      "paired_claims": 3,
      "pairs": [
        {
          "id": "AD01",
          "old_label": "supported",
          "new_label": "insufficient",
          "delta_label_correct": 0,
          "delta_strict": 0,
          "old_necessary": true,
          "new_necessary": false,
          "old_empty": false,
          "new_empty": true,
          "delta_input_tokens": -1292,
          "delta_output_tokens": -102,
          "delta_client_seconds": -14.687671900261194
        },
        {
          "id": "AD02",
          "old_label": "contradicted",
          "new_label": "insufficient",
          "delta_label_correct": 0,
          "delta_strict": 0,
          "old_necessary": false,
          "new_necessary": true,
          "old_empty": false,
          "new_empty": false,
          "delta_input_tokens": -1496,
          "delta_output_tokens": 12,
          "delta_client_seconds": -10.467402100097388
        },
        {
          "id": "AD03",
          "old_label": "supported",
          "new_label": "insufficient",
          "delta_label_correct": 0,
          "delta_strict": 0,
          "old_necessary": false,
          "new_necessary": false,
          "old_empty": false,
          "new_empty": true,
          "delta_input_tokens": -1735,
          "delta_output_tokens": -97,
          "delta_client_seconds": -19.212328299880028
        }
      ],
      "delta_correct": 0,
      "delta_strict": 0,
      "delta_input_tokens": -4523,
      "delta_client_seconds": -44.36740230023861
    },
    {
      "name": "A：惩罚0下组织因素",
      "old": "repeated_0",
      "new": "compact_0",
      "paired_claims": 3,
      "pairs": [
        {
          "id": "AD01",
          "old_label": "supported",
          "new_label": "insufficient",
          "delta_label_correct": 0,
          "delta_strict": 0,
          "old_necessary": true,
          "new_necessary": false,
          "old_empty": false,
          "new_empty": true,
          "delta_input_tokens": -1292,
          "delta_output_tokens": -92,
          "delta_client_seconds": -13.621794200036675
        },
        {
          "id": "AD02",
          "old_label": "contradicted",
          "new_label": "insufficient",
          "delta_label_correct": 0,
          "delta_strict": 0,
          "old_necessary": false,
          "new_necessary": true,
          "old_empty": false,
          "new_empty": false,
          "delta_input_tokens": -1496,
          "delta_output_tokens": -12,
          "delta_client_seconds": -12.89515299978666
        },
        {
          "id": "AD03",
          "old_label": "supported",
          "new_label": "insufficient",
          "delta_label_correct": 0,
          "delta_strict": 0,
          "old_necessary": false,
          "new_necessary": false,
          "old_empty": false,
          "new_empty": true,
          "delta_input_tokens": -1735,
          "delta_output_tokens": -142,
          "delta_client_seconds": -20.79473270010203
        }
      ],
      "delta_correct": 0,
      "delta_strict": 0,
      "delta_input_tokens": -4523,
      "delta_client_seconds": -47.311679899925366
    },
    {
      "name": "B：重复输入下惩罚归零",
      "old": "repeated_15",
      "new": "repeated_0",
      "paired_claims": 3,
      "pairs": [
        {
          "id": "AD01",
          "old_label": "supported",
          "new_label": "supported",
          "delta_label_correct": 0,
          "delta_strict": 0,
          "old_necessary": true,
          "new_necessary": true,
          "old_empty": false,
          "new_empty": false,
          "delta_input_tokens": 0,
          "delta_output_tokens": -37,
          "delta_client_seconds": -1.3531087001319975
        },
        {
          "id": "AD02",
          "old_label": "contradicted",
          "new_label": "contradicted",
          "delta_label_correct": 0,
          "delta_strict": 0,
          "old_necessary": false,
          "new_necessary": false,
          "old_empty": false,
          "new_empty": false,
          "delta_input_tokens": 0,
          "delta_output_tokens": 18,
          "delta_client_seconds": 1.3632082999683917
        },
        {
          "id": "AD03",
          "old_label": "supported",
          "new_label": "supported",
          "delta_label_correct": 0,
          "delta_strict": 0,
          "old_necessary": false,
          "new_necessary": false,
          "old_empty": false,
          "new_empty": false,
          "delta_input_tokens": 0,
          "delta_output_tokens": 41,
          "delta_client_seconds": 1.7495339000597596
        }
      ],
      "delta_correct": 0,
      "delta_strict": 0,
      "delta_input_tokens": 0,
      "delta_client_seconds": 1.7596334998961538
    },
    {
      "name": "B：紧凑输入下惩罚归零",
      "old": "compact_15",
      "new": "compact_0",
      "paired_claims": 3,
      "pairs": [
        {
          "id": "AD01",
          "old_label": "insufficient",
          "new_label": "insufficient",
          "delta_label_correct": 0,
          "delta_strict": 0,
          "old_necessary": false,
          "new_necessary": false,
          "old_empty": true,
          "new_empty": true,
          "delta_input_tokens": 0,
          "delta_output_tokens": -27,
          "delta_client_seconds": -0.2872309999074787
        },
        {
          "id": "AD02",
          "old_label": "insufficient",
          "new_label": "insufficient",
          "delta_label_correct": 0,
          "delta_strict": 0,
          "old_necessary": true,
          "new_necessary": true,
          "old_empty": false,
          "new_empty": false,
          "delta_input_tokens": 0,
          "delta_output_tokens": -6,
          "delta_client_seconds": -1.0645425997208804
        },
        {
          "id": "AD03",
          "old_label": "insufficient",
          "new_label": "insufficient",
          "delta_label_correct": 0,
          "delta_strict": 0,
          "old_necessary": false,
          "new_necessary": false,
          "old_empty": true,
          "new_empty": true,
          "delta_input_tokens": 0,
          "delta_output_tokens": -4,
          "delta_client_seconds": 0.16712949983775616
        }
      ],
      "delta_correct": 0,
      "delta_strict": 0,
      "delta_input_tokens": 0,
      "delta_client_seconds": -1.184644099790603
    },
    {
      "name": "共同变化：原方案到紧凑+0",
      "old": "repeated_15",
      "new": "compact_0",
      "paired_claims": 3,
      "pairs": [
        {
          "id": "AD01",
          "old_label": "supported",
          "new_label": "insufficient",
          "delta_label_correct": 0,
          "delta_strict": 0,
          "old_necessary": true,
          "new_necessary": false,
          "old_empty": false,
          "new_empty": true,
          "delta_input_tokens": -1292,
          "delta_output_tokens": -129,
          "delta_client_seconds": -14.974902900168672
        },
        {
          "id": "AD02",
          "old_label": "contradicted",
          "new_label": "insufficient",
          "delta_label_correct": 0,
          "delta_strict": 0,
          "old_necessary": false,
          "new_necessary": true,
          "old_empty": false,
          "new_empty": false,
          "delta_input_tokens": -1496,
          "delta_output_tokens": 6,
          "delta_client_seconds": -11.531944699818268
        },
        {
          "id": "AD03",
          "old_label": "supported",
          "new_label": "insufficient",
          "delta_label_correct": 0,
          "delta_strict": 0,
          "old_necessary": false,
          "new_necessary": false,
          "old_empty": false,
          "new_empty": true,
          "delta_input_tokens": -1735,
          "delta_output_tokens": -101,
          "delta_client_seconds": -19.04519880004227
        }
      ],
      "delta_correct": 0,
      "delta_strict": 0,
      "delta_input_tokens": -4523,
      "delta_client_seconds": -45.55204640002921
    }
  ],
  "decision": {
    "at": "2026-10-16T17:29:48.606561+08:00",
    "replace_current_entry": false,
    "keep_presence_penalty": 1.5,
    "quality_gain_claimed": false,
    "basis": "四组合标签正确与严格成功均0/3，引用支持均0/3。惩罚归零没有质量胜出，保留原1.5。紧凑确实降低输入与本轮耗时，但两题变为空引用，不能把来源真实性核验由3个非空集合降为1个时宣称已证无损；不自动采用为质量相同的替代。",
    "coverage_detail": "必要覆盖总数均1/3，但紧凑使AD01已覆盖反证丢失、AD02得到静态档案/依赖环境的替代组合；不是逐题完全不变。AD02替代依据没有强制固定Run段引用。",
    "source_detail": "空引用是合法质量结果，不是假引用或格式失败；单列not_applicable_empty，不计作真实性通过。剩余非空引用均真实，但真实不等于支持实际label。",
    "efficiency": "紧凑每组三题输入7843→3320，减少4523 tokens；本轮各题均更快，输出长度同时变化，不能声称稳定性能或单独归因去重。作为效率候选保留，未写回当前入口。",
    "factor_limit": "因素A同时改变冗余、字段组织和claim位置；因素B仅presence。条件内和共同变化分别列出，不把三题12个请求当独立12题，不从一次请求判断普遍机制。",
    "new_generations": 12,
    "cumulative": 603,
    "A_used": 69,
    "A_cap": 90,
    "A_remaining": 21,
    "technical_request_failures": 0,
    "quality_retries": 0,
    "stop": "本轮结束，不追加调用或读取七题。"
  }
}
