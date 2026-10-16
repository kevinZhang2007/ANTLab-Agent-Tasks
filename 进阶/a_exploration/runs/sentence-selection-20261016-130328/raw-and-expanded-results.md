# 句子选择固定证据诊断：原始内部响应与展开分开

复核时间：2026-10-16T13:10:45.851182+08:00

Codex辅助原文复核，尚待本人确认。新侧quote由程序依模型所选sentence_id逐字展开，不是模型生成，不构成语义证明。


## AD01 original

模型原始输出：

```json

{
  "label": "insufficient",
  "reason": "The passage does not provide sufficient evidence to confirm or deny the claim. The evidence includes rules about documentation requirements and avoiding manual data manipulation, but there is no explicit statement that addresses whether manual modifications are avoided or if saving files without recording details is acceptable.",
  "evidence": []
}

```

客户端耗时6.471秒；输入796 tokens；输出72 tokens；结束stop。

原输入已有P1-S03末句对不可避免手工操作仍要求记录文件及目的；回复insufficient与缺说明理由表面一致，但事实基础错误，空引用不支持拒判。


## AD01 revised

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

客户端耗时21.966秒；输入2332 tokens；输出165 tokens；结束stop。

程序展开的接口内容（local_rule；label/reason原样，quote不是模型抄写）：

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

模型选全部11个片段，包含P1-S03末句的明确记录要求；来源真且必要反证覆盖，但实际label为supported，reason改成保存最终文件加完整可执行流程这一不同主张。其他手工流程片段多为相关冗余，不把全部冗余一概标成无关；不能用直接反证支持无需记录。


## AD02 revised

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

客户端耗时20.256秒；输入2628 tokens；输出85 tokens；结束stop。

程序展开的接口内容（local_rule；label/reason原样，quote不是模型抄写）：

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

sentence_ids选中的是怎样访问/运行/探索这一问句，以及Binder运行环境句；没有选静态HTML/PDF用于Read的句子。理由称仅此不足与原主张冲突，但原主张恰为仅此不足，方向判断自相矛盾；contradicted及引用支持均失败。


## AD02 original

模型原始输出：

```json

{
  "label": "insufficient",
  "reason": "The claim cannot be fully supported by the given passages, as they primarily discuss how to support others’ reuse of notebooks but do not explicitly state that static HTML/PDF or static views via GitHub are sufficient for execution.",
  "evidence": []
}

```

客户端耗时6.068秒；输入842 tokens；输出65 tokens；结束stop。

已有Read/Run完整原段，原主张仅此不足执行，回复却要求原文明示静态导出足以执行才支持，否定方向错误；空引用。


## AD03 original

模型原始输出：

```json

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

客户端耗时8.145秒；输入771 tokens；输出145 tokens；结束stop。

真实引用为程序归档及HTML层次结果，不支持只存最终图。实际输入没有图底层数据章节，应保留缺证边界；不能借不可见参考原文补证。


## AD03 revised

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

客户端耗时26.092秒；输入2883 tokens；输出147 tokens；结束stop。

程序展开的接口内容（local_rule；label/reason原样，quote不是模型抄写）：

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

选中8个片段均来自程序版本/依赖归档P1-S04，不是图底层数据证据。理由将科学绘图变成graphic design及版本可用性另一主张。所选文本真实不代表支持原始只存最终图断言。

{
  "groups": {
    "original": {
      "denominator": 3,
      "format_complete": 3,
      "budget_exhausted": 0,
      "label_correct": 0,
      "label_not_checked": 0,
      "nonempty_source_authenticity": 1,
      "necessary_evidence_coverage": 0,
      "citation_support": 0,
      "strict_complete_success": 0,
      "model_request_seconds": 20.683803299907595,
      "output_tokens": 282
    },
    "revised": {
      "denominator": 3,
      "format_complete": 3,
      "budget_exhausted": 0,
      "label_correct": 0,
      "label_not_checked": 0,
      "nonempty_source_authenticity": 3,
      "necessary_evidence_coverage": 1,
      "citation_support": 0,
      "strict_complete_success": 0,
      "model_request_seconds": 68.31423379993066,
      "output_tokens": 397
    }
  },
  "decision": {
    "adopt": false,
    "reason": "两侧完整JSON均3/3，无预算耗尽；标签正确与严格成功均0/3。句子ID展开保证已选引用来源真实，新侧3/3来源验证通过，但未改善语义判断且调用更慢，按同分保留旧流程。",
    "limits": [
      "新增句子索引使输入变长；同256预算不意味着总token或时延相同，不能归因于纯输出长度。",
      "AD01把全部11片段选入，不是精确必要证据选择；含正确反证不等于支持当前错误label。",
      "程序没有添加未选句子，没有改label或reason，没有语义补证。",
      "对外接口记录由离线适配生成，未做新页面/HTTP端到端接入验证。",
      "不能把源码要求的步骤声称为模型确实执行了内部核对。"
    ],
    "future": "本轮停止，不追加调用；七道评测仍取消。"
  }
}
