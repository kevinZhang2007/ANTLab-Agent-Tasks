"""确定性句子索引及来源展开；不选择证据、不修正模型判断。"""
import copy,json,re
from engine import ANSWER_PROMPT

OLD_FORMAT='只返回JSON：{"label":"supported|contradicted|insufficient","reason":"简短中文理由","evidence":[{"block_id":"本次段落ID","quote":"对应连续原文"}]}。'
NEW_FORMAT='只返回JSON：{"label":"supported|contradicted|insufficient","reason":"简短中文理由","sentence_ids":["本次句子索引ID"]}。'
assert ANSWER_PROMPT.count(OLD_FORMAT)==1
FORMAT_NOTE='\n输出格式适配：sentence_ids只选择本次sentence_index中的编号，程序会逐字展开所选片段；模型不生成quote或evidence。不选未知或重复编号，可以返回空列表。没有选中句子不代表判断已被支持。'
CANDIDATE_PROMPT=ANSWER_PROMPT.replace(OLD_FORMAT,NEW_FORMAT).replace('evidence为空','sentence_ids为空')+FORMAT_NOTE
ABBREVIATIONS={'e.g','i.e','et','al','fig','figs','dr','mr','mrs','ms','prof','vs','etc','no','vol','pp','p','inc','jr','sr','approx','cf','st'}
CLOSERS='\"\'”’」』)]）'

def spans(text):
    if not text:return []
    result=[];start=0;i=0
    while i<len(text):
        char=text[i];boundary=char in '。！？!?'
        if char=='.':
            before=text[:i];last=re.search(r'[^\s]+$',before);token=last.group() if last else ''
            word=re.search(r'(?:[A-Za-z]\.)*[A-Za-z]+$',before);word=word.group().casefold() if word else ''
            decimal=i>0 and i+1<len(text) and text[i-1].isdigit() and text[i+1].isdigit()
            acronym=bool(re.fullmatch(r'(?:[A-Za-z]\.)+[A-Za-z]',word))
            boundary=not(decimal or word in ABBREVIATIONS or (len(word)==1 and word.isalpha()) or acronym or '://' in token or '@' in token or token.startswith('www.'))
        if boundary:
            end=i+1
            while end<len(text) and text[end] in CLOSERS:end+=1
            # 英文标点后非空白时保守合并；中文句末无需空格。
            if char in '.!?' and end<len(text) and not text[end].isspace():boundary=False
            if boundary:
                while end<len(text) and text[end].isspace():end+=1
                result.append((start,end));start=end;i=end;continue
        i+=1
    if start<len(text):result.append((start,len(text)))
    return result

def build_index(blocks,doc_ids,snapshot):
    by_id={}
    for b in blocks:
        if b['block_id'] in by_id:raise ValueError('重复块ID')
        if b['doc_id'] not in doc_ids or b['snapshot']!=snapshot:raise ValueError('块不属于本次资料范围')
        if not isinstance(b['text'],str):raise ValueError('原文不是字符串')
        by_id[b['block_id']]=b
    rows=[]
    for b in blocks:
        pieces=spans(b['text']);assert ''.join(b['text'][a:z] for a,z in pieces)==b['text']
        for start,end in pieces:
            rows.append({'sentence_id':'sent-'+str(len(rows)+1).zfill(4),'block_id':b['block_id'],'doc_id':b['doc_id'],'snapshot':b['snapshot'],'text':b['text'][start:end],'start':start,'end':end,'offset_unit':'unicode_code_point','interval':'[start,end)','segmentation':'conservative_punctuation_or_complete_fragment'})
    return rows

def schema(index):
    ids=[r['sentence_id'] for r in index]
    if len(ids)!=len(set(ids)):raise ValueError('重复句子索引ID')
    array={'type':'array','items':{'type':'string'}}
    if ids:array['items']['enum']=ids
    else:array['maxItems']=0
    return {'type':'object','properties':{'label':{'type':'string','enum':['supported','contradicted','insufficient']},'reason':{'type':'string'},'sentence_ids':array},'required':['label','reason','sentence_ids'],'additionalProperties':False}

def adapt_messages(original,index):
    result=copy.deepcopy(original);assert result[0]['content']==ANSWER_PROMPT
    result[0]['content']=CANDIDATE_PROMPT;user=json.loads(result[1]['content']);user['sentence_index']=copy.deepcopy(index)
    result[1]['content']=json.dumps(user,ensure_ascii=False,indent=2)
    return result

def expand(content,blocks,index,doc_ids,snapshot):
    outcome={'run_kind':'local_rule','judgment_source':'rule','operation':'model_selection_program_verbatim_expansion','raw_internal_content':content,'parsed_internal':None,'valid':False,'expanded_response':None,'selected_sources':[],'semantic_support':'not_checked','label_changed':False,'repair_applied':False,'added_unselected_sentences':False}
    try:
        if index!=build_index(blocks,doc_ids,snapshot):raise ValueError('索引/字符位置与本次完整原文不一致')
        obj=json.loads(content);outcome['parsed_internal']=obj
        if not isinstance(obj,dict) or set(obj)!={'label','reason','sentence_ids'}:raise ValueError('内部JSON字段不合法')
        if obj['label'] not in ('supported','contradicted','insufficient') or not isinstance(obj['reason'],str):raise ValueError('label/reason不合法')
        selected=obj['sentence_ids'];by_id={r['sentence_id']:r for r in index}
        if not isinstance(selected,list) or not all(isinstance(x,str) for x in selected):raise ValueError('sentence_ids不是字符串数组')
        if len(set(selected))!=len(selected):raise ValueError('重复选择sentence_id，不去重修补')
        if any(x not in by_id for x in selected):raise ValueError('未知sentence_id，不补选')
        evidence=[]
        for sid in selected:
            r=copy.deepcopy(by_id[sid]);b=next(b for b in blocks if b['block_id']==r['block_id'])
            assert b['doc_id'] in doc_ids and b['snapshot']==snapshot and b['text'][r['start']:r['end']]==r['text']
            outcome['selected_sources'].append(r);evidence.append({'block_id':r['block_id'],'quote':r['text']})
        outcome['expanded_response']={'label':obj['label'],'reason':obj['reason'],'evidence':evidence}
        outcome['valid']=True
    except (ValueError,TypeError,KeyError,AssertionError) as e:outcome['error']=repr(e)
    return outcome

def offline_checks():
    tests=[]
    def test(name,value):
        tests.append({'name':name,'passed':bool(value)})
        if not value:raise AssertionError(name)
    def block(text,bid='made-up-a',doc='made-up'):return {'block_id':bid,'doc_id':doc,'snapshot':'published','text':text}
    for name,text,count in [('abbreviation_decimal','Dr. Vale used e.g. version 2.5. Next step.',2),('newline','First line\ncontinues. Next.',2),('quotes','He said "Keep it." Next.',2),('unicode','甲🙂。乙！',2),('no_safe_boundary','Ambiguous fragment without an ending',1),('URL','Use https://example.org/v1.2 safely. Done.',2),('whitespace',' \n ',1)]:
        ss=spans(text);test(name+'_coverage',len(ss)==count and ''.join(text[a:z] for a,z in ss)==text and (not ss or ss[0][0]==0 and ss[-1][1]==len(text)) and all(ss[i][1]==ss[i+1][0] for i in range(len(ss)-1)))
    blocks=[block('Same sentence. Same sentence.'),block('Same sentence.','made-up-b')];idx=build_index(blocks,['made-up'],'published')
    test('repeated_sentences_unique_positions',len(idx)==3 and len({r['sentence_id'] for r in idx})==3 and idx[0]['start']!=idx[1]['start'])
    def content(ids,label='supported'):return json.dumps({'label':label,'reason':'自造选择，不是语义标签验证','sentence_ids':ids})
    exp=expand(content([idx[1]['sentence_id'],idx[0]['sentence_id']]),blocks,idx,['made-up'],'published')
    test('different_sentences_same_block_allowed_order_preserved',exp['valid'] and [r['sentence_id'] for r in exp['selected_sources']]==[idx[1]['sentence_id'],idx[0]['sentence_id']] and len(exp['expanded_response']['evidence'])==2)
    test('exact_quote_and_scope',all(next(b for b in blocks if b['block_id']==r['block_id'])['text'][r['start']:r['end']]==e['quote'] for r,e in zip(exp['selected_sources'],exp['expanded_response']['evidence'])))
    for name,selection in [('unknown',['missing']),('duplicate',[idx[0]['sentence_id']]*2)]:
        bad=expand(content(selection),blocks,idx,['made-up'],'published');test(name+'_rejected_not_repaired',not bad['valid'] and bad['expanded_response'] is None and not bad['repair_applied'] and bad['parsed_internal']['label']=='supported')
    empty=expand(content([]),blocks,idx,['made-up'],'published');test('empty_selection_preserves_label',empty['valid'] and empty['expanded_response']['label']=='supported' and empty['expanded_response']['evidence']==[] and empty['semantic_support']=='not_checked')
    test('fence_not_stripped',not expand('```json\n'+content([])+'\n```',blocks,idx,['made-up'],'published')['valid'])
    corrupt=copy.deepcopy(idx);corrupt[0]['end']-=1;test('stale_or_wrong_position_rejected',not expand(content([idx[0]['sentence_id']]),blocks,corrupt,['made-up'],'published')['valid'])
    split=[block('An unfinished','one'),block(' continuation.','two')];s=build_index(split,['made-up'],'published');test('never_merge_across_blocks',len(s)==2 and s[0]['block_id']!=s[1]['block_id'])
    remap=[{**b,'block_id':'remapped-'+str(i)} for i,b in enumerate(blocks)];ri=build_index(remap,['made-up'],'published');rexp=expand(content([ri[0]['sentence_id']]),remap,ri,['made-up'],'published');test('block_id_remapping',rexp['valid'] and rexp['expanded_response']['evidence'][0]['block_id']=='remapped-0')
    leaked=False
    try:build_index([block('foreign.','foreign','other-doc')],['made-up'],'published')
    except ValueError:leaked=True
    test('cross_doc_rejected',leaked)
    test('empty_blocks',build_index([],['made-up'],'published')==[] and schema([])['properties']['sentence_ids']['maxItems']==0)
    test('semantic_rules_unchanged',CANDIDATE_PROMPT[:-len(FORMAT_NOTE)].replace(NEW_FORMAT,OLD_FORMAT).replace('sentence_ids为空','evidence为空')==ANSWER_PROMPT)
    test('index_text_exact_not_stripped',all(r['text']==next(b for b in blocks if b['block_id']==r['block_id'])['text'][r['start']:r['end']] for r in idx))
    return {'passed':True,'count':len(tests),'checks':tests,'generation_calls':0,'limits':'保守标点切分，缩写/链接等不确定处合并，可能多句作为片段；完整覆盖不等于语言学分句完美或语义支持。'}
