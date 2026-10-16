from pathlib import Path
import sys,json,shutil,difflib
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
out=Path(Path('a-current-e2e-out.txt').read_text(encoding='utf-8').strip());target=HERE/'prepare_current_run.py';assert not target.exists()
target.write_text('''"""仅准备新目录；不启动模型、不生成，复用锁定代码及容量证据。"""
from pathlib import Path
import argparse,copy,shutil
from runtime import HERE,ROOT,load,write,sha,now
from current_candidate import query_config

SOURCE=HERE/'runs/current-e2e-20261016-183739'
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();folder=a.out.resolve()
    if folder.exists():raise ValueError('输出目录必须不存在，不覆盖归档')
    pre=load(SOURCE/'offline-preflight.json')
    for n,h in {**pre['code_hashes'],**pre['data_hashes']}.items():
        if sha(ROOT/n)!=h:raise ValueError('锁定文件改变：'+n)
    plan=load(SOURCE/'development-plan.json');assert query_config()==plan['query_configuration']
    assert load(SOURCE/'offline-capacity-exact.json')['passed'] and load(SOURCE/'page-generation-gate.json')['passed']
    for n,h in [(plan['service_arguments'][0],pre['executable_hash']),(plan['service_arguments'][plan['service_arguments'].index('-m')+1],pre['model_hash'])]:
        if sha(Path(n))!=h:raise ValueError('本机已校验模型或执行文件改变：'+n)
    folder.mkdir(parents=True)
    for n in ['configuration.json','development-inputs.json','locator-anchors.json','worst-inputs.json','offline-capacity-exact.json']:
        shutil.copy2(SOURCE/n,folder/n)
    plan=copy.deepcopy(plan);plan.update(prepared_at=now(),reproduction_of=SOURCE.relative_to(ROOT).as_posix(),not_executed=True)
    write(folder/'development-plan.json',plan)
    pre=copy.deepcopy(pre);pre.update(prepared_at=now(),capacity_reused_only_after_hash_match=True,reproduction_preparer_sha256=sha(Path(__file__)))
    pre['code_hashes'][Path(__file__).relative_to(ROOT).as_posix()]=sha(Path(__file__))
    write(folder/'offline-preflight.json',pre)
    write(folder/'prepared-only.json',{'at':now(),'status':'prepared_not_run','model_service_started':False,'generation_calls':0,'all_locked_dependencies_match':True,'note':'仅准备新目录。实际启动仍需重新检查内存、端口、健康与每阶段实际模板；启动并页面提交会新增生成。'})
    print(str(folder))

if __name__=='__main__':main()
''',encoding='utf-8')
shutil.copy2(target,out/'code-snapshot'/target.name)
with (out/'complete-code.diff').open('a',encoding='utf-8') as f:f.write(''.join(difflib.unified_diff([],target.read_text(encoding='utf-8').splitlines(True),fromfile='/dev/null',tofile='b/'+target.relative_to(ROOT).as_posix())))
write(out/'reproduction-entry.json',{'at':now(),'single_mode_entry':'进阶/a_exploration/current_candidate.py::CurrentEngine.execute(claim, doc_ids, snapshot, mode)','paired_page_entry':'CurrentEngine.execute_pair，和单侧入口共享_execute_modes及build_answer','preparer':'进阶/a_exploration/prepare_current_run.py','preparer_sha256':sha(target),'launcher':'进阶/a_exploration/launch_current.py','actual_executed_command':'python -X utf8 -B 进阶/a_exploration/launch_current.py --out 进阶/a_exploration/runs/current-e2e-20261016-183739 --port 8890','future_prepare_command':'python -X utf8 -B 进阶/a_exploration/prepare_current_run.py --out 进阶/a_exploration/runs/current_e2e_new','future_launch_command':'python -X utf8 -B 进阶/a_exploration/launch_current.py --out 进阶/a_exploration/runs/current_e2e_new --port 8890','page_url':'http://127.0.0.1:8890/','warning':'归档目录不能重跑。上述未来启动命令未再次执行；实际页面提交会新增生成。'})
print(str(target))
