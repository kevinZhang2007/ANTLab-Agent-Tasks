"""用现有运行时离线渲染原PDF；不改变原件或下载依赖。"""
from pathlib import Path
import json
import pdfplumber
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
folder=HERE/'assets';folder.mkdir(exist_ok=True)
records=[]
for doc in ('P1','P2'):
    with pdfplumber.open(ROOT/'进阶/materials/papers'/f'{doc}.pdf') as pdf:
        for index,page in enumerate(pdf.pages,1):
            path=folder/f'{doc}-{index}.png'
            if not path.exists():page.to_image(resolution=96).save(path,format='PNG')
            records.append({'doc_id':doc,'page':index,'width':page.width,'height':page.height,'image':path.relative_to(HERE).as_posix(),'dpi':96})
print(json.dumps(records,ensure_ascii=False))
