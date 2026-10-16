"""离线门禁；原生tokenizer只分词，不生成。"""
from pathlib import Path
import argparse,copy,json,subprocess,sys,itertools
from engine import HERE,ROOT,Corpus,public,answer_messages,query_messages,neighbors
from locator import Locator
from development import load_development
from checks_extended import run as offline_checks
from runtime import write,load,sha,now,config,memory

def native_tokenizer(exe,model,text,folder,label):
    command=[str(exe),'-m',str(model),'--stdin','--ids','--no-bos','--offline']
    result=subprocess.run(command,input=text.encode('utf-8'),capture_output=True)
    (folder/(label+'.stdout.txt')).write_bytes(result.stdout);(folder/(label+'.stderr.txt')).write_bytes(result.stderr)
    if result.returncode:raise RuntimeError('原生分词失败 '+str(result.returncode))
    parsed=json.loads(result.stdout.decode('utf-8').strip())
    if not isinstance(parsed,list) or any(not isinstance(x,int) for x in parsed):raise ValueError('原生分词格式不合法')
    return parsed,command

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();folder=args.out.resolve()
    folder.mkdir(parents=True,exist_ok=True)
    if (folder/'offline-preflight.json').exists():raise ValueError('门禁结果已存在，不覆盖')
    checks=offline_checks(folder);write(folder/'synthetic-checks.json',checks)
    corpus=Corpus(load(ROOT/'进阶/materials/sections.json'));tasks=load_development(ROOT/'进阶/materials/a_tasks.json')
    write(folder/'development-inputs.json',tasks)
    frozen=load(ROOT/'基础/runs/final_five/20261015-210223/round5/freeze.json')
    base=Path.home()/'AppData/Local/ANTLabLocalModel';exe=base/'llama-b11429/llama-server.exe';model=base/'models/Qwen3-0.6B-Q8_0.gguf';tokenizer=exe.parent/'llama-tokenize.exe'
    assert sha(exe)==frozen['llama_cpp']['executable_sha256'] and sha(model)==frozen['model']['actual_sha256']
    for conf in [config('query'),config('answer')]:
        assert conf['provider']=='llama.cpp' and conf['endpoint']=='http://127.0.0.1:8080/v1/chat/completions'
        schema=conf['parameters']['response_format']['json_schema']['schema'];assert schema['type']=='object' and set(schema['required'])==set(schema['properties']) and not schema['additionalProperties']
    # 用结束特殊token分隔待测片段，一次读取词表得到各完整段落长度。
    marker='<|endoftext|>';parts=[json.dumps(public(b),ensure_ascii=False,indent=2) for b in corpus.blocks]
    parts += ['<|im_start|>system\n'+answer_messages(t['claim'],[])[0]['content']+'<|im_end|>\n<|im_start|>user\n'+answer_messages(t['claim'],[])[1]['content']+'<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n' for t in tasks]
    ids,command=native_tokenizer(tokenizer,model,marker+marker.join(parts)+marker,folder,'native-capacity')
    marker_id=ids[0];chunks=[];current=[]
    for token in ids[1:]:
        if token==marker_id:chunks.append(current);current=[]
        else:current.append(token)
    assert len(chunks)==len(parts) and not current
    sizes={b['block_id']:len(chunk)+64 for b,chunk in zip(corpus.blocks,chunks)}
    wrapper=max(len(x) for x in chunks[len(corpus.blocks):])+128
    bounds=[]
    for task in tasks:
        allowed=corpus.scope(task['doc_ids'],task['snapshot']);neighborhoods=[]
        for block in allowed:
            expanded,_=neighbors([block],allowed);neighborhoods.append(sum(sizes[b['block_id']] for b in expanded))
        demand=sum(sorted(neighborhoods,reverse=True)[:2])+wrapper+256
        bounds.append({'task_id':task['id'],'scope':task['doc_ids'],'conservative_input_and_budget_upper_bound':demand,'context':4096,'fits':demand<=4096,'basis':'两个种子各自邻域的分词长度上界相加；允许重叠重复计数，逐块另加64和包装128余量。实际模板还须在服务就绪后及每次请求前复核。'})
    write(folder/'offline-capacity.json',{'native_command':command,'generation_calls':0,'bounds':bounds,'block_token_bounds':sizes,'wrapper_bound':wrapper})
    assert all(x['fits'] for x in bounds),'容量门禁不通过，不启动模型'
    # 原文锚点只用于定位组件抽查，不进入推理选择或模型提示。
    locator=Locator(load(ROOT/'进阶/materials/page_words.json'));anchors=[]
    for doc,heading_prefix,sentence in [('P1','Rule 2:','Whenever possible, rely on the execution of programs instead of manual procedures to modify data.'),('P2','Rule 9:','If you have followed the previous rules, your notebooks should capture your entire process and be easy to read.')]:
        b=next(b for b in corpus.blocks if b['doc_id']==doc and b['heading'].startswith(heading_prefix) and sentence in b['text'])
        loc=locator.locate(b,sentence);anchors.append({'block':public(b),'quote':sentence,'location':loc,'human_visual_check':'pending','used_for_inference':False})
    write(folder/'locator-anchors.json',anchors)
    assert all(x['location']['locator_status']=='valid' for x in anchors),'原文定位离线抽查门禁失败'
    assert len({x['location']['regions'][0]['page'] for x in anchors})==2,'需两个不同页'
    for doc,count in [('P1',4),('P2',8)]:
        for p in range(1,count+1):assert (HERE/'assets'/f'{doc}-{p}.png').is_file()
    result={'checked_at':now(),'passed':True,'status':'offline_preflight_not_generation','synthetic_checks':checks['passed'],'development_tasks':3,'no_AT_body_read':True,'model_hash':sha(model),'executable_hash':sha(exe),'model_source':frozen['model'],'llama_cpp':frozen['llama_cpp'],'service_arguments':frozen['service_arguments'],'source_commit':'60617b5e2e6c082771b92b1f5dae5bd11efc4955','code_hashes':{p.relative_to(ROOT).as_posix():sha(p) for p in HERE.glob('*') if p.is_file() and p.suffix in ('.py','.json','.html')},'data_hashes':{str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in [ROOT/'进阶/materials/sections.json',ROOT/'进阶/materials/page_words.json',ROOT/'进阶/materials/sources.json',ROOT/'进阶/materials/papers/P1.pdf',ROOT/'进阶/materials/papers/P2.pdf']},'memory':memory(),'generation_limit':9,'A_total_limit':54,'baseline_generations':534,'frozen':False}
    write(folder/'offline-preflight.json',result);print(json.dumps({'passed':True,'out':str(folder),'checks':checks['passed'],'capacity':bounds},ensure_ascii=False))

if __name__=='__main__':main()
