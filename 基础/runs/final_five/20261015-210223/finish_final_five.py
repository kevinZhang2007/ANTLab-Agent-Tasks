from pathlib import Path
from datetime import datetime
import hashlib,json,shutil,sys
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'基础/starter/provider.py').is_file())
F=ROOT/'基础/runs/final_five/20261015-210223'
P=ROOT/'基础/runs/repeat_integrated/20261015-192436'
L=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
N=lambda:datetime.now().astimezone().isoformat()
def W(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as o:json.dump(v,o,ensure_ascii=False,indent=2)
def main():
    review=L(F/'round5/review-summary.json');summary=L(F/'round5/execution-summary.json')
    assert not summary['technical_stop'] and summary['service_stopped'] and summary['confirmed_generation_calls']==24
    rounds=[];local_ids=set();audit=[]
    for n in [1,2,3,5]:
        folder=F/f'round{n}';execution=L(folder/'execution-summary.json');freeze=L(folder/'freeze.json')
        assert execution['service_stopped'] and not execution['technical_stop']
        assert all(H(ROOT/p)==h for p,h in {**freeze['code_hashes'],**freeze['data_hashes']}.items())
        assert L(folder/'protected-file-audit.json')['all_unchanged']
        if n<4:rounds.append({'round':n,**L(folder/'selection.json'),'generation_calls':execution['confirmed_generation_calls']})
        else:rounds.append({'round':5,'frozen_policy':freeze['order'][0]['policy'],'generation_calls':24,'groups':review['groups']})
        plan=L(folder/'execution-plan.prepared.json')
        for job in plan['items']:
            task=L(folder/f"task-{job['sequence']:02d}.json")
            if n<4:
                original=L(ROOT/job['historical_task']);assert task['question']==original['question'] and task['used_passages']==original['used_passages']
                assert task['selection_is_fresh'] is False
            else:assert task['selection_is_fresh'] is True
            for record in task['stages']:
                if record.get('historical_generation_not_new'):continue
                assert record['started_at']>freeze['frozen_at'] and record['freeze_sha256']==H(folder/'freeze.json')
                saved=L(folder/f"run-{record['run_id']}.json");assert saved==record
                assert record['actual_http_request_body']['messages']==record['messages']
                assert record['actual_http_request_body']['max_tokens']==256
                assert all(record['parameter_checks'].values()) and record['truncated'] is False
                assert record['usage']['completion_tokens']>0
                assert record['run_id'] not in local_ids;local_ids.add(record['run_id'])
                if record['stage']=='answer':
                    msg=record['messages'][1]['content'];q=task['question'];ps=task['used_passages']
                    if job['policy'].get('presentation')=='blocks':
                        expected='\n\n'.join(['问题：\n'+q]+['段落 '+str(i)+'\nID：'+p['id']+'\n来源：'+p['source']+'\n原文：\n'+p['text'] for i,p in enumerate(ps,1)])
                        assert msg==expected
                    else:assert json.loads(msg)=={'question':q,'passages':ps}
                audit.append({'round':n,'case_id':task['case_id'],'run_id':record['run_id'],'stage':record['stage'],'actual_parameters':{k:v for k,v in record['actual_http_request_body'].items() if k not in ['messages','response_format']},'input_tokens':record['input_tokens'],'input_and_256':record['input_tokens']+256,'finish_reason':record['finish_reason'],'truncated':record['truncated'],'parameter_checks':record['parameter_checks'],'passed':True})
    assert len(local_ids)==48
    r4=L(F/'round4/summary.json');assert r4['passed']
    rounds.insert(3,{'round':4,'generation_calls':0,'old_passed':r4['old_passed'],'additional_passed':r4['additional_passed'],'rule_changes':r4['rule_changes'],'decision':r4['decision']})
    previous={r['case_id']:r for r in L(P/'review/effective-reviews.json')['rows']};pairs=[]
    for row in review['rows']:
        old=previous[row['case_id']]
        def transition(a,b):return 'regressed' if a is True and b is not True else 'improved' if a is not True and b is True else 'unchanged'
        pairs.append({'case_id':row['case_id'],'dataset':row['dataset'],'previous_raw':{'answer':old['raw_review']['answer'],'citations':old['raw_review']['citations']},'current_raw':{'answer':row['raw']['answer'],'citations':row['raw']['citations']},'previous_final':{'answer':old['system_final_review']['answer'],'citations':old['system_final_review']['citations']},'current_final':{'answer':row['final']['answer'],'citations':row['final']['citations']},'raw_answer_change':transition(old['raw_review']['answer_correct'],row['raw']['answer_correct']),'raw_strict_change':transition(old['raw_review']['strict_complete_success'],row['raw']['strict_complete_success']),'system_answer_change':transition(old['system_final_review']['answer_correct'],row['final']['answer_correct']),'system_strict_change':transition(old['system_final_review']['strict_complete_success'],row['final']['strict_complete_success']),'wrong_derivation':row['wrong_derivation'],'end_to_end_seconds':row['timing']['end_to_end_seconds'],'ambiguity':row['raw'].get('ambiguity') or row['final'].get('ambiguity')})
    W(F/'request-and-version-audit.json',{'checked_at':N(),'passed':True,'calls':audit,'all_original_inputs_preserved':True,'no_truncation':True,'all_hashes_still_match':True})
    W(F/'previous-comparison.json',{'reviewed_at':N(),'rows':pairs,'source':(P/'review/effective-reviews.json').relative_to(ROOT).as_posix(),'comparison':'历史对照，不是独立重复随机评测；不用两轮较好回答拼接。'})
    # 与历史同口径：只统计顶层run_id且完成token>0的唯一ID；嵌套历史选择引用不重复计数。
    all_ids=set();paths={};invalid=[]
    for path in (ROOT/'基础/runs').rglob('*.json'):
        try:value=L(path)
        except (ValueError,UnicodeError) as error:invalid.append({'path':path.relative_to(ROOT).as_posix(),'error':str(error)});continue
        if not isinstance(value,dict) or not value.get('run_id'):continue
        response=value.get('response');usage=value.get('usage') or (response.get('usage') if isinstance(response,dict) else None) or {}
        if usage.get('completion_tokens',0)>0:
            all_ids.add(value['run_id']);paths.setdefault(value['run_id'],[]).append(path.relative_to(ROOT).as_posix())
    assert len(all_ids)==526 and local_ids<=all_ids and not invalid
    W(F/'generation-ledger.json',{'checked_at':N(),'baseline':478,'new_generation_calls':48,'new_unique_run_ids':sorted(local_ids),'cumulative_unique':len(all_ids),'new_round_counts':{'1':8,'2':8,'3':8,'4':0,'5':24},'offline_B_replays_separate':88,'all_unique_ids':sorted(all_ids),'duplicate_storage_deduplicated':{k:v for k,v in paths.items() if len(v)>1},'invalid_json_files':invalid})
    facts={'recorded_at':N(),'five_rounds_completed':True,'no_sixth_round':True,'rounds':rounds,'final_metrics':review['groups'],'final_rows':[{k:v for k,v in r.items() if k!='basis'} for r in review['rows']],'previous_comparison':pairs,'new_generation_calls':48,'cumulative_generation_calls':526,'wrong_derivations':sum(r['wrong_derivation'] for r in review['rows']),'regressions':{k:sum(p[k]=='regressed' for p in pairs) for k in ['raw_answer_change','raw_strict_change','system_answer_change','system_strict_change']},'final_entry':(F/'bounded_candidate.py').relative_to(ROOT).as_posix(),'recorded_run_command':'python -X utf8 -B '+(F/'run_bounded_round.py').relative_to(ROOT).as_posix()+' '+(F/'round5').relative_to(ROOT).as_posix(),'rerun_policy':'该历史目录已有结果，入口会拒绝覆盖。未来复现必须另建全新目录并另获调用授权。','all_owned_services_stopped':all(L(F/f'round{n}/runtime.json')['service_stopped'] for n in [1,2,3,5]),'scope':'辅助暂判，T题评测后重复测试，非独立泛化成绩；原始模型、规则计算改答、规则引用组装单列。'}
    W(F/'delivery-facts.json',facts)
    for p in [Path(__file__),Path(__file__).with_name('manage_final_five.py'),Path(__file__).with_name('check_final_five_rules.py')]:
        # 调度与纯离线辅助归档；不影响已冻结的推理模块。
        text=p.read_text(encoding='utf-8-sig').replace("ROOT=Path(r'C:\\Users\\86186\\Projects\\ANTLab-Agent-Tasks')","ROOT=next(p for p in Path(__file__).resolve().parents if (p/'基础/starter/provider.py').is_file())").replace("CAMPAIGN=Path(__file__).resolve().parent","CAMPAIGN=Path(__file__).resolve().parent")
        (F/p.name).write_text(text,encoding='utf-8',newline='\n')
    manifest=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':H(p)} for p in F.rglob('*') if p.is_file()]
    W(F/'file-list.json',{'saved_at':N(),'listed_files':len(manifest),'note':'清单不包含本清单自身；本轮文件总数为listed_files+1。','total_bytes_excluding_this_list':sum(p['bytes'] for p in manifest),'files':manifest})
    print(json.dumps({k:v for k,v in facts.items() if k in ['final_metrics','new_generation_calls','cumulative_generation_calls','wrong_derivations','regressions','all_owned_services_stopped']},ensure_ascii=False))
    print(json.dumps([{'id':p['case_id'],'raw':p['current_raw'],'final':p['current_final'],'seconds':round(p['end_to_end_seconds'],3)} for p in pairs],ensure_ascii=False))
if __name__=='__main__':main()
