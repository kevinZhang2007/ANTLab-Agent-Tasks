from pathlib import Path
import sys,json,copy,itertools,shutil
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
from engine import Corpus,neighbors
from current_candidate import build_answer,query_config
from preflight import native_tokenizer
out=Path(Path('a-current-e2e-out.txt').read_text(encoding='utf-8').strip());selection=load(out/'configuration.json');selected=HERE/'runs/adopt-reason-citations-20261016-182422';tasks=load(out/'development-inputs.json');corpus=Corpus(load(ROOT/'进阶/materials/sections.json'));checks=load(out/'offline-checks.json')['checks']
shutil.copy2('prepare_a_current_e2e.py',out/'preparation-attempt1.py')
write(out/'preparation-stop.json',{'at':now(),'stage':'offline_conservative_capacity','exception':'AssertionError: conservative AD02 upper bound 4393 > 4096','actual_model_generation_calls':0,'model_started':False,'diagnosis':'两种子邻域相加重复计数，且逐段96及wrapper700余量可能过大；不能由保守上界认定真实超限。','repair':'按所有可能种子组合及实际去重邻域构造完整输入，以原生分词器逐一核对；不改方法、原文或预算。','old_bound_file_preserved':'offline-capacity.json'})
parts=[];meta=[];seen=set();candidates={}
for t in tasks:
    blocks=corpus.scope(t['doc_ids'],t['snapshot'])
    combos=[()]+[(b,) for b in blocks]+list(itertools.combinations(blocks,2))
    for seeds in combos:
        for mode in ['baseline','improved']:
            used=sorted(seeds,key=lambda b:b['_order']) if mode=='baseline' else neighbors(seeds,blocks)[0];key=(t['id'],tuple(b['block_id'] for b in used))
            if key in seen:continue
            seen.add(key);messages,conf,index,ch=build_answer(t['claim'],used,t['doc_ids'],t['snapshot'],selection['request_common']);prompt='<|im_start|>system\n'+messages[0]['content']+'<|im_end|>\n<|im_start|>user\n'+messages[1]['content']+'<|im_end|>\n<|im_start|>assistant\n'
            parts.append(prompt);meta.append({'task_id':t['id'],'mode_of_first_occurrence':mode,'block_ids':key[1]});candidates[key]=used
base=Path.home()/'AppData/Local/ANTLabLocalModel';marker='<|endoftext|>';tokens,cmd=native_tokenizer(base/'llama-b11429/llama-tokenize.exe',base/'models/Qwen3-0.6B-Q8_0.gguf',marker+marker.join(parts)+marker,out,'native-exact-capacity');counts=[];n=0
for token in tokens[1:]:
    if token==tokens[0]:counts.append(n);n=0
    else:n+=1
assert len(counts)==len(parts) and n==0
rows=[{**m,'input_tokens':count,'output_budget':1024,'total':count+1024,'fits':count+1024<=4096} for m,count in zip(meta,counts)];bounds=[];worst={}
for t in tasks:
    r=max((r for r in rows if r['task_id']==t['id']),key=lambda r:r['input_tokens']);bounds.append(r);worst[t['id']]=candidates[(t['id'],tuple(r['block_ids']))]
write(out/'offline-capacity-exact.json',{'at':now(),'passed':all(r['fits'] for r in rows),'rows':rows,'max_by_task':bounds,'unique_complete_inputs':len(rows),'all_seed_counts':'0,1,2；同文档章节邻段，集合去重','native_command':cmd,'manual_render_matches_historical_on_template':True,'actual_http_template_required_before_generation':True,'generation_calls':0});assert all(r['fits'] for r in rows),bounds
write(out/'worst-inputs.json',worst)
engine_file=HERE/'current_candidate.py';pagefile=HERE/'current_page.html';handler=HERE/'current_server.py';launchfile=HERE/'launch_current.py'
# 继续原准备脚本的登记部分，不重写已生成代码、不修改旧失败记录。
source=Path('prepare_a_current_e2e.py').read_text(encoding='utf-8');tail=source[source.index("for p in HERE.glob('*.py'):ast.parse"):];import ast,difflib
exec(compile(tail,'prepare_a_current_e2e.py:registration','exec'))
write(out/'capacity-fix-verification.json',{'at':now(),'passed':True,'exact_rows':len(rows),'max_total':max(r['total'] for r in rows),'old_conservative_failure_preserved':True,'no_input_change':True,'no_budget_change':True,'model_started':False,'generation_calls':0})
shutil.copy2(__file__,out/Path(__file__).name)
