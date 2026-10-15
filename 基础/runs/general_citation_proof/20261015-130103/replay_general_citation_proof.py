import copy
import difflib
import hashlib
import importlib.util
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
FOLDER=ROOT/'基础/runs/general_citation_proof/20261015-130103'
SOURCE=ROOT/'基础/runs/proof_full_r0_repeat/20261015-124627'
FAILED=ROOT/'基础/runs/general_citation_proof/20261015-130028'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now().astimezone().isoformat()
def write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as out:json.dump(value,out,ensure_ascii=False,indent=2);out.write('\n')
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main():
    frozen=load(FOLDER/'freeze.json')
    assert load(FOLDER/'self-check.json')['passed'] and load(FOLDER/'snapshot-regressions.json')['passed']
    assert load(FOLDER/'offline-gate.json')['passed']
    assert all(sha(ROOT/p)==h for p,h in {**frozen['code_hashes'],**frozen['data_hashes'],**frozen['source_task_hashes']}.items())
    assert not list(FOLDER.glob('replay-*.json'))
    sys.path.insert(0,str(ROOT/'基础/tests'));sys.path.insert(0,str(FOLDER))
    import general_citation_proof as candidate
    import offline_gate
    def replay_all():
        results=[]
        for index in range(1,9):
            task=load(SOURCE/f'task-{index:02d}.json');assert task['case_id']==f'T{index:02d}'
            begin=time.perf_counter();proof=candidate.prove_answer(task['question'],task['used_passages'],task['raw_answer'],task['original_passages'])
            elapsed=time.perf_counter()-begin;raw=json.loads(task['raw_answer']);derived=proof['derived_response']
            if derived is not None:assert derived['answer']==raw['answer']
            row={'replayed_at':now(),'case_id':task['case_id'],'source_path':(SOURCE/f'task-{index:02d}.json').relative_to(ROOT).as_posix(),
                'source_sha256':sha(SOURCE/f'task-{index:02d}.json'),'freeze_sha256':sha(FOLDER/'freeze.json'),
                'run_kind':'offline_replay_no_model_generation','question':task['question'],'passages':task['used_passages'],
                'full_original_passages':task['original_passages'],'raw_response':task['raw_response'],'raw_content':task['raw_answer'],
                'raw_answer_citations':raw,'proof':proof,'derived_response':derived,
                'actual_final_response':copy.deepcopy(derived if derived is not None else raw),
                'actual_final_response_source':'local_rule_citation_assembly' if derived is not None else 'unchanged_raw_model_response',
                'local_rule_seconds':elapsed,'generation_calls':0}
            assert row['replayed_at']>frozen['frozen_at']
            write(FOLDER/f'replay-{index:02d}.json',row);results.append((task,row))
        return results
    results=offline_gate.after_offline_success(lambda:load(FOLDER/'offline-gate.json'),replay_all)
    # 此处才读取评价依据；它们从未导入证明实现。
    evaluation_path=SOURCE/'review/review_proof_full_repeat.py'
    evaluator=module(evaluation_path,'existing_original_text_review')
    positions=module(ROOT/'基础/runs/eligibility_proof/20261015-000204/prepare_eligibility_proof.py','proof_positions')
    reviews=[]
    for task,row in results:
        cid=row['case_id'];basis_path=ROOT/f'基础/runs/formal_review/round1/evidence-{cid}.json';basis=load(basis_path)
        assert basis['source_sha256']==frozen['data_hashes']['基础/data/cases.json']
        originals={p['id']:p for p in task['original_passages']}
        assert all(e['quote'] in originals[e['id']]['text'] for e in basis['required_evidence'])
        positions.positions(row['proof'],task['original_passages'])
        raw=evaluator.evaluate(task,row['raw_content'],basis)
        final=evaluator.evaluate(task,row['actual_final_response'],basis)
        derived=row['derived_response'] is not None
        # 评分复用实际原文推导及既有澄清，不将proof_established当作语义标签。
        review={'reviewed_at':now(),'reviewer_note':'Codex辅助原文复核，尚未经本人逐项确认。非官方成绩；仅离线派生，未重新运行模型。',
            'case_id':cid,'raw_review':raw,'final_review':final,'applicable':row['proof']['proof_status']!='not_applicable',
            'proof_kind':row['proof']['proof_kind'],'proof_status':row['proof']['proof_status'],'reason':row['proof'].get('reason'),
            'derived':derived,'refused':row['proof']['proof_status']!='not_applicable' and not derived,
            'erroneous_derivation':derived and final['support_actual_answer'] is not True,
            'raw_answer_unchanged':row['raw_answer_citations']['answer']==row['actual_final_response']['answer'],
            'basis_path':basis_path.relative_to(ROOT).as_posix(),'basis_sha256':sha(basis_path),
            'source_check':'当前问题和资料原文来源未变，必要摘录逐条核对；评分未依赖程序证明标志。',
            'local_rule_seconds':row['local_rule_seconds']}
        write(FOLDER/f'review-{cid}.json',{'basis':basis,'review':review});reviews.append(review)
    counts={'applicable':sum(r['applicable'] for r in reviews),'not_applicable':sum(not r['applicable'] for r in reviews),
        'refused_when_applicable':sum(r['refused'] for r in reviews),'derived':sum(r['derived'] for r in reviews),
        'erroneous_derivation':sum(r['erroneous_derivation'] for r in reviews),'denominator':8}
    def metric(side,key):
        values=[r[side][key] for r in reviews]
        return {'numerator':sum(v is True for v in values),'denominator':8,'percent':sum(v is True for v in values)*100/8,'ambiguous':sum(v=='ambiguous' for v in values)}
    summary={'reviewed_at':now(),'reviewer_note':reviews[0]['reviewer_note'],'rule_counts':counts,
        'answer_correct':metric('final_review','answer_correct'),'raw_strict':metric('raw_review','strict_complete_success'),
        'system_final_strict':metric('final_review','strict_complete_success'),'generation_calls':0,
        'previous_system_strict':load(SOURCE/'review/summary.json')['metrics']['system_final_review']['strict_complete_success'],
        'rows':[{'case_id':r['case_id'],'kind':r['proof_kind'],'proof_status':r['proof_status'],'derived':r['derived'],
            'raw_answer':r['raw_review']['answer'],'raw_citations':r['raw_review']['citations'],'final_citations':r['final_review']['citations'],
            'answer_correct':r['final_review']['answer_correct'],'raw_strict':r['raw_review']['strict_complete_success'],
            'final_strict':r['final_review']['strict_complete_success'],'reason':r['reason']} for r in reviews]}
    write(FOLDER/'summary.json',summary)
    protected=load(FOLDER/'protected-hashes.json')
    changes=[p for p,h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
    assert not changes
    ids={}
    for path in (ROOT/'基础/runs').rglob('*.json'):
        v=load(path)
        if not isinstance(v,dict):continue
        usage=v.get('usage')
        if not isinstance(usage,dict) and isinstance(v.get('response'),dict):usage=v['response'].get('usage')
        if v.get('run_id') and isinstance(usage,dict) and usage.get('completion_tokens',0)>0:
            ids.setdefault(v['run_id'],[]).append(path.relative_to(ROOT).as_posix())
    assert len(ids)==356
    write(FOLDER/'generation-count.json',{'checked_at':now(),'new_generations':0,'unique_generation_run_ids':len(ids),'sources':ids})
    diff=''.join(difflib.unified_diff((FAILED/'general_citation_proof.py').read_text(encoding='utf-8').splitlines(True),
        (FOLDER/'general_citation_proof.py').read_text(encoding='utf-8').splitlines(True),fromfile='preserved_first_offline_failure/general_citation_proof.py',tofile='frozen/general_citation_proof.py'))
    (FOLDER/'offline-boundary-repair.diff').write_text(diff,encoding='utf-8',newline='\n')
    write(FOLDER/'repair-and-limits.json',{'recorded_at':now(),'failed_run_preserved':FAILED.relative_to(ROOT).as_posix(),
        'first_test_results':'122/126；4个变体暴露未知字段被吞作候选名。门禁实际阻止冻结及八题处理。',
        'repair':'连写表格候选名称边界只接受单字中文标签或完整ASCII标识；其他名称未知，不能吞入未知字段后继承列。',
        'new_tests':'保留全部126例，增加多字无分隔名称的四个变体，共130例，另有14个旧快照回归。',
        'limits':['不支持任意多字中文名称的无分隔表格，不猜同义指标。','唯一合格项时后续排名不触发；多合格项且方向不明或并列则拒绝。',
            '差值仅支持明示统计量、同量样本集合、相同单位的唯一同批直接主/补页；不做单位换算。','快照数量通过承接唯一检查集合的解释和T01未知条件沿用，仍需人工确认。'],
        'evaluation_not_official':True})
    shutil.copyfile(Path(__file__),FOLDER/Path(__file__).name)
    write(FOLDER/'final-audit.json',{'checked_at':now(),'protected_files':len(protected),'changed':changes,
        'frozen_before_all_eight_replays':True,'replayed_all_eight':True,'raw_response_preserved':True,'all_answers_unchanged':all(r['raw_answer_unchanged'] for r in reviews),
        'new_generation_calls':0,'cumulative_generation_calls':356,'models_loaded':False,'services_started':False,
        'review_function_source':evaluation_path.relative_to(ROOT).as_posix(),'review_function_sha256':sha(evaluation_path),
        'old_documents_production_and_history_unchanged':True})
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':main()
