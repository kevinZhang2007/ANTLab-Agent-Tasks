# 三道开发题离线诊断

实际核对时间：2026-10-16T12:22:25.556828+08:00

只使用开发材料；以下原始输出未改写。参考只用于诊断与评价。


## AD01

主张：当手工修改或移动数据文件确实无法避免时，只要保存最终文件，无需记录修改对象和目的。

doc_ids：["P1"]

共享检索词：handwritten file modification, save final file, record modification object and purpose


### baseline实际完整证据

```json

[
  {
    "block_id": "P1-S02-p03",
    "doc_id": "P1",
    "snapshot": "published",
    "section_id": "P1-S02",
    "heading": "Rule 1: For Every Result, Keep Track of How It Was Produced",
    "paragraph_index": 2,
    "text": "As a minimum, you should at least record sufficient details on programs, parameters, and manual procedures to allow yourself, in a year or so, to approximately reproduce the results."
  },
  {
    "block_id": "P1-S03-p01",
    "doc_id": "P1",
    "snapshot": "published",
    "section_id": "P1-S03",
    "heading": "Rule 2: Avoid Manual Data Manipulation Steps",
    "paragraph_index": 0,
    "text": "Whenever possible, rely on the execution of programs instead of manual procedures to modify data. Such manual procedures are not only inefficient and error-prone, they are also difficult to reproduce. If working at the UNIX command line, manual modification of files can usually be replaced by the use of standard UNIX commands or small custom scripts. If working with integrated frameworks, there will typically be a quite rich collection of components for data manipulation. As an example, manual tweaking of data files to attain format compatibility should be replaced by format converters that can be reenacted and included into executable workflows. Other manual operations like the use of copy and paste between documents should also be avoided. If manual operations cannot be avoided, you should as a minimum note down which data files were modified or moved, and for what purpose."
  }
]

```

模型原始输出：

```json

{
  "label": "supported",
  "reason": "The claim is supported by the passage that states 'you should at least record sufficient details on programs, parameters, and manual procedures to allow yourself, in a year or so, to approximately reproduce the results.' Additionally, it mentions avoiding manual data manipulation steps and noting modifications when necessary.",
  "evidence": [
    {
      "block_id": "P1-S02-p03",
      "quote": "As a minimum, you should at least record sufficient details on programs, parameters, and manual procedures to allow yourself, in a year or so, to approximately reproduce the results."
    },
    {
      "block_id": "P1-S03-p01",
      "quote": "If working at the UNIX command line, manual modification of files can usually be replaced by the use of standard UNIX commands or small custom scripts. If working with integrated frameworks, there will typically be a quite rich collection of components for data manipulation."
    }
  ]
}

```


### improved实际完整证据

```json

[
  {
    "block_id": "P1-S02-p02",
    "doc_id": "P1",
    "snapshot": "published",
    "section_id": "P1-S02",
    "heading": "Rule 1: For Every Result, Keep Track of How It Was Produced",
    "paragraph_index": 1,
    "text": "Although manually noting the precise sequence of steps taken allows for an analysis to be reproduced, the documentation can easily get out of sync with how the analysis was really performed in its final version. By instead specifying the full analysis workflow in a form that allows for direct execution, one can ensure that the specification matches the analysis that was (subsequently) performed, and that the analysis can be reproduced by yourself or others in an automated way. Such executable descriptions [10] might come in the form of simple shell scripts or makefiles [15] , [16] at the command line, or in the form of stored workflows in a workflow management system [10] , [11] , [13] , [17] , [18] ."
  },
  {
    "block_id": "P1-S02-p03",
    "doc_id": "P1",
    "snapshot": "published",
    "section_id": "P1-S02",
    "heading": "Rule 1: For Every Result, Keep Track of How It Was Produced",
    "paragraph_index": 2,
    "text": "As a minimum, you should at least record sufficient details on programs, parameters, and manual procedures to allow yourself, in a year or so, to approximately reproduce the results."
  },
  {
    "block_id": "P1-S03-p01",
    "doc_id": "P1",
    "snapshot": "published",
    "section_id": "P1-S03",
    "heading": "Rule 2: Avoid Manual Data Manipulation Steps",
    "paragraph_index": 0,
    "text": "Whenever possible, rely on the execution of programs instead of manual procedures to modify data. Such manual procedures are not only inefficient and error-prone, they are also difficult to reproduce. If working at the UNIX command line, manual modification of files can usually be replaced by the use of standard UNIX commands or small custom scripts. If working with integrated frameworks, there will typically be a quite rich collection of components for data manipulation. As an example, manual tweaking of data files to attain format compatibility should be replaced by format converters that can be reenacted and included into executable workflows. Other manual operations like the use of copy and paste between documents should also be avoided. If manual operations cannot be avoided, you should as a minimum note down which data files were modified or moved, and for what purpose."
  }
]

```

模型原始输出：

```json

{
  "label": "insufficient",
  "reason": "The passage does not provide sufficient evidence to confirm or deny the claim. The evidence includes rules about documentation requirements and avoiding manual data manipulation, but there is no explicit statement that addresses whether manual modifications are avoided or if saving files without recording details is acceptable.",
  "evidence": []
}

```


### 公开参考原文与限定

```json

[
  {
    "block_id": "P1-S03-p01",
    "doc_id": "P1",
    "snapshot": "published",
    "section_id": "P1-S03",
    "heading": "Rule 2: Avoid Manual Data Manipulation Steps",
    "paragraph_index": 0,
    "text": "Whenever possible, rely on the execution of programs instead of manual procedures to modify data. Such manual procedures are not only inefficient and error-prone, they are also difficult to reproduce. If working at the UNIX command line, manual modification of files can usually be replaced by the use of standard UNIX commands or small custom scripts. If working with integrated frameworks, there will typically be a quite rich collection of components for data manipulation. As an example, manual tweaking of data files to attain format compatibility should be replaced by format converters that can be reenacted and included into executable workflows. Other manual operations like the use of copy and paste between documents should also be avoided. If manual operations cannot be avoided, you should as a minimum note down which data files were modified or moved, and for what purpose."
  }
]

```

参考标签：contradicted

retrieval：两侧均含必要原文，无检索遗漏。

qualifiers：原文有人工操作无法避免时的例外及最低记录要求；主张把无需记录说成足够。

judgment：baseline支持却在理由中复述要记录；improved声称没有明确说明，均未正确对照否定方向。

citations：baseline摘录真实，但没有引用句末直接冲突条件；improved为空。

reference_limit：contradicted针对无需记录，不把原文解读为绝对禁止人工操作。

ambiguity：未发现影响标签的实质歧义。


## AD02

主张：把Notebook导出为静态HTML或PDF，可以帮助他人阅读，但仅此不足以让他人执行原计算。

doc_ids：["P2"]

共享检索词：notebook export, static HTML/PDF, help others read, execute original calculations


### baseline实际完整证据

```json

[
  {
    "block_id": "P2-S10-p01",
    "doc_id": "P2",
    "snapshot": "published",
    "section_id": "P2-S10",
    "heading": "Rule 9: Design your notebooks to be read, run, and explored",
    "paragraph_index": 0,
    "text": "If you have followed the previous rules, your notebooks should capture your entire process and be easy to read. But how will others access, run, and explore them? There are a number of ways you can support others’ reuse of your notebooks. First, store your notebooks in a public code repository with a clear README file and a liberal open source license ( https://opensource.org/licenses ) granting permission to reuse your code."
  },
  {
    "block_id": "P2-S10-p02",
    "doc_id": "P2",
    "snapshot": "published",
    "section_id": "P2-S10",
    "heading": "Rule 9: Design your notebooks to be read, run, and explored",
    "paragraph_index": 1,
    "text": "Read: Beyond granting permission to reuse your notebook, consider how you can leverage the unique structure of notebooks to support reading. At the very least, leave static HTML/PDF versions of all notebooks stored in the final version of the repository accompanying a publication. If, in 20 years, all other execution technology fails, these are likely to still provide a readable archival record, and with a full dependences list, future users are more likely to be able to recreate the compute environment. You can also use Nbviewer ( https://nbviewer.jupyter.org/ ) to provide static views of your executed notebook online without needing to convert it to a PDF/HTML document first. GitHub uses this service to render any notebooks on their site, so pushing a notebook to GitHub is another good way to make static views easily available. In both cases, you can point collaborators to a URL where they can read through your notebook online."
  }
]

```

模型原始输出：

```json

{
  "label": "insufficient",
  "reason": "资料中未明确说明是否足以让他人执行原计算，仅提到存储方式和静态HTML/PDF的可用性，但未涉及具体执行计算的技术或方法。",
  "evidence": []
}

```


### improved实际完整证据

```json

[
  {
    "block_id": "P2-S10-p01",
    "doc_id": "P2",
    "snapshot": "published",
    "section_id": "P2-S10",
    "heading": "Rule 9: Design your notebooks to be read, run, and explored",
    "paragraph_index": 0,
    "text": "If you have followed the previous rules, your notebooks should capture your entire process and be easy to read. But how will others access, run, and explore them? There are a number of ways you can support others’ reuse of your notebooks. First, store your notebooks in a public code repository with a clear README file and a liberal open source license ( https://opensource.org/licenses ) granting permission to reuse your code."
  },
  {
    "block_id": "P2-S10-p02",
    "doc_id": "P2",
    "snapshot": "published",
    "section_id": "P2-S10",
    "heading": "Rule 9: Design your notebooks to be read, run, and explored",
    "paragraph_index": 1,
    "text": "Read: Beyond granting permission to reuse your notebook, consider how you can leverage the unique structure of notebooks to support reading. At the very least, leave static HTML/PDF versions of all notebooks stored in the final version of the repository accompanying a publication. If, in 20 years, all other execution technology fails, these are likely to still provide a readable archival record, and with a full dependences list, future users are more likely to be able to recreate the compute environment. You can also use Nbviewer ( https://nbviewer.jupyter.org/ ) to provide static views of your executed notebook online without needing to convert it to a PDF/HTML document first. GitHub uses this service to render any notebooks on their site, so pushing a notebook to GitHub is another good way to make static views easily available. In both cases, you can point collaborators to a URL where they can read through your notebook online."
  },
  {
    "block_id": "P2-S10-p03",
    "doc_id": "P2",
    "snapshot": "published",
    "section_id": "P2-S10",
    "heading": "Rule 9: Design your notebooks to be read, run, and explored",
    "paragraph_index": 2,
    "text": "Run: To support others running your notebooks, you can use Binder [ 16 ] to provide a zero-install environment to run your notebooks in the cloud ( https://mybinder.org/ ). Binder enables community members to rerun your notebook online without needing to install Jupyter Notebook or Jupyter Lab on their own machine. More generally, you can create a portable containerized environment, for example, a Docker image ( https://docs.docker.com/ ), or create a dependency description file (see Rule 3 ) so future users of your notebook can more easily replicate your computing environment when rerunning your notebook."
  }
]

```

模型原始输出：

```json

{
  "label": "insufficient",
  "reason": "The claim cannot be fully supported by the given passages, as they primarily discuss how to support others’ reuse of notebooks but do not explicitly state that static HTML/PDF or static views via GitHub are sufficient for execution.",
  "evidence": []
}

```


### 公开参考原文与限定

```json

[
  {
    "block_id": "P2-S10-p01",
    "doc_id": "P2",
    "snapshot": "published",
    "section_id": "P2-S10",
    "heading": "Rule 9: Design your notebooks to be read, run, and explored",
    "paragraph_index": 0,
    "text": "If you have followed the previous rules, your notebooks should capture your entire process and be easy to read. But how will others access, run, and explore them? There are a number of ways you can support others’ reuse of your notebooks. First, store your notebooks in a public code repository with a clear README file and a liberal open source license ( https://opensource.org/licenses ) granting permission to reuse your code."
  },
  {
    "block_id": "P2-S10-p02",
    "doc_id": "P2",
    "snapshot": "published",
    "section_id": "P2-S10",
    "heading": "Rule 9: Design your notebooks to be read, run, and explored",
    "paragraph_index": 1,
    "text": "Read: Beyond granting permission to reuse your notebook, consider how you can leverage the unique structure of notebooks to support reading. At the very least, leave static HTML/PDF versions of all notebooks stored in the final version of the repository accompanying a publication. If, in 20 years, all other execution technology fails, these are likely to still provide a readable archival record, and with a full dependences list, future users are more likely to be able to recreate the compute environment. You can also use Nbviewer ( https://nbviewer.jupyter.org/ ) to provide static views of your executed notebook online without needing to convert it to a PDF/HTML document first. GitHub uses this service to render any notebooks on their site, so pushing a notebook to GitHub is another good way to make static views easily available. In both cases, you can point collaborators to a URL where they can read through your notebook online."
  },
  {
    "block_id": "P2-S10-p03",
    "doc_id": "P2",
    "snapshot": "published",
    "section_id": "P2-S10",
    "heading": "Rule 9: Design your notebooks to be read, run, and explored",
    "paragraph_index": 2,
    "text": "Run: To support others running your notebooks, you can use Binder [ 16 ] to provide a zero-install environment to run your notebooks in the cloud ( https://mybinder.org/ ). Binder enables community members to rerun your notebook online without needing to install Jupyter Notebook or Jupyter Lab on their own machine. More generally, you can create a portable containerized environment, for example, a Docker image ( https://docs.docker.com/ ), or create a dependency description file (see Rule 3 ) so future users of your notebook can more easily replicate your computing environment when rerunning your notebook."
  },
  {
    "block_id": "P2-S10-p04",
    "doc_id": "P2",
    "snapshot": "published",
    "section_id": "P2-S10",
    "heading": "Rule 9: Design your notebooks to be read, run, and explored",
    "paragraph_index": 3,
    "text": "Explore: Beyond simply replicating the analysis in your notebook, consider how you can design your notebook so future users can tweak and explore your analysis. Consider using ipywidgets ( https://ipywidgets.readthedocs.io/en/stable/ ) to enable future users to change parameters using graphical elements such as dropdowns and sliders rather than tweaking code. Beyond enabling future users to change parameters or insert their own data set, consider how they might want remix or reuse portions of your notebook (perhaps only the data cleaning or plotting steps) and use cell-structure and functions to make it easier to extract these sections (Rule 7)."
  }
]

```

参考标签：supported

retrieval：baseline缺Run段，improved已含Read与Run。

qualifiers：静态可读记录与执行环境是两种用途；主张含仅此不足这一限制。

judgment：improved理由把待验证内容改成静态HTML足以执行，出现否定方向改变。

citations：两侧均无引用，不能算支持成功。

reference_limit：原文区分Read/Run并提出执行环境；不是证明静态导出在任何附带条件下都绝对不能参与执行。

ambiguity：不足以独自保证运行来自Read/Run用途及环境条件的组合解释，非逐字原句；保留推导边界。


## AD03

主张：绘图过程中做过数据转换时，只保留最终图片就满足作者关于图底层数据的建议。

doc_ids：["P1"]

共享检索词：data conversion, final image


### baseline实际完整证据

```json

[
  {
    "block_id": "P1-S04-p01",
    "doc_id": "P1",
    "snapshot": "published",
    "section_id": "P1-S04",
    "heading": "Rule 3: Archive the Exact Versions of All External Programs Used",
    "paragraph_index": 0,
    "text": "In order to exactly reproduce a given result, it may be necessary to use programs in the exact versions used originally. Also, as both input and output formats may change between versions, a newer version of a program may not even run without modifying its inputs. Even having noted which version was used of a given program, it is not always trivial to get hold of a program in anything but the current version. Archiving the exact versions of programs actually used may thus save a lot of hassle at later stages. In some cases, all that is needed is to store a single executable or source code file. In other cases, a given program may again have specific requirements to other installed programs/packages, or dependencies to specific operating system components. To ensure future availability, the only viable solution may then be to store a full virtual machine image of the operating system and program. As a minimum, you should note the exact names and versions of the main programs you use."
  },
  {
    "block_id": "P1-S09-p01",
    "doc_id": "P1",
    "snapshot": "published",
    "section_id": "P1-S09",
    "heading": "Rule 8: Generate Hierarchical Analysis Output, Allowing Layers of Increasing Detail to Be Inspected",
    "paragraph_index": 0,
    "text": "The final results that make it to an article, be it plots or tables, often represent highly summarized data. For instance, each value along a curve may in turn represent averages from an underlying distribution. In order to validate and fully understand the main result, it is often useful to inspect the detailed values underlying the summaries. A common but impractical way of doing this is to incorporate various debug outputs in the source code of scripts and programs. When the storage context allows, it is better to simply incorporate permanent output of all underlying data when a main result is generated, using a systematic naming convention to allow the full data underlying a given summarized value to be easily found. We find hypertext (i.e., html file output) to be particularly useful for this purpose. This allows summarized results to be generated along with links that can be very conveniently followed (by simply clicking) to the full data underlying each summarized value. When working with summarized results, you should as a minimum at least once generate, inspect, and validate the detailed values underlying the summaries."
  }
]

```

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


### improved实际完整证据

```json

[
  {
    "block_id": "P1-S04-p01",
    "doc_id": "P1",
    "snapshot": "published",
    "section_id": "P1-S04",
    "heading": "Rule 3: Archive the Exact Versions of All External Programs Used",
    "paragraph_index": 0,
    "text": "In order to exactly reproduce a given result, it may be necessary to use programs in the exact versions used originally. Also, as both input and output formats may change between versions, a newer version of a program may not even run without modifying its inputs. Even having noted which version was used of a given program, it is not always trivial to get hold of a program in anything but the current version. Archiving the exact versions of programs actually used may thus save a lot of hassle at later stages. In some cases, all that is needed is to store a single executable or source code file. In other cases, a given program may again have specific requirements to other installed programs/packages, or dependencies to specific operating system components. To ensure future availability, the only viable solution may then be to store a full virtual machine image of the operating system and program. As a minimum, you should note the exact names and versions of the main programs you use."
  },
  {
    "block_id": "P1-S09-p01",
    "doc_id": "P1",
    "snapshot": "published",
    "section_id": "P1-S09",
    "heading": "Rule 8: Generate Hierarchical Analysis Output, Allowing Layers of Increasing Detail to Be Inspected",
    "paragraph_index": 0,
    "text": "The final results that make it to an article, be it plots or tables, often represent highly summarized data. For instance, each value along a curve may in turn represent averages from an underlying distribution. In order to validate and fully understand the main result, it is often useful to inspect the detailed values underlying the summaries. A common but impractical way of doing this is to incorporate various debug outputs in the source code of scripts and programs. When the storage context allows, it is better to simply incorporate permanent output of all underlying data when a main result is generated, using a systematic naming convention to allow the full data underlying a given summarized value to be easily found. We find hypertext (i.e., html file output) to be particularly useful for this purpose. This allows summarized results to be generated along with links that can be very conveniently followed (by simply clicking) to the full data underlying each summarized value. When working with summarized results, you should as a minimum at least once generate, inspect, and validate the detailed values underlying the summaries."
  }
]

```

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


### 公开参考原文与限定

```json

[
  {
    "block_id": "P1-S08-p01",
    "doc_id": "P1",
    "snapshot": "published",
    "section_id": "P1-S08",
    "heading": "Rule 7: Always Store Raw Data behind Plots",
    "paragraph_index": 0,
    "text": "From the time a figure is first generated to it being part of a published article, it is often modified several times. In some cases, such modifications are merely visual adjustments to improve readability, or to ensure visual consistency between figures. If raw data behind figures are stored in a systematic manner, so as to allow raw data for a given figure to be easily retrieved, one can simply modify the plotting procedure, instead of having to redo the whole analysis. An additional advantage of this is that if one really wants to read fine values in a figure, one can consult the raw numbers. In cases where plotting involves more than a direct visualization of underlying numbers, it can be useful to store both the underlying data and the processed values that are directly visualized. An example of this is the plotting of histograms, where both the values before binning (original data) and the counts per bin (heights of visualized bars) could be stored. When plotting is performed using a command-based system like R, it is convenient to also store the code used to make the plot. One can then apply slight modifications to these commands, instead of having to specify the plot from scratch. As a minimum, one should note which data formed the basis of a given plot and how this data could be reconstructed."
  }
]

```

参考标签：contradicted

retrieval：两侧都漏P1-S08；命中P1-S04的virtual machine image及P1-S09的HTML用途。

qualifiers：原文建议保留底层数据、处理值，最低要求注明图依据哪些数据及如何重建；不是所有图都必须保留所有中间值。

judgment：把虚拟机/HTML用途当作图底层数据建议，出现对象混淆；缺检索与生成判断同时存在。

citations：两条摘录真实且可定位，但与判断所需图数据依据无关。

reference_limit：contradicted针对仅保留最终图满足建议；can be useful是建议，不强化为无例外强制存储每项数据。

ambiguity：建议强度有限，但仅存图片无法满足末句最低数据重建说明；本次参考标签可由完整段落支持。
