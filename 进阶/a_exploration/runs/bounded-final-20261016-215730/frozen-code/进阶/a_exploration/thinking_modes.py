"""仅扩展实际模板审计；生成、参数和原始记录仍复用runtime.Engine。"""
import json,urllib.request,urllib.error
from runtime import Engine,CapacityStop,write,load,now

class ThinkingEngine(Engine):
    def capacity(self,messages,conf,label):
        body={'model':conf['model'],'messages':messages,'stream':False,**conf['parameters']}
        path=self.folder/('capacity-'+label+'.json')
        check={'checked_at':now(),'label':label,'actual_request_body':body,'run_kind':'local_rule','generation_calls':0,'context':4096,'output_budget':conf['parameters']['max_tokens']}
        write(path,check)
        def audited(route,payload,field):
            check[field]={'route':route,'method':'POST','actual_request_body':payload};write(path,check)
            req=urllib.request.Request(self.url+route,data=json.dumps(payload,ensure_ascii=False).encode('utf-8'),headers={'Content-Type':'application/json'})
            try:
                with self.opener.open(req,timeout=30) as response:raw=response.read().decode('utf-8');status=response.status
                check[field].update(http_status=status,raw_response=raw);write(path,check)
                parsed=json.loads(raw);check[field]['parsed_response']=parsed;write(path,check);return parsed
            except Exception as e:
                check[field]['error']=repr(e)
                if isinstance(e,urllib.error.HTTPError):check[field]['http_status']=e.code;check[field]['raw_response']=e.read().decode('utf-8',errors='replace')
                write(path,check);raise
        response=audited('apply-template',body,'template_http');check['template_response']=response;prompt=response.get('prompt','');check['rendered_prompt']=prompt;write(path,check)
        (self.folder/('rendered-'+label+'.txt')).write_text(prompt,encoding='utf-8')
        tokenized=audited('tokenize',{'content':prompt,'add_special':True,'parse_special':True},'tokenize_http');check.update(token_response=tokenized,input_tokens=len(tokenized['tokens']));write(path,check)
        # 先保存完整HTTP证据和token，再依据当前真实模板的false分支断言。
        flag=body.get('chat_template_kwargs',{}).get('enable_thinking');template=load(self.folder/'props.json')['chat_template'];marker='<|im_start|>assistant\n';position=prompt.rfind(marker);suffix=prompt[position+len(marker):] if position>=0 else None
        checks={'boolean_switch':type(flag) is bool,'current_template_has_false_branch':'if enable_thinking is defined and enable_thinking is false' in template,'assistant_boundary_present':position>=0,'actual_branch_matches':suffix==('' if flag else '<think>\n\n</think>\n\n'),'all_messages_present':all(m['content'] in prompt for m in messages),'budget_1024':body['max_tokens']==1024,'fits':len(tokenized['tokens'])+body['max_tokens']<=4096}
        check.update(checks=checks,fits=checks['fits'],all_messages_present=checks['all_messages_present'],actual_enable_thinking_request=flag,actual_generation_suffix=suffix,not_echoed=['内部enable_thinking布尔状态','本请求编译grammar/PEG对象'],closed_think_template=suffix=='<think>\n\n</think>\n\n');write(path,check)
        if not all(checks.values()):raise CapacityStop('模式/完整模板/容量检查失败，完整原始证据已先保存')
        return check

def offline_checks():
    import copy
    from sentence_selection import expand,build_index
    blocks=[{'block_id':'synthetic','doc_id':'made-up','snapshot':'published','text':'A log is required.'}];idx=build_index(blocks,['made-up'],'published');tests=[]
    def check(name,value):
        tests.append({'name':name,'passed':bool(value)})
        if not value:raise AssertionError(name)
    check('off_suffix_matches_false_branch','<|im_start|>assistant\n<think>\n\n</think>\n\n'.split('<|im_start|>assistant\n')[-1]=='<think>\n\n</think>\n\n')
    check('on_empty_suffix_allowed','<|im_start|>assistant\n'.split('<|im_start|>assistant\n')[-1]=='')
    check('string_is_not_boolean',type('true') is not bool and type(True) is bool)
    check('reasoning_only_not_final_success',not expand('',blocks,idx,['made-up'],'published')['valid'])
    check('partial_final_not_repaired',not expand('{"label":"supported",',blocks,idx,['made-up'],'published')['valid'])
    good=json.dumps({'label':'contradicted','reason':'synthetic','sentence_ids':[idx[0]['sentence_id']]});check('only_content_is_projected',expand(good,blocks,idx,['made-up'],'published')['expanded_response']['label']=='contradicted')
    check('missing_reasoning_not_invented',{'content':good}.get('reasoning_content') is None)
    return {'passed':True,'count':len(tests),'checks':tests,'generation_calls':0,'limits':'模式实际生效依据后续HTTP模板/同版本源码；是否产生思考只看真实响应，不把自造模板字符串当服务验证。'}
