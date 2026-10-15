"""只读复算归档标签；不导入实验代码，不访问网络，不重新判定语义。"""
import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from pathlib import Path

METRICS = {
    "answer_correct": ["answer_correct", "specified_answer_correct", "answer_correct_specified_form", "answer_correct_under_specified_form", "answer_grounded_and_correct"],
    "semantic_consistent": ["semantic_consistent", "semantic_correct", "semantic_answer_correct", "answer_semantic_agreement"],
    "format_complete": ["format_complete", "json_complete", "json_object_complete"],
    "citation_ids_exist": ["citation_ids_exist", "citation_ids_in_input", "citations_exist"],
    "necessary_input_coverage": ["necessary_input_coverage", "input_necessary_coverage", "input_necessary_evidence_covered", "input_necessary_evidence_coverage"],
    "necessary_coverage": ["necessary_coverage", "necessary_evidence_coverage", "necessary_citation_coverage", "necessary_evidence_covered", "data_and_release_rule_citations_complete"],
    "support_actual_answer": ["support_actual_answer", "citations_support_actual_answer", "citations_support_answer", "citation_support", "citation_support_sufficient", "citation_supports_answer", "evidence_supports_actual_answer"],
    "has_unrelated_references": ["has_unrelated_references", "unrelated_citations", "irrelevant_ids", "irrelevant_citations", "additional_citations"],
    "strict_complete_success": ["strict_complete_success", "complete_success"],
    "missing_evidence_response_compliant": ["missing_evidence_response_compliant"],
}
FIELDS = ["row_id", "row_kind", "experiment_class", "version", "freeze_path", "freeze_sha256", "case_id", "condition", "variant", "main_task_id", "run_id", "request_id", "stage", "attempt", "retry_of", "model", "configuration_ref", "result_source", "output_origin", "status", "http_status", "elapsed_seconds", "elapsed_scope", "raw_content", "answer", "citations", "usage", "usage_source", "judgment_reason", "run_kind", "judgment_source", "original_run_kind", "original_judgment_source", "count_as_generation", "count_as_b_replay", "scoring_view", "source_path", "source_pointer", "raw_record_path", "assessment_path", "ambiguity", "original_values"] + list(METRICS)


def safe_path(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or Path(relative).is_absolute():
        raise ValueError("路径必须位于仓库内: " + relative)
    return path


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def pointer(data, path):
    for part in path.split("/")[1:] if path else []:
        part = part.replace("~1", "/").replace("~0", "~")
        data = data[int(part)] if isinstance(data, list) else data[part]
    return data


def label(value):
    if value is True or value == "true":
        return "true"
    if value is False or value == "false":
        return "false"
    if value in ("ambiguous", "unverifiable", "无法核验"):
        return "ambiguous"
    return "not_checked"


def make_rows(root, manifest, cache=None):
    cache = {} if cache is None else cache
    def load(name):
        if name not in cache:
            cache[name] = read_json(safe_path(root, name))
        return cache[name]
    rows = []
    for spec in manifest["records"]:
        source = pointer(load(spec["source_path"]), spec["source_pointer"])
        row = {key: "" for key in FIELDS}
        row.update(spec["metadata"])
        row.update({k: spec[k] for k in ("source_path", "source_pointer")})
        original = {}
        for key in METRICS:
            binding = spec.get("labels", {}).get(key)
            if binding:
                value = pointer(load(binding["path"]), binding["pointer"])
                original[key] = {"value": value, **binding}
                if binding.get("list_presence") and isinstance(value, list):
                    value = bool(value)
                row[key] = label(value)
            else:
                row[key] = "not_checked"
        row["original_values"] = json.dumps(original, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        # 原字段直接取自归档，不以导出层常量替代。
        row["original_run_kind"] = json.dumps(source.get("run_kind"), ensure_ascii=False) if isinstance(source, dict) else "null"
        row["original_judgment_source"] = json.dumps(source.get("judgment_source"), ensure_ascii=False) if isinstance(source, dict) else "null"
        rows.append({k: str(v) if not isinstance(v, bool) else str(v).lower() for k, v in row.items()})
    return rows


def csv_text(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def totals(rows):
    groups = defaultdict(list)
    for row in rows:
        if row["scoring_view"]:
            key = (row["scoring_view"], row["condition"], row["variant"], row["result_source"])
            groups[key].append(row)
    result = []
    for key, members in sorted(groups.items()):
        metrics = {}
        for name in METRICS:
            counts = Counter(row[name] for row in members)
            metrics[name] = {"numerator": counts["true"], "denominator": len(members), "false": counts["false"], "ambiguous": counts["ambiguous"], "not_checked": counts["not_checked"]}
        result.append({"view": key[0], "condition": key[1], "variant": key[2], "result_source": key[3], "metrics": metrics})
    return result


def run(root):
    manifest = read_json(root / "results/scoring/manifest.json")
    cache = {}
    for relative, expected in manifest["source_hashes"].items():
        actual = hashlib.sha256(safe_path(root, relative).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError("归档文件哈希改变: " + relative)
    rows = make_rows(root, manifest, cache)
    actual_csv = (root / "results/results.csv").read_text(encoding="utf-8")
    if csv_text(rows) != actual_csv:
        raise ValueError("CSV与明确配置及归档标签不一致")
    generation_ids = [row["run_id"] for row in rows if row["count_as_generation"] == "true"]
    b_keys = [row["row_id"] for row in rows if row["count_as_b_replay"] == "true"]
    if len(set(generation_ids)) != len(generation_ids):
        raise ValueError("生成run ID重复")
    if len(set(b_keys)) != len(b_keys):
        raise ValueError("B执行记录重复")
    b_ids = [row["request_id"] for row in rows if row["count_as_b_replay"] == "true"]
    if len(b_ids) != len(set(b_ids)):
        raise ValueError("B request_id重复，不能重复统计HTTP与后端执行")
    counts = {"model_generations": len(generation_ids), "b_offline_executions": len(b_keys)}
    if counts != manifest["expected_counts"]:
        raise ValueError("调用账本计数不符: " + str(counts))
    for spec in manifest["records"]:
        if spec["metadata"]["count_as_generation"]:
            data = cache[spec["source_path"]]
            response = data.get("response", {})
            usage = data.get("usage") or (response.get("usage") if isinstance(response, dict) else {}) or {}
            if usage.get("completion_tokens", 0) <= 0 or data["run_id"] != spec["metadata"]["run_id"]:
                raise ValueError("计入生成的记录没有实际生成用量: " + spec["source_path"])
    for link in manifest.get("b_log_links", []):
        lines = safe_path(root, link["path"]).read_text(encoding="utf-8-sig").splitlines()
        event = json.loads(lines[link["line"] - 1])
        archived = read_json(safe_path(root, link["source_path"]))["response"]
        if event.get("request_id") != link["request_id"] or event.get("response") != archived:
            raise ValueError("B HTTP与同request_id后端日志不一致: " + link["source_path"])
    grouped = totals(rows)
    comparisons = []
    for check in manifest["summary_checks"]:
        matches = [g for g in grouped if all(g[k] == check[k] for k in ("view", "condition", "variant", "result_source"))]
        if len(matches) != 1:
            raise ValueError("汇总对应组不存在或不唯一: " + str(check))
        saved = pointer(read_json(safe_path(root, check["path"])), check["pointer"])
        computed = matches[0]["metrics"][check["metric"]]
        fields = [k for k in ("numerator", "denominator", "ambiguous", "not_checked") if k in saved]
        comparisons.append({**check, "saved": {k: saved[k] for k in fields}, "recomputed": {k: computed[k] for k in fields}, "equal": all(saved[k] == computed[k] for k in fields)})
    for check in manifest.get("scalar_summary_checks", []):
        members = [row for row in rows if row["scoring_view"] == check["view"] and row["variant"] == check["variant"]]
        saved = read_json(safe_path(root, check["path"]))
        expected = {"numerator": pointer(saved, check["numerator_pointer"]), "denominator": pointer(saved, check["denominator_pointer"])}
        actual = {"numerator": sum(row[check["metric"]] == "true" for row in members), "denominator": len(members)}
        comparisons.append({**check, "saved": expected, "recomputed": actual, "equal": expected == actual})
    return {"purpose": "仅复算归档评价，不重新证明语义正确；各view不可相加为一轮成绩。", "counts": counts, "b_same_request_log_links": len(manifest.get("b_log_links", [])), "csv_rows": len(rows), "row_kinds": dict(Counter(r["row_kind"] for r in rows)), "groups": grouped, "summary_comparisons": comparisons, "all_compared_summaries_equal": all(c["equal"] for c in comparisons), "scanned_source_files": len(manifest["source_hashes"])}


if __name__ == "__main__":
    result = run(Path(__file__).resolve().parents[2])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["all_compared_summaries_equal"]:
        raise SystemExit(2)
