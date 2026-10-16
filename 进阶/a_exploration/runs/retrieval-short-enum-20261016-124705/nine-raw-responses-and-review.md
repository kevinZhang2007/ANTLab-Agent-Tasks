# 整体候选九条原始响应及复核

实际复核时间：2026-10-16T12:55:36.319554+08:00

仅三道开发题自动流程；Codex辅助原文复核，尚待本人确认。残缺JSON原样保留，不补字段或从前缀计标签成功。


## AD01 共享查询

```json

{"terms":"save, modify, file, object, purpose"}

```

run ID: 5cc189eb-cdf7-4cb6-a0b6-e8bf1e4b62bf；0.975秒。


### baseline 原始content

```text

{
  "label": "supported",
  "reason": "Rule 2 explicitly states that manual data manipulation is not advisable and recommends using automated tools to avoid errors. Rule 3 emphasizes storing exact program versions to ensure reproducibility, which aligns with the claim that final files should be saved regardless of manual modifications.",
  "evidence": [
    {
      "block_id": "P1-S03-p01",
      "quote": "If working at the UNIX command line, manual modification of files can usually be replaced by the use of standard UNIX commands or small custom scripts."
    },
    {
      "block_id": "P1-S04-p01",
      "quote": "In order to exactly reproduce a given result, it may be necessary to use programs in the exact versions used originally."
    }
  ]
}

```

两侧都含完整P1-S03末句，要求人工操作不可避免时仍记录对象和目的。模型只据避免手工操作/保存程序版本来支持无需记录；后者无关。两个摘录确属对应原文，但不支持当前label。

run ID: be1b7c00-7c03-4534-9d0a-da56501bdc97；客户端8.111秒；结束stop。


### improved 原始content

```text

{
  "label": "supported",
  "reason": "Rule 2 explicitly states that manual data manipulation is not advisable and recommends using automated tools to avoid errors. Rule 3 emphasizes storing exact program versions to ensure reproducibility, which aligns with the claim that final files should be saved regardless of manual modifications.",
  "evidence": [
    {
      "block_id": "P1-S03-p01",
      "quote": "If working at the UNIX command line, manual modification of files can usually be replaced by the use of standard UNIX commands or small custom scripts."
    },
    {
      "block_id": "P1-S04-p01",
      "quote": "In order to exactly reproduce a given result, it may be necessary to use programs in the exact versions used originally."
    }
  ]
}

```

两侧都含完整P1-S03末句，要求人工操作不可避免时仍记录对象和目的。模型只据避免手工操作/保存程序版本来支持无需记录；后者无关。两个摘录确属对应原文，但不支持当前label。

run ID: 99d772c0-5733-4aec-b2a8-c3b0d29ae3df；客户端11.050秒；结束stop。


## AD02 共享查询

```json

{"terms":"notebook export, static HTML/PDF, help read, execute calculation"}

```

run ID: 6665814c-e192-4104-b5d3-9ae91dd8a424；0.972秒。


### baseline 原始content

```text

{
  "label": "supported",
  "reason": "The passage supports the claim that exporting notebooks as HTML or PDF helps readers access content, but it also highlights that this is not sufficient for execution and sharing.",
  "evidence": [
    {
      "block_id": "P2-S01-p04",
      "quote": "Read: Beyond granting permission to reuse your notebook, consider how you can leverage the unique structure of notebooks to support reading. At the very least, leave static HTML/PDF versions of all notebooks stored in the final version of the repository accompanying a publication."
    },
    {
      "block_id": "P2-S10-p02",
      "quote": "You can also use Nbviewer ( https://nbviewer.jupyter.org/ ) to provide static views of your executed notebook online without needing to convert it to a PDF/HTML document first. GitHub uses this service to render any notebooks on their site, so pushing a notebook to GitHub is another good way to make static views easily available."
    }
  ]
}

```

label与参考一致，理由大体保持有助阅读但不足执行。第一条quote来自实际P2-S10-p02，却标为P2-S01-p04；不能修ID后算通过。基线只有Read与概览，Read也提依赖清单/重建环境，是否单段已足够支持全部运行限制有解释边界，输入覆盖单列待确认，不按固定ID强制缺证。

run ID: 2f88ee1a-2e79-4eac-bd4b-379cfdf87df3；客户端9.103秒；结束stop。


### improved 原始content

```text

{
  "label": "supported",
  "reason": "The passage supports the claim that exporting notebooks as static HTML or PDF does not fully solve the problem of reusing them, as it highlights the need for additional steps like storing in public repositories, using tools like Nbviewer, and setting up a zero-install environment (e.g., Binder). These measures are necessary to ensure readability, reproducibility, and accessibility.",
  "evidence": [
    {
      "block_id": "P2-S01-p03",
      "quote": "Analyses documented in notebooks cannot be easily rerun if users do not first freeze their dependencies, share their data, and adequately describe their computing environment [ 13 ]."
    },
    {
      "block_id": "P2-S10-p01",
      "quote": "Store your notebooks in a public code repository with a clear README file and a liberal open source license ( https://opensource.org/licenses ) granting permission to reuse your code."
    },
    {
      "block_id": "P2-S10-p02",
      "quote": "Use Nbviewer to provide static views of your executed notebook online without needing to convert it to a PDF/HTML document first."
    },


```

补邻段取得明确执行依赖(P2-S01-p03)及Run完整原文；但输出256 token耗尽，第三个evidence后未闭合。不得抽取supported前缀判答案成功。片段还把Store与Use等改写成原句，局部风险另记，不冒充完整字段评价。

run ID: 9590bbd6-54eb-4b12-90a1-00d01adb9ccb；客户端15.548秒；结束length。


## AD03 共享查询

```json

{"terms":"data conversion, final image, author's recommendation"}

```

run ID: a098b4ad-fc2f-44fb-9a66-fc8820a41ddf；1.214秒。


### baseline 原始content

```text

{
  "label": "supported",
  "reason": "绘图过程中做过数据转换时，只保留最终图片就满足作者关于图底层数据的建议。根据规则3和规则8，只有在必要时保留原始程序版本文件，并通过系统化命名来确保数据可访问。",
  "evidence": [
    {
      "block_id": "P1-S04-p01",
      "quote": "In order to exactly reproduce a given result, it may be necessary to use programs in the exact versions used originally. Also, as both input and output formats may change between versions, a newer version of a program may not even run without modifying its inputs. Even having noted which version was used of a given program, it is not always trivial to get hold of a program in anything but the current version. Archiving the exact versions of programs actually saves a lot of hassle at later stages."
    },
    {
      "block_id": "P1-S09-p01",
      "quote": "We find hypertext (i.e., html file output) to be particularly useful for this purpose. This allows summarized results to be generated along with links that can be very conveniently followed (by simply clicking)

```

新查询仍未出现plot/plotting等具体对象，只有data/conversion/final/image及author's recommendation；必要图数据章节仍未命中，无同章节邻段。两侧请求及原始输出相同，均在第二个quote中途耗尽256预算，完整语义字段not_checked。可见前缀仍用程序版本/层次输出解释只存图，不能用不可见图数据原文补证。

run ID: cf948e31-15fb-4d7c-8357-38bd0e416c92；客户端10.374秒；结束length。


### improved 原始content

```text

{
  "label": "supported",
  "reason": "绘图过程中做过数据转换时，只保留最终图片就满足作者关于图底层数据的建议。根据规则3和规则8，只有在必要时保留原始程序版本文件，并通过系统化命名来确保数据可访问。",
  "evidence": [
    {
      "block_id": "P1-S04-p01",
      "quote": "In order to exactly reproduce a given result, it may be necessary to use programs in the exact versions used originally. Also, as both input and output formats may change between versions, a newer version of a program may not even run without modifying its inputs. Even having noted which version was used of a given program, it is not always trivial to get hold of a program in anything but the current version. Archiving the exact versions of programs actually saves a lot of hassle at later stages."
    },
    {
      "block_id": "P1-S09-p01",
      "quote": "We find hypertext (i.e., html file output) to be particularly useful for this purpose. This allows summarized results to be generated along with links that can be very conveniently followed (by simply clicking)

```

新查询仍未出现plot/plotting等具体对象，只有data/conversion/final/image及author's recommendation；必要图数据章节仍未命中，无同章节邻段。两侧请求及原始输出相同，均在第二个quote中途耗尽256预算，完整语义字段not_checked。可见前缀仍用程序版本/层次输出解释只存图，不能用不可见图数据原文补证。

run ID: 22d2f504-f178-4f9f-b15d-f9e75bc8120c；客户端10.522秒；结束length。

{
  "groups": {
    "baseline": {
      "denominator": 3,
      "definite_input_coverage": 1,
      "ambiguous_input_coverage": 1,
      "format_complete": 2,
      "label_correct": 1,
      "label_not_checked": 1,
      "id_valid_complete_outputs": 2,
      "authentic_nonempty_quote_outputs": 1,
      "necessary_citation_coverage": 0,
      "citation_support": 0,
      "semantic_support_not_checked": 1,
      "strict_complete_success": 0,
      "budget_exhausted": 1,
      "answer_http_seconds": 27.587497900007293,
      "allocated_total_seconds": 29.97882135026157,
      "old_group": {
        "denominator": 3,
        "format_complete": 3,
        "answer_correct": 0,
        "semantic_consistent": 0,
        "id_membership_check": 3,
        "nonempty_references": 2,
        "necessary_input_coverage": 1,
        "necessary_cited_coverage": 0,
        "citation_support_actual_judgment": 0,
        "has_unrelated_citations": 1,
        "strict_complete_success": 0,
        "locator_valid_tasks": 1,
        "answer_http_total_seconds": 21.32179700001143,
        "allocated_total_seconds": 23.81139540008735
      }
    },
    "improved": {
      "denominator": 3,
      "definite_input_coverage": 2,
      "ambiguous_input_coverage": 0,
      "format_complete": 1,
      "label_correct": 0,
      "label_not_checked": 2,
      "id_valid_complete_outputs": 1,
      "authentic_nonempty_quote_outputs": 1,
      "necessary_citation_coverage": 0,
      "citation_support": 0,
      "semantic_support_not_checked": 2,
      "strict_complete_success": 0,
      "budget_exhausted": 2,
      "answer_http_seconds": 37.119571099756286,
      "allocated_total_seconds": 39.963998050196096,
      "old_group": {
        "denominator": 3,
        "format_complete": 3,
        "answer_correct": 0,
        "semantic_consistent": 0,
        "id_membership_check": 3,
        "nonempty_references": 1,
        "necessary_input_coverage": 2,
        "necessary_cited_coverage": 0,
        "citation_support_actual_judgment": 0,
        "has_unrelated_citations": 1,
        "strict_complete_success": 0,
        "locator_valid_tasks": 1,
        "answer_http_total_seconds": 18.48617439996451,
        "allocated_total_seconds": 21.031955699785613
      }
    }
  },
  "decision": {
    "strict_success_improvement": false,
    "baseline_secondary_label_improvement": "按预先的次级指标，baseline有效标签由0/3到1/3；但这一题引用归属失败，不能算严格成功。",
    "improved_arm": "完整有效标签正确与严格成功仍0/3且2条not_checked；同分保留旧侧，格式从3/3降至1/3。",
    "common_flow_adoption": "两侧共同流程不能分别挑选有利结果。本轮不自动替换原入口：仅baseline次级标签改善，邻段侧无收益且格式退步；保留整体候选及负面结果供本人决定，不声称整体胜出。",
    "quality_regressions": "完整JSON总数由6/6降至3/6，出现3次输出预算耗尽；没有输入截断。",
    "mechanism_limits": "检索词提示、短判断和动态ID enum共同改变，不能独立归因；enum防止未知ID但没防住合法ID下的错误摘录归属、改写或语义错误。",
    "no_more_search": true,
    "AT_not_read": true,
    "no_formal_freeze": true,
    "3B_cancelled": true
  }
}
