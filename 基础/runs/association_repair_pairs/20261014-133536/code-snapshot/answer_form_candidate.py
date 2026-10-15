"""只从当前问题末尾的明确输出要求派生Schema，不处理模型响应。"""
import copy
import re

NUMBER = r'[-+]?([0-9]+([.][0-9]+)?|[.][0-9]+)([eE][-+]?[0-9]+)?'
PATTERNS = {
    '数值': '^(' + NUMBER + '|证据不足)$',
    '百分数': '^(' + NUMBER + '%|证据不足)$',
}

def constrain_schema(question, original_schema):
    schema = copy.deepcopy(original_schema)
    mentioned = [kind for kind in PATTERNS if '只输出' + kind in question]
    match = re.search(r'只输出(数值|百分数)[。.!！\s]*$', question)
    if not match or len(mentioned) != 1:
        return schema, {'kind': None, 'reason': '没有可靠的末尾明确要求或要求冲突；沿用原Schema。'}
    kind = match.group(1)
    schema['properties']['answer']['pattern'] = PATTERNS[kind]
    return schema, {'kind': kind, 'reason': '问题末尾明确只输出' + kind, 'pattern': PATTERNS[kind]}
