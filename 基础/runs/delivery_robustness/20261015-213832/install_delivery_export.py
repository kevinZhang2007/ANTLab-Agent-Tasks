from pathlib import Path
from datetime import datetime
import ast,difflib,hashlib,json,shutil
R=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
F=R/'基础/runs/delivery_robustness/20261015-213832'
def main():
    results=R/'results';stamp=datetime.now().strftime('%Y%m%d-%H%M%S');archive=results/'history'/stamp
    assert not archive.exists()
    oldfiles=[p for p in results.rglob('*') if p.is_file() and not p.relative_to(results).parts[0]=='history']
    archive.mkdir(parents=True,exist_ok=False)
    oldhash={}
    for p in oldfiles:
        rel=p.relative_to(results);dest=archive/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
        oldhash[rel.as_posix()]=hashlib.sha256(dest.read_bytes()).hexdigest();assert dest.read_bytes()==p.read_bytes()
    with (F/'previous-results-snapshot.json').open('x',encoding='utf-8') as o:json.dump({'saved_at':datetime.now().astimezone().isoformat(),'path':archive.relative_to(R).as_posix(),'files':oldhash},o,ensure_ascii=False,indent=2)
    old=(results/'scoring/build_export.py').read_text(encoding='utf-8-sig');new=Path(__file__).with_name('build_export_updated.py').read_text(encoding='utf-8-sig');ast.parse(new)
    (results/'scoring/build_export.py').write_text(new,encoding='utf-8',newline='\n')
    (F/'build-export.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='old/results/scoring/build_export.py',tofile='new/results/scoring/build_export.py')),encoding='utf-8')
    path=results/'scoring/recalculate.py';old=path.read_text(encoding='utf-8-sig');new=old
    marker='    b_keys = [row["row_id"] for row in rows if row["count_as_b_replay"] == "true"]'
    assert new.count(marker)==1
    new=new.replace(marker,'    if "expected_generation_ids" in manifest and sorted(generation_ids) != manifest["expected_generation_ids"]:\n        raise ValueError("生成ID集合不符，不能只比较总数")\n'+marker)
    marker='    return {"purpose": "仅复算归档评价，不重新证明语义正确；各view不可相加为一轮成绩。"'
    assert new.count(marker)==1
    addition='''    by_id = {row["row_id"]: row for row in rows}
    if len(by_id) != len(rows):
        raise ValueError("导出row_id重复")
    for check in manifest.get("new_group_summary_checks", []):
        group = pointer(read_json(safe_path(root, check["summary_path"])), check["summary_pointer"])
        selected = [by_id[rid] for rid in check["row_ids"]]
        metric = check["metric"]
        expected = {"numerator": group[check["saved_numerator_field"]], "denominator": group[check["saved_denominator_field"]]}
        computed = {"numerator": sum(row[metric] == "true" for row in selected), "denominator": len(selected)}
        comparisons.append({**check, "saved": expected, "recomputed": computed, "equal": expected == computed})
'''
    new=new.replace(marker,addition+marker);ast.parse(new);path.write_text(new,encoding='utf-8',newline='\n')
    (F/'recalculate.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='old/results/scoring/recalculate.py',tofile='new/results/scoring/recalculate.py')),encoding='utf-8')
    print((archive/'scoring/manifest.json').relative_to(R).as_posix())
if __name__=='__main__':main()
