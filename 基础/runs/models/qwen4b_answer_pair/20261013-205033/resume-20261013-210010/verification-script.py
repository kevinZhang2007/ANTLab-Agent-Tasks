from pathlib import Path
from datetime import datetime
import ctypes,json,hashlib,shutil
repo=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');base=repo/'基础';previous=base/'runs/models/qwen4b_answer_pair/20261013-205033'
now=datetime.now().astimezone();folder=previous/('resume-'+now.strftime('%Y%m%d-%H%M%S'));folder.mkdir(parents=True,exist_ok=False)
def write(name,value):(folder/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
source=json.loads((previous/'locked-source.json').read_text(encoding='utf-8'))['official_metadata']
protected={p.relative_to(repo).as_posix():digest(p) for p in repo.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts and p.name!='config.local.json' and folder not in p.parents}
write('protected-hashes.json',protected)
write('resume-plan.json',{'recorded_at':now.isoformat(),'original_plan':(previous/'design-plan.json').relative_to(repo).as_posix(),'settings_and_choice_unchanged':True,'old_failures_preserved':True,'maximum_generation_calls':8,'existing_generation_calls_this_comparison':0,'prior_cumulative_generation_calls':162,'download_source':'浏览器已下载文件；本轮不联网下载'})
class MemoryStatus(ctypes.Structure):
    _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ['total_phys','available_phys','total_page','available_page','total_virtual','available_virtual','extended']]
def memory():
    s=MemoryStatus();s.length=ctypes.sizeof(s);assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s))
    return {'measured_at':datetime.now().astimezone().isoformat(),'available_bytes':s.available_phys,'available_gib':s.available_phys/1024**3,'total_bytes':s.total_phys}
record={'recorded_at':now.isoformat(),'expected_bytes':source['Bytes'],'expected_sha256':source['SHA256'],'source_revision':source['Revision'],'before_verification_memory':memory(),'verified':False}
download=Path(r'C:\Users\86186\Downloads\Qwen3-4B-Q4_K_M.gguf');destination=Path(r'C:\Users\86186\AppData\Local\ANTLabLocalModel\models\Qwen3-4B-Q4_K_M.gguf')
try:
    record['actual_download_bytes']=download.stat().st_size;record['actual_download_sha256']=digest(download)
    assert record['actual_download_bytes']==source['Bytes'] and record['actual_download_sha256']==source['SHA256'],'下载文件大小或SHA-256不匹配'
    if destination.exists():assert destination.stat().st_size==source['Bytes'] and digest(destination)==source['SHA256'],'模型目录已有不匹配文件，保留并停止'
    else:shutil.copyfile(download,destination)
    record['model_copy_bytes']=destination.stat().st_size;record['model_copy_sha256']=digest(destination)
    assert record['model_copy_sha256']==source['SHA256']
    record['verified']=True;record['weight_location']='%LOCALAPPDATA%/ANTLabLocalModel/models/Qwen3-4B-Q4_K_M.gguf'
except Exception as error:record.update(error_type=type(error).__name__,error_detail=str(error))
record['before_loading_memory']=memory()
record['load_minimum_available_gib']=5.25;record['resource_ready']=record['before_loading_memory']['available_gib']>=5.25
record['resource_gap_gib']=max(0,5.25-record['before_loading_memory']['available_gib'])
write('file-verification-and-resource.json',record)
write('phase-progress.json',{'recorded_at':datetime.now().astimezone().isoformat(),'weight_verified':record['verified'],'resource_ready':record['resource_ready'],'loading_started':False,'generation_calls':0,'cumulative_generation_calls':162})
print(json.dumps({'folder':str(folder),'result':record},ensure_ascii=False,indent=2))
