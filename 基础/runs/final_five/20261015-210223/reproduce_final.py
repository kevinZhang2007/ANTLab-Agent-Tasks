"""复用第五轮已执行运行器；只允许全新目录。执行将新增最多24次生成。"""
from pathlib import Path
from datetime import datetime
import argparse,copy,hashlib,json,os,shutil,subprocess,sys
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'基础/starter/provider.py').is_file())
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,ensure_ascii=False,indent=2)
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,help='仓库内基础/runs下的全新目录')
    parser.add_argument('--verify-only',action='store_true',help='只核对哈希与路径，不建目录、不启动或调用模型')
    args=parser.parse_args();output=(ROOT/args.output).resolve()
    assert output.is_relative_to(ROOT/'基础/runs') and not output.exists(),'输出目录须全新且在基础/runs内'
    source=HERE/'round5';freeze=load(source/'freeze.json')
    assert all(sha(ROOT/p)==h for p,h in {**freeze['code_hashes'],**freeze['data_hashes']}.items())
    local=Path(os.environ['LOCALAPPDATA'])/'ANTLabLocalModel'
    assert sha(local/'models/Qwen3-0.6B-Q8_0.gguf')==freeze['model']['actual_sha256']
    assert sha(local/'llama-b11429/llama-server.exe')==freeze['llama_cpp']['executable_sha256']
    for name in ['settings.prepared.json','answer.prepared.json','selection.prepared.json','execution-plan.prepared.json','execution-offline-check.json','parent-freeze-verification.json','version-verification.json']:assert (source/name).is_file()
    assert load(source/'execution-offline-check.json')['passed']
    print(json.dumps({'verified':True,'source_freeze_sha256':sha(source/'freeze.json'),'generation_calls':0,'verify_only':args.verify_only},ensure_ascii=False),flush=True)
    if args.verify_only:return 0
    # 复现是新的已接触题重复运行，不覆盖历史，也不挑选历史最好回答。
    output.mkdir(parents=True,exist_ok=False)
    for name in ['settings.prepared.json','answer.prepared.json','selection.prepared.json','execution-offline-check.json','parent-freeze-verification.json','version-verification.json']:shutil.copyfile(source/name,output/name)
    ids=set()
    for path in (ROOT/'基础/runs').rglob('*.json'):
        data=load(path)
        if not isinstance(data,dict) or not data.get('run_id'):continue
        response=data.get('response');usage=data.get('usage') or (response.get('usage') if isinstance(response,dict) else {}) or {}
        if usage.get('completion_tokens',0)>0:ids.add(data['run_id'])
    plan=copy.deepcopy(load(source/'execution-plan.prepared.json'))
    plan.update(saved_at=datetime.now().astimezone().isoformat(),previous_cumulative=len(ids))
    plan['design']['reproduction_of']=source.relative_to(ROOT).as_posix()
    write(output/'execution-plan.prepared.json',plan)
    write(output/'reproduction-source.json',{'source_freeze':(source/'freeze.json').relative_to(ROOT).as_posix(),'source_freeze_sha256':sha(source/'freeze.json'),'maximum_calls':24,'existing_results_not_reused':True})
    return subprocess.call([sys.executable,'-X','utf8','-B',str(HERE/'run_bounded_round.py'),str(output)])
if __name__=='__main__':raise SystemExit(main())
