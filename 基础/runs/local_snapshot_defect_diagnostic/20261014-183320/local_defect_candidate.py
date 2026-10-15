"""局部原句诊断；只核验连续摘录来源，不自动判断缺陷。"""
import json
import evidence_first_candidate as evidence
REVIEW_PROMPT = '只看下面的原文，该候选是否明确存在检查缺陷？\n返回JSON：\n{"has_explicit_defect":true或false,\n "quote":"对应连续原文；没有则为空字符串"}。\n只判断明示缺陷，不判断整体资格，不推断未提到的条件。'
REVIEW_SCHEMA = {'type': 'object', 'properties': {'has_explicit_defect': {'type': 'boolean'}, 'quote': {'type': 'string'}}, 'required': ['has_explicit_defect', 'quote'], 'additionalProperties': False}

def prepare_local_messages(clause):
    payload={k:clause[k] for k in ('snapshot','passage_id','start','end','text')}
    return [{'role':'system','content':REVIEW_PROMPT},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}]

def check_local(raw, passages):
    try:
        parsed=json.loads(raw,object_pairs_hook=evidence.unique_fields)
        if not isinstance(parsed,dict) or set(parsed)!={'has_explicit_defect','quote'} or type(parsed['has_explicit_defect']) is not bool or not isinstance(parsed['quote'],str):
            raise ValueError('字段或类型不合法')
        quote=parsed['quote']
        return {'json_object_complete':True,'nonempty_quote_continuous':bool(quote) and quote in passages[0]['text'],
                'quote_empty':not quote,'defect_truth_verified':False}
    except (ValueError,TypeError) as error:
        return {'json_object_complete':False,'error':str(error),'defect_truth_verified':False}
