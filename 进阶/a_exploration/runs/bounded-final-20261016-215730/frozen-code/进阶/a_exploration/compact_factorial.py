"""独立输入组织因素；不改变system、句子选择或原文。"""
import copy,json,hashlib
from sentence_selection import build_index

def compact_messages(messages,blocks,index,doc_ids,snapshot):
    if index!=build_index(blocks,doc_ids,snapshot):raise ValueError('索引与原段/范围不一致')
    result=copy.deepcopy(messages);user=json.loads(result[1]['content'])
    if set(user)!={'claim','passages','sentence_index'} or user['sentence_index']!=index or user['passages']!=blocks:raise ValueError('不是已归档句子选择输入')
    compact=[]
    for b in blocks:
        rows=[s for s in index if s['block_id']==b['block_id']]
        if ''.join(s['text'] for s in rows).encode('utf-8')!=b['text'].encode('utf-8'):raise ValueError('原文无法逐字节重建')
        compact.append({k:copy.deepcopy(b[k]) for k in ['block_id','doc_id','snapshot','heading']})
        compact[-1]['sentence_index']=[{'sentence_id':s['sentence_id'],'text':s['text']} for s in rows]
    result[1]['content']=json.dumps({'passages':compact,'claim':user['claim']},ensure_ascii=False,indent=2)
    return result

def audit(messages,blocks,index,doc_ids,snapshot):
    if index!=build_index(blocks,doc_ids,snapshot):raise ValueError('服务端原索引不一致')
    user=json.loads(messages[1]['content']);ps=user['passages'];seen=[];rows=[]
    if list(user)!=['passages','claim'] or len(ps)!=len(blocks):raise ValueError('顺序或段落数量不符')
    for b,p in zip(blocks,ps):
        if set(p)!={'block_id','doc_id','snapshot','heading','sentence_index'}:raise ValueError('紧凑段落字段不符')
        if any(p[k]!=b[k] for k in ['block_id','doc_id','snapshot','heading']):raise ValueError('来源/标题/顺序不符')
        original=[s for s in index if s['block_id']==b['block_id']]
        if p['sentence_index']!=[{'sentence_id':s['sentence_id'],'text':s['text']} for s in original]:raise ValueError('句子ID/顺序/正文不符')
        rebuilt=''.join(s['text'] for s in p['sentence_index']).encode('utf-8');raw=b['text'].encode('utf-8')
        if rebuilt!=raw:raise ValueError('原文UTF-8字节不一致')
        seen.extend(s['sentence_id'] for s in p['sentence_index']);rows.append({'block_id':b['block_id'],'bytes':len(raw),'source_sha256':hashlib.sha256(raw).hexdigest(),'rebuilt_sha256':hashlib.sha256(rebuilt).hexdigest(),'byte_identical':True})
    if seen!=[s['sentence_id'] for s in index]:raise ValueError('全局句子顺序不符')
    return {'passed':True,'paragraphs':rows,'sentence_ids_in_original_order':seen,'claim_last':True,'server_only_fields':['字符位置','offset_unit','interval','segmentation','section_id','paragraph_index'],'semantic_support':'not_checked'}

def offline_checks():
    from engine import answer_messages,public
    from sentence_selection import adapt_messages,expand
    blocks=[{'block_id':'sample-a','doc_id':'made-up','snapshot':'published','section_id':'one','heading':'Made-up heading','paragraph_index':0,'text':'  First "quoted" line.\nSecond\tline 2.5. 重复。重复。🙂\n'},{'block_id':'sample-b','doc_id':'made-up','snapshot':'published','section_id':'two','heading':'Other heading','paragraph_index':0,'text':'Another clause without terminal punctuation  '}]
    idx=build_index(blocks,['made-up'],'published');ms=adapt_messages(answer_messages('不应删除原文，仅保留一次。',blocks),idx);before=copy.deepcopy((ms,blocks,idx));new=compact_messages(ms,blocks,idx,['made-up'],'published');tests=[]
    def check(name,value):
        tests.append({'name':name,'passed':bool(value)})
        if not value:raise AssertionError(name)
    check('all_bytes_and_order',audit(new,blocks,idx,['made-up'],'published')['passed'])
    check('inputs_not_mutated',(ms,blocks,idx)==before)
    check('system_and_roles_unchanged',new[0]==ms[0] and [m['role'] for m in new]==[m['role'] for m in ms])
    check('claim_exact_once_and_last',json.loads(new[1]['content'])['claim']==json.loads(ms[1]['content'])['claim'] and new[1]['content'].count('不应删除原文，仅保留一次。')==1 and list(json.loads(new[1]['content']))[-1]=='claim')
    for name,mutate in [('whitespace',lambda u:u['passages'][0]['sentence_index'][0].update(text=u['passages'][0]['sentence_index'][0]['text'].strip())),('unknown_id',lambda u:u['passages'][0]['sentence_index'][0].update(sentence_id='missing')),('wrong_scope',lambda u:u['passages'][0].update(doc_id='other')),('dropped_sentence',lambda u:u['passages'][0]['sentence_index'].pop()),('order_changed',lambda u:u['passages'].reverse())]:
        bad=copy.deepcopy(new);u=json.loads(bad[1]['content']);mutate(u);bad[1]['content']=json.dumps(u,ensure_ascii=False)
        try:audit(bad,blocks,idx,['made-up'],'published');caught=False
        except ValueError:caught=True
        check(name+'_rejected',caught)
    raw=json.dumps({'label':'contradicted','reason':'synthetic','sentence_ids':[idx[1]['sentence_id'],idx[0]['sentence_id']]});a=expand(raw,blocks,idx,['made-up'],'published');check('same_expansion_and_label',a['valid'] and a['expanded_response']['label']=='contradicted' and a['selected_sources'][0]['text']==idx[1]['text'])
    empty=adapt_messages(answer_messages('No material.',[]),[]);ce=compact_messages(empty,[],[],['made-up'],'published');check('empty_materials',audit(ce,[],[],['made-up'],'published')['passed'])
    return {'passed':True,'count':len(tests),'checks':tests,'generation_calls':0,'scope':'验证组织与字节，不证明模型理解或语义支持。'}
