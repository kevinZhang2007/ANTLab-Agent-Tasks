"""从本机服务取得实际编译GBNF，再用原生grammar sampler检查自造JSON；不decode或生成。"""
from pathlib import Path
from datetime import datetime
import ctypes as c
import json,math,os,socket,subprocess,time,urllib.request
work=Path(__file__).parent;folder=Path((work/'answer_form_folder.txt').read_text(encoding='utf-8'))
root=Path(r'C:\Users\86186\AppData\Local\ANTLabLocalModel');binary=root/'llama-b11429'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(route):
 with opener.open('http://127.0.0.1:8088/'+route,timeout=5) as r:return json.loads(r.read())
grammars={};probes=[]
with socket.socket() as s:s.settimeout(1);assert s.connect_ex(('127.0.0.1',8088))!=0
for kind in ['number','percent']:
 args=[str(binary/'llama-server.exe'),'-m',str(root/'models/Qwen3-0.6B-Q8_0.gguf'),'--host','127.0.0.1','--port','8088','--ctx-size','512','--parallel','1','--threads','4','--gpu-layers','0','--no-warmup','--no-context-shift','--json-schema-file',str(work/('schema-probe-'+kind+'.json'))]
 with (folder/('probe-'+kind+'.stdout.txt')).open('wb') as stdout,(folder/('probe-'+kind+'.stderr.txt')).open('wb') as stderr:
  process=subprocess.Popen(args,stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
 try:
  start=time.monotonic()
  while True:
   assert process.poll() is None,'原生pattern检查服务启动失败'
   try:
    if get('health').get('status')=='ok':break
   except (OSError,TimeoutError):pass
   assert time.monotonic()-start<60;time.sleep(.25)
  props=get('props');grammar=props['default_generation_settings']['params']['grammar']
  assert isinstance(grammar,str) and grammar and '证据不足' in grammar
  grammars[kind]=grammar;(folder/('native-'+kind+'.gbnf')).write_text(grammar,encoding='utf-8')
  props['model_path']='%LOCALAPPDATA%/ANTLabLocalModel/models/Qwen3-0.6B-Q8_0.gguf'
  probes.append({'kind':kind,'arguments':[a.replace(str(root),'%LOCALAPPDATA%/ANTLabLocalModel').replace(str(work),'WORKSPACE/work') for a in args],'props':props,'http_routes':['health','props'],'generation_requests':0})
 finally:
  if process.poll() is None:process.terminate();process.wait(timeout=10)
  probes[-1]['service_stopped']=process.poll() is not None if probes and probes[-1]['kind']==kind else False
  (folder/'native-pattern-probes.json').write_text(json.dumps(probes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 log=(folder/('probe-'+kind+'.stderr.txt')).read_text(encoding='utf-8',errors='replace')
 assert 'accepting any string' not in log and 'is not supported' not in log,'pattern回退，停止'

class ModelParams(c.Structure):
 _fields_=[('devices',c.c_void_p),('tensor_buft_overrides',c.c_void_p),('n_gpu_layers',c.c_int32),('split_mode',c.c_int),('load_mode',c.c_int),('lazy_mode',c.c_int),('main_gpu',c.c_int32),('tensor_split',c.c_void_p),('progress_callback',c.c_void_p),('progress_callback_user_data',c.c_void_p),('kv_overrides',c.c_void_p),('vocab_only',c.c_bool),('check_tensors',c.c_bool),('use_extra_bufts',c.c_bool),('no_host',c.c_bool),('no_alloc',c.c_bool),('load_mtp',c.c_bool)]
class Token(c.Structure):_fields_=[('id',c.c_int32),('logit',c.c_float),('p',c.c_float)]
class Tokens(c.Structure):_fields_=[('data',c.POINTER(Token)),('size',c.c_size_t),('selected',c.c_int64),('sorted',c.c_bool)]
dll_dir=os.add_dll_directory(str(binary));lib=c.CDLL(str(binary/'llama.dll'))
def signature(name,args,ret):
 fn=getattr(lib,name);fn.argtypes=args;fn.restype=ret;return fn
signature('llama_backend_init',[],None)()
default=signature('llama_model_default_params',[],ModelParams)
load=signature('llama_model_load_from_file',[c.c_char_p,ModelParams],c.c_void_p)
free_model=signature('llama_model_free',[c.c_void_p],None)
vocab_of=signature('llama_model_get_vocab',[c.c_void_p],c.c_void_p)
tokenize=signature('llama_tokenize',[c.c_void_p,c.c_char_p,c.c_int32,c.POINTER(c.c_int32),c.c_int32,c.c_bool,c.c_bool],c.c_int32)
eos_of=signature('llama_vocab_eos',[c.c_void_p],c.c_int32)
grammar_init=signature('llama_sampler_init_grammar',[c.c_void_p,c.c_char_p,c.c_char_p],c.c_void_p)
apply=signature('llama_sampler_apply',[c.c_void_p,c.POINTER(Tokens)],None)
accept=signature('llama_sampler_accept',[c.c_void_p,c.c_int32],None)
free_sampler=signature('llama_sampler_free',[c.c_void_p],None)
params=default();params.vocab_only=True;params.n_gpu_layers=0
model=load(str(root/'models/Qwen3-0.6B-Q8_0.gguf').encode(),params);assert model
rows=[]
try:
 vocab=vocab_of(model);eos=eos_of(vocab)
 for test in json.loads((folder/'offline-regex-check.json').read_text(encoding='utf-8'))['tests']:
  if test['rule']['kind'] is None:continue
  kind='number' if test['rule']['kind']=='数值' else 'percent'
  value={'answer':test['answer'],'citations':[]};text=json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()
  output=(c.c_int32*2048)();n=tokenize(vocab,text,len(text),output,len(output),False,False);assert 0<n<=len(output)
  sampler=grammar_init(vocab,grammars[kind].encode(),b'root');assert sampler
  valid=True;failed_token=None
  try:
   for token in list(output[:n])+[eos]:
    data=(Token*1)(Token(token,0.0,0.0));array=Tokens(data,1,-1,False);apply(sampler,c.byref(array))
    if not math.isfinite(data[0].logit):valid=False;failed_token=token;break
    accept(sampler,token)
  finally:free_sampler(sampler)
  rows.append({'kind':kind,'json_text':text.decode(),'expected_accept':test['expected_accept'],'native_accept':valid,'first_rejected_token':failed_token})
  assert valid==test['expected_accept'],'原生grammar与预期不符：'+text.decode()
finally:
 free_model(model);signature('llama_backend_free',[],None)();dll_dir.close()
record={'checked_at':datetime.now().astimezone().isoformat(),'supported':True,'native_tests':rows,'method':'本机server从Schema编译的GBNF；同包llama.dll仅vocab_only加载，以grammar sampler检查人工构造token串和EOS，不调用encode/decode，不生成token。','generated_tokens':0,'counts_as_generation':False,'api_source':'official-llama.h：llama_model_params、token_data_array、llama_sampler_init_grammar/apply/accept','fallback_seen':False,'probe_services_stopped':True}
(folder/'native-pattern-validation.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PASS native grammar',len(rows),'synthetic JSON acceptance/rejection cases; zero generated tokens')
