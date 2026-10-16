from pathlib import Path
import sys,json,copy,shutil,subprocess,ast
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now,config
out=Path(Path('a-round-out.txt').read_text().strip())
for src,dest in [('a_short_enum_candidate.py','short_enum_candidate.py'),('a_launch_short_enum.py','launch_short_enum.py')]:
    p=HERE/dest;assert not p.exists();ast.parse(Path(src).read_text(encoding='utf-8'));shutil.copy2(src,p)
from short_enum_candidate import offline_checks,answer_schema,QUERY_PROMPT,ANSWER_PROMPT
from common_judgment_candidate import offline_checks as common_checks
checks=offline_checks();common=common_checks();assert checks['passed'] and common['passed']
write(out/'candidate-offline-checks.json',{'at':now(),'passed':True,'candidate_checks':checks,'prior_source_validation_checks':common,'generation_calls':0})
# 复用已经验证的同包C++转换器与原生grammar sampler，无context或decode。
native_source=(ROOT/'基础/tests/check_numeric_index_schema_native.py').read_text(encoding='utf-8')
start=native_source.index("schema=json.loads((folder/'schema.plan.json')")
end=native_source.index('class ModelParams',start)
native_source=native_source[:start]+"cases=json.loads((folder/'schema-cases.json').read_text(encoding='utf-8'))\ngrammars={item['name']:native_convert(item['schema']) for item in cases}\nfor name,grammar in grammars.items():(folder/('native-'+name+'.gbnf')).write_text(grammar,encoding='utf-8')\n"+native_source[end:]
start=native_source.index("    fixtures=json.loads((folder/'offline-check.json')")
end=native_source.index('\nfinally:\n    free_model',start)
native_source=native_source[:start]+"    for case in cases:\n        for fixture in case['fixtures']:\n            actual,failed=native_accepts(case['name'],fixture['response'])\n            rows.append({'case':case['name'],'name':fixture['name'],'expected':fixture['accept'],'actual':actual,'rejected_token':failed,'response':fixture['response']})\n            save('native-progress-'+str(len(rows))+'.json',{'tests':rows.copy(),'generation_calls':0})\n            assert actual==fixture['accept'],'原生enum正反例不符'\n"+native_source[end:]
native_source=native_source.replace("save('native-plan-validation.json'","save('native-id-enum-validation.json'").replace('native plan-schema cases','native ID-enum cases')
native_source=native_source.replace('位置/引用/除零语义由独立程序检查','动态ID enum正反例，未知ID由原生grammar拒绝；摘录真实性和语义不由Schema保证')
p=HERE/'check_id_enum_native.py';assert not p.exists();ast.parse(native_source);p.write_text(native_source,encoding='utf-8')
cases=[]
for n in [0,1,2,3]:
    blocks=[{'block_id':'synthetic-'+str(i)} for i in range(n)];schema=answer_schema(blocks)
    def response(ids):return {'label':'insufficient','reason':'made up','evidence':[{'block_id':x,'quote':'original phrase'} for x in ids]}
    fixtures=[{'name':'empty_array','response':response([]),'accept':True},{'name':'foreign_id','response':response(['not-in-current-input']),'accept':False}]
    if n:fixtures.extend([{'name':'actual_id','response':response([blocks[-1]['block_id']]),'accept':True},{'name':'actual_all_ids','response':response([b['block_id'] for b in blocks]),'accept':True}])
    cases.append({'name':'ids-'+str(n),'schema':schema,'fixtures':fixtures})
write(out/'schema-cases.json',cases)
command=[sys.executable,'-X','utf8','-B',str(p),str(out)];r=subprocess.run(command,capture_output=True)
(out/'native-validation.stdout.txt').write_bytes(r.stdout);(out/'native-validation.stderr.txt').write_bytes(r.stderr)
write(out/'native-validation-command.json',{'at':now(),'command':command,'exit_code':r.returncode,'source_reused':'基础/tests/check_numeric_index_schema_native.py','source_hash':sha(ROOT/'基础/tests/check_numeric_index_schema_native.py'),'generation_calls':0})
assert r.returncode==0,'原生验证失败，不启动模型'
assert load(out/'native-id-enum-validation.json')['passed']
# 标准离线门禁复用，仅让容量计算采用本轮短提示；不修改原模块文件。
import preflight
original_answer=preflight.answer_messages;original_query=preflight.query_messages
def answer(claim,blocks):
    m=original_answer(claim,blocks);m[0]['content']=ANSWER_PROMPT;return m
def query(claim):
    m=original_query(claim);m[0]['content']=QUERY_PROMPT;return m
preflight.answer_messages=answer;preflight.query_messages=query
saved_argv=sys.argv;sys.argv=['preflight','--out',str(out)]
try:preflight.main()
finally:sys.argv=saved_argv
from engineering_check import main as engineering_main
sys.argv=['engineering','--out',str(out)]
try:engineering_main()
finally:sys.argv=saved_argv
# 独立启动器失败门禁；错误应发生在任何服务启动前。
fixture=out/'candidate-blocked-fixture';fixture.mkdir()
negcmd=[sys.executable,'-X','utf8','-B',str(HERE/'launch_short_enum.py'),'--out',str(fixture)]
negative=subprocess.run(negcmd,capture_output=True);(fixture/'stderr.txt').write_bytes(negative.stderr)
assert negative.returncode!=0 and not (fixture/'owned-service.json').exists()
tasks=load(out/'development-inputs.json');pre=load(out/'offline-preflight.json')
plan={'saved_at':now(),'status':'development_only_not_formal_freeze','prior_exposure':'看过三道开发题和其错误；未读七道AT评测题','cancelled':'尚未执行的3B对照和七题评测取消；只使用已校验0.6B，不下载或加载其他模型。','changes':['共同查询转换提示保留具体对象/操作/条件；TF-IDF分词/评分/范围/邻段不变，无实现bug修复宣称','共同短判断提示，reason一句、必要短连续原句，不裁剪输入或输出','两方案按各自实际输入ID动态派生同一Schema规则；引用存在/连续原文统一核验，不修复输出'],'query_prompt':QUERY_PROMPT,'answer_prompt':ANSWER_PROMPT,'query_config':config('query'),'answer_base_config':config('answer'),'dynamic_schema':'原answer结构不变，仅block_id enum随实际输入变化；空输入强制evidence为空，原生正反例均通过。不是以两方案ID并集放宽引用范围。','generation_limit':9,'cumulative_baseline':561,'A_used_before':27,'A_budget_total':54,'order':[{'id':t['id'],'order':['baseline','improved'] if i%2==0 else ['improved','baseline']} for i,t in enumerate(tasks)],'counting':'每题1次共享转换+两方案各1次回答；查询计一次，分摊50%查询成本，另报整对端到端耗时；页面不额外重复生成。','prediction':'保留具体对象的检索词可能改善词面命中；短摘录要求可能减少预算耗尽；enum可约束ID但不能约束quote或语义。整体修改不能独立归因，可能仍误判/漏引。','selection':'分别报告三题baseline/improved和旧结果；严格成功优先、其次公开参考标签正确，既有成功项不得退步；无改善保留旧结果不追加同类搜索。不是正式冻结或独立泛化评测。','evaluation':'完整JSON、标签、必要输入覆盖、引用来源/连续性、必要引用覆盖、引用支持、无关引用、严格成功与客户端耗时分开。失败/not_checked保留分母；公开参考与按实际可见证据合理性分列，不借漏检原文补模型证据。','stopping':'沿用加载前2GiB；运行连续3个2秒样本低于1GiB停止自有PID；技术失败停止不重发，质量错误保存不重试。','native_proof':'native-id-enum-validation.json；原生C++ Schema转换和grammar sampler，仅词表，无模型张量/context/decode。','negative_launcher_gate':{'command':negcmd,'exit':negative.returncode,'owned_pid_created':False},'model_hash':pre['model_hash'],'executable_hash':pre['executable_hash'],'preflight_hash':sha(out/'offline-preflight.json'),'no_reference_answers_in_runtime':True}
write(out/'candidate-plan.json',plan)
snapshot=out/'code-snapshot';snapshot.mkdir()
for p in HERE.glob('*.py'):shutil.copy2(p,snapshot/p.name)
print(json.dumps({'out':str(out),'native_cases':len(load(out/'native-id-enum-validation.json')['tests']),'offline_checks':35+checks['count']+common['count'],'candidate_gate':negative.returncode,'plan_saved':True,'generation_calls':0},ensure_ascii=False))
