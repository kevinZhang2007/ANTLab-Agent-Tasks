"""独立开发候选：原定位结果加唯一直接补页，不修改生产排序。"""
import copy
import importlib.util
from pathlib import Path
import two_step_candidate as selection

LINKED_SOURCE = Path(__file__).resolve().parents[1] / 'runs/improve/linked_r0/student-v2.py'
spec = importlib.util.spec_from_file_location('saved_linked_candidate', LINKED_SOURCE)
linked = importlib.util.module_from_spec(spec)
spec.loader.exec_module(linked)

def complete_passages(question, passages, validation):
    # 复用原合法性检查；非法选择不能修补或回退。
    original_selected = selection.select_original_passages(passages, validation)
    seed_ids = {p['id'] for p in original_selected}
    _, decisions = linked.organize_passages(question, passages)
    included = set(seed_ids)
    trace = []
    for decision in decisions:
        row = copy.deepcopy(decision)
        row['added'] = False
        if row['target_id'] in seed_ids and row['supplement_id'] not in seed_ids:
            included.add(row['supplement_id'])
            row['added'] = True
            row['completion_reason'] = '唯一直接主段属于原定位选择，补入完整补页。'
        elif row['target_id'] is None:
            row['completion_reason'] = row['reason']
        elif row['supplement_id'] in seed_ids:
            row['completion_reason'] = '已被定位选择，不重复补入。'
        else:
            row['completion_reason'] = '直接主段不在原定位选择；不从新补入段继续扩展。'
        trace.append(row)
    # included只用于成员判断；顺序始终来自当前完整输入。
    result = [copy.deepcopy(p) for p in passages if p['id'] in included]
    return result, trace
