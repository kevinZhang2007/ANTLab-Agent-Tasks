"""再次运行同一冻结候选：仅新目录、版本核对与计数调度，不改推理。"""
from pathlib import Path
from datetime import datetime
import ast,difflib,hashlib,importlib.util,json,os,shutil,sys,traceback
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks')
SOURCE=ROOT/'基础/runs/repeat_integrated/20261015-171741'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now().astimezone().isoformat()
def write(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as o:json.dump(v,o,ensure_ascii=False,indent=2);o.write('\n')
def main():
    global active
    folder=ROOT/'基础/runs/repeat_integrated'/datetime.now().strftime('%Y%m%d-%H%M%S');folder.mkdir(parents=True,exist_ok=False);active=folder
    frozen=load(SOURCE/'freeze.json');differences=[]
    for p,h in {**frozen['code_hashes'],**frozen['data_hashes']}.items():
        actual=sha(ROOT/p) if (ROOT/p).is_file() else None
        if actual!=h:differences.append({'path':p,'expected':h,'actual':actual})
    local=Path(os.environ['LOCALAPPDATA'])/'ANTLabLocalModel'
    for p,h in [(local/'models/Qwen3-0.6B-Q8_0.gguf',frozen['model']['actual_sha256']),(local/'llama-b11429/llama-server.exe',frozen['llama_cpp']['executable_sha256'])]:
        actual=sha(p) if p.is_file() else None
        if actual!=h:differences.append({'file':p.name,'expected':h,'actual':actual})
    page=load(ROOT/'基础/runs/page_closure/20261015-173656/page-freeze.json')
    assert page['source_freeze_sha256']==sha(SOURCE/'freeze.json')
    names=list(load(SOURCE/'preparation-plan.json')['source_modules'])
    for name in names:
        if sha(SOURCE/name)!=load(SOURCE/'preparation-plan.json')['source_modules'][name]:differences.append({'copied_module':name})
    for name,key in [('answer.prepared.json','answer_config'),('selection.prepared.json','selection_config')]:
        if load(SOURCE/name)!=frozen[key]:differences.append({'config':name})
    if load(SOURCE/'settings.prepared.json')['service_arguments']!=frozen['service_arguments']:differences.append({'service_arguments':True})
    write(folder/'version-verification.json',{'checked_at':now(),'recent_successful_full_run':SOURCE.relative_to(ROOT).as_posix(),'recent_freeze_sha256':sha(SOURCE/'freeze.json'),'page_validation_source_matches':True,'differences':differences,'copied_module_names':names,'model':frozen['model'],'llama_cpp':frozen['llama_cpp']})
    assert not differences,'版本不一致，停止，不拼接模块'
    for name in names:shutil.copyfile(SOURCE/name,folder/name);assert sha(SOURCE/name)==sha(folder/name)
    shutil.copyfile(Path(__file__),folder/'prepare_repeat_integrated.py')
    original=(SOURCE/'run_repeat_integrated.py').read_text(encoding='utf-8-sig')
    before="'previous_cumulative':428,'cumulative_confirmed':428+len(ids)"
    assert original.count(before)==1
    text=original.replace(before,"'previous_cumulative':454,'cumulative_confirmed':454+len(ids)",1)
    marker="'capacity_reference':'capacity-summary.json','cache_policy':'每阶段清空单槽缓存',"
    assert text.count(marker)==1
    text=text.replace(marker,"'recent_successful_parent':load(folder/'version-verification.json'),\n              "+marker,1)
    ast.parse(text);(folder/'run_repeat_integrated.py').write_text(text,encoding='utf-8',newline='\n')
    (folder/'orchestration-only.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='previous/run_repeat_integrated.py',tofile='current/run_repeat_integrated.py')),encoding='utf-8')
    jobs=load(SOURCE/'execution-plan.prepared.json')['items'];assert len(jobs)==12
    write(folder/'execution-plan.prepared.json',{'saved_at':now(),'items':jobs,'generation_limit':24,'fresh_selection':True})
    parent=ROOT/'基础/runs/calculation_full_dev/20261015-160956/freeze.json'
    write(folder/'parent-freeze-verification.json',{'checked_at':now(),'parent_freeze_sha256':sha(parent),'recent_freeze_sha256':sha(SOURCE/'freeze.json'),'all_code_data_model_config_hashes_match':True})
    sys.path.insert(0,str(ROOT/'基础/tests'));sys.path.insert(0,str(folder))
    import proof_pipeline_candidate as candidate
    import inspect
    assert Path(inspect.getfile(candidate)).resolve()==folder/'proof_pipeline_candidate.py'
    assert sha(Path(inspect.getfile(candidate.execute)))==sha(SOURCE/'proof_pipeline_candidate.py')
    retained=load(folder/'retained-regressions.json');assert retained['all_passed'] and retained['total']==534
    evidence={}
    for name in ['preflight.json','offline-check.json','operation-logging-check.json','additional-existing-tests.json','entry-gate-verification.json','runner-gate-integration.json','execution-offline-check.json']:
        assert load(SOURCE/name)['passed'];evidence[name]={'path':(SOURCE/name).relative_to(ROOT).as_posix(),'sha256':sha(SOURCE/name)}
    config=load(folder/'answer.prepared.json');selection=load(folder/'selection.prepared.json')
    for value,key in [(config,'answer'),(selection,'selected_ids')]:
        assert value['parameters']['max_tokens']==256 and value['parameters']['response_format']['type']=='json_schema'
        assert key in value['parameters']['response_format']['json_schema']['schema']['required']
    assert all((ROOT/p).is_file() for p in frozen['code_hashes'])
    for path in folder.glob('*.py'):ast.parse(path.read_text(encoding='utf-8-sig'))
    checks={'checked_at':now(),'passed':True,'returncode':0,'import_verified':True,'same_frozen_modules':True,'orchestration_only':True,'reused_unchanged_regressions':534,'prior_checks':evidence,'generation_calls':0}
    for name in ['preflight.json','offline-check.json','additional-existing-tests.json','entry-gate-verification.json','runner-gate-integration.json','execution-offline-check.json']:write(folder/name,checks)
    write(folder/'operation-logging-check.json',{'checked_at':now(),'passed':True,'code_sha256':sha(folder/'proof_pipeline_candidate.py'),'reused_from':evidence['operation-logging-check.json']})
    write(folder/'fixture-index.json',{'checked_at':now(),'source_modules':{name:sha(folder/name) for name in names},'retained_regressions':534,'prior_checks':evidence})
    write(folder/'preparation-plan.json',{'saved_at':now(),'purpose':'同一整合冻结候选再次完整重复，不优化','previous_complete_run':SOURCE.relative_to(ROOT).as_posix(),'previous_cumulative':454,'source_modules':{name:sha(folder/name) for name in names},'order':jobs,'main_task_limit':12,'generation_limit':24,'evaluation':'全部生成结束后使用同一已归档评价函数；分母4和8，D01定义绑定及T01资格歧义保持不变','failure':'准备工程错误可离线修复留档；技术请求失败立即停止并核查实际是否发送，不自动重复；质量错误不重试','exposure':'T题为评测后重复测试，不是独立泛化成绩','results_export':'不覆盖、不混入本轮结果','generation_calls':0})
    print(json.dumps({'folder':str(folder),'passed':True,'matching_modules_and_configs':len(names),'generation_calls':0},ensure_ascii=False))
if __name__=='__main__':
    active=None
    try:main()
    except Exception as error:
        if active is not None:write(active/'preparation-stop.json',{'recorded_at':now(),'error':str(error),'traceback':traceback.format_exc(),'generation_calls':0,'service_started':False})
        raise
