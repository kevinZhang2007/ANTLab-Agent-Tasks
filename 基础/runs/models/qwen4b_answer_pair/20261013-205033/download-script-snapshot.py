"""一次正常证书校验下载；保留旧部分文件，失败不重试。"""
from pathlib import Path
from datetime import datetime
import json,hashlib,shutil,ssl,urllib.request,time,sys

folder=Path(sys.argv[1]);root=Path(r'C:\Users\86186\AppData\Local\ANTLabLocalModel')
source=json.loads((folder/'locked-source.json').read_text(encoding='utf-8'))['official_metadata']
original=root/'models/Qwen3-4B-Q4_K_M.gguf.partial'
destination=root/'models/Qwen3-4B-Q4_K_M.gguf'
partial=root/('models/Qwen3-4B-Q4_K_M.gguf.resume-'+folder.name+'.partial')
def digest(p):
    with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def save(name,value):(folder/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
record={'recorded_at':datetime.now().astimezone().isoformat(),'url':source['URL'],'expected_bytes':source['Bytes'],'expected_sha256':source['SHA256'],'certificate_verification':True,'attempts':0,'generation_calls':0,'status':'preparing','old_partial_preserved':True}
record['old_partial_bytes']=original.stat().st_size if original.exists() else 0
record['old_partial_sha256']=digest(original) if original.exists() else None
record['disk_free_bytes']=shutil.disk_usage(root).free
start=time.perf_counter()
try:
    if destination.exists():
        record['existing_complete_bytes']=destination.stat().st_size;record['actual_sha256']=digest(destination)
        assert destination.stat().st_size==source['Bytes'] and record['actual_sha256']==source['SHA256'],'已存在完整文件不匹配，保留并停止'
        record['status']='verified_existing';record['verified']=True
    else:
        assert record['disk_free_bytes']>source['Bytes']+256*1024**2,'下载剩余磁盘空间不足'
        assert not partial.exists(),'本轮部分文件已存在，禁止重复执行'
        if original.exists():shutil.copyfile(original,partial)
        else:partial.touch()
        offset=partial.stat().st_size
        headers={'User-Agent':'ANTLab-official-model-download/1.0'}
        if offset:headers['Range']='bytes='+str(offset)+'-'
        request=urllib.request.Request(source['URL'],headers=headers)
        record.update(attempts=1,status='connecting',resume_offset=offset);save('download.json',record)
        context=ssl.create_default_context()
        assert context.check_hostname and context.verify_mode==ssl.CERT_REQUIRED
        with urllib.request.urlopen(request,timeout=45,context=context) as response:
            record['http_status']=response.status
            record['content_range']=response.headers.get('Content-Range')
            if response.status==206:
                assert record['content_range'] and record['content_range'].startswith('bytes '+str(offset)+'-') and record['content_range'].endswith('/'+str(source['Bytes'])),'Range响应与预期不符'
                mode='ab'
            elif response.status==200:
                mode='wb';record['server_ignored_range_restart_in_new_file']=True
            else:raise RuntimeError('不支持的HTTP状态:'+str(response.status))
            last=time.perf_counter()
            with partial.open(mode) as output:
                while True:
                    chunk=response.read(1024*1024)
                    if not chunk:break
                    output.write(chunk)
                    if time.perf_counter()-last>=10:
                        output.flush();record.update(status='downloading',downloaded_bytes=output.tell(),elapsed_seconds=time.perf_counter()-start)
                        save('download.json',record);print(json.dumps({'bytes':output.tell(),'elapsed_seconds':record['elapsed_seconds']},ensure_ascii=False),flush=True);last=time.perf_counter()
        record['downloaded_bytes']=partial.stat().st_size;record['actual_sha256']=digest(partial)
        assert partial.stat().st_size==source['Bytes'] and record['actual_sha256']==source['SHA256'],'完整大小或SHA-256不一致，保留并停止'
        assert not destination.exists();partial.rename(destination)
        record.update(status='verified_download',verified=True)
except Exception as error:
    record.update(status='download_or_validation_failed',verified=False,error_type=type(error).__name__,error_detail=str(error),retry_attempted=False)
    if partial.exists():record['downloaded_bytes']=partial.stat().st_size
finally:
    record['elapsed_seconds']=time.perf_counter()-start
    record['old_partial_unchanged']=not original.exists() or (original.stat().st_size==record['old_partial_bytes'] and digest(original)==record['old_partial_sha256'])
    assert record['old_partial_unchanged']
    save('download.json',record)
    save('phase-progress.json',{'recorded_at':datetime.now().astimezone().isoformat(),'download_status':record['status'],'weight_verified':record.get('verified',False),'loading_not_started':True,'generation_calls':0})
    print(json.dumps(record,ensure_ascii=False,indent=2),flush=True)
