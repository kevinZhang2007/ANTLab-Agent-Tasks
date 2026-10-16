"""只顺序读取前三个开发任务，停止后不读取AT对象。"""
from pathlib import Path
import json

def load_development(path):
    tasks=[]; current=[]; depth=0; quoted=False; escaped=False
    with Path(path).open(encoding='utf-8-sig') as stream:
        while len(tasks)<3:
            char=stream.read(1)
            if not char:raise ValueError('开发题不足3条')
            if depth==0:
                if char=='{':current=[char];depth=1
                continue
            current.append(char)
            if quoted:
                if escaped:escaped=False
                elif char=='\\':escaped=True
                elif char=='"':quoted=False
            elif char=='"':quoted=True
            elif char in '{[':depth+=1
            elif char in '}]':depth-=1
            if depth==0:
                item=json.loads(''.join(current))
                if item.get('split')!='dev':raise ValueError('开发题读取器遇到非开发项，停止')
                tasks.append(item)
    return tasks
