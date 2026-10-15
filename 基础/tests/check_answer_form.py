"""自造问题及字符串检查；不生成、不读开发答案。"""
from pathlib import Path
from datetime import datetime
import copy,json,re,sys,hashlib
import answer_form_candidate as candidate

folder=Path(sys.argv[1]);repo=Path(__file__).resolve().parents[2]
conf=json.loads((repo/'基础/runs/two_step/dev_r0/config.answer.json').read_text(encoding='utf-8'))
base=conf['parameters']['response_format']['json_schema']['schema']
tests=[]
for question,kind,accept,reject in [
 ('差值是什么？只输出数值。','数值',['0','-7','2.75','+.5','-1e-3','证据不足'],['1.8秒','结果为2','',' 2','2\n','2/3','证据不足。']),
 ('比例是什么？只输出百分数。','百分数',['0%','-0.5%','23.75%','2e1%','证据不足'],['12','12％','比例12%','','证据不足。']),
 ('请说明差值。',None,['有说明的答案','证据不足'],[]),
 ('请选择名称。只输出配置名称。',None,['配置名称'],[]),
 ('只输出数值。又要求只输出百分数。',None,['未施加冲突约束'],[]),
 ('解释“只输出数值”的含义。',None,['这是说明'],[]),
]:
 before=copy.deepcopy(base);schema,rule=candidate.constrain_schema(question,base)
 assert base==before and rule['kind']==kind
 assert schema['properties']['citations']==base['properties']['citations'] and schema['required']==base['required']
 for text in accept+reject:
  valid=bool(re.fullmatch(rule['pattern'],text)) if kind else True
  assert valid==(text in accept)
  tests.append({'question':question,'rule':rule,'answer':text,'expected_accept':text in accept,'actual_accept':valid})
 if kind:
  (folder/('schema-self-'+('number' if kind=='数值' else 'percent')+'.json')).write_text(json.dumps(schema,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
record={'checked_at':datetime.now().astimezone().isoformat(),'status':'local_regex_checks_passed_native_support_pending','counts_as_generation':False,'tests':tests,'module_sha256':hashlib.sha256(Path(candidate.__file__).read_bytes()).hexdigest(),'boundary':'仅识别末尾明确短语；冲突、不明确和名称要求沿用原Schema；不判断数值正确性。'}
p=folder/'offline-regex-check.json';assert not p.exists();p.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PASS',len(tests),'self-built rule/string cases; native support not yet asserted')
