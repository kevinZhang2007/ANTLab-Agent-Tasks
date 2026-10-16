"""原文到题包词框的保守映射；不推断语义支持。"""
from collections import defaultdict
import unicodedata

def normalize(text):
    result=[]; positions=[]
    for i,char in enumerate(text):
        for c in unicodedata.normalize('NFKD',char).casefold():
            if c.isalnum():result.append(c); positions.append(i)
    return ''.join(result),positions

def page_streams(words):
    rows=[]
    for w in sorted(words,key=lambda w:(w['bbox'][1],w['bbox'][0])):
        row=next((r for r in rows if abs(r[0]['bbox'][1]-w['bbox'][1])<2),None)
        if row is None:rows.append([w])
        else:row.append(w)
    segments=[]
    for row in rows:
        segment=[]
        for w in sorted(row,key=lambda w:w['bbox'][0]):
            if segment and w['bbox'][0]-segment[-1]['bbox'][2]>12:
                segments.append(segment);segment=[]
            segment.append(w)
        if segment:segments.append(segment)
    clusters=[]
    for seg in sorted(segments,key=lambda s:s[0]['bbox'][0]):
        x=seg[0]['bbox'][0]
        match=next((c for c in clusters if abs(c['x']-x)<12),None)
        if match:match['segments'].append(seg)
        else:clusters.append({'x':x,'segments':[seg]})
    origins=[c['x'] for c in clusters if len(c['segments'])>=max(4,len(segments)*0.08)]
    if not origins:origins=[min(s[0]['bbox'][0] for s in segments)] if segments else []
    columns=defaultdict(list)
    for seg in segments:
        col=min(origins,key=lambda x:abs(x-seg[0]['bbox'][0]))
        columns[col].append(seg)
    streams=[]
    for col,groups in sorted(columns.items()):
        chars=[]; refs=[]
        for seg in sorted(groups,key=lambda s:(s[0]['bbox'][1],s[0]['bbox'][0])):
            for w in seg:
                n,_=normalize(w['text']);chars.extend(n);refs.extend([w]*len(n))
        streams.append({'column_x':col,'text':''.join(chars),'refs':refs})
    return streams

class Locator:
    def __init__(self,words):
        pages=defaultdict(list)
        for w in words:pages[(w['doc_id'],w['snapshot'],w['page'])].append(w)
        self.streams={key:page_streams(ws) for key,ws in pages.items()}

    def locate(self,block,quote):
        if not quote or quote not in block['text']:return {'locator_status':'invalid','reason':'摘录不是对应原段落连续子串','regions':[]}
        normalized,_=normalize(quote)
        if len(normalized)<20:return {'locator_status':'absent','reason':'摘录过短，拒绝假精确定位','regions':[]}
        found=[]
        for (doc,snapshot,page),streams in self.streams.items():
            if (doc,snapshot)!=(block['doc_id'],block['snapshot']):continue
            for stream in streams:
                start=stream['text'].find(normalized)
                while start>=0:
                    unique={w['id']:w for w in stream['refs'][start:start+len(normalized)]}
                    words=list(unique.values())
                    # 不根据字符比例切割题包整行框，保留其实际精度。
                    found.append({'page':page,'column_x':stream['column_x'],'page_width':words[0]['page_width'],'page_height':words[0]['page_height'],'boxes':[{'word_id':w['id'],'bbox':w['bbox'],'text':w['text']} for w in words],'precision':'provided_word_or_line_boxes','coordinate_system':'PDF top-left origin, points','quote_start':block['text'].index(quote),'quote_end':block['text'].index(quote)+len(quote)})
                    start=stream['text'].find(normalized,start+1)
        if len(found)!=1:return {'locator_status':'absent' if not found else 'invalid','reason':'未找到可靠连续区域' if not found else '区域不唯一，拒绝猜测','regions':found if len(found)==1 else []}
        return {'locator_status':'valid','reason':'原文连续摘录、文档范围与唯一规范化词框序列一致；不代表语义支持','regions':found}

def scale_box(box,width,height,display_width,display_height):
    if min(width,height,display_width,display_height)<=0:raise ValueError('页面尺寸不合法')
    return [box[0]*display_width/width,box[1]*display_height/height,box[2]*display_width/width,box[3]*display_height/height]
