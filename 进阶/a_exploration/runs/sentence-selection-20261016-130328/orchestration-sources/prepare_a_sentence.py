from pathlib import Path
import sys,json,copy,shutil,subprocess,ast,difflib
from datetime import datetime
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now,config
from engine import ANSWER_PROMPT
from preflight import native_tokenizer
from checks_extended import run as prior_checks
out=HERE/'runs'/('sentence-selection-'+datetime.now().strftime('%Y%m%d-%H%M%S'));out.mkdir();Path('a-sentence-out.txt').write_text(str(out),encoding='utf-8')
protected={p.relative_to(ROOT).as_posix():sha(p) for p in HERE.rglob('*') if p.is_file() and out not in p.parents and not {'__pycache__','slot-cache'}&set(p.parts)}
for n in ['README.md','report.md','decisions.md','declaration.md','基础/开发记录.md','基础/starter/student.py','进阶/challenge_b/challenge.py','进阶/challenge_b/no_cache_engine.py']:protected[n]=sha(ROOT/n)
write(out/'protected-before.json',protected)
target=HERE/'sentence_selection.py';assert not target.exists();ast.parse(Path('a_sentence_selection.py').read_text(encoding='utf-8'));shutil.copy2('a_sentence_selection.py',target)
from sentence_selection import build_index,schema,adapt_messages,CANDIDATE_PROMPT,offline_checks,expand
checks=offline_checks();assert checks['passed'];prior=prior_checks(out);assert prior['passed']==35
write(out/'segmentation-checks.json',checks)
rules=[]
for filename,needles in [('进阶/00_共同规则与接口.md',['接口路径自由','每项证据','locator_status：','run_kind：']),('进阶/01_A_研究机制迁移.md',['主要改进作用于','真实生成必须保留实际messages'])]:
    p=ROOT/filename;lines=p.read_text(encoding='utf-8').splitlines()
    for needle in needles:
        matched=[{'line':i+1,'text':line} for i,line in enumerate(lines) if needle in line];assert matched;rules.append({'path':filename,'sha256':sha(p),'matches':matched})
write(out/'interface-evidence.json',{'at':now(),'sources':rules,'conclusion':'共同接口规定对外结果字段、来源和原始请求记录，未发现禁止模型内部选句后适配证据的明确条款。外部展开仍须有原文/页码/范围/来源；当前只做独立输出诊断，不声称完成新的页面交付或取代生成前邻段主改进。','limitation':'接口层级解释非外部验收确认；程序展开要标local_rule，模型label来源=model，语义状态not_checked。','same_block_multiple_sentences':'原文未禁止同块多条片段。不同sentence_id可指向同一block_id；重复sentence_id拒绝。旧parse_answer对block_id去重规则不修改，也不用于把这种合法展开误判为重复模型选句。'})
old=HERE/'runs/development-20261016-115250';inputs=[];diffs=[]
for h in sorted([load(p) for p in old.glob('http-*.json')],key=lambda x:x['task_id']):
    pair=h['response'];arm=pair['arms']['improved'];blocks=arm['actual_input_passages'];m=arm['raw_record']['messages'];assert m[0]['content']==ANSWER_PROMPT
    index=build_index(blocks,pair['doc_ids'],pair['snapshot']);candidate=adapt_messages(m,index);oc=copy.deepcopy(arm['raw_record']['config']);nc=copy.deepcopy(oc);nc['parameters']['response_format']['json_schema']['schema']=schema(index)
    original_user=json.loads(m[1]['content']);candidate_user=json.loads(candidate[1]['content']);assert candidate_user=={**original_user,'sentence_index':index}
    inputs.append({'id':h['task_id'],'claim':pair['claim'],'doc_ids':pair['doc_ids'],'snapshot':pair['snapshot'],'blocks':blocks,'sentence_index':index,'messages':{'original':m,'revised':candidate},'configs':{'original':oc,'revised':nc},'origin':{'kind':'first_development_improved_automatic_evidence_replay','pair_file':('http-'+pair['request_id']+'.json'),'original_run_id':arm['raw_record']['run_id'],'no_new_query':True,'manual_evidence_replacement':False}})
    write(out/('sentence-index-'+h['task_id']+'.json'),{'at':now(),'index':index,'source_blocks':blocks,'coverage':'每块[0,len(text))连续覆盖，Unicode码点，含空白，不跨段合并'})
    diffs.append({'id':h['task_id'],'old_system':m[0]['content'],'new_system':candidate[0]['content'],'only_semantic_system_change':'无，原语义指令保留；只替换JSON格式声明并追加选句展开说明','old_user':m[1]['content'],'new_user':candidate[1]['content'],'full_original_passages_unchanged':True,'numeric_parameters_unchanged':{k:v for k,v in oc['parameters'].items() if k!='response_format'}=={k:v for k,v in nc['parameters'].items() if k!='response_format'},'changed_parts':['内部输出Schema','输出格式说明','附加完整句子索引']})
write(out/'diagnostic-inputs.json',inputs);write(out/'planned-request-differences.json',diffs)
cases=[]
for item in inputs:
    ids=[r['sentence_id'] for r in item['sentence_index']]
    def response(sids):return {'label':'insufficient','reason':'synthetic structure check','sentence_ids':sids}
    cases.append({'name':item['id'],'schema':schema(item['sentence_index']),'fixtures':[{'name':'empty','response':response([]),'accept':True},{'name':'first_last','response':response([ids[0],ids[-1]]),'accept':True},{'name':'unknown','response':response(['not-in-index']),'accept':False},{'name':'duplicate_schema_accepts_program_rejects','response':response([ids[0],ids[0]]),'accept':True},{'name':'old_shape_rejected','response':{'label':'insufficient','reason':'synthetic','evidence':[]},'accept':False}]})
cases.append({'name':'empty-input','schema':schema([]),'fixtures':[{'name':'empty','response':{'label':'insufficient','reason':'empty','sentence_ids':[]},'accept':True},{'name':'foreign','response':{'label':'insufficient','reason':'empty','sentence_ids':['not-here']},'accept':False}]})
write(out/'schema-cases.json',cases)
native_cmd=[sys.executable,'-X','utf8','-B',str(HERE/'check_id_enum_native.py'),str(out)];r=subprocess.run(native_cmd,capture_output=True);(out/'native-schema.stdout.txt').write_bytes(r.stdout);(out/'native-schema.stderr.txt').write_bytes(r.stderr)
write(out/'native-schema-command.json',{'at':now(),'command':native_cmd,'exit':r.returncode,'generation_calls':0});assert r.returncode==0 and load(out/'native-id-enum-validation.json')['passed']
# 仅复制既有生命周期；按本轮契约替换预检与选句展开回调。
runner=HERE/'diagnose_sentence_selection.py';assert not runner.exists();source=(HERE/'diagnose_development.py').read_text(encoding='utf-8')
before="        assert item['messages']['original'][1:]==item['messages']['revised'][1:]\n        assert item['messages']['revised'][0]['content']==item['messages']['original'][0]['content']+plan['prompt_appendix']"
after="        from sentence_selection import build_index,adapt_messages,schema\n        assert item['sentence_index']==build_index(item['blocks'],item['doc_ids'],item['snapshot'])\n        assert item['messages']['revised']==adapt_messages(item['messages']['original'],item['sentence_index'])\n        assert item['configs']['revised']['parameters']['response_format']['json_schema']['schema']==schema(item['sentence_index'])\n        assert {k:v for k,v in item['configs']['original']['parameters'].items() if k!='response_format'}=={k:v for k,v in item['configs']['revised']['parameters'].items() if k!='response_format'}"
assert source.count(before)==1;source=source.replace(before,after).replace("item['config']","item['configs'][variant]").replace("'generations_baseline':543","'generations_baseline':plan['cumulative_baseline']")
source=source.replace("'diagnostic_input_origin':'manual_development_evidence'","'diagnostic_input_origin':'automatic_improved_evidence_replay'").replace("'input_origin':'manual_verified_development_evidence'","'input_origin':'automatic_improved_evidence_replay'")
point="            write(out/f'item-{n+1:02}.json',";assert source.count(point)==1
adaptation="""            if variant=='revised':
                from sentence_selection import expand
                expansion=expand(raw['content'],item['blocks'],item['sentence_index'],item['doc_ids'],item['snapshot'])
                write(out/f'expansion-{n+1:02}.json',expansion)
            else:
                from common_judgment_candidate import validate_raw
                write(out/f'old-validation-{n+1:02}.json',validate_raw(raw['content'],item['blocks']))
"""
source=source.replace(point,adaptation+point).replace('开发期人工证据诊断；只复用A请求记录器，不执行检索或读取答案。','固定自动证据的原输出/句子选择对照；复用请求记录器，不重检索或读答案。')
ast.parse(source);runner.write_text(source,encoding='utf-8');(out/'runner.diff').write_text(''.join(difflib.unified_diff((HERE/'diagnose_development.py').read_text(encoding='utf-8').splitlines(keepends=True),source.splitlines(keepends=True),fromfile='existing-runner',tofile='diagnose_sentence_selection.py')),encoding='utf-8')
launch_plan=load(HERE/'runs/claim-language-20261016-123016/intervention-plan.json');launch=launch_plan['service_arguments'];base=Path.home()/'AppData/Local/ANTLabLocalModel'
parts=[]
for item in inputs:
    for variant in ['original','revised']:parts.append('<|im_start|>system\n'+item['messages'][variant][0]['content']+'<|im_end|>\n<|im_start|>user\n'+item['messages'][variant][1]['content']+'<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n')
marker='<|endoftext|>';ids,cmd=native_tokenizer(base/'llama-b11429/llama-tokenize.exe',Path(launch[launch.index('-m')+1]),marker+marker.join(parts)+marker,out,'native-sentence-capacity');sep=ids[0];counts=[];n=0
for x in ids[1:]:
    if x==sep:counts.append(n);n=0
    else:n+=1
assert len(counts)==6 and all(n+256+64<=4096 for n in counts),'容量不足，不截断资料，不启动'
write(out/'offline-checks.json',{'at':now(),'passed':True,'previous_35_checks':prior,'sentence_checks':checks,'native_schema_tests':len(load(out/'native-id-enum-validation.json')['tests']),'native_token_counts':counts,'output_budget':256,'extra_margin':64,'actual_template_recheck_required':True,'generation_calls':0})
for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
plan={'saved_at':now(),'status':'development_fixed_evidence_diagnostic_not_formal_freeze','hypothesis':'用短句子ID代替模型重抄长quote可能减少预算耗尽和原文归属错误。','competing_explanation':'判断极性、条件组合或证据遗漏仍可使模型选错句或判错；来源真实不保证支持。附加索引增加输入长度，效果不能只归因于解码字符串变短。','original_prompt':ANSWER_PROMPT,'candidate_prompt':CANDIDATE_PROMPT,'config_numeric':{k:v for k,v in config('answer')['parameters'].items() if k!='response_format'},'order':[{'id':x['id'],'variant':v} for i,x in enumerate(inputs) for v in (['original','revised'] if i%2==0 else ['revised','original'])],'generation_cap':6,'cumulative_baseline':570,'A_used_before':36,'A_remaining_before':18,'A_budget_total':54,'selection':'严格成功优先、其次公开参考标签正确；已有成功项不能退步；同分保留旧。仅结构改善不称整体质量提高，不自动接生产，不追加调用。','evaluation':'分别记录内部JSON、预算耗尽、有效标签、理由label一致、选择/展开来源、必要覆盖、引用支持、无关引用、严格成功和客户端耗时。非法/残缺/重复选择保留失败分母，展开失败不补选不修label。','evidence_origin':'最初自动开发improved完整证据历史重放，不重查询，不人工替换；不是端到端成绩。','AD03_scope':'自动证据未含绘图底层数据章节；不借不可见参考补证；公开参考标签与实际输入可判定性分开。','expansion_provenance':'模型选择、程序展开原文。raw内部响应与expanded/interface分开，派生操作run_kind=local_rule、judgment_source=rule；label来源model，support_status=not_checked。同块不同句可多条，重复sentence_id拒绝。','stop':'加载前2GiB；运行连续3个2秒样本低于1GiB停止自有PID；先过全部实际模板检查。技术错误停止不自动重发，质量失败继续不重试。','input_sha256':sha(out/'diagnostic-inputs.json'),'code_hashes':{p.relative_to(ROOT).as_posix():sha(p) for p in HERE.glob('*.py')},'data_hashes':launch_plan['data_hashes'],'model_hash':launch_plan['model_hash'],'executable_hash':launch_plan['executable_hash'],'service_arguments':launch,'no_AT_read':True,'no_reference_answers_in_runtime':True}
write(out/'intervention-plan.json',plan);snap=out/'code-snapshot';snap.mkdir()
for p in HERE.glob('*.py'):shutil.copy2(p,snap/p.name)
print(json.dumps({'out':str(out),'previous_checks':35,'new_checks':checks['count'],'native_tests':len(load(out/'native-id-enum-validation.json')['tests']),'sentence_counts':[(x['id'],len(x['sentence_index'])) for x in inputs],'token_counts':counts,'plan_saved':True,'generations':0},ensure_ascii=False))
