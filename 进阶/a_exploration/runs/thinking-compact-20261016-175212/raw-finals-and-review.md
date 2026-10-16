# 开启思考：重复输入与紧凑输入的六次原始结果

三道开发题固定自动improved证据重放，不是端到端检索成绩。所有比较仅基于本轮完整六次，未拼接历史较好输出。

Codex辅助原文复核，尚待本人确认；reasoning不替代最终content判分。


## AD01 repeated

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

输入2328、总输出341 tokens；客户端31.439724秒；结束stop。

原文没有流程描述可豁免记录文件和目的的说法。选0002/0003/0004，漏直接记录要求0011，理由与supported表面一致但事实和引用支持均错。

完整思考：reasoning-01-AD01-repeated.txt


## AD01 compact

```json

{
  "label": "insufficient",
  "reason": "资料中并未明确支持当手工修改文件时无需记录对象和目的，而是强调即使有这些操作也需详细记录程序、参数等信息（如P1-S02-p02中的sent-0004要求至少记录程序细节）。",
  "sentence_ids": ["sent-0004", "sent-0011"]
}

```

输入1036、总输出387 tokens；客户端16.823919秒；结束stop。

选0004和0011已含最低限度细节及明确记录文件/目的的直接反证；必要覆盖改善，但理由自己称仍需记录却给insufficient，仍未判反驳。理由把sent-0004说成P1-S02-p02，实际属于P1-S02-p03；程序展开归属正确，模型自由理由中的归属错误另记，不能改写。

完整思考：reasoning-02-AD01-compact.txt


## AD02 compact

```json

{
  "label": "supported",
  "reason": "资料中明确提到使用GitHub、Nbviewer等方法提供静态视图可帮助阅读，同时指出Binder和Docker等容器化环境能支持执行原计算。主张认为仅导出HTML/PDF不足以执行计算的表述与资料内容存在矛盾，因此被支持。",
  "sentence_ids": ["sent-0004", "sent-0006", "sent-0007", "sent-0010", "sent-0011", "sent-0012", "sent-0013"]
}

```

输入1128、总输出460 tokens；客户端21.386918秒；结束stop。

0006/0007/0010为静态可读档案及依赖重建环境，0011/0012/0013为执行环境，集合可支持实际supported，必要覆盖和支持均改善。理由末句却说与资料存在矛盾因此被支持，标签理由矛盾；0004仓库许可对该判断无必要支持，另记无关。即使标签正确及引用集合支持，也不算严格成功。

完整思考：reasoning-03-AD02-compact.txt


## AD02 repeated

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

输入2624、总输出502 tokens；客户端43.541252秒；结束stop。

supported符合公开参考，理由区分静态阅读与Binder环境，但最终只引问句0002及运行0011/0013，没有Read来源，不能严格成功。

完整思考：reasoning-04-AD02-repeated.txt


## AD03 repeated

```json

{
  "label": "insufficient",
  "reason": "资料中未提及绘图过程中数据转换后仅保留最终图片是否满足作者关于图底层数据的建议，且无直接证据表明这一操作与作者要求相关。",
  "sentence_ids": []
}

```

输入2879、总输出438 tokens；客户端43.633772秒；结束stop。

实际缺指定S08绘图变换直接依据，拒判较保守但不符合公开参考contradicted。S09仍有相关底层值论述，保留边界；空引用没有必要检查来源，引用支持不通过。

完整思考：reasoning-05-AD03-repeated.txt


## AD03 compact

```json

{
  "label": "insufficient",
  "reason": "资料中未明确提及绘图过程中仅保留最终图片满足作者关于图底层数据的建议，且相关证据（如使用HTML文件输出）支持其他做法而非直接关联。",
  "sentence_ids": ["sent-0009", "sent-0013"]
}

```

输入1144、总输出491 tokens；客户端22.066400秒；结束stop。

只引0009汇总图表与0013在存储条件允许时保留全部底层数据；没有补入未输入S08。它们既可能作当前可见范围的缺证检查来源，也对只留图的断言有条件性反证，支持insufficient是否充分保留ambiguous，不能强行判通过或借参考补证。公开标签仍不符合，严格失败不受此歧义影响。

完整思考：reasoning-06-AD03-compact.txt

{
  "groups": {
    "repeated": {
      "denominator": 3,
      "format_complete": 3,
      "label_correct": 1,
      "reason_label_consistent": 3,
      "nonempty_source_authenticity_passed": 2,
      "empty_selection": 1,
      "necessary_coverage_passed": 0,
      "necessary_coverage_ambiguous": 0,
      "citation_support_passed": 0,
      "citation_support_ambiguous": 0,
      "unrelated_citations": 0,
      "strict_complete_success": 0,
      "budget_exhausted": 0,
      "no_valid_final": 0,
      "reasoning_produced": 3,
      "input_tokens": 7831,
      "total_output_tokens": 1281,
      "client_seconds": 118.61474740016274
    },
    "compact": {
      "denominator": 3,
      "format_complete": 3,
      "label_correct": 1,
      "reason_label_consistent": 1,
      "nonempty_source_authenticity_passed": 3,
      "empty_selection": 0,
      "necessary_coverage_passed": 2,
      "necessary_coverage_ambiguous": 1,
      "citation_support_passed": 1,
      "citation_support_ambiguous": 1,
      "unrelated_citations": 1,
      "strict_complete_success": 0,
      "budget_exhausted": 0,
      "no_valid_final": 0,
      "reasoning_produced": 3,
      "input_tokens": 3308,
      "total_output_tokens": 1338,
      "client_seconds": 60.277237199945375
    }
  },
  "pairs": [
    {
      "id": "AD01",
      "repeated_run_id": "122cb09e-5b2e-4e6b-957e-73cca315a218",
      "compact_run_id": "39c5a8fa-5a4a-454c-ac18-99ae6742e4e6",
      "old_label": "supported",
      "new_label": "insufficient",
      "label_regressed": false,
      "historically_correct_item_lost": false,
      "old_necessary": false,
      "new_necessary": true,
      "old_support": false,
      "new_support": false,
      "delta_client_seconds": -14.61580410017632
    },
    {
      "id": "AD02",
      "repeated_run_id": "a4f91340-3539-41d1-8813-37e54b686eb1",
      "compact_run_id": "3c844048-cde4-48ea-b3ff-8a414e93474c",
      "old_label": "supported",
      "new_label": "supported",
      "label_regressed": false,
      "historically_correct_item_lost": false,
      "old_necessary": false,
      "new_necessary": true,
      "old_support": false,
      "new_support": true,
      "delta_client_seconds": -22.15433400007896
    },
    {
      "id": "AD03",
      "repeated_run_id": "6fbd914f-bc67-4816-8f1f-e2f7a2ed1482",
      "compact_run_id": "d357e1fb-7ffb-45ea-b5ab-3f118550b986",
      "old_label": "insufficient",
      "new_label": "insufficient",
      "label_regressed": false,
      "historically_correct_item_lost": false,
      "old_necessary": false,
      "new_necessary": "ambiguous",
      "old_support": false,
      "new_support": "ambiguous",
      "delta_client_seconds": -21.567372099962085
    }
  ],
  "decision": {
    "at": "2026-10-16T17:58:31.276125+08:00",
    "replace_current_entry": false,
    "retain_compact_as_independent_candidate": true,
    "basis": "本轮两侧严格成功均0/3、标签正确均1/3，没有已有标签正确项退步。主指标未胜出，按事前同分规则保留重复侧当前入口；紧凑侧的引用选择与效率收益单列，不写成正确率提高。",
    "evidence_changes": "AD01必要覆盖false→true但拒判仍错且理由归属写错；AD02必要覆盖及引用集合支持false→true，但理由标签矛盾且许可引用无关，仍严格失败；AD03从空引用到两个真实片段，缺证支持是否充分保留ambiguous，不移出分母。",
    "efficiency": "紧凑输入总tokens7831→3308，减少4523；总输出1281→1338，反而多57；客户端耗时仍明显下降。只限本轮三题，输入组织与claim位置共同变化，不能归因单独去重或外推稳定性能。",
    "source_truth_not_semantic": "已选原文来源真实不等于支持；AD01理由中错误归属也不因程序展开正确而消失。",
    "new_generations": 6,
    "cumulative": 615,
    "A_used": 81,
    "original_plan_budget": 90,
    "original_plan_remaining": 9,
    "future_reserved_additional": 30,
    "future_reservation_used": 0,
    "future_reservation_authorizes_execution": false,
    "technical_request_failures": 0,
    "quality_retries": 0,
    "stop": "自有服务已停止，不追加生成，不读取七题。"
  }
}
