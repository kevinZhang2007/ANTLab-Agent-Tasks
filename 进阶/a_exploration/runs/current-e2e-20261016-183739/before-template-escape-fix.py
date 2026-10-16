"""统一单侧入口及共享查询配对；不读取任务、答案或历史模型输出。"""
import copy,json,time,uuid,urllib.request,urllib.error
from runtime import Engine as RecordedEngine,TechnicalStop,CapacityStop,load,write,sha_text,now,config as original_config
from engine import answer_messages,query_messages,retrieve,neighbors,public,parse_terms
from sentence_selection import adapt_messages,build_index,schema,expand,CANDIDATE_PROMPT
from compact_factorial import compact_messages,audit
from reason_citations import adapt,NOTE
from sentence_interface import interface_response

def build_answer(claim,blocks,doc_ids,snapshot,base_config):
    blocks=[public(b) for b in blocks];index=build_index(blocks,doc_ids,snapshot)
    original=adapt_messages(answer_messages(claim,blocks),index)
    compact=compact_messages(original,blocks,index,doc_ids,snapshot);messages=adapt(compact)
    assert messages[0]['content']==CANDIDATE_PROMPT+NOTE and messages[1:]==compact[1:]
    check=audit(messages,blocks,index,doc_ids,snapshot)
    conf=copy.deepcopy(base_config);conf['parameters']['response_format']={'type':'json_schema','json_schema':{'schema':schema(index)}}
    return messages,conf,index,check

def query_config():
    c=original_config('query');c['parameters']['chat_template_kwargs']={'enable_thinking':False};return c

class CurrentEngine(RecordedEngine):
    def __init__(self,folder):
        super().__init__(folder);self.configuration=load(folder/'configuration.json');self.answer_base=self.configuration['request_common']
    def capacity(self,messages,conf,label):
        body={'model':conf['model'],'messages':messages,'stream':False,**conf['parameters']};path=self.folder/('capacity-'+label+'.json')
        check={'checked_at':now(),'label':label,'actual_request_body':body,'context':4096,'output_budget':body['max_tokens'],'run_kind':'local_rule','generation_calls':0};write(path,check)
        def http(route,payload,key):
            check[key]={'url':self.url+route,'request':payload};write(path,check)
            req=urllib.request.Request(self.url+route,data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
            try:
                with self.opener.open(req,timeout=30) as r:raw=r.read().decode();status=r.status
                check[key].update(http_status=status,raw_response=raw);write(path,check);return json.loads(raw)
            except Exception as e:
                check[key]['error']=repr(e)
                if isinstance(e,urllib.error.HTTPError):check[key].update(http_status=e.code,raw_response=e.read().decode(errors='replace'))
                write(path,check);raise
        template=http('apply-template',body,'template_http');prompt=template.get('prompt','');check.update(template_response=template,rendered_prompt=prompt);write(path,check)
        (self.folder/('rendered-'+label+'.txt')).write_text(prompt,encoding='utf-8')
        tok=http('tokenize',{'content':prompt,'add_special':True,'parse_special':True},'tokenize_http');flag=body['chat_template_kwargs']['enable_thinking'];suffix=prompt.rsplit('<|im_start|>assistant\n',1)[-1]
        checks={'boolean_mode':type(flag) is bool,'expected_budget':body['max_tokens']==(1024 if flag else 128),'branch':suffix==('' if flag else '<think>\n\n</think>\n\n'),'all_messages_present':all(m['content'] in prompt for m in messages),'fits':len(tok['tokens'])+body['max_tokens']<=4096}
        check.update(token_response=tok,input_tokens=len(tok['tokens']),checks=checks,fits=checks['fits'],actual_generation_suffix=suffix,actual_enable_thinking_request=flag,not_echoed=['内部enable_thinking布尔状态','编译grammar与PEG对象']);write(path,check)
        if not all(checks.values()):raise CapacityStop('阶段模板/完整资料/容量门禁失败，证据已保存')
        return check
    def execute(self,claim,doc_ids,snapshot,mode='improved'):
        if mode not in ('baseline','improved'):raise ValueError('unknown mode')
        return self._execute_modes(claim,doc_ids,snapshot,[mode])
    def execute_pair(self,claim,doc_ids,snapshot,order):
        if sorted(order)!=['baseline','improved']:raise ValueError('invalid pair order')
        return self._execute_modes(claim,doc_ids,snapshot,order)
    def _execute_modes(self,claim,doc_ids,snapshot,modes):
        if self.technical_stop:raise TechnicalStop('上次技术失败，不再调用')
        blocks=self.corpus.scope(doc_ids,snapshot)
        if not isinstance(claim,str) or not claim.strip():raise ValueError('empty claim')
        key=sha_text(json.dumps([claim,doc_ids,snapshot],ensure_ascii=False))
        if key in self.started:raise ValueError('同一输入已尝试，不重发')
        self.started.add(key);pid=str(uuid.uuid4());start=time.perf_counter();path=self.folder/('pair-'+pid+'.json')
        pair={'request_id':pid,'claim':claim,'doc_ids':doc_ids,'snapshot':snapshot,'order':modes,'status':'started','shared_query':None,'arms':{},'run_kind':'live_api','judgment_source':'model','started_at':now(),'scope_blocks':[public(b) for b in blocks],'version':'compact-thinking-sentence-reason-citations'}
        write(path,pair);self.event('pair_start',request_id=pid,doc_ids=doc_ids,snapshot=snapshot,version=pair['version'])
        try:
            qstart=time.perf_counter();qraw=self.generate(query_messages(claim),query_config(),'query-'+pid,pid,[]);pair['shared_query']=qraw;pair['shared_query_wall_seconds']=time.perf_counter()-qstart;write(path,pair)
            try:terms=parse_terms(qraw['content'])
            except (ValueError,TypeError,json.JSONDecodeError) as e:pair.update(status='query_quality_failure',error=repr(e));return pair
            rstart=time.perf_counter();seeds,scores=retrieve(terms,blocks);extended,added=neighbors(seeds,blocks);pair.update(retrieval_terms=terms,retrieval_scores=scores,seed_ids=[b['block_id'] for b in seeds],added_neighbors=added,retrieval_seconds=time.perf_counter()-rstart)
            prepared={};prep_times={}
            for arm in modes:
                t=time.perf_counter();used=seeds if arm=='baseline' else extended;ms,conf,index,bytecheck=build_answer(claim,used,doc_ids,snapshot,self.answer_base)
                self.capacity(ms,conf,'before-pair-'+pid+'-'+arm);prepared[arm]=(used,ms,conf,index,bytecheck);prep_times[arm]=time.perf_counter()-t
            for arm in modes:
                used,ms,conf,index,bytecheck=prepared[arm];mid=str(uuid.uuid4());t=time.perf_counter();raw=self.generate(ms,conf,arm+'-'+pid,mid,used)
                params=raw['slot_after'][0].get('params',{});assert raw['actual_http_request_body']['max_tokens']==1024 and params.get('max_tokens')==1024 and params.get('presence_penalty')==1.5 and params.get('repeat_penalty')==1.0
                ex=expand(raw['content'],[public(b) for b in used],index,doc_ids,snapshot);write(self.folder/('expansion-'+raw['run_id']+'.json'),ex)
                interface=interface_response(mid,claim,doc_ids,snapshot,raw['run_id'],ex,raw['elapsed_seconds'],locator=self.locator,actual_input_blocks=used)
                interface.update(end_to_end_note='自动完整流程，流程组件耗时和整对实测时间另列；非固定证据重放。')
                view={'main_task_id':mid,'parent_request_id':pid,'variant':arm,'raw_record':raw,'actual_input_passages':[public(b) for b in used],'sentence_index':index,'byte_audit':bytecheck,'format_complete':ex['valid'],'status':'returned' if ex['valid'] else 'answer_quality_failure','parsed':ex['expanded_response'] or {},'claim_judgment':interface['answer'],'claim_judgment_source':'model','support_status':'not_checked','judgment_source':'unverified','locator_status':interface['locator_status'],'evidence':[],'expansion_record':'expansion-'+raw['run_id']+'.json','interface_response':interface}
                for e in interface['evidence']:view['evidence'].append({**e,'location':e['pdf_location'],'citation_semantic_support':'not_checked'})
                view.update(answer_stage_wall_seconds=time.perf_counter()-t,preparation_seconds=prep_times[arm],shared_query_cost_share=1/len(modes))
                view['reconstructed_flow_seconds']=pair['shared_query_wall_seconds']+pair['retrieval_seconds']+view['preparation_seconds']+view['answer_stage_wall_seconds']
                view['allocated_total_seconds']=(pair['shared_query_wall_seconds']+pair['retrieval_seconds'])/len(modes)+view['preparation_seconds']+view['answer_stage_wall_seconds']
                view['cost_note']='共享查询只计一次；各侧分摊一半公共耗时和usage。reconstructed_flow_seconds为实测组件和，非两条独立请求计时；pair_elapsed_seconds为整对实测。'
                pair['arms'][arm]=view;write(path,pair);self.event('arm_result',request_id=mid,parent_request_id=pid,variant=arm,run_id=raw['run_id'],locator_status=view['locator_status'],semantic_support='not_checked')
            pair['status']='completed';return pair
        except Exception as e:self.technical_stop=True;pair.update(status='technical_stop',error=repr(e));self.event('technical_stop',request_id=pid,error=repr(e),dispatches=self.dispatches);raise
        finally:pair.update(pair_elapsed_seconds=time.perf_counter()-start,ended_at=now());write(path,pair);self.event('pair_saved',request_id=pid,status=pair['status'],path=path.name)
