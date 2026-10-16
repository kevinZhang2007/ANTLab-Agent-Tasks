from pathlib import Path
import sys,json,copy,ast,shutil,difflib
from datetime import datetime
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now,config
from engine import Corpus,public,neighbors,query_messages
from sentence_selection import offline_checks as sentence_checks
from sentence_interface import offline_checks as interface_checks
from compact_factorial import offline_checks as compact_checks
from thinking_modes import offline_checks as thinking_checks
from audited_health import offline_checks as health_checks
from checks_extended import run as old_checks
from preflight import native_tokenizer
selected=HERE/'runs/adopt-reason-citations-20261016-182422';selection=load(selected/'configuration.json')
out=HERE/'runs'/('current-e2e-'+datetime.now().strftime('%Y%m%d-%H%M%S'));out.mkdir();Path('a-current-e2e-out.txt').write_text(str(out),encoding='utf-8')
protected={p.relative_to(ROOT).as_posix():sha(p) for p in HERE.rglob('*') if p.is_file() and out not in p.parents and not {'slot-cache','__pycache__'}&set(p.parts)}
for n in ['README.md','report.md','decisions.md','declaration.md','基础/开发记录.md','基础/starter/student.py','进阶/challenge_b/challenge.py','进阶/challenge_b/no_cache_engine.py']:protected[n]=sha(ROOT/n)
write(out/'protected-before.json',protected)
for n,h in selection['code_hashes'].items():assert sha(ROOT/n)==h,n
write(out/'configuration.json',selection)
engine_file=HERE/'current_candidate.py';assert not engine_file.exists()
engine_file.write_text('''"""统一单侧入口及共享查询配对；不读取任务、答案或历史模型输出。"""
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
        tok=http('tokenize',{'content':prompt,'add_special':True,'parse_special':True},'tokenize_http');flag=body['chat_template_kwargs']['enable_thinking'];suffix=prompt.rsplit('<|im_start|>assistant\\n',1)[-1]
        checks={'boolean_mode':type(flag) is bool,'expected_budget':body['max_tokens']==(1024 if flag else 128),'branch':suffix==('' if flag else '<think>\\n\\n</think>\\n\\n'),'all_messages_present':all(m['content'] in prompt for m in messages),'fits':len(tok['tokens'])+body['max_tokens']<=4096}
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
''',encoding='utf-8')

page=(HERE/'index.html').read_text(encoding='utf-8').replace('进阶A：邻段补全开发对照','进阶A：当前采用版本完整开发配对').replace('进阶A：同章节邻段补全','进阶A：紧凑＋思考＋句子选择＋理由引用提示')
page=page.replace('terms:pair.retrieval_terms','version:pair.version,query_raw_content:pair.shared_query?.content,query_enable_thinking:pair.shared_query?.actual_http_request_body?.chat_template_kwargs?.enable_thinking,terms:pair.retrieval_terms')
page=page.replace('raw_content:a.raw_record.content,','raw_content:a.raw_record.content,reasoning_content:a.raw_record.response?.choices?.[0]?.message?.reasoning_content,expanded_interface:a.interface_response,reconstructed_flow_seconds:a.reconstructed_flow_seconds,preparation_seconds:a.preparation_seconds,')
pagefile=HERE/'current_page.html';assert not pagefile.exists();pagefile.write_text(page,encoding='utf-8')
handler=HERE/'current_server.py';assert not handler.exists();handler.write_text('''"""仅切换页面，复用原HTTP鉴权、开发白名单、日志和PDF路由。"""
from server import Handler as OriginalHandler,TOKEN
from runtime import HERE
class Handler(OriginalHandler):
    def do_GET(self):
        if self.path=='/':
            raw=(HERE/'current_page.html').read_text(encoding='utf-8').replace('__TOKEN__',TOKEN).encode();self.send_response(200);self.send_header('Content-Type','text/html;charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw);return
        return super().do_GET()
''',encoding='utf-8')

# 独立启动器，沿用原服务管理，只替换当前入口与模板阶段门禁。
oldlaunch=(HERE/'launch.py').read_text(encoding='utf-8');launch=oldlaunch
launch=launch.replace('from runtime import HERE,ROOT,Engine,TechnicalStop,load,write,sha,now,memory,config','from runtime import HERE,ROOT,TechnicalStop,load,write,sha,now,memory\nfrom current_candidate import CurrentEngine as Engine,query_config,build_answer\nfrom audited_health import wait_health')
launch=launch.replace('from server import Handler,HTTPServer','from current_server import Handler\nfrom http.server import HTTPServer')
begin=launch.index("    pre=load(folder/'offline-preflight.json')");end=launch.index('    for port in [8080,a.port]:',begin)
launch=launch[:begin]+"    pre=load(folder/'offline-preflight.json');assert pre['passed']\n    if (folder/'owned-service.json').exists() or list(folder.glob('run-*.json')):raise ValueError('已有启动/请求，不重发')\n    for name,h in {**pre['code_hashes'],**pre['data_hashes']}.items():assert sha(ROOT/name)==h,name\n"+launch[end:]
begin=launch.index("    plan={'saved_at':now()");end=launch.index('    process=None;',begin)
launch=launch[:begin]+"    plan=load(folder/'development-plan.json')\n    launch=plan['service_arguments'];(folder/'slot-cache').mkdir()\n    assert sha(Path(launch[0]))==pre['executable_hash'] and sha(Path(launch[launch.index('-m')+1]))==pre['model_hash']\n"+launch[end:]
begin=launch.index('        while time.perf_counter()-start<120:');end=launch.index("        props=engine.service('props')",begin)
launch=launch[:begin]+"        wait_health(engine,process,folder,abort,start,120)\n"+launch[end:]
begin=launch.index('        for t in development:');end=launch.index("        server=HTTPServer",begin)
launch=launch[:begin]+"        for t in development:\n            engine.capacity(query_messages(t['claim']),query_config(),'startup-query-'+t['id'])\n            for variant,blocks in [('empty',[]),('worst',load(folder/'worst-inputs.json')[t['id']])]:\n                ms,conf,index,audit=build_answer(t['claim'],blocks,t['doc_ids'],t['snapshot'],engine.answer_base)\n                engine.capacity(ms,conf,'startup-'+variant+'-'+t['id'])\n"+launch[end:]
launch=launch.replace("        stop.set()","        runtime.update(exit_code_before_cleanup=process.poll() if process else None)\n        stop.set()")
launch=launch.replace("runtime.update(ended_at=now()","runtime.update(exit_code_after_cleanup=process.poll() if process else None,ended_at=now()")
launchfile=HERE/'launch_current.py';assert not launchfile.exists();ast.parse(launch);launchfile.write_text(launch,encoding='utf-8')
from current_candidate import build_answer,query_config
from sentence_selection import expand
from reason_citations import NOTE
checks={'health':health_checks(),'compact':compact_checks(),'thinking':thinking_checks(),'sentence':sentence_checks(),'interface':interface_checks(),'existing':old_checks(out)};assert all(x['passed'] for x in checks.values())
synthetic=[{'block_id':'original-x','doc_id':'made-up','snapshot':'published','section_id':'s','heading':'Scope','paragraph_index':0,'text':'Keep a record.\nDo not invent facts.  '}]
ms,conf,idx,byte=build_answer('Records are required.',synthetic,['made-up'],'published',selection['request_common']);assert ms[0]['content'].endswith(NOTE) and ms[0]['content'].count(NOTE)==1
assert build_answer('Empty.',[],['made-up'],'published',selection['request_common'])[2]==[]
assert expand(json.dumps({'label':'supported','reason':'synthetic','sentence_ids':['missing']}),synthetic,idx,['made-up'],'published')['valid'] is False
write(out/'offline-checks.json',{'at':now(),'passed':True,'checks':checks,'existing_count':85,'new_wiring_assertions':3,'generation_calls':0,'no_AT_read':True})
previous=HERE/'runs/development-20261016-115250';tasks=load(previous/'development-inputs.json');assert len(tasks)==3 and all(t['split']=='dev' for t in tasks);write(out/'development-inputs.json',tasks)
shutil.copy2(previous/'locator-anchors.json',out/'locator-anchors.json')
corpus=Corpus(load(ROOT/'进阶/materials/sections.json'));parts=[]
for b in corpus.blocks:
    message,c,index,ch=build_answer('Capacity wrapper.',[b],[b['doc_id']],b['snapshot'],selection['request_common']);parts.append(json.dumps(json.loads(message[1]['content'])['passages'][0],ensure_ascii=False,indent=2))
base=Path.home()/'AppData/Local/ANTLabLocalModel';marker='<|endoftext|>';ids,cmd=native_tokenizer(base/'llama-b11429/llama-tokenize.exe',base/'models/Qwen3-0.6B-Q8_0.gguf',marker+marker.join(parts)+marker,out,'native-block-capacity');counts=[];n=0
for token in ids[1:]:
    if token==ids[0]:counts.append(n);n=0
    else:n+=1
assert len(counts)==len(corpus.blocks);sizes={b['block_id']:n+96 for b,n in zip(corpus.blocks,counts)}
worst={};bounds=[]
for t in tasks:
    blocks=corpus.scope(t['doc_ids'],t['snapshot']);ranked=sorted(blocks,key=lambda b:sum(sizes[x['block_id']] for x in neighbors([b],blocks)[0]),reverse=True);used,_=neighbors(ranked[:2],blocks);worst[t['id']]=used
    upper=sum(sorted([sum(sizes[x['block_id']] for x in neighbors([b],blocks)[0]) for b in blocks],reverse=True)[:2])+700+1024
    bounds.append({'task_id':t['id'],'conservative_tokens_with_budget':upper,'fits':upper<=4096,'actual_template_required':True})
write(out/'offline-capacity.json',{'at':now(),'bounds':bounds,'block_sizes':sizes,'wrapper_margin':700,'output_budget':1024,'native_command':cmd,'generation_calls':0});assert all(x['fits'] for x in bounds),bounds
write(out/'worst-inputs.json',worst)
for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
newfiles=[engine_file,pagefile,handler,launchfile]
plan={'at':now(),'status':'development_e2e_not_formal_freeze','source_selection':(selected/'decision.json').relative_to(ROOT).as_posix(),'generation_baseline':621,'A_used_before':87,'generation_cap':9,'hypothesis':'采用的共同判断流程在新共享关键词及自动检索证据下可能保留严格成功收益，也可能因检索变化或推理错误失败。','competing_explanation':'固定证据重放改善不保证端到端改善；查询遗漏、命中或邻段条件不足仍可能限制判断。','method':'baseline正TF-IDF最高两段；improved仅同章节前后邻段、原文原序；共享同一次查询。','query_configuration':query_config(),'query_control_note':'相对旧查询仅显式enable_thinking=false，保持旧closed-think模板；防止服务全局reasoning=on改变查询。其余原配置数值不变。','answer_configuration':selection['request_common'],'answer_schema_factory':'sentence_selection.schema(current_index)','system':selection['system'],'order':[{'id':t['id'],'arms':['baseline','improved'] if i%2==0 else ['improved','baseline']} for i,t in enumerate(tasks)],'strict_formula':'format_complete AND selection_valid AND label_correct AND necessary_coverage_is_true AND citation_support_is_true AND NOT unrelated','reason_consistency_separate':True,'evaluation':'全部调用结束后读取公开开发参考；来源真实性、自动检索必要覆盖与实际所选引用覆盖分列。AD03不补S08。','failure':'技术失败停止不重发；质量失败保留三题分母；每个输入一次页面提交。','shared_cost':'每题查询实际只计一次，两个方案成本各分摊50%；另报整对实测及逐侧组件和。','service_arguments':selection['service_arguments'],'budget':'本轮最多9次使A最多96次，按本次明确授权登记；原90次计划超出部分记为修订，不动用额外未执行七题预留。','protected_old_records':True,'no_AT_read':True}
write(out/'development-plan.json',plan)
pre={'at':now(),'passed':True,'code_hashes':{p.relative_to(ROOT).as_posix():sha(p) for p in HERE.iterdir() if p.is_file() and p.suffix in ('.py','.json','.html')},'data_hashes':selection['data_hashes'],'model_hash':selection['model']['sha256'],'executable_hash':selection['executable']['sha256'],'generation_calls':0,'capacity_all_bounds_fit':True}
write(out/'offline-preflight.json',pre);write(out/'new-file-index.json',{'files':[p.relative_to(ROOT).as_posix() for p in newfiles]})
snap=out/'code-snapshot';snap.mkdir()
diff=''
for p in newfiles:shutil.copy2(p,snap/p.name);diff+=''.join(difflib.unified_diff([],p.read_text(encoding='utf-8').splitlines(True),fromfile='/dev/null',tofile='b/'+p.relative_to(ROOT).as_posix()))
(out/'complete-code.diff').write_text(diff,encoding='utf-8');shutil.copy2(__file__,out/Path(__file__).name)
print(json.dumps({'out':str(out),'passed':True,'capacity':bounds,'generations':0,'new_files':[p.name for p in newfiles]},ensure_ascii=False))
