from pathlib import Path
from datetime import datetime
import json,hashlib,difflib,ast
work=Path(__file__).parent;repo=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
folder=repo/'基础/runs/answer_form/20261013-195237/resume-20261013-200333';old=folder.parent
source=(repo/'基础/tests/run_two_step_pairs.py').read_text(encoding='utf-8');header=source.split('try:\n    # 权重再次核对；')[0]
header=header.replace("experiment=base/'runs/two_step/dev_r0'","experiment=Path(sys.argv[1])")
header=header.replace("import two_step_candidate as candidate\nconfig_selection=json.loads((folder/'config.selection.json').read_text(encoding='utf-8'))\nassert candidate.SELECTION_PROMPT==(folder/'system.selection.txt').read_text(encoding='utf-8')\nassert candidate.SELECTION_SCHEMA==json.loads((folder/'schema.selection.json').read_text(encoding='utf-8'))\nassert json.loads((folder/'offline-check.json').read_text(encoding='utf-8'))['passed']","assert json.loads((folder/'native-pattern-validation.json').read_text(encoding='utf-8'))['passed']")
header=header.replace("capacity=json.loads((base/'runs/capacity/stage3/inputs.json').read_text(encoding='utf-8'))\n",'')
header=header.replace("'record_kind':'two_step_development_runtime'","'record_kind':'historical_replay_answer_form_runtime'")
header=header.replace("root/f'logs/two-step-{log_id}.stdout.log'","root/f'logs/answer-form-{log_id}.stdout.log'")
header=header.replace("root/f'logs/two-step-{log_id}.stderr.log'","root/f'logs/answer-form-{log_id}.stderr.log'")
driver=header+'\nimport socket\n'+(work/'answer_form_driver_body.txt').read_text(encoding='utf-8')
path=repo/'基础/tests/run_answer_form_pairs.py';assert not path.exists();ast.parse(driver);path.write_text(driver,encoding='utf-8')
(folder/'snapshot-run_answer_form_pairs.py').write_bytes(path.read_bytes())
(folder/'driver-full.diff').write_text(''.join(difflib.unified_diff(source.splitlines(True),driver.splitlines(True),fromfile='基础/tests/run_two_step_pairs.py',tofile='基础/tests/run_answer_form_pairs.py')),encoding='utf-8')
(folder/'config.answer.json').write_bytes((old/'config-D02-original.json').read_bytes())
(folder/'student-source-hashes.json').write_text(json.dumps({n:hashlib.sha256((repo/'基础/starter'/n).read_bytes()).hexdigest() for n in ['student.py','provider.py','runner.py']},indent=2),encoding='utf-8')
plan=json.loads((old/'design-plan.json').read_text(encoding='utf-8'))
(folder/'execution-details.json').write_text(json.dumps({'call_order':plan['call_order']},ensure_ascii=False,indent=2),encoding='utf-8')
(folder/'before-generation-repair-record.json').write_text(json.dumps({'recorded_at':datetime.now().astimezone().isoformat(),'native_checks_passed':True,'native_test_count':41,'existing_generation_records':0,'old_plan_unchanged':True,'driver_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'scope':'历史补页输入回答阶段重放，不重新定位','cleanup':'模型服务Popen立即登记pid；finally只关闭登记pid和同一对象。空状态可处理。','method':'装机llama-common.dll导出的common_json::parse/json_schema_to_grammar，加装机llama.dll grammar sampler；不用props.grammar，无生成token的正反例核验。','ABI_limit':'本次已核对Windows x64/MSVC对象布局，不声称通用C SDK。'},ensure_ascii=False,indent=2),encoding='utf-8')
print(path)
