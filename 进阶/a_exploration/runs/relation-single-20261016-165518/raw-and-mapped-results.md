# 关系单输出与确定性标签映射：六条原始输出

Codex辅助原文复核，尚待本人确认。固定自动证据重放，不是端到端成绩。候选模型不输出label；以下外部标签均由模型关系确定性映射。


## AD01 original

模型原始输出：

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

外部标签：supported；来源：model_original_label

客户端耗时 22.378 秒；输出 165 tokens；结束 stop。

label为supported，但理由改为保存文件加可执行流程这个不同主张；全选11句包含末句明确记录文件及目的的反证，覆盖反证不等于支持实际label。

展开的外部接口内容（映射/展开为local_rule，不是原始模型响应）：

```json

{
  "label": "supported",
  "reason": "The passages provided support the claim that when manual modifications or file movements are unavoidable, saving the final file and specifying the full analysis workflow in an executable form ensures the specification matches the analysis and can be reproduced by others.",
  "evidence": [
    {
      "block_id": "P1-S02-p02",
      "quote": "Although manually noting the precise sequence of steps taken allows for an analysis to be reproduced, the documentation can easily get out of sync with how the analysis was really performed in its final version. "
    },
    {
      "block_id": "P1-S02-p02",
      "quote": "By instead specifying the full analysis workflow in a form that allows for direct execution, one can ensure that the specification matches the analysis that was (subsequently) performed, and that the analysis can be reproduced by yourself or others in an automated way. "
    },
    {
      "block_id": "P1-S02-p02",
      "quote": "Such executable descriptions [10] might come in the form of simple shell scripts or makefiles [15] , [16] at the command line, or in the form of stored workflows in a workflow management system [10] , [11] , [13] , [17] , [18] ."
    },
    {
      "block_id": "P1-S02-p03",
      "quote": "As a minimum, you should at least record sufficient details on programs, parameters, and manual procedures to allow yourself, in a year or so, to approximately reproduce the results."
    },
    {
      "block_id": "P1-S03-p01",
      "quote": "Whenever possible, rely on the execution of programs instead of manual procedures to modify data. "
    },
    {
      "block_id": "P1-S03-p01",
      "quote": "Such manual procedures are not only inefficient and error-prone, they are also difficult to reproduce. "
    },
    {
      "block_id": "P1-S03-p01",
      "quote": "If working at the UNIX command line, manual modification of files can usually be replaced by the use of standard UNIX commands or small custom scripts. "
    },
    {
      "block_id": "P1-S03-p01",
      "quote": "If working with integrated frameworks, there will typically be a quite rich collection of components for data manipulation. "
    },
    {
      "block_id": "P1-S03-p01",
      "quote": "As an example, manual tweaking of data files to attain format compatibility should be replaced by format converters that can be reenacted and included into executable workflows. "
    },
    {
      "block_id": "P1-S03-p01",
      "quote": "Other manual operations like the use of copy and paste between documents should also be avoided. "
    },
    {
      "block_id": "P1-S03-p01",
      "quote": "If manual operations cannot be avoided, you should as a minimum note down which data files were modified or moved, and for what purpose."
    }
  ]
}

```


## AD01 revised

模型原始输出：

```json

{
  "relation": "undetermined",
  "reason": "The claim is not directly supported by the provided passages, as they discuss best practices for documenting workflows but do not explicitly address whether manual modifications are necessary or if saving files without tracking can be avoided.",
  "sentence_ids": ["sent-0004", "sent-0005", "sent-0006", "sent-0007", "sent-0008", "sent-0009", "sent-0010", "sent-0011"]
}

```

外部标签：insufficient；来源：deterministic_mapping_from_model_relation

客户端耗时 20.911 秒；输出 128 tokens；结束 stop。

原主张以手工操作不可避免为条件，理由却转为资料是否说明手工操作必要，并漏用已选sent-0011的明确记录要求。理由的缺证叙述与undetermined表面一致，但实际完整输入可直接反驳无需记录，映射insufficient错误。

展开的外部接口内容（映射/展开为local_rule，不是原始模型响应）：

```json

{
  "label": "insufficient",
  "reason": "The claim is not directly supported by the provided passages, as they discuss best practices for documenting workflows but do not explicitly address whether manual modifications are necessary or if saving files without tracking can be avoided.",
  "evidence": [
    {
      "block_id": "P1-S02-p03",
      "quote": "As a minimum, you should at least record sufficient details on programs, parameters, and manual procedures to allow yourself, in a year or so, to approximately reproduce the results."
    },
    {
      "block_id": "P1-S03-p01",
      "quote": "Whenever possible, rely on the execution of programs instead of manual procedures to modify data. "
    },
    {
      "block_id": "P1-S03-p01",
      "quote": "Such manual procedures are not only inefficient and error-prone, they are also difficult to reproduce. "
    },
    {
      "block_id": "P1-S03-p01",
      "quote": "If working at the UNIX command line, manual modification of files can usually be replaced by the use of standard UNIX commands or small custom scripts. "
    },
    {
      "block_id": "P1-S03-p01",
      "quote": "If working with integrated frameworks, there will typically be a quite rich collection of components for data manipulation. "
    },
    {
      "block_id": "P1-S03-p01",
      "quote": "As an example, manual tweaking of data files to attain format compatibility should be replaced by format converters that can be reenacted and included into executable workflows. "
    },
    {
      "block_id": "P1-S03-p01",
      "quote": "Other manual operations like the use of copy and paste between documents should also be avoided. "
    },
    {
      "block_id": "P1-S03-p01",
      "quote": "If manual operations cannot be avoided, you should as a minimum note down which data files were modified or moved, and for what purpose."
    }
  ]
}

```


## AD02 revised

模型原始输出：

```json

{
  "relation": "undetermined",
  "reason": "The claim states that exporting to static HTML/PDF does not fully satisfy the requirement for others to run and explore notebooks, but the evidence provided in the passages does not directly address whether it can fulfill this requirement.",
  "sentence_ids": ["sent-0002", "sent-0011"]
}

```

外部标签：insufficient；来源：deterministic_mapping_from_model_relation

客户端耗时 19.986 秒；输出 83 tokens；结束 stop。

reason保留了主张的不足执行方向，并以没有直接明说为由给undetermined；完整实际输入的Read静态档案与Run环境可组合支持该区别，不能因没有逐字复述就拒判。只选sent-0002/0011，缺Read必要依据，引用也不能支持拒判。

展开的外部接口内容（映射/展开为local_rule，不是原始模型响应）：

```json

{
  "label": "insufficient",
  "reason": "The claim states that exporting to static HTML/PDF does not fully satisfy the requirement for others to run and explore notebooks, but the evidence provided in the passages does not directly address whether it can fulfill this requirement.",
  "evidence": [
    {
      "block_id": "P2-S10-p01",
      "quote": "But how will others access, run, and explore them? "
    },
    {
      "block_id": "P2-S10-p03",
      "quote": "Run: To support others running your notebooks, you can use Binder [ 16 ] to provide a zero-install environment to run your notebooks in the cloud ( https://mybinder.org/ ). "
    }
  ]
}

```


## AD02 original

模型原始输出：

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

外部标签：contradicted；来源：model_original_label

客户端耗时 18.819 秒；输出 85 tokens；结束 stop。

理由将仅静态导出不足执行称为反驳，但原主张正是仅此不足；只选引言问句和Binder运行环境，漏Read静态导出来源。

展开的外部接口内容（映射/展开为local_rule，不是原始模型响应）：

```json

{
  "label": "contradicted",
  "reason": "The passage explicitly states that 'only this' (the method of exporting as HTML/PDF) is insufficient for others to run and explore the notebooks, which directly contradicts the original claim.",
  "evidence": [
    {
      "block_id": "P2-S10-p01",
      "quote": "But how will others access, run, and explore them? "
    },
    {
      "block_id": "P2-S10-p03",
      "quote": "Run: To support others running your notebooks, you can use Binder [ 16 ] to provide a zero-install environment to run your notebooks in the cloud ( https://mybinder.org/ ). "
    }
  ]
}

```


## AD03 original

模型原始输出：

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

外部标签：supported；来源：model_original_label

客户端耗时 24.905 秒；输出 147 tokens；结束 stop。

理由把绘图数据转换变成graphic design及程序版本归档，选中前8句均为程序依赖与版本，不支持只存最终图足够。

展开的外部接口内容（映射/展开为local_rule，不是原始模型响应）：

```json

{
  "label": "supported",
  "reason": "The passage supports the claim that in graphic design, data transformations are essential for producing accurate results, and archiving exact program versions ensures future usability. The text emphasizes the necessity of storing programs at their exact versions to maintain compatibility and avoid issues.",
  "evidence": [
    {
      "block_id": "P1-S04-p01",
      "quote": "In order to exactly reproduce a given result, it may be necessary to use programs in the exact versions used originally. "
    },
    {
      "block_id": "P1-S04-p01",
      "quote": "Also, as both input and output formats may change between versions, a newer version of a program may not even run without modifying its inputs. "
    },
    {
      "block_id": "P1-S04-p01",
      "quote": "Even having noted which version was used of a given program, it is not always trivial to get hold of a program in anything but the current version. "
    },
    {
      "block_id": "P1-S04-p01",
      "quote": "Archiving the exact versions of programs actually used may thus save a lot of hassle at later stages. "
    },
    {
      "block_id": "P1-S04-p01",
      "quote": "In some cases, all that is needed is to store a single executable or source code file. "
    },
    {
      "block_id": "P1-S04-p01",
      "quote": "In other cases, a given program may again have specific requirements to other installed programs/packages, or dependencies to specific operating system components. "
    },
    {
      "block_id": "P1-S04-p01",
      "quote": "To ensure future availability, the only viable solution may then be to store a full virtual machine image of the operating system and program. "
    },
    {
      "block_id": "P1-S04-p01",
      "quote": "As a minimum, you should note the exact names and versions of the main programs you use."
    }
  ]
}

```


## AD03 revised

模型原始输出：

```json

{
  "relation": "entails",
  "reason": "原文支持了主张，即绘图过程中只保留最终图片满足作者关于图底层数据的建议。",
  "sentence_ids": ["sent-0001", "sent-0002", "sent-0003", "sent-0004", "sent-0005", "sent-0006", "sent-0007", "sent-0008"]
}

```

外部标签：supported；来源：deterministic_mapping_from_model_relation

客户端耗时 26.081 秒；输出 111 tokens；结束 stop。

entails与reason支持原主张在文字上相符，但只选程序版本/依赖前8句，不能推出只留最终图满足底层数据建议。实际未输入指定S08，不能借参考补证；S09实际含检查详细值的相关论述，不能笼统说完全没有相关材料，也不能把它改判为支持只留图。

展开的外部接口内容（映射/展开为local_rule，不是原始模型响应）：

```json

{
  "label": "supported",
  "reason": "原文支持了主张，即绘图过程中只保留最终图片满足作者关于图底层数据的建议。",
  "evidence": [
    {
      "block_id": "P1-S04-p01",
      "quote": "In order to exactly reproduce a given result, it may be necessary to use programs in the exact versions used originally. "
    },
    {
      "block_id": "P1-S04-p01",
      "quote": "Also, as both input and output formats may change between versions, a newer version of a program may not even run without modifying its inputs. "
    },
    {
      "block_id": "P1-S04-p01",
      "quote": "Even having noted which version was used of a given program, it is not always trivial to get hold of a program in anything but the current version. "
    },
    {
      "block_id": "P1-S04-p01",
      "quote": "Archiving the exact versions of programs actually used may thus save a lot of hassle at later stages. "
    },
    {
      "block_id": "P1-S04-p01",
      "quote": "In some cases, all that is needed is to store a single executable or source code file. "
    },
    {
      "block_id": "P1-S04-p01",
      "quote": "In other cases, a given program may again have specific requirements to other installed programs/packages, or dependencies to specific operating system components. "
    },
    {
      "block_id": "P1-S04-p01",
      "quote": "To ensure future availability, the only viable solution may then be to store a full virtual machine image of the operating system and program. "
    },
    {
      "block_id": "P1-S04-p01",
      "quote": "As a minimum, you should note the exact names and versions of the main programs you use."
    }
  ]
}

```

{
  "groups": {
    "original": {
      "denominator": 3,
      "format_complete": 3,
      "model_relation_correct": "not_applicable",
      "mapping_consistency": "not_applicable",
      "external_label_correct": 0,
      "reason_relation_or_label_consistent": 0,
      "source_authenticity": 3,
      "necessary_coverage": 1,
      "citation_support": 0,
      "strict_complete_success": 0,
      "budget_exhausted": 0,
      "client_seconds": 66.10218640021048,
      "output_tokens": 397
    },
    "revised": {
      "denominator": 3,
      "format_complete": 3,
      "model_relation_correct": 0,
      "mapping_consistency": 3,
      "external_label_correct": 0,
      "reason_relation_or_label_consistent": 3,
      "source_authenticity": 3,
      "necessary_coverage": 1,
      "citation_support": 0,
      "strict_complete_success": 0,
      "budget_exhausted": 0,
      "client_seconds": 66.97819519997574,
      "output_tokens": 322
    }
  },
  "decision": {
    "at": "2026-10-16T16:59:58.267379+08:00",
    "adopt_relation_single": false,
    "retain_current_sentence_selection": true,
    "reason": "严格成功均0/3，外部标签正确均0/3，引用支持均0/3；同分保留旧流程。单关系加映射消除了独立双字段矛盾，却没有提高语义正确性。",
    "existing_correct_items_regressed": 0,
    "history_replay_limit": "历史relation-first的AD02映射后标签正确，不代表本轮新生成还输出同一relation；本轮实际为undetermined，不能拼接历史较好结果。",
    "mapping_not_semantic": "3/3映射一致只是程序枚举映射正确，不是原文关系或引用支持正确。候选理由与关系可表面一致但事实/推断错误，原样保留。",
    "prior_decisions_preserved": true,
    "stop": "本轮结束，不追加生成或提示优化，不读七道评测。",
    "new_generations": 6,
    "cumulative": 591,
    "A_used": 57,
    "A_cap": 90,
    "A_remaining": 33,
    "technical_request_failures": 0,
    "quality_retries": 0
  }
}
