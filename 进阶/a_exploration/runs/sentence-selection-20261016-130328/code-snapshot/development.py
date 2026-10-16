"""只顺序读取前三个开发任务，停止后不读取AT对象。"""
from pathlib import Path
import json

def read_development_stream(stream):
    tasks=[]; current=[]; depth=0; quoted=False; escaped=False
    while len(tasks)<3:
        char=stream.read(1)
        if not char:raise ValueError('开发题不足3条')
        if depth==0:
            if char==b'{':current=[char];depth=1
            continue
        current.append(char)
        if quoted:
            if escaped:escaped=False
            elif char==b'\\':escaped=True
            elif char==b'"':quoted=False
        elif char==b'"':quoted=True
        elif char in (b'{',b'['):depth+=1
        elif char in (b'}',b']'):depth-=1
        if depth==0:
            item=json.loads(b''.join(current))
            if item.get('split')!='dev':raise ValueError('开发题读取器遇到非开发项，停止')
            tasks.append(item)
    return tasks

def load_development(path):
    # 二进制无缓冲逐字节读取，第三个开发对象结束即停，不预读AT正文。
    with Path(path).open('rb',buffering=0) as stream:return read_development_stream(stream)
