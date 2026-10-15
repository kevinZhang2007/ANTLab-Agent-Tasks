from pathlib import Path
from datetime import datetime
import copy,json,hashlib,socket,subprocess,re,shutil
work=Path(__file__).parent;folder=Path((work/'two_step_linked_folder.txt').read_text(encoding='utf-8'));repo=folder.parents[3]
read=lambda name:json.loads((folder/name).read_text(encoding='utf-8'))
def save(name,value):
 p=folder/name
 if p.exists():
  old=json.loads(p.read_text(encoding='utf-8'))
  without_time=lambda v:{k:x for k,x in v.items() if k not in ['recorded_at','checked_at','reviewed_at']} if isinstance(v,dict) else v
  assert without_time(old)==without_time(value),'恢复时已保存内容不一致：'+name
  return
 p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
rows=read('semantic-review.json');tasks=read('task-results.json');summary=read('summary.json')
effective=copy.deepcopy(rows)
target=next(r for r in effective if r['case_id']=='D03' and r['variant']=='linked_answer')
assert target['answer']=='1.8秒' and target['necessary_evidence_covered'] and target['citation_ids_exist']
target.update(semantic_consistent=True,evidence_supports_actual_answer=True)
target['failure_reasons']=['输入必要依据齐全，数值及引用集合支持成立，但问题要求只输出数值；answer附带单位，指定答法不合格。']
target['clarification']='只澄清语义与指定答法的区别；保留原响应、原自动评价、严格完整成功=false。'
clarification={'recorded_at':datetime.now().astimezone().isoformat(),'source':'Codex依据本轮开发原文复核，尚未经本人逐项确认','kind':'post_generation_evaluation_clarification','affected_record':target['answer_record_path'],
 'automatic_review_limit':'预先保存的自动评价仅对D02区分语义一致与指定答法，D03带单位的正确数值被一并判成语义和支持失败。这是评价检查的不足，不是模型响应修复。',
 'question':next(t['question'] for t in tasks if t['case_id']=='D03'),'original_quotes':[{'id':p['id'],'quote':p['quote'].split('。')[0]+'。'} for p in target['source_basis']],
 'calculation':'7.6-5.8=1.8秒','changes':{'semantic_consistent':{'before':False,'after':True},'evidence_supports_actual_answer':{'before':False,'after':True}},
 'unchanged':{'specified_answer_correct':False,'strict_complete_success':False,'necessary_coverage':True,'irrelevant_citations':[]},
 'selection_rule_unchanged':True,'adoption_unchanged':'old_answer','original_review_preserved':'semantic-review.json'}
save('evaluation-clarification.json',clarification);save('effective-semantic-review.json',effective)
updated=copy.deepcopy(summary);updated['effective_review']='effective-semantic-review.json';updated['clarification']='evaluation-clarification.json'
updated['semantic_and_support_counts']=[{'variant':v,'semantic_consistent':sum(r['semantic_consistent'] for r in effective if r['variant']==v),'necessary_citation_coverage':sum(r['necessary_evidence_covered'] for r in effective if r['variant']==v),'citations_support_answer':sum(r['evidence_supports_actual_answer'] for r in effective if r['variant']==v),'irrelevant_citation_cases':sum(bool(r['irrelevant_citations']) for r in effective if r['variant']==v),'input_necessary_coverage':sum(r['input_necessary_evidence_coverage'] for r in effective if r['variant']==v)} for v in ['old_answer','linked_answer']]
save('effective-summary.json',updated)
records=[json.loads(p.read_text(encoding='utf-8')) for p in sorted(folder.glob('run-*.json'))]
runtime=read('runtime.json');assert runtime['server_stopped'] and len(records)==12
with socket.socket() as s:s.settimeout(1);stopped=s.connect_ex(('127.0.0.1',8080))!=0
assert stopped
protected=read('protected-hashes.json');changed=[p for p,h in protected.items() if hashlib.sha256((repo/p).read_bytes()).hexdigest()!=h];assert not changed
assert read('precall-plan.json')['recorded_at']<min(r['recorded_at'] for r in records)
assert all(r['status']=='ok' and r['total_capacity']<4096 for r in records)
assert all(json.loads(r['messages'][1]['content'])=={'question':next(t['question'] for t in tasks if t['case_id']==r['case_id']),'passages':r['used_passages']} for r in records)
assert all(r['used_passages']==[p for p in next(t['ordered_passages'] for t in tasks if t['case_id']==r['case_id']) if p['id'] in {q['id'] for q in r['used_passages']}] for r in records)
log=(folder/'server-log.txt').read_text(encoding='utf-8')+(folder/'server-stdout.txt').read_text(encoding='utf-8')
version_lines=[line for line in log.splitlines() if 'build:' in line or '11429' in line][:10]
index=[]
for t in tasks:
 item={'case_id':t['case_id'],'shared_selection_run_id':t['selection_run_id'],'shared_record':'run-'+t['selection_run_id']+'.json','task_record':'task-'+t['case_id']+'.json','selected_ids':t['selection_validation']['selected_ids'],'branches':{}}
 for v,b in t['branches'].items():item['branches'][v]={'run_id':b['run_id'],'record_path':'run-'+b['run_id']+'.json','used_ids':[p['id'] for p in b['used_passages']],'added_ids':[p['id'] for p in b['used_passages'] if p['id'] not in t['selection_validation']['selected_ids']],'end_to_end_seconds':b['end_to_end_shared_accounting_seconds'],'wall_clock_span_seconds':b['wall_clock_from_shared_start_seconds']}
 index.append(item)
save('result-index.json',index)
git=r'C:\Users\86186\AppData\Local\Programs\Git\cmd\git.exe'
def command(*args):
 p=subprocess.run([git,*args],cwd=repo,text=True,encoding='utf-8',capture_output=True);return {'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
audit={'checked_at':datetime.now().astimezone().isoformat(),'new_generations':12,'shared_selection':4,'answer_generations':8,'cumulative_generations':136,
 'unique_new_run_ids':len({r['run_id'] for r in records}),'technical_failures':0,'retries':0,'finish_reasons':[r['response']['choices'][0]['finish_reason'] for r in records],
 'truncation_flags':re.findall(r'truncated\s*=\s*(\d+)',log),'before_generation_capacity_max':max(r['input_tokens'] for r in read('preflight.json')['rows']),'precall_plan_precedes_generation':True,
 'model_build_log':version_lines,'old_protected_files':len(protected),'changed_old_files':changed,'three_documents_and_first_freeze_preserved':True,'server_stopped':stopped,
 'request_budget':'实际序列化正文均max_tokens=256；未以props默认值或finish_reason当预算回显。',
 'source_snapshot_raw_byte_matches':{n:(repo/'基础/tests'/n).read_bytes()==(folder/('snapshot-'+n)).read_bytes() for n in ['two_step_linked_candidate.py','check_two_step_linked.py','run_two_step_linked_pairs.py','review_two_step_linked.py']},
 'source_snapshot_matches':{n:(repo/'基础/tests'/n).read_bytes().replace(b'\r\n',b'\n')==(folder/('snapshot-'+n)).read_bytes().replace(b'\r\n',b'\n') for n in ['two_step_linked_candidate.py','check_two_step_linked.py','run_two_step_linked_pairs.py','review_two_step_linked.py']},
 'snapshot_comparison_note':'原始字节差异仅为CRLF/LF；原快照和执行代码均未修改，原始失败另存audit-error-crlf.json。执行代码哈希以生成前实际文件哈希为准。',
 'memory_before':runtime['before_load'],'memory_after_load':runtime['after_load'],'load_seconds':runtime['load_seconds'],
 'git_status':command('-c','core.quotepath=false','status','--short','--branch'),'staged_diff':command('diff','--cached','--stat'),'production_diff':command('diff','--','基础/starter/student.py','report.md','README.md','基础/开发记录.md')}
assert all(audit['source_snapshot_matches'].values()) and not audit['staged_diff']['stdout'] and not audit['production_diff']['stdout']
save('final-audit.json',audit)
shutil.copyfile(Path(__file__),folder/'finalize-review.py')
(folder/'all-code.diff').write_text((folder/'code-full.diff').read_text(encoding='utf-8')+(folder/'review-code.diff').read_text(encoding='utf-8'),encoding='utf-8')
tests=['基础/tests/two_step_linked_candidate.py','基础/tests/check_two_step_linked.py','基础/tests/run_two_step_linked_pairs.py','基础/tests/review_two_step_linked.py']
files=tests+[p.relative_to(repo).as_posix() for p in sorted(folder.rglob('*')) if p.is_file()]+[(folder/'new-files.json').relative_to(repo).as_posix()]
save('new-files.json',{'count':len(files),'all_new':True,'files':files})
out=work.parent/'outputs/two-step-linked';out.mkdir(parents=True,exist_ok=True)
for n in ['all-code.diff','effective-summary.json','effective-semantic-review.json','evaluation-clarification.json','result-index.json','final-audit.json','new-files.json']:(out/n).write_bytes((folder/n).read_bytes())
print(json.dumps({'files':len(files),'adoption':updated['selected'],'counts':updated['semantic_and_support_counts'],'audit':audit,'pairs':index},ensure_ascii=False,indent=2))
