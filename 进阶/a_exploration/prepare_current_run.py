"""仅准备新目录；不启动模型、不生成，复用锁定代码及容量证据。"""
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
