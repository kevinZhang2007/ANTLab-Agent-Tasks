from pathlib import Path
import sys,json,copy,shutil,subprocess,ast
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration'
sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
from sentence_selection import CANDIDATE_PROMPT as CURRENT_PROMPT
from relation_first import PROMPT,schema,messages,offline_checks
from preflight import native_tokenizer
out=Path('a-relation-out.txt').read_text(encoding='utf-8').strip();out=Path(out)
previous=HERE/'runs/sentence-selection-20261016-130328'
assert not list(out.glob('run-*.json')) and not (out/'owned-service.json').exists()
rows=[]
for item in load(out/'schema-cases.json'):
    grammar=(out/('compiled-'+item['name']+'.gbnf')).read_text(encoding='utf-8')
    root=next(line for line in grammar.splitlines() if line.startswith('root ::='))
    mapping={}
    for key in ['relation','explanation','sentence_ids','label']:
        literal=json.dumps(json.dumps(key))
        matches=[line.split(' ::= ',1)[0] for line in grammar.splitlines() if ' ::= '+literal+' space ":"' in line]
        assert len(matches)==1,(key,literal,matches)
        mapping[key]=matches[0]
    positions=[root.find(mapping[k]) for k in mapping]
    forced=all(n>=0 for n in positions) and positions==sorted(positions) and root.count('-kv')==4 and '|' not in root
    rows.append({'case':item['name'],'root':root,'json_key_to_native_rule':mapping,'positions':positions,'forced':forced})
write(out/'schema-order-compilation-corrected.json',{'at':now(),'all_forced':all(x['forced'] for x in rows),'rows':rows,'generation_calls':0,'source':'已保存的实际装机原生转换结果；依据JSON键字面量匹配规则名，不假定内部规则名称保留下划线。'})
assert all(x['forced'] for x in rows)
write(out/'preparation-repair.json',{'at':now(),'previous_failure':'order-not-forced-stop.json','cause':'检查器假定sentence_ids-kv，实际转换器内部名称为sentence-ids-kv；真实JSON键未变。此前不支持的结论属于检查器误判，原记录保留。','repair':'通过规则定义中的真实JSON键字面量定位内部规则，再检查root序列；保留全部顺序断言并原生验证24种字段排列。','model_generations_before':0,'old_checker_sha256':sha(out/'compile_schema_order.py'),'repair_script_sha256':sha(Path(__file__))})
inputs=load(out/'diagnostic-inputs.json');checks=offline_checks();assert checks['passed']
prior={'passed':35,'source':'首次准备实际执行成功，复用已存检查结果，不重跑。'}
original=Path('prepare_a_relation.py').read_text(encoding='utf-8')
tail=original[original.index("cmd=[sys.executable,'-X','utf8','-B',str(HERE/'check_id_enum_native.py')"):]
tail=tail.replace("schema-order-compilation.json')['all_forced']", "schema-order-compilation-corrected.json')['all_forced']")
resume=out/'resume_preparation_tail.py';assert not resume.exists()
preamble="from pathlib import Path\nimport sys,json,copy,shutil,subprocess,ast\nROOT=Path("+repr(str(ROOT))+ ");HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))\nfrom runtime import load,write,sha,now\nfrom sentence_selection import CANDIDATE_PROMPT as CURRENT_PROMPT\nfrom relation_first import PROMPT,schema,messages,offline_checks\nfrom preflight import native_tokenizer\nout=Path("+repr(str(out))+ ");previous=HERE/'runs/sentence-selection-20261016-130328';inputs=load(out/'diagnostic-inputs.json');checks=offline_checks();prior="+repr(prior)+"\n"
resume.write_text(preamble+tail,encoding='utf-8');ast.parse(resume.read_text(encoding='utf-8'))
r=subprocess.run([sys.executable,'-X','utf8','-B',str(resume)],capture_output=True)
(out/'resume.stdout.txt').write_bytes(r.stdout);(out/'resume.stderr.txt').write_bytes(r.stderr)
print(r.stdout.decode('utf-8',errors='replace'));print(r.stderr.decode('utf-8',errors='replace'));sys.exit(r.returncode)
