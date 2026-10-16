from pathlib import Path
import copy,ctypes,datetime,hashlib,json,math,os,sys,time,uuid,urllib.request,re,importlib.util
from engine import ROOT,HERE,Corpus,query_messages,answer_messages,parse_terms,parse_answer,public,retrieve,neighbors,QUERY_SCHEMA,ANSWER_SCHEMA
from locator import Locator
spec=importlib.util.spec_from_file_location('a_shared_provider',ROOT/'基础/starter/provider.py')
provider=importlib.util.module_from_spec(spec);spec.loader.exec_module(provider)
call_model=provider.call_model

def now():return datetime.datetime.now().astimezone().isoformat()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='\n') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())

class Memory(ctypes.Structure):
    _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ('total','available','total_page','available_page','total_virtual','available_virtual','extended')]
def memory():
    m=Memory();m.length=ctypes.sizeof(m)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):raise OSError('无法测量物理内存')
    return {'time':now(),'total_bytes':m.total,'available_bytes':m.available}

class TechnicalStop(RuntimeError):pass
class CapacityStop(TechnicalStop):pass

def config(stage):
    value=load(HERE/'config.json');parameters=value['parameters']
    parameters['response_format']={'type':'json_schema','json_schema':{'schema':QUERY_SCHEMA if stage=='query' else ANSWER_SCHEMA}}
    if stage=='query':parameters.update(temperature=0.0,max_tokens=128)
    return value

class Engine:
    def __init__(self,folder):
        self.folder=folder;self.corpus=Corpus(load(ROOT/'进阶/materials/sections.json'));self.locator=Locator(load(ROOT/'进阶/materials/page_words.json'))
        self.dispatches=0;self.completed=0;self.started=set();self.technical_stop=False
        self.url='http://127.0.0.1:8080/';self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def service(self,path,body=None):
        req=urllib.request.Request(self.url+path,data=None if body is None else json.dumps(body,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
        with self.opener.open(req,timeout=30) as r:return json.loads(r.read())

    def event(self,event,**fields):
        with (self.folder/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'at':now(),'event':event,**fields},ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())

    def capacity(self,messages,conf,label):
        body={'model':conf['model'],'messages':messages,'stream':False,**conf['parameters']}
        response=self.service('apply-template',body);prompt=response.get('prompt','')
        tokenized=self.service('tokenize',{'content':prompt,'add_special':True,'parse_special':True})
        check={'checked_at':now(),'label':label,'actual_request_body':body,'template_response':response,'token_response':tokenized,'input_tokens':len(tokenized['tokens']),'output_budget':conf['parameters']['max_tokens'],'context':4096,'run_kind':'local_rule','generation_calls':0}
        check['fits']=check['input_tokens']+check['output_budget']<=4096
        check['all_messages_present']=all(m['content'] in prompt for m in messages)
        check['closed_think_template']='<think>\n\n</think>' in prompt and not prompt.endswith('<think>\n')
        write(self.folder/('capacity-'+label+'.json'),check)
        if not all(check[x] for x in ['fits','all_messages_present','closed_think_template']):raise CapacityStop('完整模板、关闭思考或容量检查失败')
        return check

    def generate(self,messages,conf,label,request_id,blocks):
        if self.technical_stop or self.dispatches>=9:raise TechnicalStop('本轮请求停止或已到9次上限')
        if memory()['available_bytes']<1024**3:raise TechnicalStop('请求前可用内存低于1 GiB')
        checked=self.capacity(messages,conf,label)
        rid=str(uuid.uuid4());path=self.folder/('run-'+rid+'.json')
        record={'run_id':rid,'request_id':request_id,'stage':label,'run_kind':'live_api','judgment_source':'model','started_at':now(),'messages':messages,'config':copy.deepcopy(conf),'actual_input_passages':[public(b) for b in blocks],'actual_http_request_body':checked['actual_request_body'],'input_tokens':checked['input_tokens'],'attempt':1,'retry_of':None,'generation_dispatched':False,'memory_before':memory()}
        write(path,record);self.service('slots/0?action=erase',{})
        log=self.folder/'model-stderr.log';offset=log.stat().st_size
        original_build=urllib.request.build_opener;owner=self
        class Capture:
            def __init__(self,opener):self.opener=opener
            def open(self,request,*args,**kwargs):
                body=json.loads(request.data)
                if body!=checked['actual_request_body']:raise TechnicalStop('实际HTTP正文与容量检查不一致')
                record['actual_http_request_raw']=request.data.decode('utf-8');record['generation_dispatched']=True
                owner.dispatches+=1;write(path,record);owner.event('model_request',request_id=request_id,run_id=rid,stage=label,record=path.name)
                return self.opener.open(request,*args,**kwargs)
        urllib.request.build_opener=lambda *a,**kw:Capture(original_build(*a,**kw))
        try:record.update(call_model(messages,conf))
        except Exception as e:
            record.update(status='technical_error',error=repr(e));raise
        finally:urllib.request.build_opener=original_build;write(path,record)
        record['memory_after']=memory()
        with log.open('rb') as f:f.seek(offset);record['server_log_segment']=f.read().decode('utf-8',errors='replace')
        if record.get('status')!='ok' or not isinstance(record.get('response'),dict) or not record['response'].get('choices'):
            write(path,record);raise TechnicalStop('模型请求技术失败；不自动重发，实际执行状态须从日志核查')
        choice=record['response']['choices'][0];message=choice.get('message',{})
        record.update(content=message.get('content',''),reasoning_content=message.get('reasoning_content'),finish_reason=choice.get('finish_reason'))
        if (record.get('usage') or {}).get('completion_tokens',0)>0:self.completed+=1
        slots=self.service('slots');record['slot_after']=slots
        params=slots[0].get('params',{})
        numeric={k:v for k,v in conf['parameters'].items() if isinstance(v,(int,float)) and k!='max_tokens'}
        record['echoed_parameter_checks']={k:math.isclose(params[k],v,rel_tol=1e-6,abs_tol=1e-6) for k,v in numeric.items() if k in params}
        record['not_echoed']=[k for k in numeric if k not in params]+['response_format','effective_max_tokens']
        flags=re.findall(r'truncated\s*=\s*(\d+)',record['server_log_segment']);record['truncated']=any(int(x) for x in flags) if flags else 'not_verified'
        record['budget_check_basis']='实际发送max_tokens及响应usage/finish_reason另存；不把stop解释为预算直接回显'
        write(path,record);self.event('model_response',request_id=request_id,run_id=rid,status=record['status'],finish_reason=record['finish_reason'],record=path.name)
        if not all(record['echoed_parameter_checks'].values()) or record['truncated'] is True:raise TechnicalStop('参数回显或截断异常')
        return record

    def execute_pair(self,claim,doc_ids,snapshot,order):
        # 此方法只依赖当前输入，任务编号由页面编排层记录。
        blocks=self.corpus.scope(doc_ids,snapshot)
        if not isinstance(claim,str) or not claim.strip():raise ValueError('主张不能为空')
        if sorted(order)!=['baseline','improved']:raise ValueError('两方案顺序不合法')
        key=sha_text(json.dumps([claim,doc_ids,snapshot],ensure_ascii=False))
        if key in self.started:raise ValueError('本轮同一输入已尝试；不重复生成')
        self.started.add(key);pid=str(uuid.uuid4());start=time.perf_counter()
        pair={'request_id':pid,'claim':claim,'doc_ids':doc_ids,'snapshot':snapshot,'order':order,'status':'started','shared_query':None,'arms':{},'run_kind':'live_api','judgment_source':'model','started_at':now(),'scope_blocks':[public(b) for b in blocks]}
        path=self.folder/('pair-'+pid+'.json');write(path,pair)
        self.event('pair_start',request_id=pid,claim=claim,doc_ids=doc_ids,snapshot=snapshot)
        try:
            qstart=time.perf_counter();query=self.generate(query_messages(claim),config('query'),'query-'+pid,pid,[])
            pair['shared_query']=query;pair['shared_query_wall_seconds']=time.perf_counter()-qstart
            try:q=parse_terms(query['content'])
            except (ValueError,TypeError,json.JSONDecodeError) as e:
                pair.update(status='query_quality_failure',error=str(e));return pair
            selected,scores=retrieve(q,blocks);extended,added=neighbors(selected,blocks)
            pair.update(retrieval_terms=q,retrieval_scores=scores,seed_ids=[b['block_id'] for b in selected],added_neighbors=added)
            # 两侧均在任何最终回答调用前完成实际容量检查。
            for arm,used in [('baseline',selected),('improved',extended)]:self.capacity(answer_messages(claim,used),config('answer'),'before-pair-'+pid+'-'+arm)
            for arm in order:
                used=selected if arm=='baseline' else extended;main_id=str(uuid.uuid4());arm_start=time.perf_counter()
                raw=self.generate(answer_messages(claim,used),config('answer'),arm+'-'+pid,main_id,used)
                view={'main_task_id':main_id,'parent_request_id':pid,'variant':arm,'raw_record':raw,'actual_input_passages':[public(b) for b in used],'status':'returned','support_status':'not_checked','judgment_source':'unverified','locator_status':'absent','evidence':[]}
                try:
                    obj,checks=parse_answer(raw['content'],used);view.update(parsed=obj,reference_checks=checks,format_complete=True,claim_judgment=obj['label'],claim_judgment_source='model')
                    by_id={b['block_id']:b for b in used}
                    for e,check in zip(obj['evidence'],checks):
                        b=by_id.get(e['block_id']);loc=self.locator.locate(b,e['quote']) if b and check['quote_continuous_original'] else {'locator_status':'invalid','reason':'ID或连续原文摘录核验失败','regions':[]}
                        view['evidence'].append({**e,'doc_id':b['doc_id'] if b else None,'snapshot':b['snapshot'] if b else None,'text':b['text'] if b else None,'page':loc['regions'][0]['page'] if loc['regions'] else None,'location':loc,'citation_semantic_support':'not_checked','judgment_source':'unverified'})
                    view['locator_status']='valid' if view['evidence'] and all(e['location']['locator_status']=='valid' for e in view['evidence']) else 'invalid' if view['evidence'] else 'absent'
                except (ValueError,TypeError,KeyError,json.JSONDecodeError) as e:view.update(status='answer_quality_failure',format_complete=False,error=str(e))
                view['answer_stage_wall_seconds']=time.perf_counter()-arm_start
                view['shared_query_cost_share']=0.5
                view['allocated_total_seconds']=pair['shared_query_wall_seconds']/2+view['answer_stage_wall_seconds']
                view['cost_note']='共享查询仅计1次；各侧分摊50%查询耗时/usage，分摊合计是成本口径，不冒充独立端到端计时。pair_elapsed_seconds为页面整对实测。'
                pair['arms'][arm]=view;write(path,pair)
                self.event('arm_result',request_id=main_id,parent_request_id=pid,variant=arm,run_id=raw['run_id'],locator_status=view['locator_status'],semantic_support='not_checked')
            pair['status']='completed'
            return pair
        except Exception as e:
            self.technical_stop=True;pair.update(status='technical_stop',error=repr(e));self.event('technical_stop',request_id=pid,error=repr(e),dispatches=self.dispatches);raise
        finally:
            pair['pair_elapsed_seconds']=time.perf_counter()-start;pair['ended_at']=now();write(path,pair)
            self.event('pair_saved',request_id=pid,status=pair['status'],path=path.name)

def sha_text(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()
