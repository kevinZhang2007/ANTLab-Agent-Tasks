"""仅从当前question/text派生正文编号enum；不判断哪个编号正确。"""
import copy
import re

IDENTIFIER = re.compile(r'(?<![A-Za-z0-9_])(?=[A-Za-z0-9]*[A-Za-z])(?=[A-Za-z0-9]*[0-9])[A-Za-z0-9]+(?![A-Za-z0-9_])')

def constrain_body_identifiers(question, passages, original_schema):
    occurrences = []
    values = []
    for index, passage in enumerate(passages):
        text = passage['text']
        for match in IDENTIFIER.finditer(text):
            value = match.group(0)
            occurrences.append({'passage_index': index, 'value': value, 'start': match.start(), 'end': match.end()})
            if value not in values:
                values.append(value)
    enabled = bool(re.search(r'只输出[^。！？\n]*编号[。.!！\s]*$', question)) and bool(values)
    schema = copy.deepcopy(original_schema)
    if enabled:
        schema['properties']['answer']['enum'] = values + ['证据不足']
    return schema, {'enabled': enabled, 'values': values, 'occurrences': occurrences,
                    'position_unit': 'Python Unicode字符，start含/end不含',
                    'identifier_definition': '完整连续ASCII英数词，至少一个字母和一个数字；不按前缀或语义过滤。'}
