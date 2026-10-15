"""问句结构的项目实体消歧；不删字符，以正文头部声明和版本/日期作核对。"""
import copy
import re

VERSION=r'(?:[A-Za-z][A-Za-z0-9_.-]*|[0-9]+(?:\.[0-9]+)*)版本'
ENTITY=r'[一-鿿A-Za-z0-9]+项目'
HEAD=re.compile(r'^(?P<entity>'+ENTITY+r')(?P<version>'+VERSION+r')(?:在)?(?P<date>[0-9]{4}-[0-9]{2})(?P<declaration>的记录[:：])')
QUESTION=re.compile(r'^(?P<entity>'+ENTITY+r')(?P<version>'+VERSION+r')')

def resolve_question_scope(question,passages,raw_scope):
    scope=copy.deepcopy(raw_scope)
    audit={'status':'unknown','question_candidates':[],'body_declarations':[],
        'question_original':question,'reason':None,'missing_fields_not_assumed_equal':True}
    heads=list(QUESTION.finditer(question))
    if len(heads)!=1 or len(scope.get('version',[]))!=1 or heads[0]['version']!=scope['version'][0]:
        audit['reason']='question_entity_version_boundary_not_unique';return scope,audit
    head=heads[0]
    if not re.search(r'(?:选择|多少|是什么|哪)',question[head.end():]):
        audit['reason']='question_structure_not_recognized';return scope,audit
    literal={'entity':head['entity'],'interpretation':'literal_entity_no_char_removed',
        'start':head.start('entity'),'end':head.end('entity'),'version_position':[head.start('version'),head.end('version')]}
    candidates=[literal]
    for guide in ('按照','根据','依据','按'):
        guided=re.fullmatch(re.escape(guide)+r'(?P<entity>'+ENTITY+r')',head['entity'])
        if guided:
            candidates.append({'entity':guided['entity'],'interpretation':'leading_question_guide',
                'guide':guide,'start':guided.start('entity'),'end':guided.end('entity'),
                'version_position':[head.start('version'),head.end('version')]})
    declarations=[]
    for passage in passages:
        match=HEAD.match(passage['text'])
        if match:
            declarations.append({'entity':match['entity'],'version':match['version'],'date':match['date'],
                'passage_id':passage['id'],'source':passage['source'],'start':match.start(),'end':match.end(),
                'quote':match.group(),'entity_start':match.start('entity'),'entity_end':match.end('entity')})
    audit.update(question_candidates=candidates,body_declarations=declarations)
    declared={d['entity'] for d in declarations}
    possible=[c for c in candidates if c['entity'] in declared]
    if len(possible)!=1:
        audit['reason']='zero_or_multiple_declared_entity_interpretations';return scope,audit
    chosen=possible[0]
    supporting=[d for d in declarations if d['entity']==chosen['entity'] and d['version']==head['version']
        and (not scope.get('date') or scope['date']==[d['date']])]
    if not supporting:
        audit['reason']='entity_declaration_version_or_date_not_confirmed';return scope,audit
    scope['project']=[chosen['entity']]
    audit.update(status='resolved',reason='unique_question_interpretation_confirmed_by_body_entity_version_date',
        chosen=chosen,supporting_declarations=supporting)
    return scope,audit
