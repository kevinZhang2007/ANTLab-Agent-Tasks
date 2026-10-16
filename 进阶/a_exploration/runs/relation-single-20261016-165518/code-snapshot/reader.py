"""原PDF的离线物理页查看器；不依赖浏览器PDF插件。"""
from pathlib import Path
import json,html

def reader_html(root,query):
    doc=query.get('doc_id',[''])[0]
    words=json.loads((root/'进阶/materials/page_words.json').read_text(encoding='utf-8-sig'))
    pages=sorted({w['page'] for w in words if w['doc_id']==doc and w['snapshot']=='published'})
    page=int(query.get('page',['1'])[0])
    if not pages or page not in pages:raise ValueError('未知文档或物理页')
    sample=next(w for w in words if w['doc_id']==doc and w['page']==page)
    links=' '.join(f'<a href="/reader?doc_id={html.escape(doc)}&page={p}">{p}</a>' for p in pages)
    return f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>{html.escape(doc)} 物理页 {page}</title><style>body{{font:16px system-ui}}#paper{{display:block;width:{sample['page_width']}px}}.scroll{{overflow:auto;border:1px solid #aaa}}</style><h1>{html.escape(doc)} 物理页 {page}/{max(pages)}</h1><p>来自原始PDF的离线渲染，不改变正文；此页查看不调用模型。定位及语义支持另行检查。</p><nav>物理页：{links} | <a href="/">返回对照页面</a> | <a href="/pdf/{html.escape(doc)}#page={page}">原PDF文件</a></nav><p><label>页面缩放 <input id="zoom" type="range" min="0.5" max="2" step="0.25" value="1"></label></p><div class="scroll"><img id="paper" src="/assets/{html.escape(doc)}-{page}.png" alt="{html.escape(doc)} 原PDF物理页{page}"></div><script>document.getElementById('zoom').oninput=e=>{{document.getElementById('paper').style.width=({sample['page_width']}*Number(e.target.value))+'px'}};</script></html>'''.encode('utf-8')
