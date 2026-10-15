from pathlib import Path
import json, hashlib, uuid, datetime, argparse, copy, random
import student
from provider import call_model

BASE=Path(__file__).resolve().parents[1]
def digest(raw): return hashlib.sha256(raw).hexdigest()
def cases(): return json.loads((BASE/'data/cases.json').read_text(encoding='utf-8'))
def get_case(cid):
    return next((c for c in cases() if c['id']==cid),None)
def load_config(path):
    conf=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    allowed={'provider','endpoint','model','parameters','timeout_seconds'}
    if set(conf)-allowed: raise ValueError('配置包含未声明字段；不得加入密钥')
    if not all(isinstance(conf.get(k),str) and conf[k] for k in ('provider','endpoint','model')):
        raise ValueError('provider/endpoint/model必须填写')
    return conf
def prepare(cid, condition, variant):
    c=get_case(cid)
    if c is None: raise ValueError('未知case_id')
    if condition not in c['conditions']: raise ValueError('未知condition')
    if variant not in ('baseline','improved'): raise ValueError('未知variant')
    by_id={p['id']:p for p in c['passages']}
    original=[copy.deepcopy(by_id[i]) for i in c['conditions'][condition]]
    selected=copy.deepcopy(original)
    if variant=='improved':
        selected=student.improve(c['question'],selected)
        if not isinstance(selected,list) or any(not isinstance(p,dict) or p.get('id') not in by_id or p != by_id[p['id']] for p in selected):
            raise ValueError('默认接口要求改进仅重排/选择原始段落；扩展格式须自己实现并披露')
        if len({p['id'] for p in selected})!=len(selected): raise ValueError('重复证据块')
    msgs=student.prepare_messages(c['question'],copy.deepcopy(selected))
    if not isinstance(msgs,list) or not msgs or any(not isinstance(m,dict) or set(m)!={'role','content'} or m['role'] not in ('system','user','assistant') or not isinstance(m['content'],str) for m in msgs):
        raise ValueError('messages格式不合法')
    return c,original,selected,msgs
def execute(cid,condition,variant,config,*,mock=False,dry=False,outdir=None):
    c,original,selected,msgs=prepare(cid,condition,variant)
    record={'schema_version':1,'run_id':str(uuid.uuid4()),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'case_id':cid,'split':c['split'],'condition':condition,'variant':variant,
            'mode':'dry' if dry else ('mock' if mock else ('local' if config.get('provider')=='llama.cpp' else 'paid')),
            'run_kind':'dry_run' if dry else ('mock' if mock else 'live_api'),
            'config':copy.deepcopy(config), 'data_sha256':digest((BASE/'data/cases.json').read_bytes()), 'dataset_version':json.loads((BASE/'data/manifest.json').read_text(encoding='utf-8'))['version'],
            'student_sha256':digest((BASE/'starter/student.py').read_bytes()),
            'provider_sha256':digest((BASE/'starter/provider.py').read_bytes()),
            'original_passage_ids':[p['id'] for p in original],
            'selected_passage_ids':[p['id'] for p in selected], 'messages':msgs,
            'input_characters':sum(len(m['content']) for m in msgs)}
    record.update({'status':'dry_run','response':None,'usage':None,'elapsed_seconds':None} if dry else call_model(msgs,config,mock))
    folder=Path(outdir) if outdir else BASE/'runs';folder.mkdir(parents=True,exist_ok=True)
    # UUID filename preserves all attempts; never silently overwrite retry results.
    (folder/(record['run_id']+'.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    return record
def main():
    p=argparse.ArgumentParser(description='默认只预览；本机调用用--local，付费调用用--paid')
    p.add_argument('--config',default=str(BASE/'config.example.json'))
    p.add_argument('--split',choices=['dev','evaluation'],default='dev')
    p.add_argument('--case');p.add_argument('--condition',choices=['E','R0','R1','R2','K','all'],default='R0')
    p.add_argument('--variant',choices=['baseline','improved'],default='baseline')
    mode=p.add_mutually_exclusive_group();mode.add_argument('--local',action='store_true');mode.add_argument('--paid',action='store_true');mode.add_argument('--mock',action='store_true');mode.add_argument('--dry-run',action='store_true')
    p.add_argument('--limit',type=int,default=1);p.add_argument('--order-seed',type=int,default=20261006)
    args=p.parse_args()
    if args.limit<1 or args.limit>100: p.error('limit须在1～100之间')
    jobs=[(c['id'],cond) for c in cases() if (c['id']==args.case if args.case else c['split']==args.split)
          for cond in (['R0','R1','R2','K'] if args.condition=='all' else [args.condition]) if cond in c['conditions']]
    if not jobs: p.error('没有匹配任务')
    random.Random(args.order_seed).shuffle(jobs)
    conf=load_config(args.config)
    if args.local and conf['provider']!='llama.cpp': p.error('--local要求provider为llama.cpp')
    if args.paid and conf['provider']=='llama.cpp': p.error('本机调用请用--local，不用--paid')
    for cid,cond in jobs[:args.limit]:
        r=execute(cid,cond,args.variant,conf,mock=args.mock,dry=not(args.paid or args.mock or args.local))
        print(r['run_id'],cid,cond,r['status'])
if __name__=='__main__':main()
