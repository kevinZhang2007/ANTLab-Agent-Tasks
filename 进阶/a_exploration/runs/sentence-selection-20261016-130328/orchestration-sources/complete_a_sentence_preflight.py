from pathlib import Path
import sys,json,shutil,ast,difflib
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
out=Path(Path('a-sentence-out.txt').read_text().strip());history=out/'preparation-history';history.mkdir()
module=HERE/'sentence_selection.py';runner=HERE/'diagnose_sentence_selection.py'
for p in [module,runner,out/'intervention-plan.json',out/'diagnostic-inputs.json']:shutil.copy2(p,history/p.name)
source=module.read_text(encoding='utf-8')
source=source.replace('ANSWER_PROMPT.replace(OLD_FORMAT,NEW_FORMAT)+FORMAT_NOTE',"ANSWER_PROMPT.replace(OLD_FORMAT,NEW_FORMAT).replace('evidence为空','sentence_ids为空')+FORMAT_NOTE")
source=source.replace('CANDIDATE_PROMPT[:-len(FORMAT_NOTE)].replace(NEW_FORMAT,OLD_FORMAT)==ANSWER_PROMPT',"CANDIDATE_PROMPT[:-len(FORMAT_NOTE)].replace(NEW_FORMAT,OLD_FORMAT).replace('sentence_ids为空','evidence为空')==ANSWER_PROMPT")
module.write_text(source,encoding='utf-8')
adapter=HERE/'sentence_interface.py';assert not adapter.exists();shutil.copy2('a_sentence_interface.py',adapter)
from sentence_selection import CANDIDATE_PROMPT,adapt_messages,offline_checks
from sentence_interface import offline_checks as interface_checks
checks=offline_checks();ic=interface_checks();assert checks['passed'] and ic['passed']
items=load(out/'diagnostic-inputs.json')
for item in items:item['messages']['revised']=adapt_messages(item['messages']['original'],item['sentence_index'])
write(out/'diagnostic-inputs.json',items)
# 这个补充门禁也由实际运行器执行，不能离线失败后仍启动。
src=runner.read_text(encoding='utf-8');old="    assert load(out/'offline-checks.json')['passed']";assert src.count(old)==1
src=src.replace(old,old+"\n    assert load(out/'interface-adapter-check.json')['passed']")
runner.write_text(src,encoding='utf-8')
write(out/'interface-adapter-check.json',{'at':now(),'passed':True,'sentence_recheck':checks,'interface_checks':ic,'source_hash':sha(adapter),'generation_calls':0,'scope':'普通输出字段适配修正：原提示空引用字段在内部对应sentence_ids；不改语义、假设、Schema、采样或预算。完整接口在本轮输出后离线构造，不宣称已重接页面。'})
initial=load(history/'intervention-plan.json');plan=load(out/'intervention-plan.json')
plan.update(preparation_revised_at=now(),original_plan_preserved='preparation-history/intervention-plan.json',original_plan_hash=sha(history/'intervention-plan.json'),preparation_fix='仅统一空引用内部字段名并补对外接口适配器和失败门禁；研究预测与取舍未改。',input_sha256=sha(out/'diagnostic-inputs.json'),code_hashes={p.relative_to(ROOT).as_posix():sha(p) for p in HERE.glob('*.py')})
write(out/'intervention-plan.json',plan)
write(out/'preparation-repair.json',{'at':now(),'actual_generated_before_fix':0,'original_plan_saved_at':initial['saved_at'],'changes':['空引用字段evidence改为内部sentence_ids，完整语义原样保留','增加对外接口来源字段及失败测试，语义仍not_checked','实际运行器执行补充门禁'],'not_model_failure':True,'history':'preparation-history/'})
snap=out/'code-snapshot-execution';snap.mkdir()
for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'));shutil.copy2(p,snap/p.name)
print(json.dumps({'passed':True,'sentence_checks':checks['count'],'interface_checks':ic['count'],'new_model_calls':0,'out':str(out)},ensure_ascii=False))
