# 关系优先：本轮六条原始输出

Codex辅助原文复核，尚待本人确认；固定自动证据重放，不是端到端成绩。两侧预算均512。


## AD01 original

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

客户端耗时 21.427 秒；输出 165 tokens；结束 stop。

原主张称无需记录；理由却换成最终文件加可执行流程这一不同主张。选中全部11句含末句明确记录要求，覆盖了反证，却不能支持实际supported。

程序按所选句子展开的接口内容：

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

```json

{
  "relation": "entails",
  "explanation": "原文明确指出，当手工修改或移动数据文件确实无法避免时，只要保存最终文件，无需记录修改对象和目的。",
  "sentence_ids": ["sent-0001", "sent-0002", "sent-0003", "sent-0004", "sent-0005", "sent-0006", "sent-0007", "sent-0008", "sent-0009", "sent-0010", "sent-0011"],
  "label": "supported"
}

```

客户端耗时 20.916 秒；输出 145 tokens；结束 stop。

entails/supported内部一致，但解释声称原文明确无需记录，与已选sent-0011的you should as a minimum note down which data files...and for what purpose直接相反。关系与标签都错。

程序按所选句子展开的接口内容：

```json

{
  "label": "supported",
  "reason": "原文明确指出，当手工修改或移动数据文件确实无法避免时，只要保存最终文件，无需记录修改对象和目的。",
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


## AD02 revised

```json

{
  "relation": "entails",
  "explanation": "The passage supports the claim that exporting notebooks as static HTML or PDF can help others read and run them, but this is not sufficient to enable execution of original computations.",
  "sentence_ids": ["sent-0002", "sent-0003"],
  "label": "contradicted"
}

```

客户端耗时 20.041 秒；输出 80 tokens；结束 stop。

对完整实际输入，Read静态档案与Run运行环境组合支持原主张，因此entails方向正确；实际label仍contradicted，关系标签不一致。解释先称帮助read and run又称不足执行，且只选sent-0002/0003这两个泛泛问句/引言，不含静态导出与运行环境证据。不能把正确relation当成最终label成功。

程序按所选句子展开的接口内容：

```json

{
  "label": "contradicted",
  "reason": "The passage supports the claim that exporting notebooks as static HTML or PDF can help others read and run them, but this is not sufficient to enable execution of original computations.",
  "evidence": [
    {
      "block_id": "P2-S10-p01",
      "quote": "But how will others access, run, and explore them? "
    },
    {
      "block_id": "P2-S10-p01",
      "quote": "There are a number of ways you can support others’ reuse of your notebooks. "
    }
  ]
}

```


## AD02 original

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

客户端耗时 19.279 秒；输出 85 tokens；结束 stop。

理由把仅静态导出不足执行视为反驳，原主张本来就说仅此不足；只选访问/运行问句和Binder句，漏掉Read静态导出依据。

程序按所选句子展开的接口内容：

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

客户端耗时 25.582 秒；输出 147 tokens；结束 stop。

只选程序版本/依赖归档前8句，把绘图只存最终图改成graphic design及归档程序的另一主张；真实摘录不支持原主张。

程序按所选句子展开的接口内容：

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

```json

{
  "relation": "entails",
  "explanation": "证据支持了原主张，即在绘图过程中只保留最终图片满足作者关于图底层数据的建议。",
  "sentence_ids": ["sent-0001", "sent-0003", "sent-0005", "sent-0007", "sent-0008", "sent-0016"],
  "label": "supported"
}

```

客户端耗时 22.994 秒；输出 101 tokens；结束 stop。

entails/supported及解释一致，但选中程序归档句和S09检查详细值句；这些不证明只存最终图满足转换后数据保留建议。S09末句还是应检查详细值的依据，不是只留图足够。不可借未输入的S08补引用；即使对S09替代反证的充分性有边界，entails仍不成立。

程序按所选句子展开的接口内容：

```json

{
  "label": "supported",
  "reason": "证据支持了原主张，即在绘图过程中只保留最终图片满足作者关于图底层数据的建议。",
  "evidence": [
    {
      "block_id": "P1-S04-p01",
      "quote": "In order to exactly reproduce a given result, it may be necessary to use programs in the exact versions used originally. "
    },
    {
      "block_id": "P1-S04-p01",
      "quote": "Even having noted which version was used of a given program, it is not always trivial to get hold of a program in anything but the current version. "
    },
    {
      "block_id": "P1-S04-p01",
      "quote": "In some cases, all that is needed is to store a single executable or source code file. "
    },
    {
      "block_id": "P1-S04-p01",
      "quote": "To ensure future availability, the only viable solution may then be to store a full virtual machine image of the operating system and program. "
    },
    {
      "block_id": "P1-S04-p01",
      "quote": "As a minimum, you should note the exact names and versions of the main programs you use."
    },
    {
      "block_id": "P1-S09-p01",
      "quote": "When working with summarized results, you should as a minimum at least once generate, inspect, and validate the detailed values underlying the summaries."
    }
  ]
}

```
