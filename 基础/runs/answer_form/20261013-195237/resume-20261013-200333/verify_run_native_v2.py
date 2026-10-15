from pathlib import Path
from datetime import datetime
import json,hashlib,difflib,ast,subprocess,sys
folder=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks\基础\runs\answer_form\20261013-195237\resume-20261013-200333')
old=(folder.parent/'check_native_pattern.py').read_text(encoding='utf-8')
path=folder/'check-native-pattern-v2.py';new=path.read_text(encoding='utf-8');ast.parse(new)
assert 'get(\'props\')' not in new and 'probes[-1]' not in new
assert path.read_bytes()==(Path(__file__).parent/'check_answer_form_native_v2.py').read_bytes()
(folder/'repair-full.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='check_native_pattern.py',tofile='check-native-pattern-v2.py')),encoding='utf-8')
(folder/'repair-content-check.json').write_text(json.dumps({'checked_at':datetime.now().astimezone().isoformat(),'actual_file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'props_grammar_assumption_removed':True,'unsafe_empty_list_index_removed':True,'actual_bytes_match_written_source':True,'AST_pass':True,'CRLF_note':'新文件整体写入；实际字节核对，无字符串替换是否命中的假设。'},ensure_ascii=False,indent=2),encoding='utf-8')
(folder/'launch-wiring-failure.json').write_text(json.dumps({'recorded_at':datetime.now().astimezone().isoformat(),'issues':['PowerShell内嵌Python引号失效，检查命令SyntaxError。','随后调用检查器遗漏目录参数，进入任何DLL调用前IndexError。'],'native_grammar_tests_executed':0,'generation_calls':0,'correction':'用保存的Python启动脚本传入明确参数；先验证实际代码，再唯一执行原生检查。'},ensure_ascii=False,indent=2),encoding='utf-8')
args=[sys.executable,'-X','utf8','-B',str(path),str(folder)]
started=datetime.now().astimezone().isoformat()
p=subprocess.run(args,capture_output=True,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
(folder/'native-v2.stdout.txt').write_bytes(p.stdout);(folder/'native-v2.stderr.txt').write_bytes(p.stderr)
(folder/'native-v2-command-result.json').write_text(json.dumps({'started_at':started,'arguments':args,'returncode':p.returncode,'counts_as_generation':False,'stdout':'native-v2.stdout.txt','stderr':'native-v2.stderr.txt'},ensure_ascii=False,indent=2),encoding='utf-8')
print(p.stdout.decode('utf-8',errors='replace'));print(p.stderr.decode('utf-8',errors='replace')[-2000:]);print('EXIT',p.returncode)
assert p.returncode==0,'原生正反例检查失败，停止，不生成'
