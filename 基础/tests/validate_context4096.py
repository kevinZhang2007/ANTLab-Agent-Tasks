"""启动4096上下文，仅验证一次D04 R0；配置和旧记录保持不变。"""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json
import math
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

repo = Path(__file__).resolve().parents[2]
base = repo/'基础'
folder = base/'runs/capacity/context4096'
assert not folder.exists(), 'Preserve any existing verification records'
old_hashes = {str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest()
              for p in repo.rglob('*') if p.is_file() and '.git' not in p.relative_to(repo).parts}
folder.mkdir(parents=True)
runtime_root = Path(os.environ['LOCALAPPDATA'])/'ANTLabLocalModel'
server = runtime_root/'llama-b11429/llama-server.exe'
log_id = str(uuid.uuid4())
stdout_path = runtime_root/f'logs/context4096-{log_id}.stdout.log'
stderr_path = runtime_root/f'logs/context4096-{log_id}.stderr.log'

def memory(pid=None):
    command = "$os=Get-CimInstance Win32_OperatingSystem; $total=Get-CimInstance Win32_ComputerSystem; "
    command += "$m=[ordered]@{available_kib=$os.FreePhysicalMemory;total_bytes=$total.TotalPhysicalMemory}; "
    if pid is not None:
        command += f"$p=Get-Process -Id {pid} -ErrorAction Stop; $m.pid=$p.Id; $m.working_set_bytes=$p.WorkingSet64; $m.private_bytes=$p.PrivateMemorySize64; "
    command += '[PSCustomObject]$m | ConvertTo-Json -Compress'
    result = subprocess.run([r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe',
                             '-NoProfile','-Command',command],capture_output=True,text=True,encoding='utf-8',check=True)
    return {'sampled_at_utc':datetime.now(timezone.utc).isoformat(),**json.loads(result.stdout)}

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
def service(route,body=None):
    assert route in {'health','props','apply-template','tokenize','slots'}
    data = None if body is None else json.dumps(body,ensure_ascii=False).encode()
    request = urllib.request.Request('http://127.0.0.1:8080/'+route,data=data,headers={'Content-Type':'application/json'})
    with opener.open(request,timeout=10) as response: return json.loads(response.read())

startup = {'record_kind':'context4096_startup','recorded_at_utc':datetime.now(timezone.utc).isoformat(),
           'source_commit':'58a8655a30c50ac565472081fab88fb70b2308f9',
           'before_load':memory(),'generation_call_count':0,
           'resource_stop_rule':'Stop before generation if available physical memory after load is below 256 MiB or the model service exits; do not switch models.',
           'reference_settings':'Previous ctx2048 capacity service; only context is enlarged. Explicit no-context-shift matches prior default-disabled behavior.'}
args = [str(server),'-m',str(runtime_root/'models/Qwen3-0.6B-Q8_0.gguf'),
        '--host','127.0.0.1','--port','8080','--alias','Qwen3-0.6B-Q8_0',
        '--ctx-size','4096','--parallel','1','--batch-size','128','--ubatch-size','64',
        '--threads','4','--gpu-layers','0','--reasoning','off','--no-context-shift','--no-warmup']
startup['server_arguments'] = [value.replace(str(runtime_root),'%LOCALAPPDATA%/ANTLabLocalModel') for value in args]
process = None
record = None
try:
    with stdout_path.open('wb') as stdout, stderr_path.open('wb') as stderr:
        process = subprocess.Popen(args,stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
    started = time.monotonic()
    while True:
        if process.poll() is not None: raise RuntimeError('Model server exited during loading')
        try:
            if service('health').get('status')=='ok': break
        except (urllib.error.URLError,TimeoutError):
            pass
        if time.monotonic()-started>60: raise TimeoutError('Model startup exceeded 60 seconds')
        time.sleep(0.5)
    props = service('props')
    actual_context = props['default_generation_settings']['n_ctx']
    assert actual_context==4096
    startup.update(status='loaded',actual_context=actual_context,after_load=memory(process.pid),
                   build_info=props['build_info'])
    props['model_path'] = '%LOCALAPPDATA%/ANTLabLocalModel/models/Qwen3-0.6B-Q8_0.gguf'
    startup['server_props'] = props
    if startup['after_load']['available_kib']<256*1024:
        raise MemoryError('Available physical memory below the recorded stop threshold')
    (folder/'startup.json').write_text(json.dumps(startup,ensure_ascii=False,indent=2),encoding='utf-8')
    print('STARTUP:',json.dumps({key:startup[key] for key in ('before_load','after_load','actual_context','build_info')},ensure_ascii=False),flush=True)

    # 复用此前容量记录中的开发题完整输入，不读取正式题或答案来构造消息。
    capacity = json.loads((base/'runs/capacity/stage3/inputs.json').read_text(encoding='utf-8'))
    row = next(r for r in capacity['rows'] if r['case_id']=='D04' and r['condition']=='R0')
    payload = json.loads(row['messages'][1]['content'])
    sys.path.insert(0,str(base/'starter'))
    import student
    import provider
    messages = student.prepare_messages(payload['question'],payload['passages'])
    assert messages==row['messages']
    first = json.loads((base/'runs/62a41e78-da75-48ca-b9a3-d0ec29127825.json').read_text(encoding='utf-8'))
    config = copy.deepcopy(first['config'])
    assert config['parameters']['max_tokens']==256 and 'chat_template_kwargs' not in config['parameters']
    prompt = service('apply-template',{'messages':messages})['prompt']
    tokens = service('tokenize',{'content':prompt,'add_special':True,'parse_special':True})['tokens']
    assert len(tokens)==row['input_tokens']==2190
    assert len(tokens)+256<4096
    plan = {'record_kind':'pre_call_capacity_validation_plan','recorded_at_utc':datetime.now(timezone.utc).isoformat(),
            'purpose':'Verify one complete D04 R0 baseline input enters ctx4096 and returns an answer; not an improvement experiment.',
            'expectation':'2190 input tokens plus 256 output budget need 2446, below actual ctx4096. Expect no context truncation; answer quality remains unverified.',
            'stop_conditions':['At most one generation call, no retry even for wrong/incomplete output.','Keep model, original student prompt, passage order and original generation parameters.','Stop service after test; do not modify config examples, private config, documents or old records.'],
            'config':config,'context':4096,'input_tokens':len(tokens),'thinking':'off','context_shift':'disabled'}
    (folder/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    print('PRE-CALL PLAN:',plan['recorded_at_utc'],flush=True)
    record = {'schema_version':1,'run_id':str(uuid.uuid4()),'utc':datetime.now(timezone.utc).isoformat(),
              'case_id':'D04','split':'dev','condition':'R0','variant':'baseline','mode':'local','run_kind':'live_api',
              'experiment_role':'context_capacity_validation','config':config,'messages':messages,
              'selected_passage_ids':row['passage_ids'],'original_passage_ids':row['passage_ids'],
              'rendered_prompt':prompt,'rendered_prompt_tokens':len(tokens),'context':4096,
              'student_sha256':hashlib.sha256((base/'starter/student.py').read_bytes()).hexdigest(),
              'provider_sha256':hashlib.sha256((base/'starter/provider.py').read_bytes()).hexdigest(),
              'status':'request_pending','plan_recorded_at_utc':plan['recorded_at_utc']}
    path = folder/f"run-{record['run_id']}.json"
    def save(): path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    save()
    build_opener = urllib.request.build_opener
    class CaptureOpener:
        def __init__(self,inner): self.inner=inner
        def open(self,request,*args,**kwargs):
            record['actual_http_request_body']=json.loads(request.data)
            record['raw_http_request_body']=request.data.decode('utf-8')
            return self.inner.open(request,*args,**kwargs)
    urllib.request.build_opener=lambda *args,**kwargs: CaptureOpener(build_opener(*args,**kwargs))
    try:
        startup['generation_call_count']=1
        record.update(provider.call_model(messages,config))
    except Exception as error:
        record.update(status='driver_exception',error=type(error).__name__,error_detail=str(error),response=None,elapsed_seconds=None,usage=None)
    finally:
        urllib.request.build_opener=build_opener
        save()
    record['server_slot_after_request']=service('slots')
    slot=record['server_slot_after_request'][0]
    record['actual_context_after_request']=slot['n_ctx']
    record['parameter_checks']={key:math.isclose(slot['params'][key],value,rel_tol=1e-6,abs_tol=1e-6)
                               for key,value in config['parameters'].items()}
    expected={'model':config['model'],'messages':messages,'stream':False,**config['parameters']}
    record['transport_body_matches_expected']=record.get('actual_http_request_body')==expected
    startup['after_request']=memory(process.pid)

    # 公开答案在真实响应已经保存之后才读取，仅用于评价。
    gold = next(a for a in json.loads((base/'data/dev_answers.json').read_text(encoding='utf-8')) if a['id']=='D04')
    choice=(record.get('response') or {}).get('choices',[{}])[0]
    content=choice.get('message',{}).get('content','')
    parsed=None
    try: parsed=json.loads(content)
    except ValueError: pass
    valid=(isinstance(parsed,dict) and set(parsed)=={'answer','citations'} and isinstance(parsed.get('answer'),str)
           and isinstance(parsed.get('citations'),list) and all(isinstance(v,str) for v in parsed['citations']))
    correct=isinstance(parsed,dict) and isinstance(parsed.get('answer'),str) and parsed['answer'].strip() in gold['aliases']
    citations=parsed.get('citations') if isinstance(parsed,dict) else None
    exists=all(v in row['passage_ids'] for v in citations) if isinstance(citations,list) and all(isinstance(v,str) for v in citations) else None
    sufficient=bool(correct and exists and isinstance(citations,list) and set(gold['evidence_ids']).issubset(citations))
    record['evaluation']={'checked_by':'Codex','public_answer_evaluation_only':True,'complete_answer_citations_json':valid,
                          'answer_correct':correct,'citation_ids_in_input':exists,'citation_support_sufficient':sufficient,
                          'answer_basis':'公开答案为配置丙；正式选择表中乙、丙合格，丙预算1720低于乙1980。',
                          'citation_basis':'原文选择规则为覆盖率至少88%、格式失败不超过1次，再按预算决定；需要选择表及签署规则两段共同支持。',
                          'finish_reason':choice.get('finish_reason')}
    save()
    print('RESULT:',json.dumps({'run_id':record['run_id'],'path':str(path.relative_to(repo)),'status':record['status'],
          'message':choice.get('message'),'usage':record.get('usage'),'elapsed_seconds':record.get('elapsed_seconds'),
          'evaluation':record['evaluation'],'parameter_checks':record['parameter_checks']},ensure_ascii=False),flush=True)
except Exception as error:
    startup.update(status='failed',error=type(error).__name__,error_detail=str(error))
    print('FAILURE:',type(error).__name__,str(error),flush=True)
finally:
    if process is not None and process.poll() is None:
        process.terminate()
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait()
    startup['server_stopped']=process is not None and process.poll() is not None
    log=stderr_path.read_text(encoding='utf-8',errors='replace') if stderr_path.exists() else ''
    log=log.replace(str(runtime_root),'%LOCALAPPDATA%\\ANTLabLocalModel')
    (folder/'server-log.txt').write_text(log,encoding='utf-8')
    if record is not None:
        record['server_log_truncated_zero']=('truncated = 0' in log)
        record['server_log']=str((folder/'server-log.txt').relative_to(repo))
        save()
    for relative,digest in old_hashes.items():
        assert hashlib.sha256((repo/relative).read_bytes()).hexdigest()==digest,relative
    startup['old_repository_files_unchanged']=True
    (folder/'startup.json').write_text(json.dumps(startup,ensure_ascii=False,indent=2),encoding='utf-8')
    print('FINAL: service stopped; all prior repository files unchanged',flush=True)
