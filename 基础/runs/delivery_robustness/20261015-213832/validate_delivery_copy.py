"""拟提交清单、干净副本及只读复算；不会调用模型、暂存或修改旧评价。"""
from pathlib import Path
from datetime import datetime
import hashlib,json,os,re,shutil,subprocess,sys,tempfile
R=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');F=R/'基础/runs/delivery_robustness/20261015-213832'
L=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def H(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
N=lambda:datetime.now().astimezone().isoformat()
def W(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2)
def main():
    git=Path(os.environ['LOCALAPPDATA'])/'Programs/Git/cmd/git.exe'
    names=subprocess.check_output([str(git),'ls-files','--cached','--others','--exclude-standard','-z'],cwd=R).decode('utf-8').split('\0')
    paths=sorted(set(n for n in names if n and (R/n).is_file()))
    denied=[n for n in paths if Path(n).name in ['config.local.json','.env'] or Path(n).suffix.lower() in ['.gguf','.pyc','.pyo'] or '__pycache__' in Path(n).parts]
    W(F/'candidate-file-safety.json',{'checked_at':N(),'private_weight_cache_files':denied,'selection_source':'git ls-files --cached --others --exclude-standard -z；仅清单，不执行git add','no_model_calls':True})
    assert not denied,'拟提交清单含私人配置或权重缓存，停止'
    secrets=[];pattern=re.compile(rb'(?<![A-Za-z0-9])(?:sk-[A-Za-z0-9_-]{24,}|ghp_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,})')
    for name in paths:
        p=R/name
        if p.suffix.lower() in ['.json','.jsonl','.py','.md','.txt','.html','.csv','.toml','.yaml','.yml'] and pattern.search(p.read_bytes()):secrets.append(name)
    W(F/'credential-pattern-check.json',{'checked_at':N(),'matched_files':secrets,'patterns':'常见OpenAI/GitHub令牌前缀及足够长度；不输出可能的值','limit':'静态常见模式检查不是对所有凭据形式的完整证明。','no_model_calls':True})
    assert not secrets,'疑似凭据，保留位置并停止'
    index_before=H(R/'.git/index') if (R/'.git/index').is_file() else None
    head=subprocess.check_output([str(git),'rev-parse','HEAD'],cwd=R,text=True).strip()
    snapshot=L(F/'previous-results-snapshot.json')
    assert all(H(R/snapshot['path']/name)==h for name,h in snapshot['files'].items())
    allprotected=L(F/'protected-hashes.json');assert all(H(R/p)==h for p,h in allprotected.items())
    # 自身清单的哈希不递归嵌套；其余文件内容会在临时副本中重新逐项核对。
    manifest={'recorded_at':N(),'source_commit':head,'file_count_before_this_validation_artifacts':len(paths),'total_bytes':sum((R/p).stat().st_size for p in paths),'selection_command':'git ls-files --cached --others --exclude-standard -z','not_staged':True,'excluded_private_config':True,'paths':paths,'note':'这是拟交付工作区文件清单，不代表已经暂存或最终提交；后续本轮验证输出另见audit目录文件清单。'}
    (R/'results/scoring/submission-files.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temp=Path(tempfile.mkdtemp(prefix='antlab_delivery_')).resolve()
    before={}
    for name in paths:
        source=R/name;destination=(temp/name).resolve();assert destination.is_relative_to(temp)
        destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
        before[name]=H(destination);assert before[name]==H(source)
    command=[sys.executable,'-I','-X','utf8','-B',str(temp/'results/scoring/recalculate.py')]
    proc=subprocess.run(command,cwd=F,capture_output=True,text=True,encoding='utf-8')
    (F/'clean-recalculation.stdout.json').write_text(proc.stdout,encoding='utf-8');(F/'clean-recalculation.stderr.txt').write_text(proc.stderr,encoding='utf-8')
    passed=proc.returncode==0
    recalculated=json.loads(proc.stdout) if passed else {}
    assert passed,'干净副本复算失败，日志已保存'
    reference=L(F/'recalculation-final.json');assert recalculated==reference
    changed=[p for p,h in before.items() if H(temp/p)!=h];assert not changed,'只读复算改写副本文件'
    index_after=H(R/'.git/index') if (R/'.git/index').is_file() else None;assert index_before==index_after
    result={'recorded_at':N(),'status':'passed','clean_copy':'临时副本/'+temp.name,'copied_candidate_files':len(paths),'git_metadata_copied':False,'private_config_copied':False,'model_weights_copied':False,'command':['python','-I','-X','utf8','-B','<CLEAN_COPY>/results/scoring/recalculate.py'],'exit_code':proc.returncode,'isolated_output_equals_worktree':True,'copied_files_unchanged':True,'external_experiment_dependencies':False,'model_generations':recalculated['counts']['model_generations'],'b_offline_executions':recalculated['counts']['b_offline_executions'],'same_request_log_links':recalculated['b_same_request_log_links'],'csv_rows':recalculated['csv_rows'],'compared_summaries':len(recalculated['summary_comparisons']),'all_compared_summaries_equal':recalculated['all_compared_summaries_equal'],'new_model_calls':0,'old_archive_and_three_docs_unchanged':True,'index_unchanged':True,'source_commit':head,'limitations':'只复算归档辅助标签，不自动证明语义正确；当前Python3.14，仅隔离路径与依赖，不是其他操作系统/解释器/新机模型复跑。'}
    W(F/'clean-copy-validation.json',result)
    (R/'results/scoring/validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
