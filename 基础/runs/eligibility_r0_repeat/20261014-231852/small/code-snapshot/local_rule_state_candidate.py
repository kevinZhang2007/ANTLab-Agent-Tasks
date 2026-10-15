"""独立local_rule附加输入；不改变原请求的提示词、枚举或原资料。"""
import copy
import json

NOTICE = ('local_rule只识别原文明示状态，不判断整体资格。unknown不能当通过，'
          '无缺陷不能当合格；局部通过不表示全部资格满足，未明示的未关闭问题数量不能默认零。'
          '这些规则检查不能替代完整原文，不删除候选、不指定答案，不自动补引用。')


def attach_rule_states(original_request, states, checker_sha256):
    request = copy.deepcopy(original_request)
    assert len(request['messages']) == 2 and request['messages'][1]['role'] == 'user'
    payload = json.loads(request['messages'][1]['content'])
    assert 'local_rule_states' not in payload
    payload['local_rule_states'] = {'judgment_source': 'local_rule', 'notice': NOTICE,
                                  'checker_sha256': checker_sha256, 'items': copy.deepcopy(states)}
    request['messages'][1]['content'] = json.dumps(payload, ensure_ascii=False, indent=2)
    removed = copy.deepcopy(request)
    decoded = json.loads(removed['messages'][1]['content'])
    decoded.pop('local_rule_states')
    assert decoded == json.loads(original_request['messages'][1]['content'])
    removed['messages'][1]['content'] = original_request['messages'][1]['content']
    assert removed == original_request
    return request
