from pathlib import Path
from datetime import datetime
import ast,difflib,hashlib,json,shutil
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');WORK=Path(__file__).resolve().parent
def main():
    folder=ROOT/'基础/runs/page_closure'/datetime.now().strftime('%Y%m%d-%H%M%S');folder.mkdir(parents=True,exist_ok=False)
    target=ROOT/'基础/starter/index.html';before=target.read_text(encoding='utf-8');(folder/'index-before.html').write_bytes(target.read_bytes())
    for source,dest in [('server_exploration.py','基础/starter/server_exploration.py'),('run_page_closure.py','基础/tests/run_page_closure.py')]:
        path=ROOT/dest
        if path.exists():raise FileExistsError(path)
        ast.parse((WORK/source).read_text(encoding='utf-8'));shutil.copyfile(WORK/source,path)
    start=before.index('<script>');end=before.index('</script>',start)
    after=before[:start]+'<script>\n'+(WORK/'page_closure_ui.js').read_text(encoding='utf-8')+'\n'+before[end:]
    after=after.replace('这是骨架，不是完成的作业。先实现 student.py。预览不调用模型；模拟结果不能作实验证据。','原入口保留。探索入口使用冻结的整合方案；预览和模拟不能作真实模型证据。')
    after=after.replace('<label>样例','<label>入口<select id="entry"><option value="original">原入口</option><option value="integrated" disabled>评测后系统探索</option></select></label><p id="version-note">正在使用：原入口</p>\n<label>样例',1)
    after=after.replace('<option value="paid">自费API</option>','<option value="paid">自费API</option><option value="local" disabled>本地真实模型（免费）</option>')
    after=after.replace('<pre id="result">等待输入。请自行补充对照结果呈现与分析。</pre>','<details><summary>提交问题、完整可见资料与配置预览</summary><pre id="preview">原入口预览由原后端处理。</pre></details><section id="closure"></section><details><summary>实际HTTP返回完整内容</summary><pre id="result">等待输入。</pre></details>')
    assert after!=before and '__SESSION_TOKEN__' in after
    target.write_text(after,encoding='utf-8',newline='\n')
    diff=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/基础/starter/index.html',tofile='b/基础/starter/index.html'))
    for name,dest in [('server_exploration.py','基础/starter/server_exploration.py'),('run_page_closure.py','基础/tests/run_page_closure.py')]:diff+=''.join(difflib.unified_diff([], (ROOT/dest).read_text(encoding='utf-8').splitlines(True),fromfile='/dev/null',tofile='b/'+dest))
    (folder/'code.diff').write_text(diff,encoding='utf-8')
    (folder/'validation-plan.json').write_text(json.dumps({'recorded_at':datetime.now().astimezone().isoformat(),'purpose':'页面真实请求闭环，不更新准确率','first_40_preserved':True,'entry':'基础/runs/repeat_integrated/20261015-171741/proof_pipeline_candidate.py','case':'D03','condition':'R0','variant':'improved','generation_limit':2,'requests':'页面一次提交；定位和回答各最多一次；不使用mock/draft','failure':'准备小错误可离线修复留档；真实请求发出后不自动重发，技术错误停止','model_and_rule_results':'模型原答live_api；规则派生local_rule/rule；语义not_checked；原文和原始字段保留','expected':'可从同main_task_id回查页面、HTTP、模型stage ID和原文来源；答错保留，不作为优化实验','offline_first':True},ensure_ascii=False,indent=2),encoding='utf-8')
    shutil.copyfile(Path(__file__),folder/'prepare_page_closure.py')
    print(str(folder))
if __name__=='__main__':main()
