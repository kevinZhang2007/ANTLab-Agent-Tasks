"""默认只准备新目录；--run才执行，将新增真实生成。"""
from pathlib import Path
import argparse,sys,copy,subprocess
SOURCE=Path(__file__).resolve().parent
ROOT=next(p for p in SOURCE.parents if (p/'进阶/a_exploration/runtime.py').is_file())
HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--stage',choices=['evaluation','variants','counterfactual'],default='evaluation');p.add_argument('--run',action='store_true');a=p.parse_args();out=a.out.resolve()
    if out.exists():raise ValueError('新输出目录必须不存在')
    freeze=load(SOURCE/'final-freeze.json')
    for n,h in {**freeze['code_hashes'],**freeze['data_hashes']}.items():
        if sha(ROOT/n)!=h:raise ValueError('冻结依赖改变：'+n)
    cfg=load(SOURCE/'configuration.json')
    for path,h in [(cfg['model']['path'],freeze['model_hash']),(cfg['executable']['path'],freeze['executable_hash'])]:
        if sha(Path(path))!=h:raise ValueError('本机模型或运行工具与冻结不符')
    out.mkdir(parents=True);write(out/'configuration.json',cfg);write(out/'final-freeze.json',freeze);write(out/'final-profile.json',freeze['profile'])
    stage=out/a.stage;stage.mkdir()
    for name in ['plan.json','tasks.json','profile.json','offline-checks.json']:write(stage/name,load(SOURCE/a.stage/name))
    write(out/'prepared-only.json',{'at':now(),'source':SOURCE.relative_to(ROOT).as_posix(),'stage':a.stage,'generations':0,'note':'复用相同代码及数据下的归档离线门禁；实际启动会重查内存、健康、阶段模板与容量。'})
    if a.run:subprocess.run([sys.executable,'-X','utf8','-B',str(HERE/'run_bounded_stage.py'),'--stage',str(stage)],check=True,cwd=ROOT)
    else:print('PREPARED_ONLY',stage)
if __name__=='__main__':main()
