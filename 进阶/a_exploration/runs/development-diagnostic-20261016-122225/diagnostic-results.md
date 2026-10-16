# 人工指定开发证据的诊断结果

核对时间：2026-10-16T12:24:59.586928+08:00

Codex辅助原文复核，尚待本人确认。非自动检索、端到端或独立评测成绩。


## AD01 original

```json

{
  "label": "supported",
  "reason": "资料支持了主张，因为该段落明确指出：当手工修改或移动数据文件确实无法避免时，应记录修改对象和目的。",
  "evidence": [
    {
      "block_id": "P1-S03-p01",
      "quote": "If working at the UNIX command line, manual modification of files can usually be replaced by the use of standard UNIX commands or small custom scripts. If working with integrated frameworks, there will typically be a quite rich collection of components for data manipulation."
    }
  ]
}

```

主张说无需记录；理由却说应记录。所引UNIX替代手工操作片段没有覆盖无法避免时仍须记录的关键句。引用来源属目标文档，但无法支持supported。

客户端耗时 5.044 秒；finish_reason=stop；截断状态=False。


## AD01 revised

```json

{
  "label": "supported",
  "reason": "原文明确指出，当手工修改或移动数据文件无法避免时，应记录修改对象和目的。该主张与原文的逻辑一致。",
  "evidence": [
    {
      "block_id": "P1-S03-p01",
      "quote": "If manual operations cannot be avoided, you should as a minimum note down which data files were modified or moved, and for what purpose."
    }
  ]
}

```

引到了If manual operations cannot be avoided...note down which data files...for what purpose，摘录直接要求记录，与无需记录冲突；理由也说应记录，却标supported。证据覆盖不等于支持当前错误label。

客户端耗时 4.690 秒；finish_reason=stop；截断状态=False。


## AD02 revised

```json

{
  "label": "insufficient",
  "reason": "资料中未明确说明是否足以让他人执行原计算，且主张中的否定方向与原文的条件不完全匹配。",
  "evidence": []
}

```

实际输入已有Read与Run完整段落，回复仍要求逐字说明是否足以执行并称否定不匹配，但没有给出原文冲突或具体缺失条件，空引用。该参考是用途/环境的组合推导，保留解释边界。

客户端耗时 4.822 秒；finish_reason=stop；截断状态=False。


## AD02 original

```json

{
  "label": "insufficient",
  "reason": "资料中未明确说明是否足以让他人执行原计算，仅提到导出为静态HTML/PDF或使用工具如Nbviewer/ Binder 来辅助阅读和运行，但未涉及执行计算本身的能力。",
  "evidence": []
}

```

Read段说明静态HTML/PDF提供readable archival record；Run段另要求运行环境或依赖描述。原主张限定仅此不足执行；回复追问是否足以执行并空引用，未运用组合依据。

客户端耗时 4.459 秒；finish_reason=stop；截断状态=False。


## AD03 original

```json

{
  "label": "supported",
  "reason": "资料明确支持绘图过程中保留最终图片满足作者关于图底层数据的建议，且提供了系统存储原始数据和处理后的可视化数据的例子。",
  "evidence": [
    {
      "block_id": "P1-S08-p01",
      "quote": "An additional advantage of this is that if one really wants to read fine values in a figure, one can consult the raw numbers."
    }
  ]
}

```

完整段落末句As a minimum...note which data...how...reconstructed与只保留最终图片不符。模型引用consult the raw numbers，只覆盖原始数据一种用途，没有覆盖最低记录条件；正确来源不能支持错误supported。

客户端耗时 4.607 秒；finish_reason=stop；截断状态=False。


## AD03 revised

```json

{
  "label": "insufficient",
  "reason": "资料中未明确说明绘图过程中数据转换后是否只保留最终图片以满足作者关于图底层数据的建议。虽然提到了存储原始数据和处理后的可视化结果，但缺乏具体信息来支持该主张。",
  "evidence": []
}

```

完整原文已有底层数据、处理值与最低重建说明，回复承认原文提到存原始数据和处理值但仍insufficient；空引用。can be useful不解读为一切数据都必须无例外存储。

客户端耗时 4.510 秒；finish_reason=stop；截断状态=False。

{
  "H1": "补齐/减少证据干扰仍未让原提示任何一题恢复，所以仅检索遗漏不是完整解释；历史比较非同步，不能量化单独证据效应。",
  "H2": "AD01两侧reason均要求记录但label支持无需记录，AD02继续改变主张方向；完整命题/标签映射错误仍与观察相容。修订提示未改善，不证明内部机制，也不能排除表述、模型限制或其他因素。",
  "decision": "不采用本轮修订提示，原共同提示保持不变；主候选仍仅同章节邻段补全。人工指定证据不计正式方法或端到端成绩。",
  "reference_limits": [
    "AD02是Read/Run用途与环境条件组合推导，不声称任何情形都不能运行静态导出附带的其他材料。",
    "AD03尊重建议强度，反对仅存最终图满足最低数据重建建议，不强制每种绘图都存全部中间值。"
  ],
  "wiring": "实际请求逐项比对：同题仅system追加文字，其余正文、顺序、模型、Schema、采样、256预算相同；未发现接线、范围泄漏或序列化错误。"
}
