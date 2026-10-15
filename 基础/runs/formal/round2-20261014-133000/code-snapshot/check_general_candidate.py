"""通用入口离线检查；所有定位响应都是明确标注的自造测试夹具。"""
import copy
import json
import sys
from datetime import datetime
from pathlib import Path
import general_candidate as candidate

def check(folder):
    repo = Path(__file__).resolve().parents[2]
    load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
    answer = load(repo/'基础/runs/two_step/dev_r0/config.answer.json')
    selection = load(repo/'基础/runs/two_step/dev_r0/config.selection.json')
    rows = [{'id':'main','source':'same/a','text':'甲项目R2版本2026-07批次AB12记录：总数12。'},
            {'id':'supp','source':'same/b','text':'批次AB12的复核补页：通过6项。'}]
    results = []
    def run(name, passages, selected, expected, question='资料说明，只输出数值。'):
        before = copy.deepcopy(passages)
        calls = []
        def fixture(stage, messages, config, used):
            calls.append(stage)
            assert json.loads(messages[1]['content']) == {'question':question, 'passages':used}
            content = selected if stage == 'selection' else '{"answer":"证据不足","citations":[]}'
            return {'status':'ok','fixture_not_generation':True,'response':{'choices':[{'message':{'content':content}}]}}
        result = candidate.execute(question, passages, 'improved', answer, selection, fixture)
        assert passages == before
        assert calls == (['selection','answer'] if expected is not None else ['selection'])
        if expected is not None:
            assert [p['id'] for p in result['used_passages']] == expected
            assert all(p in before for p in result['used_passages'])
        results.append({'sample':name, 'passed':True, 'calls_are_fixtures':True, 'result':result})
    run('直接补页', rows, '{"selected_ids":["main"]}', ['main','supp'])
    run('空资料', [], '{"selected_ids":[]}', [])
    run('合法空选择', rows, '{"selected_ids":[]}', [])
    run('非法ID', rows, '{"selected_ids":["missing"]}', None)
    run('重复ID', rows, '{"selected_ids":["main","main"]}', None)
    run('非法JSON', rows, 'bad json', None)
    repeated = rows + [dict(rows[0], id='other', text='乙项目R2版本批次AB12记录。')]
    run('编号复用', repeated, '{"selected_ids":["main"]}', ['main'])
    conflict = [rows[0], dict(rows[1], text='甲项目R3版本批次AB12的复核补页。')]
    run('范围冲突', conflict, '{"selected_ids":["main"]}', ['main'])
    run('顺序变化', rows[::-1], '{"selected_ids":["main"]}', ['supp','main'])
    mapped = [dict(p,id='renamed-'+str(i)) for i,p in enumerate(rows)]
    run('ID重映射', mapped, '{"selected_ids":["renamed-0"]}', ['renamed-0','renamed-1'])
    run('无明确答法', rows, '{"selected_ids":["main"]}', ['main','supp'], '说明情况')
    assert results[-1]['result']['answer_form_rule']['kind'] is None
    for question, kind in [('只输出数值。','数值'),('只输出百分数。','百分数'),('给出名称','none')]:
        _, conf, rule = candidate.answer_request(question, rows, answer)
        assert (rule['kind'] or 'none') == kind
    calls = []
    def baseline(stage, messages, config, used):
        calls.append(stage); assert used == rows
        return {'response':{'choices':[{'message':{'content':'{"answer":"证据不足","citations":[]}'}}]}}
    candidate.execute('说明', rows, 'baseline', answer, selection, baseline)
    assert calls == ['answer']
    value = {'checked_at':datetime.now().astimezone().isoformat(), 'passed':True,
             'generation_calls':0,'uses_only_synthetic_fixtures':True,'items':results,
             'baseline_preserves_input':True,'final_order':'原输入相对顺序',
             'limits':'夹具只检查程序分支，不表示模型能正确定位或回答。'}
    path = folder/'generic-offline-check.json'
    assert not path.exists()
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    print('PASS generic offline checks; 0 generation calls')

if __name__ == '__main__':
    check(Path(sys.argv[1]))
