from pathlib import Path
import sys,json,shutil,ast
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
from preflight import native_tokenizer
out=Path(Path('a-sentence-out.txt').read_text().strip());hist=out/'preparation-history'
p=HERE/'sentence_interface.py';shutil.copy2(p,hist/'sentence_interface.before-scope-fix.py');shutil.copy2(out/'intervention-plan.json',hist/'intervention-plan.before-scope-fix.json');shutil.copy2(out/'planned-request-differences.json',hist/'planned-request-differences.initial.json')
src=p.read_text(encoding='utf-8').replace('model_elapsed_seconds,locator=None):','model_elapsed_seconds,locator=None,actual_input_blocks=None):')
src=src.replace("    start=time.perf_counter()","    start=time.perf_counter()\n    actual_input_blocks=[] if actual_input_blocks is None else actual_input_blocks\n    if any(b['doc_id'] not in doc_ids or b['snapshot']!=snapshot for b in actual_input_blocks):raise ValueError('实际模型输入跨范围')\n    by_block={b['block_id']:b for b in actual_input_blocks}")
src=src.replace("'actual_doc_ids':[],'actual_snapshots':[]","'actual_doc_ids':sorted({b['doc_id'] for b in actual_input_blocks}),'actual_snapshots':sorted({b['snapshot'] for b in actual_input_blocks})")
src=src.replace("locator.locate({'doc_id':r['doc_id'],'text':r['text']},e['quote']) if locator else", "locator.locate(by_block[r['block_id']],e['quote']) if locator else")
src=src.replace("response['actual_doc_ids']=sorted({r['doc_id'] for r in expansion['selected_sources']})","response['evidence_doc_ids']=sorted({r['doc_id'] for r in expansion['selected_sources']})")
src=src.replace("response['actual_snapshots']=sorted({r['snapshot'] for r in expansion['selected_sources']})","response['evidence_snapshots']=sorted({r['snapshot'] for r in expansion['selected_sources']})")
src=src.replace("'synthetic-run',x,1.25)","'synthetic-run',x,1.25,actual_input_blocks=[b])").replace("'run',empty,1)","'run',empty,1,actual_input_blocks=[b])").replace("'run',bad,1)","'run',bad,1,actual_input_blocks=[b])")
src=src.replace("assert er['answer']=='supported' and er['evidence']==[] and er['support_status']=='not_checked'","assert er['answer']=='supported' and er['evidence']==[] and er['support_status']=='not_checked' and er['actual_doc_ids']==['made-up']")
p.write_text(src,encoding='utf-8');ast.parse(src)
from sentence_selection import CANDIDATE_PROMPT,offline_checks
from sentence_interface import offline_checks as interface_checks
assert offline_checks()['passed'] and interface_checks()['passed']
items=load(out/'diagnostic-inputs.json')
diffs=load(out/'planned-request-differences.json')
for d,item in zip(diffs,items):
    d['new_system']=item['messages']['revised'][0]['content'];d['new_user']=item['messages']['revised'][1]['content'];assert d['new_system']==CANDIDATE_PROMPT
write(out/'planned-request-differences.json',diffs)
parts=[]
for item in items:
    for variant in ['original','revised']:
        ms=item['messages'][variant];parts.append('<|im_start|>system\n'+ms[0]['content']+'<|im_end|>\n<|im_start|>user\n'+ms[1]['content']+'<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n')
plan=load(out/'intervention-plan.json');launch=plan['service_arguments'];marker='<|endoftext|>';base=Path.home()/'AppData/Local/ANTLabLocalModel'
ids,cmd=native_tokenizer(base/'llama-b11429/llama-tokenize.exe',Path(launch[launch.index('-m')+1]),marker+marker.join(parts)+marker,out,'native-sentence-capacity-final');sep=ids[0];counts=[];n=0
for x in ids[1:]:
    if x==sep:counts.append(n);n=0
    else:n+=1
assert len(counts)==6 and all(n+256+64<=4096 for n in counts)
supp=load(out/'interface-adapter-check.json');supp.update(final_checked_at=now(),passed=True,source_hash=sha(p),native_token_counts_current=counts,native_command_current=cmd,scope_mapping_checked='实际输入范围与选中证据范围分开；空选择仍报告实际模型输入范围。PDF定位使用完整输入块及snapshot。')
write(out/'interface-adapter-check.json',supp)
plan.update(preparation_finalized_at=now(),candidate_prompt=CANDIDATE_PROMPT,code_hashes={p.relative_to(ROOT).as_posix():sha(p) for p in HERE.glob('*.py')},current_capacity_evidence='interface-adapter-check.json',preparation_metadata='preparation-finalization.json')
write(out/'intervention-plan.json',plan)
write(out/'preparation-finalization.json',{'at':now(),'generation_calls_before':0,'ordinary_engineering_fixes':['区分实际输入范围与选句范围','PDF定位传完整块与snapshot','完整提示/请求差异与实际代码同步','六组当前原生分词容量重新通过'],'history':'preparation-history/','hypotheses_selection_sampling_budget_unchanged':True})
snap=out/'code-snapshot-execution-final';snap.mkdir()
for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'));shutil.copy2(p,snap/p.name)
print(json.dumps({'passed':True,'current_capacity':counts,'max_total_with_budget':max(counts)+256,'generations':0,'plan_current':True},ensure_ascii=False))
