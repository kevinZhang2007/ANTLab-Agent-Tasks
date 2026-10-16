from pathlib import Path
import sys,subprocess,ast
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
out=Path(Path('a-query-translation-out.txt').read_text(encoding='utf-8').strip())
write(out/'preparation-error.json',{'at':now(),'phase':'offline_historical_scope_comparison','error':'AssertionError: scope == pair[scope_blocks]','source':'prepare_a_query_translation.py:16','cause':'Corpus.scope包含内部排序字段_order，而历史scope_blocks仅保存public字段；逐字原文及范围实际一致。','generation_calls':0,'service_started':False})
src=Path('prepare_a_query_translation.py').read_text(encoding='utf-8')
prefix=src[:src.index("out=HERE/'runs'/")]
state="out=Path("+repr(str(out))+ ")\ntranslations_path=HERE/'runs/claim-language-20261016-123016/translations.json'\nsource=HERE/'runs/development-20261016-115250'\n"
tail=src[src.index('tr=load(translations_path)'):]
assert "assert scope==pair['scope_blocks']" in tail
tail=tail.replace("assert scope==pair['scope_blocks']","assert [public(b) for b in scope]==pair['scope_blocks']")
target=out/'replay_preparation_repaired.py';assert not target.exists();target.write_text(prefix+state+tail,encoding='utf-8');ast.parse(target.read_text(encoding='utf-8'))
write(out/'preparation-repair.json',{'at':now(),'original_source_sha256':sha(Path('prepare_a_query_translation.py')),'actual_repaired_source_sha256':sha(target),'change':'将当前scope转为与历史相同的public结构比较，仍检查所有原字段、完整正文及顺序；只排除内部_order元数据，不改变检索或正文。','original_error_preserved':'preparation-error.json','generation_calls':0})
r=subprocess.run([sys.executable,'-X','utf8','-B',str(target)],capture_output=True)
(out/'replay.stdout.txt').write_bytes(r.stdout);(out/'replay.stderr.txt').write_bytes(r.stderr)
print(r.stdout.decode('utf-8',errors='replace'));print(r.stderr.decode('utf-8',errors='replace'));sys.exit(r.returncode)
