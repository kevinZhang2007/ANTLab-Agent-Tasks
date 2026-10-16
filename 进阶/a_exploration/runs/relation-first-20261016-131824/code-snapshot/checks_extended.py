from pathlib import Path
import io,json,copy
import checks
import runtime
from development import read_development_stream
from engine import Corpus

def run(folder):
    result=checks.run();extra=[]
    def test(name,value):
        extra.append({'name':name,'passed':bool(value)})
        if not value:raise AssertionError(name)
    fixture=b'['+b','.join(json.dumps({'id':str(i),'split':'dev','claim':'self-made'},ensure_ascii=False).encode() for i in range(3))+b',DO_NOT_READ]'
    stream=io.BytesIO(fixture);items=read_development_stream(stream)
    test('development_parser_stops_before_fourth_object',len(items)==3 and stream.read()==b',DO_NOT_READ]')
    original=checks.neighbors
    checks.neighbors=lambda seeds,blocks:(copy.deepcopy(blocks),[])
    caught=False
    try:checks.run()
    except AssertionError:caught=True
    finally:checks.neighbors=original
    test('regression_detects_bad_cross_chapter_implementation',caught)
    root=folder/'offline-failure-fixture';root.mkdir()
    engine=runtime.Engine(root)
    engine.corpus=Corpus([{'id':'synthetic','doc_id':'made_up','heading':'self test','paragraphs':['archive data']}])
    def fail(*args,**kwargs):raise runtime.TechnicalStop('synthetic offline transport failure; no HTTP sent')
    engine.generate=fail
    failed=False
    try:engine.execute_pair('synthetic claim',['made_up'],'published',['baseline','improved'])
    except runtime.TechnicalStop:failed=True
    saved=json.loads(next(root.glob('pair-*.json')).read_text(encoding='utf-8'))
    test('technical_failure_saved_without_generation',failed and saved['status']=='technical_stop' and engine.dispatches==0)
    test('technical_failure_blocks_next_generation',engine.technical_stop)
    # 明确修正该自造夹具的类型，避免被当成真实API实验。
    saved['run_kind']='dry_run';saved['offline_fixture']=True;runtime.write(next(root.glob('pair-*.json')),saved)
    (root/'fixture-not-experiment.json').write_text(json.dumps({'kind':'offline_test_fixture','actual_model_requests':0,'not_a_model_run':True}),encoding='utf-8')
    e=runtime.Engine(folder/'unused-fixture');e.folder.mkdir()
    original_memory=runtime.memory;runtime.memory=lambda:{'available_bytes':3*1024**3}
    e.capacity=lambda *args:(_ for _ in ()).throw(runtime.CapacityStop('synthetic over-context'))
    stopped=False
    try:e.generate([],runtime.config('query'),'synthetic','synthetic',[])
    except runtime.CapacityStop:stopped=True
    finally:runtime.memory=original_memory
    test('capacity_failure_blocks_http',stopped and e.dispatches==0 and not list(e.folder.glob('run-*.json')))
    result['checks']+=extra;result['passed']+=len(extra)
    return result
