"""构建新的交付层；只读旧归档，仅写results/。不运行实验。"""
import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
import recalculate as scoring


def escape(value):
    return str(value).replace("~", "~0").replace("/", "~1")


def main(root, refresh=False):
    root = root.resolve()
    output = root / "results"
    output.mkdir(exist_ok=True)
    (output / "scoring").mkdir(exist_ok=True)
    if (output / "scoring/manifest.json").exists() and not refresh:
        raise FileExistsError("不覆盖已有导出；新一轮请另存版本。")
    files = {}
    for folder in ("基础/runs", "进阶/runs"):
        for path in sorted((root / folder).rglob("*.json")):
            if any("snapshot" in part.lower() and "code" in part.lower() for part in path.parts):
                continue
            try:
                files[path.relative_to(root).as_posix()] = scoring.read_json(path)
            except (ValueError, UnicodeError):
                continue
    manifest = {"schema_version": 1, "created_at": datetime.now(timezone(timedelta(hours=8))).isoformat(), "expected_counts": {"model_generations": 428, "b_offline_executions": 88}, "records": [], "source_hashes": {}, "summary_checks": [], "limits": ["重算保存的评价，不新判语义", "不同评价文件、不同配置和模型原始/系统最终视图不能相加", "旧归档保留；规则结果不计入首次主评分"]}
    records = manifest["records"]
    generation_paths = {}
    assessment_views = []

    def remember(path):
        manifest["source_hashes"][path] = hashlib.sha256(scoring.safe_path(root, path).read_bytes()).hexdigest()

    def provenance(path):
        if path.startswith("基础/runs/formal_review/round1/"):
            frozen = "基础/runs/formal/round1/freeze.json"
            remember(frozen)
            return "基础/runs/formal/round1", frozen
        parent = (root / path).parent
        while parent.is_relative_to(root / "基础/runs") or parent.is_relative_to(root / "进阶/runs"):
            frozen = parent / "freeze.json"
            if frozen.is_file():
                rel = frozen.relative_to(root).as_posix()
                remember(rel)
                return parent.relative_to(root).as_posix(), rel
            if parent.name in ("runs", "基础", "进阶"):
                break
            parent = parent.parent
        return str(Path(path).parent).replace("\\", "/"), ""

    def add(path, ptr, data, kind, source, extra=None, label_data=None, label_ptr=None):
        version, freeze = provenance(path)
        rid = data.get("run_id", "")
        raw = generation_paths.get(rid, "")
        ids = data.get("stage_run_ids", data.get("run_ids", []))
        if isinstance(ids, dict): ids = list(ids.values())
        if isinstance(ids, list) and ids:
            last = ids[-1]
            if isinstance(last, str): rid = last; raw = generation_paths.get(rid, "")
        if not raw:
            for key in ("answer_record_path", "record_path"):
                target = data.get(key)
                if isinstance(target, str):
                    match = [(key, value) for key, value in generation_paths.items() if Path(value).name == Path(target.replace("\\", "/")).name]
                    if len(match) == 1: rid, raw = match[0]
        if not raw and isinstance(data.get("stage_records"), list):
            for stage in reversed(data["stage_records"]):
                if isinstance(stage, dict) and stage.get("run_id") in generation_paths:
                    rid = stage["run_id"]; raw = generation_paths[rid]; break
        if raw:
            raw_data = files[raw]
        else:
            raw_data = {}
        elapsed = data.get("elapsed_seconds", data.get("end_to_end_seconds", data.get("client_answer_seconds", "")))
        timing = data.get("timing", data.get("timing_summary", {}))
        if elapsed == "" and isinstance(timing, dict): elapsed = timing.get("end_to_end_seconds", "")
        origin = data.get("output_source", data.get("actual_final_output_source", "not_saved"))
        if origin == "not_saved" and source == "system_final" and "derived_response" in data:
            origin = "local_rule_derived" if data["derived_response"] is not None else "raw_model_response"
        metadata = {"row_id": f"{kind}:{path}#{ptr}", "row_kind": kind, "experiment_class": "first_primary" if path.startswith(("基础/runs/formal/round1/", "基础/runs/formal_review/round1/")) else "subsequent_exploration", "version": version, "freeze_path": freeze, "freeze_sha256": manifest["source_hashes"].get(freeze, "not_saved"), "case_id": data.get("case_id", raw_data.get("case_id", "not_saved")), "condition": data.get("condition", raw_data.get("condition", "not_saved")), "variant": data.get("variant", data.get("scheme", raw_data.get("variant", "not_saved"))), "main_task_id": data.get("main_task_id", data.get("parent_request_id", raw_data.get("main_task_id", raw_data.get("parent_request_id", "not_saved")))), "run_id": rid or "not_saved", "request_id": "", "result_source": source, "output_origin": origin, "status": data.get("status", raw_data.get("status", "not_saved")), "elapsed_seconds": elapsed, "elapsed_scope": "end_to_end" if ("end_to_end_seconds" in data or timing) else "archived_request_or_not_saved", "run_kind": raw_data.get("run_kind", data.get("run_kind", "not_saved")), "judgment_source": "unverified", "count_as_generation": False, "count_as_b_replay": False, "scoring_view": "", "raw_record_path": raw, "assessment_path": "", "ambiguity": json.dumps(data.get("ambiguity", "not_checked"), ensure_ascii=False)}
        if source in ("system_final", "local_rule_trace", "local_rule_derived"):
            metadata.update(run_kind="local_rule", judgment_source="rule", experiment_class="system_exploration")
            if origin == "raw_model_response":
                metadata.update(run_kind=raw_data.get("run_kind", "live_api"), judgment_source="unverified")
        if kind == "assessment":
            metadata["scoring_view"] = path + "#" + source
            metadata["assessment_path"] = path
            assessment_views.append(metadata["scoring_view"])
        if extra: metadata.update(extra)
        if kind == "assessment" and metadata["condition"] == "not_saved":
            matches = [(name, item.get("condition")) for name, item in files.items()
                       if name in generation_paths.values() and name.startswith(str(Path(path).parent).replace("\\", "/") + "/")
                       and isinstance(item, dict) and item.get("case_id") == metadata["case_id"] and item.get("condition")]
            conditions = {condition for _, condition in matches}
            if len(conditions) == 1:
                metadata["condition"] = next(iter(conditions))
                remember(matches[0][0])
        response = raw_data.get("response", {})
        choices = response.get("choices", []) if isinstance(response, dict) else []
        content = data.get("raw_content", data.get("raw_final_content", ""))
        if not content and choices: content = choices[0].get("message", {}).get("content", "")
        if not content and isinstance(data.get("raw_response"), str): content = data["raw_response"]
        output_value = data.get("actual_final_output", data.get("system_final_response", data.get("candidate_response"))) if source == "system_final" else None
        if not isinstance(output_value, dict):
            try: output_value = json.loads(content) if isinstance(content, str) else None
            except ValueError: output_value = None
        output_value = output_value if isinstance(output_value, dict) else data
        config = raw_data.get("config", {})
        usage = raw_data.get("usage") or (response.get("usage") if isinstance(response, dict) else {})
        metadata.update({"stage": raw_data.get("stage", "not_saved"), "attempt": raw_data.get("attempt", "not_saved"), "retry_of": raw_data.get("retry_of", "not_saved"), "model": config.get("model", response.get("model", "not_saved") if isinstance(response, dict) else "not_saved"), "configuration_ref": raw + "#/config" if raw else "not_saved", "http_status": raw_data.get("http_status", "not_saved"), "raw_content": content or "not_saved", "answer": json.dumps(output_value.get("answer", "not_saved"), ensure_ascii=False), "citations": json.dumps(output_value.get("citations", "not_saved"), ensure_ascii=False), "usage": json.dumps(usage or "not_saved", ensure_ascii=False), "usage_source": raw if usage else "not_saved", "judgment_reason": json.dumps(data.get("reasons", data.get("judgment_reasons", data.get("reason", data.get("basis", "not_checked")))), ensure_ascii=False)})
        spec = {"source_path": path, "source_pointer": ptr, "metadata": metadata, "labels": {}}
        if label_data is not None:
            for metric, aliases in scoring.METRICS.items():
                key = next((key for key in aliases if key in label_data), None)
                if key:
                    spec["labels"][metric] = {"path": path, "pointer": (label_ptr if label_ptr is not None else ptr) + "/" + escape(key)}
                    if metric == "has_unrelated_references" and isinstance(label_data[key], list):
                        spec["labels"][metric]["list_presence"] = True
        records.append(spec)
        remember(path)
        return spec

    # 仅根级run_id+实际completion_tokens计生成；嵌套索引与复制引用不计。
    for path, data in files.items():
        if not path.startswith("基础/runs/") or not isinstance(data, dict) or not data.get("run_id"):
            continue
        response = data.get("response", {})
        usage = data.get("usage") or (response.get("usage") if isinstance(response, dict) else {}) or {}
        if usage.get("completion_tokens", 0) > 0:
            if data["run_id"] in generation_paths:
                raise ValueError("生成记录重复，需人工确认: " + data["run_id"])
            generation_paths[data["run_id"]] = path
    for rid, path in generation_paths.items():
        data = files[path]
        spec = add(path, "", data, "model_generation", "model_raw", {"count_as_generation": True, "raw_record_path": path, "run_kind": data.get("run_kind", "live_api"), "elapsed_scope": "single_model_request"})
        for key in ("evaluation", "judgment", "checks"):
            if isinstance(data.get(key), dict):
                for metric, aliases in scoring.METRICS.items():
                    field = next((x for x in aliases if x in data[key]), None)
                    if field and metric not in spec["labels"]:
                        spec["labels"][metric] = {"path": path, "pointer": "/" + key + "/" + field, **({"list_presence": True} if isinstance(data[key][field], list) and metric == "has_unrelated_references" else {})}

    # 显式列出B单次执行文件模式，排除同request_id的日志、汇总及截图。
    b_patterns = [
        ("进阶/runs/b_scope_diagnosis/20261013-184411", "04-observation-*.json", "direct_engine"),
        ("进阶/runs/b_cache_repair/20261013-185609", "03-run-*.json", "direct_engine"),
        ("进阶/runs/b_http_page/20261013-190716", "http-*.json", "direct_http"),
        ("进阶/runs/b_http_page/20261013-190716/page", "page-*.json", "page_submission"),
        ("进阶/runs/b_warm_boundary/20261013-191921", "http-*.json", "direct_http"),
        ("进阶/runs/b_warm_boundary/20261013-191921/page", "page-*.json", "page_submission"),
    ]
    for folder, pattern, channel in b_patterns:
        for p in sorted((root / folder).glob(pattern)):
            if channel != "direct_engine" and not re.fullmatch(r"(?:http|page)-(?:original|fixed)-\d+\.json", p.name):
                continue
            path = p.relative_to(root).as_posix(); data = files[path]
            response = data["response"]
            request_id = response.get("request_id", data.get("request_id", "not_saved"))
            elapsed = data.get("client_function_elapsed_ms", response.get("elapsed_ms", ""))
            add(path, "/response", response, "b_offline_replay", "fixed_draft_" + channel, {"experiment_class": "B_offline", "version": folder, "case_id": data.get("case", data.get("scenario", data.get("http_request", data.get("submitted", {})).get("case_id", "not_saved"))), "variant": data.get("variant", data.get("engine", "not_saved")), "request_id": request_id, "run_id": "not_applicable", "run_kind": "offline_replay", "judgment_source": response.get("judgment_source", "unverified"), "count_as_b_replay": True, "elapsed_seconds": elapsed / 1000 if isinstance(elapsed, (int, float)) else "not_saved", "elapsed_scope": "direct_engine_client" if channel == "direct_engine" else "archived_backend_elapsed_not_full_http", "raw_record_path": path, "status": response.get("status", data.get("http_status", "not_saved"))})
    manifest["b_log_links"] = []
    event_index = {}
    for path in sorted((root / "进阶/runs").rglob("events.jsonl")):
        relative = path.relative_to(root).as_posix()
        for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            event = json.loads(line)
            if event.get("request_id"):
                event_index.setdefault(event["request_id"], []).append({"path": relative, "line": number})
    for spec in records:
        meta = spec["metadata"]
        if meta["row_kind"] == "b_offline_replay" and meta["result_source"] != "fixed_draft_direct_engine":
            links = event_index.get(meta["request_id"], [])
            if len(links) != 1:
                raise ValueError("B HTTP请求没有唯一后端日志: " + meta["request_id"])
            manifest["b_log_links"].append({"request_id": meta["request_id"], "source_path": spec["source_path"], **links[0]})
            remember(links[0]["path"])

    # 每个评价文件都是独立视图；不拿不同时间的最好标签拼接同一轮。
    accepted = {"effective-reviews.json", "effective-semantic-review.json", "semantic-review.json", "evaluations.json", "evaluation.json", "comparison-review.json", "defect-review.json", "local-reading-review.json", "local-and-final-review.json", "qualification-review.json"}
    sides = ("raw_review", "system_final_review", "before_system_review", "after_system_review")
    for path, document in files.items():
        if not path.startswith("基础/runs/") or Path(path).name not in accepted:
            continue
        def walk(node, ptr="", inherited=None):
            if isinstance(node, list):
                for i, child in enumerate(node): walk(child, ptr + "/" + str(i), inherited)
            elif isinstance(node, dict):
                context = {**(inherited or {}), **{k: node[k] for k in ("case_id", "condition", "variant", "main_task_id", "run_id", "run_ids", "stage_run_ids", "dataset", "parent_request_id") if k in node}}
                nested_sides = [side for side in sides if isinstance(node.get(side), dict)]
                if nested_sides:
                    for side in nested_sides:
                        source = "model_raw" if side == "raw_review" else ("system_final" if side == "system_final_review" else side)
                        extra = {"scoring_view": path + "#" + side + "#" + str(context.get("dataset", ""))}
                        add(path, ptr + "/" + side, {**node, **context}, "assessment", source, extra, node[side], ptr + "/" + side)
                    return
                metrics_here = sum(any(alias in node for alias in aliases) for aliases in scoring.METRICS.values())
                if metrics_here >= 2 and (context.get("case_id") or context.get("run_id")):
                    source = "system_final" if isinstance(node.get("candidate_response"), dict) else "model_raw"
                    add(path, ptr, {**node, **context}, "assessment", source, label_data=node)
                    return
                for name in ("evaluation", "final_evaluation", "rows", "items", "tasks", "results", "final_answers", "reviews"):
                    if name in node: walk(node[name], ptr + "/" + escape(name), context)
        walk(document)

    # 规则轨迹不增加生成次数；明确保留原run_kind/judgment_source供审计。
    for path, data in files.items():
        if not isinstance(data, dict) or not path.startswith("基础/runs/"):
            continue
        if Path(path).name.startswith("task-"):
            for key in ("proof_record", "ratio_proof", "difference_proposal"):
                value = data.get(key)
                if isinstance(value, dict) and value:
                    add(path, "/" + key, {**data, **value}, "rule_trace", "local_rule_trace", {"run_kind": "local_rule", "judgment_source": "rule", "scoring_view": ""})
        if "stop" in Path(path).name and not data.get("run_id"):
            add(path, "", data, "preparation_or_stop", "preserved_failure_record", {"status": data.get("status", "see_original"), "run_kind": "not_applicable"})

    # 用原汇总中的明确分子/分母核对，不以汇总数字回填逐条标签。
    for path, data in files.items():
        if Path(path).name != "effective-reviews.json" or not isinstance(data, dict): continue
        summary_path = str(Path(path).with_name("summary.json")).replace("\\", "/")
        summary = files.get(summary_path)
        if not isinstance(summary, dict): continue
        view_rows = [s for s in records if s["metadata"].get("assessment_path") == path]
        def append_checks(metrics, base_ptr, view, condition, variant, source):
            if not isinstance(metrics, dict): return
            for metric, saved in metrics.items():
                if metric in scoring.METRICS and isinstance(saved, dict) and "numerator" in saved:
                    manifest["summary_checks"].append({"path": summary_path, "pointer": base_ptr + "/" + metric, "view": view, "condition": condition, "variant": variant, "result_source": source, "metric": metric})
                    remember(summary_path)
        if isinstance(summary.get("table"), list):
            for i, group in enumerate(summary["table"]):
                side = "model_raw"; view = path + "#model_raw"
                append_checks(group.get("metrics"), "/table/" + str(i) + "/metrics", view, group.get("condition", "not_saved"), group.get("variant", "not_saved"), side)
        for spec in view_rows:
            meta = spec["metadata"]
            for side in ("raw_review", "system_final_review"):
                if spec["source_pointer"].endswith("/" + side):
                    dataset = meta["scoring_view"].split("#")[-1]
                    metrics = summary.get("metrics", {}).get(side)
                    prefix = "/metrics/" + side
                    if "datasets" in summary and dataset in summary["datasets"]:
                        metrics = summary["datasets"][dataset].get("metrics", {}).get(side)
                        prefix = "/datasets/" + dataset + "/metrics/" + side
                    append_checks(metrics, prefix, meta["scoring_view"], meta["condition"], meta["variant"], meta["result_source"])
    manifest["summary_checks"] = list({json.dumps(c, sort_keys=True): c for c in manifest["summary_checks"]}.values())
    manifest["scalar_summary_checks"] = []
    manifest["unmatched_summary_rows"] = []
    for summary_path, summary in files.items():
        if Path(summary_path).name not in ("summary.json", "effective-summary.json") or not isinstance(summary, dict) or not isinstance(summary.get("table"), list):
            continue
        directory = str(Path(summary_path).parent).replace("\\", "/")
        review_paths = [directory + "/" + name for name in ("effective-semantic-review.json", "semantic-review.json") if directory + "/" + name in files]
        if not review_paths: continue
        review_path = review_paths[0] if Path(summary_path).name == "effective-summary.json" else review_paths[-1]
        for index, group in enumerate(summary["table"]):
            variant = group.get("variant", group.get("setting"))
            view = review_path + "#model_raw"
            members = [s for s in records if s["metadata"].get("scoring_view") == view and s["metadata"]["variant"] == variant]
            if not members:
                manifest["unmatched_summary_rows"].append({"path": summary_path, "pointer": "/table/" + str(index), "reason": "本文件没有对应逐条评价；可能为历史复用侧，不拼接其他轮次"})
                continue
            denominator_key = next((k for k in ("denominator", "tasks", "calls") if k in group), None)
            if not denominator_key: continue
            for metric, aliases in scoring.METRICS.items():
                key = next((k for k in aliases if isinstance(group.get(k), int) and not isinstance(group[k], bool)), None)
                if key:
                    manifest["scalar_summary_checks"].append({"path": summary_path, "numerator_pointer": f"/table/{index}/{key}", "denominator_pointer": f"/table/{index}/{denominator_key}", "view": view, "variant": variant, "metric": metric})
                    remember(summary_path)
    manifest["source_hashes"] = dict(sorted(manifest["source_hashes"].items()))
    manifest["record_counts"] = dict(Counter(s["metadata"]["row_kind"] for s in records))
    (output / "scoring/manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rows = scoring.make_rows(root, manifest, files)
    (output / "results.csv").write_text(scoring.csv_text(rows), encoding="utf-8", newline="")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--refresh-export", action="store_true", help="仅重建results导出层，不写旧归档")
    args = parser.parse_args()
    result = main(args.root, args.refresh_export)
    print(json.dumps({"records": result["record_counts"], "summary_checks": len(result["summary_checks"])}, ensure_ascii=False))
