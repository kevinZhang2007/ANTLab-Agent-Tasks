import ast, copy, difflib, hashlib, importlib.util, json, os, shutil, subprocess, sys, traceback
from pathlib import Path
from datetime import datetime
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
BASE=ROOT/'基础/runs/association_compat_dev/20261015-154928'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now().astimezone().isoformat()
def write(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as o:json.dump(v,o,ensure_ascii=False,indent=2);o.write('\n')
def patch(t,a,b):
    assert t.count(a)==1,a[:100]
    return t.replace(a,b,1)
def module(p,n):
    s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
    global active
    folder=ROOT/'基础/runs/calculation_compat_dev'/datetime.now().strftime('%Y%m%d-%H%M%S');folder.mkdir(parents=True,exist_ok=False);active=folder
    protected={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'基础/runs').rglob('*') if p.is_file() and folder not in p.parents}
    for n in ['report.md','README.md','基础/开发记录.md','基础/starter/student.py','基础/config.local.json']:
        if (ROOT/n).exists():protected[n]=sha(ROOT/n)
    write(folder/'protected-hashes.json',protected)
    write(folder/'design-plan.json',{'saved_at':now(),'mode':'offline_development_replay','generation_calls':0,
        'hypothesis':'D03同一比较集合的“相同”与“同样”是措辞兼容缺口；安全识别后可以独立计算建议，但原answer不符仍不能生成引用证明。',
        'D01_limit':'已进入比例分支，缺少当前解析器要求的所求指标定义。只有完整支持计数不足以自动声明核验率定义；保留拒绝，不以开发答案补定义。',
        'changes':'仅比较集合措辞、直接否定检查与正规模检查；差值工具单独保存新答案。比例与选择规则不变。',
        'risks':['有限语法不能覆盖全部中文表达。','相同数量只有在唯一直接关系、范围和指标单位一致时才参与证明。'],
        'gate':'保留原437项检查并逐项对照证明状态；新增自造正反例。无法解释的回归阻断冻结/重放。',
        'evaluation':'全部四条开发题原始响应原样重放。公开开发答案只用于重放后的辅助原文评价，不进入计算器。',
        'no_T_content_for_rule_changes':True,'no_model_service':True})
    names=['scope_candidate.py','scope_first_occurrences.py','eligibility_proof_checker.py','explicit_state_checker.py',
        'eligibility_exclusion_candidate.py','typed_enum_role_revision.py','typed_identifier_enum_candidate.py','body_identifier_enum_candidate.py','offline_gate.py',
        'proof_scope_occurrences.py','proof_snapshot_checker.py','general_citation_proof.py','project_scope_resolution.py',
        'ratio_calculation_proof.py','proof_pipeline_candidate.py','direct_reference_candidate.py',
        'check_association_compat.py','check_general_citation_proof.py','check_project_scope_resolution.py','check_ratio_calculation_proof.py']
    for name in names:shutil.copyfile(BASE/name,folder/name)
    for name in ['settings.prepared.json','answer.prepared.json','selection.prepared.json']:shutil.copyfile(BASE/name,folder/name)
    for name in ['difference_calculation_proposal.py','check_calculation_compat.py']:
        shutil.copyfile(Path(__file__).with_name(name),folder/name)
    shutil.copyfile(Path(__file__),folder/Path(__file__).name)
    sys.path.insert(0,str(ROOT/'基础/tests'));sys.path.insert(0,str(BASE))
    old=module(BASE/'general_citation_proof.py','old_difference_diagnosis')
    ratio=module(BASE/'ratio_calculation_proof.py','old_ratio_diagnosis')
    diagnosis=[]
    for i in [1,3]:
        task=load(BASE/f'task-{i:02d}.json');record={'case_id':task['case_id'],'question':task['question'],
            'actual_final_input':task['used_passages'],'actual_raw_response':task['raw_response'],
            'old_reference_proof':old.prove_answer(task['question'],task['used_passages'],task['raw_answer'],task['original_passages']),
            'old_ratio_proof':ratio.propose(task['question'],task['used_passages'],task['raw_answer'],task['original_passages'])}
        if i==1:
            record.update(classification='applicable_ratio_then_definition_proof_refusal_not_raw_answer_mismatch',
                original_quote='有68个问题的必要结论获所选文档完整支持，另有11个无支持结论、6个响应格式错误',
                code_branch='metric=targets[0][metric]; definition=definitions(metric,fact_passages); require(len(found)==1,metric_definition_missing_or_multiple)',
                conclusion='所求指标被解析为核验；只计/列为定义匹配为空。原文未明示核验与完整支持类别的定义映射，不能从公开答案补入。')
        else:
            q=old.DIFFERENCE.search(task['question']);attempts=[]
            for left,right in [task['used_passages'],list(reversed(task['used_passages']))]:
                row={'left_id':left['id'],'right_id':right['id']}
                try:
                    row['left']=old.metric_value(left,q['left'],q['metric'],'中位数',True)
                    row['right']=old.metric_value(right,q['right'],q['metric'],'中位数',True)
                    row['comparability_old_pattern']='同样(?P<number>DEC)(?P<unit>个|条|次|人)'
                    row['comparability_actual_quote']='处理相同40个问题'
                    row['failure']='comparability_not_explicit (caught by difference() then zero_or_multiple_reliable_operand_assignments)'
                except old.Refuse as error:row['failure']=str(error)
                attempts.append(row)
            record.update(classification='applicable_difference_operands_parsed_comparability_wording_rejected_before_answer_comparison',attempts=attempts,
                code_branch='same=re.finditer(同样...); require(len(same)==1,comparability_not_explicit); except Refuse:continue',
                conclusion='匹配方向的两项指标5.8秒和7.6秒均能解析；漏相同措辞使options为空。尚未到original_answer_not_equal_to_proven_difference。')
        diagnosis.append(record)
    write(folder/'diagnosis-before-repair.json',{'checked_at':now(),'rows':diagnosis})
    original=(folder/'general_citation_proof.py').read_text(encoding='utf-8')
    updated=patch(original,"r'同样(?P<number>'+DEC+r')(?P<unit>个|条|次|人)'","r'(?:同样|相同)\\s*(?P<number>'+DEC+r')(?P<unit>个|条|次|人)'")
    updated=patch(updated,"            same=same[0]\n            primary=", "            same=same[0]\n            prefix=first_sentence(extra)[max(first_sentence(extra).rfind(c,0,same.start()) for c in '，,；;：:')+1:same.start()].rstrip()\n            require(not re.search(r'(?:不|并非|不是|未|不能|无法)$',prefix),'comparison_population_negated')\n            require(Decimal(same['number'])>0 and Decimal(same['number'])==Decimal(same['number']).to_integral_value(),'comparison_population_nonpositive_or_fractional')\n            primary=")
    updated=patch(updated,'        except Refuse:\n            continue\n    require(len(options)==1',"        except Refuse as error:\n            trace.append({'stage':'difference_operand_attempt_refused','left_source_id':left_source['id'],'right_source_id':right_source['id'],'reason':str(error)})\n            continue\n    require(len(options)==1")
    ast.parse(updated);(folder/'general_citation_proof.py').write_text(updated,encoding='utf-8',newline='\n')
    (folder/'calculation-compat.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),updated.splitlines(True),fromfile='previous/general_citation_proof.py',tofile='independent/general_citation_proof.py'))
        +''.join(difflib.unified_diff([], (folder/'difference_calculation_proposal.py').read_text(encoding='utf-8').splitlines(True),fromfile='/dev/null',tofile='independent/difference_calculation_proposal.py')),encoding='utf-8',newline='\n')
    # 历史诊断导入均为旧路径；新回归在独立进程加载当前目录，避免模块缓存混用。
    suites=['check_association_compat.py','check_general_citation_proof.py','check_project_scope_resolution.py','check_ratio_calculation_proof.py','check_calculation_compat.py']
    execution=[]
    for name in suites:
        result=subprocess.run([sys.executable,'-X','utf8','-B',str(folder/name)],capture_output=True,text=True,encoding='utf-8',env={**os.environ,'PYTHONPATH':str(ROOT/'基础/tests')})
        row={'suite':name,'checked_at':now(),'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'generation_calls':0}
        write(folder/(name+'.execution.json'),row);execution.append(row)
        assert result.returncode==0,result.stdout+result.stderr
    changes=[]
    for pattern,keys in [('self-test-*.json',['proof_established','proof_status','reason','derived_response']),('ratio-test-*.json',['proof_established','status','reason','proposed_response'])]:
        oldfiles=sorted(BASE.glob(pattern));assert oldfiles
        for path in oldfiles:
            before=load(path)['actual'];after=load(folder/path.name)['actual']
            for k in keys:
                if before.get(k)!=after.get(k):changes.append({'file':path.name,'field':k,'before':before.get(k),'after':after.get(k)})
    assert not changes,'existing proof states changed unexpectedly'
    write(folder/'regression-summary.json',{'checked_at':now(),'old_cases':437,'old_cases_passed':437,
        'new_cases':load(folder/'calculation-compat-self-tests.json')['total'],'new_cases_passed':load(folder/'calculation-compat-self-tests.json')['passed_count'],
        'existing_proof_state_changes':changes,'all_passed':True,'suites':execution,'generation_calls':0})
    settings=load(folder/'settings.prepared.json');data_hashes={p:sha(ROOT/p) for p in settings['data_sha256']}
    assert data_hashes==settings['data_sha256']
    code_hashes={p.relative_to(ROOT).as_posix():sha(p) for p in folder.glob('*.py')}
    write(folder/'freeze.json',{'frozen_at':now(),'kind':'offline_development_calculation_compatibility','code_hashes':code_hashes,'data_hashes':data_hashes,
        'model':settings['model'],'model_not_loaded':True,'source_round':BASE.relative_to(ROOT).as_posix(),'input_records':[f'task-{i:02d}.json' for i in range(1,5)],
        'input_record_hashes':{f'task-{i:02d}.json':sha(BASE/f'task-{i:02d}.json') for i in range(1,5)},
        'output_policy':'独立差值建议或比例建议成立才生成local_rule计算改答；否则引用证明；否则原答。原始响应永远保留。',
        'D01_missing_definition_no_guessed_mapping':True,'generations':0,'evaluation':'四题分母，公开答案仅用于运行后独立辅助原文核对。'})
    print(json.dumps({'folder':str(folder),'passed':True,'old_cases':437,'new_cases':load(folder/'calculation-compat-self-tests.json')['total'],'generation_calls':0},ensure_ascii=False))

if __name__=='__main__':
    active=None
    try:main()
    except Exception as error:
        if active is not None:write(active/'offline-stop.json',{'recorded_at':now(),'stage':'preparation_or_regression','error':str(error),'traceback':traceback.format_exc(),'generation_calls':0,'model_service_started':False})
        raise
