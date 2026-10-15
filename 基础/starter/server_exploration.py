"""基础页面的独立探索适配器；冻结算法只导入，不改写。"""
from pathlib import Path
from http.server import HTTPServer
from urllib.parse import urlparse, parse_qs
import argparse, copy, hashlib, importlib.util, json, math, os, re, sys, time, uuid
import urllib.request
import server as original_server
import runner, provider

ROOT=Path(__file__).resolve().parents[2]
FROZEN=ROOT/'基础/runs/repeat_integrated/20261015-171741'
def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def now():return __import__('datetime').datetime.now().astimezone().isoformat()
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.flush();os.fsync(stream.fileno())
def parse_answer(content):
    try:
        value=json.loads(content)
        if isinstance(value,dict) and isinstance(value.get('answer'),str) and isinstance(value.get('citations'),list):return value
    except (ValueError,TypeError):pass
    return None
def evidence_for(value,passages):
    ids=value.get('citations',[]) if isinstance(value,dict) else []
    by_id={p['id']:p for p in passages}
    evidence=[{'block_id':pid,'doc_id':None,'snapshot':None,'page':None,'text':by_id[pid]['text'],'source':by_id[pid]['source'],'start':0,'end':len(by_id[pid]['text']),'locator_status':'valid','support_status':'not_checked','metadata_reason':'输入未提供独立doc_id/snapshot/page；不从source猜造。'} for pid in ids if pid in by_id]
    status='absent' if not ids else 'valid' if len(ids)==len(set(ids)) and all(pid in by_id for pid in ids) else 'invalid'
    return {'evidence':evidence,'locator_status':status,'support_status':'not_checked','judgment_source':'unverified'}

class Exploration:
    def __init__(self,folder,allowed_case,model_log):
        self.folder=folder;self.allowed_case=allowed_case;self.model_log=model_log;self.started=False;self.calls=0;self.main_id=None
        self.contract=load(FROZEN/'freeze.json');self.answer=copy.deepcopy(self.contract['answer_config']);self.selection=copy.deepcopy(self.contract['selection_config'])
        for relative,expected in {**self.contract['code_hashes'],**self.contract['data_hashes']}.items():
            if sha(ROOT/relative)!=expected:raise ValueError('冻结文件哈希改变 '+relative)
        sys.path.insert(0,str(ROOT/'基础/tests'));sys.path.insert(0,str(FROZEN))
        spec=importlib.util.spec_from_file_location('page_exploration_pipeline',FROZEN/'proof_pipeline_candidate.py')
        self.candidate=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.candidate)
        self.freeze_hash=sha(FROZEN/'freeze.json')
        self.url='http://127.0.0.1:8080/'
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def event(self,kind,**fields):
        with (self.folder/'events.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps({'recorded_at':now(),'event':kind,'request_id':self.main_id,'main_task_id':self.main_id,**fields},ensure_ascii=False)+'\n');stream.flush();os.fsync(stream.fileno())
    def service(self,route,body=None):
        request=urllib.request.Request(self.url+route,data=None if body is None else json.dumps(body,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
        with self.opener.open(request,timeout=30) as response:return json.loads(response.read())
    def render(self,messages,config,label):
        request={'model':config['model'],'messages':messages,'stream':False,**config['parameters']}
        template=self.service('apply-template',request);prompt=template['prompt']
        tokens=self.service('tokenize',{'content':prompt,'add_special':True,'parse_special':True})['tokens']
        result={'label':label,'request':request,'template_response':template,'input_tokens':len(tokens),'output_budget':256,'fits':len(tokens)+256<=4096}
        write(self.folder/f'template-{label}.json',result)
        if not result['fits'] or not all(m['content'] in prompt for m in messages):raise ValueError('完整模板容量或消息核对失败')
        if not prompt.endswith('<think>\n\n</think>\n\n'):raise ValueError('关闭思考模板不符')
        return result
    def preview(self,cid,condition):
        if cid!=self.allowed_case:raise ValueError('本次只授权所选开发题')
        case,passages,_,_=runner.prepare(cid,condition,'baseline')
        return {'query':case['question'],'question':case['question'],'passages':passages,'doc_ids':None,'snapshot':None,'scope_metadata_reason':'输入没有独立文档/快照字段，段落ID和source原样保留。','configuration_ref':str((FROZEN/'freeze.json').relative_to(ROOT)).replace('\\','/'),'configuration_sha256':self.freeze_hash}
    def preflight_templates(self):
        data=self.preview(self.allowed_case,'R0');q=data['question'];p=data['passages']
        messages,config,_=self.candidate.answer_request(q,p,self.answer);self.render(messages,config,'preflight-answer-full')
        ordered=self.candidate.student.improve(q,copy.deepcopy(p));self.render(self.candidate.selection.prepare_selection_messages(q,ordered),self.selection,'preflight-selection-full')
        messages,config,_=self.candidate.answer_request(q,[],self.answer);self.render(messages,config,'preflight-answer-empty')
    def execute(self,body):
        if self.started or (self.folder/'request-started.json').exists():raise ValueError('本目录已执行或尝试请求，禁止重复发送')
        expected=self.preview(body['case_id'],body['condition'])
        if body.get('mode')!='local' or body.get('variant')!='improved' or body.get('condition')!='R0':raise ValueError('本轮只验证local/R0/improved')
        if any(body.get(k)!=expected[k] for k in ['query','question','passages','configuration_ref','configuration_sha256','doc_ids','snapshot']):raise ValueError('页面输入或冻结配置与预览不一致')
        self.started=True;self.main_id=str(uuid.uuid4());begin=time.perf_counter()
        write(self.folder/'request-started.json',{'recorded_at':now(),'request_id':self.main_id,'request':body})
        self.event('http_request',body=body,entry='post_evaluation_system_exploration',run_kind='live_api')
        task={'request_id':self.main_id,'main_task_id':self.main_id,'case_id':body['case_id'],'condition':body['condition'],'variant':'improved','dataset':'development_page_closure','started_at':now()}
        def save(value):task.update(value);write(self.folder/'task.json',task)
        def dispatch(stage,messages,config,used):
            if self.calls>=2:raise ValueError('超过本次两次生成授权')
            if hasattr(self,'memory_status') and self.memory_status()['available_bytes']<1024**3:raise RuntimeError('请求前可用内存低于1 GiB，停止')
            if sha(FROZEN/'freeze.json')!=self.freeze_hash:raise ValueError('冻结版本变化')
            check=self.render(messages,config,stage)
            record={'run_id':str(uuid.uuid4()),'request_id':self.main_id,'main_task_id':self.main_id,'case_id':body['case_id'],'condition':'R0','variant':'improved','stage':stage,'run_kind':'live_api','judgment_source':'unverified','attempt':1,'retry_of':None,'started_at':now(),'config':config,'messages':messages,'used_passages':copy.deepcopy(used),'actual_http_request_body':check['request'],'input_tokens':check['input_tokens'],'generation_dispatched':False}
            record['cache_erase']=self.service('slots/0?action=erase',{})
            if hasattr(self,'memory_status'):record['memory_before']=self.memory_status()
            offset=self.model_log.stat().st_size;path=self.folder/('run-'+record['run_id']+'.json');write(path,record)
            old_build=urllib.request.build_opener
            class Capture:
                def __init__(self,inner):self.inner=inner
                def open(self,request,*args,**kwargs):
                    actual=json.loads(request.data)
                    if actual!=check['request'] or actual['max_tokens']!=256:raise ValueError('实际模型请求参数不符')
                    record['raw_http_request_body']=request.data.decode();record['generation_dispatched']=True
                    self_owner.calls+=1;write(path,record);self_owner.event('model_request',run_id=record['run_id'],stage=stage,record_path=path.relative_to(ROOT).as_posix(),run_kind='live_api')
                    return self.inner.open(request,*args,**kwargs)
            self_owner=self
            urllib.request.build_opener=lambda *args,**kwargs:Capture(old_build(*args,**kwargs))
            try:record.update(provider.call_model(messages,config))
            finally:urllib.request.build_opener=old_build;write(path,record)
            if record.get('status')!='ok' or not isinstance(record.get('response'),dict) or not record['response'].get('choices'):raise RuntimeError('真实请求技术失败，停止，不重试')
            message=record['response']['choices'][0]
            if hasattr(self,'memory_status'):record['memory_after']=self.memory_status()
            record.update(finish_reason=message.get('finish_reason'),raw_content=message.get('message',{}).get('content',''),reasoning_content=message.get('message',{}).get('reasoning_content'))
            slots=self.service('slots');record['slot_after']=slots
            params=slots[0]['params'];numeric={k:v for k,v in config['parameters'].items() if isinstance(v,(int,float)) and k!='max_tokens'}
            record['parameter_checks']={k:math.isclose(params[k],v,rel_tol=1e-6,abs_tol=1e-6) for k,v in numeric.items() if k in params}
            record['parameters_not_echoed']=[k for k in numeric if k not in params]+['response_format','effective_max_tokens']
            with self.model_log.open('rb') as stream:stream.seek(offset);record['server_log_segment']=stream.read().decode(errors='replace')
            flags=re.findall(r'truncated\s*=\s*(\d+)',record['server_log_segment']);record['truncated']=any(int(x) for x in flags) if flags else 'not_verified'
            write(path,record);self.event('model_response',run_id=record['run_id'],stage=stage,status=record['status'],record_path=path.relative_to(ROOT).as_posix(),elapsed_seconds=record['elapsed_seconds'],run_kind='live_api')
            if not all(record['parameter_checks'].values()) or record['truncated'] is True:raise RuntimeError('参数或截断检查失败')
            return copy.deepcopy(record)
        try:
            save(self.candidate.execute(body['question'],body['passages'],'improved',self.answer,self.selection,dispatch,save))
            raw=parse_answer(task.get('raw_answer',''));final=task.get('actual_final_output');passages=task.get('used_passages',[])
            stages=[{'run_id':s['run_id'],'stage':s['stage'],'elapsed_seconds':s.get('elapsed_seconds'),'run_kind':'live_api','raw_response':s.get('response')} for s in task.get('stages',[])]
            rules=[]
            for name in ['proof_record','ratio_proof','difference_proposal']:
                if isinstance(task.get(name),dict):rules.append({'name':name,'run_kind':'local_rule','judgment_source':'rule','original_record':task[name]})
            result={'request_id':self.main_id,'main_task_id':self.main_id,'entry':'post_evaluation_system_exploration','configuration_ref':expected['configuration_ref'],'configuration_sha256':self.freeze_hash,'status':task.get('status'),'query':body['question'],'doc_ids':None,'snapshot':None,'scope_metadata_reason':expected['scope_metadata_reason'],'run_kind':'live_api','judgment_source':'unverified','support_status':'not_checked','model_raw_response':{'value':raw,**evidence_for(raw,passages)},'rule_processing':rules,'reference_derived_response':task.get('reference_derived_response'),'calculation_proposed_response':task.get('proposed_response'),'derived_response':final if task.get('actual_final_output_source')!='raw_model_response' else None,'final_output':final,'final_output_source':task.get('actual_final_output_source'),'final_display':{**evidence_for(final,passages),'run_kind':'local_rule' if task.get('actual_final_output_source')!='raw_model_response' else 'live_api','judgment_source':'rule' if task.get('actual_final_output_source')!='raw_model_response' else 'unverified'},'answer':final.get('answer') if isinstance(final,dict) else None,'evidence':evidence_for(final,passages)['evidence'],'locator_status':evidence_for(final,passages)['locator_status'],'actual_input_passages':passages,'stages':stages,'elapsed_ms':1000*(time.perf_counter()-begin),'pipeline_timing':task.get('timing_summary'),'generation_calls':self.calls,'record_path':(self.folder/'task.json').relative_to(ROOT).as_posix(),'semantic_note':'not_checked：定位有效与local_rule证明均不等于独立语义核验；非主评分结果。'}
            result['rule_operations']=[{'run_kind':'local_rule','judgment_source':'rule','original_event':event} for event in task.get('local_rule_processing',[])]
            result['model_raw_response']['run_kind']='live_api'
            write(self.folder/'http-response.json',result);self.event('http_response',response=result,run_kind='live_api')
            return result
        except Exception as error:
            self.event('technical_stop',error_type=type(error).__name__,error=str(error),generation_calls=self.calls)
            write(self.folder/'technical-stop.json',{'recorded_at':now(),'request_id':self.main_id,'error':str(error),'generation_calls':self.calls})
            raise

class Handler(original_server.Handler):
    def do_GET(self):
        path=urlparse(self.path)
        if path.path=='/api/versions':return self.reply(200,{'original':'原入口：生产student.py；首次40项仍为原主实验','integrated':'评测后系统探索；不计作首次主成绩','configuration_ref':self.server.engine.preview(self.server.engine.allowed_case,'R0')['configuration_ref']})
        if path.path=='/api/cases':return self.reply(200,[{'id':c['id'],'split':c['split'],'question':c['question']} for c in runner.cases() if c['id']==self.server.engine.allowed_case])
        if path.path=='/api/input':
            try:
                query=parse_qs(path.query);return self.reply(200,self.server.engine.preview(query['case_id'][0],query['condition'][0]))
            except Exception as error:return self.reply(400,{'error':str(error)})
        return super().do_GET()
    def do_POST(self):
        if self.path not in ('/api/run','/api/page-observation'):return self.reply(404,{'error':'not found'})
        if self.headers.get('X-Assessment-Session')!=original_server.TOKEN:return self.reply(403,{'error':'会话不匹配'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<200000:raise ValueError('请求长度不合法')
            raw_body=self.rfile.read(length);body=json.loads(raw_body)
            if self.path=='/api/page-observation':
                if body.get('request_id')!=self.server.engine.main_id:raise ValueError('主任务ID不符')
                write(self.server.engine.folder/'page-observation.json',body);self.server.engine.event('page_observation',observation=body)
                return self.reply(200,{'saved':True})
            if body.get('entry','original')=='original':
                if body.get('mode') not in ('dry','mock'):raise ValueError('原入口本轮仅保留预览/模拟；真实验证使用明确的探索入口')
                return self.reply(200,runner.execute(body['case_id'],body['condition'],body['variant'],self.server.config,dry=body['mode']=='dry',mock=body['mode']=='mock',outdir=self.server.engine.folder/'original'))
            if body.get('entry')!='integrated':raise ValueError('未知入口')
            try:result=self.server.engine.execute(body)
            finally:write(self.server.engine.folder/'http-request.json',{'request_id':self.server.engine.main_id,'main_task_id':self.server.engine.main_id,'method':'POST','path':self.path,'content_type':self.headers.get('Content-Type'),'raw_body':raw_body.decode(),'body':body,'session_header':'省略本次会话令牌，未省略实验输入'})
            self.reply(200,result)
        except Exception as error:self.reply(400 if isinstance(error,(ValueError,KeyError)) else 500,{'error':str(error),'request_id':self.server.engine.main_id,'generation_calls':self.server.engine.calls,'retry_allowed':False})
