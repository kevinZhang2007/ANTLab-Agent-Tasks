"""有限明示状态：按局部检查项解析；不推断资格或选择快照。"""
import re

SIGNAL = re.compile(r'缺失|缺少|缺(?!陷)|失败|偏移|未关闭(?:的问题|问题)?|通过')
NUMBER = r'(?:[+＋\-负]?[0-9]+(?:\.[0-9]+)?|[零〇一二两三四五六七八九十百千]+)'
BEFORE_COUNT = re.compile(r'(?<![0-9.＋+\-负])(?P<n>'+NUMBER+r')\s*(?:项|次)\s*$')
AFTER_COUNT = re.compile(r'^\s*(?:(?:次数|数量|数目|计数|总数)\s*(?:为|是|[:：=])?\s*|(?:为|是|[:：=])\s*)(?P<n>'+NUMBER+r')\s*(?:项|次)?\s*$')
PASS_COUNT = re.compile(r'(?<![0-9.＋+\-负])(?P<n>'+NUMBER+r')\s*项\s*(?:检查)?\s*$')
PASS_LIMIT = re.compile(r'部分|未全部|未全|不全|尚未全部|其中|项中')
AFTER_ITEMS = re.compile(r'^\s*(?P<n>'+NUMBER+r')\s*(?:项|次)\s*$')
NEGATION = re.compile(r'并非|不是|不存在|没有|未发生|未发现|未见|无|不|未(?!关闭)')
AFTER_NEGATION = re.compile(r'^\s*(?:情况|现象|记录)?\s*(?:不存在|没有|未发生|未发现|未见)\s*$')
UNCERTAIN = re.compile(r'如果|假如|若|是否|可能|或许|未说明|不确定|尚未确认|无法确认|不一定|不能确认|不能排除|无法排除|尚未排除|不代表|不意味着|未证明|超过|至少|至多|约|大概')
SEPARATOR = re.compile(r'但是|然而|不过|并且|但|且|[，,、；;。！？!?\n]')
OTHER_OWNER = re.compile(r'其他候选|另一候选|另一个候选|前者|后者')
DIGITS = dict(zip('零〇一二两三四五六七八九','001223456789'))


def parse_integer(text):
    if text.isascii() and text.isdigit():
        return int(text)
    if len(text) == 1 and text in DIGITS:
        return int(DIGITS[text])
    if re.fullmatch(r'[一二三四五六七八九]?十[一二三四五六七八九]?', text):
        left, right = text.split('十')
        return (int(DIGITS[left]) if left else 1)*10 + (int(DIGITS[right]) if right else 0)
    return None


def clause_bounds(text, start, end):
    left = max(text.rfind(c, 0, start) for c in '；。;') + 1
    right = min((p for c in '；。;' if (p := text.find(c, end)) >= 0), default=len(text))
    return left, right+1 if right < len(text) else right


def item_spans(text):
    start = 0
    for separator in SEPARATOR.finditer(text):
        if separator.start() > start:
            yield start, separator.start()
        start = separator.end()
    if start < len(text):
        yield start, len(text)


def scope(text, start, end):
    return {'start': start, 'end': end, 'quote': text[start:end]}


def inspect_item(text, start, end):
    phrase = text[start:end]
    signals = list(SIGNAL.finditer(phrase))
    events = []
    for signal in signals:
        token = signal.group()
        prefix, suffix = phrase[:signal.start()], phrase[signal.end():]
        before = (PASS_COUNT if token == '通过' else BEFORE_COUNT).search(prefix)
        after = AFTER_COUNT.fullmatch(suffix) or AFTER_ITEMS.fullmatch(suffix)
        counts = [(before, start), (after, start+signal.end())]
        quantities = []
        for match, offset in counts:
            if match:
                quantities.append({**scope(text, offset+match.start(), offset+match.end()),
                                   'number_start': offset+match.start('n'),
                                   'number_end': offset+match.end('n'), 'raw': match['n'],
                                   'value': parse_integer(match['n']),
                                   'ownership': 'current_check_item',
                                   'quantity_kind': 'passed_check_count' if token == '通过' else 'defect_count',
                                   'item_scope': scope(text, start, end)})
        # 否定只在本项内查找；多重否定、否定精确数量不作反向推断。
        prefix_negatives = list(NEGATION.finditer(prefix))
        negatives = [scope(text, start+m.start(), start+m.end()) for m in prefix_negatives]
        loose_prefix_negation = any(m.group() in {'不', '未'} and m.end() != (before.start() if before else len(prefix))
                                    for m in prefix_negatives)
        post_negative = AFTER_NEGATION.fullmatch(suffix)
        suffix_negatives = list(NEGATION.finditer(suffix))
        if post_negative:
            negatives.append(scope(text, start+signal.end()+post_negative.start(), end))
        else:
            negatives.extend(scope(text, start+signal.end()+m.start(), start+signal.end()+m.end()) for m in suffix_negatives)
        negation_scope = {**scope(text, start, end), 'markers': negatives} if negatives else None
        quantity = quantities[0] if len(quantities) == 1 else None
        value = quantity['value'] if quantity else None
        status, category, reason = 'unknown', 'unparsed', 'unparsed_check_item'
        metric = token == '失败' and re.match(r'率|概率|风险|定义|规则|要求', suffix)
        malformed_quantity = bool(re.search(r'[0-9零〇一二两三四五六七八九十]|次数|数量|数目|计数|总数', suffix)) and not after
        unowned_prefix_quantity = bool(re.search(NUMBER, prefix)) and not before
        if len(signals) != 1:
            reason = 'multiple_predicates_without_reliable_scope'
        elif UNCERTAIN.search(phrase) or metric:
            reason = 'conditional_uncertain_or_metric'
        elif token == '通过' and PASS_LIMIT.search(phrase):
            reason = 'partial_or_not_all_pass_not_generalized'
        elif len(quantities) > 1 or (quantity and value is None) or malformed_quantity or unowned_prefix_quantity:
            reason = 'quantity_not_reliably_parsed_or_owned'
        elif loose_prefix_negation or (suffix_negatives and not post_negative):
            reason = 'negation_scope_not_reliably_parsed'
        elif negatives:
            if len(negatives) != 1 or quantity:
                reason = 'nested_negation_or_negated_exact_quantity'
            elif token == '通过':
                reason = 'negative_pass_not_assumed_failure'
            else:
                status, category, reason = 'explicit_absence', 'explicit_negation', 'local_explicit_negation'
        elif quantity and value == 0:
            if token != '通过':
                status, category, reason = 'explicit_absence', 'explicit_zero_quantity', 'local_explicit_zero'
            else:
                reason = 'zero_pass_not_assumed_failure'
        elif token == '通过':
            status, category, reason = 'explicit_pass', 'positive_presence', 'literal_pass_only'
        elif quantity and value > 0:
            status, category, reason = 'explicit_defect', 'positive_presence', 'local_nonzero_quantity'
        elif token.startswith('缺') or token == '失败':
            status, category, reason = 'explicit_defect', 'positive_presence', 'literal_missing_or_failure'
        else:
            reason = 'quantity_not_explicit'
        events.append({'status': status, 'expression_class': category, 'rule': reason,
                       'trigger': token, 'trigger_start': start+signal.start(),
                       'trigger_end': start+signal.end(), 'description_quote': phrase,
                       'description_start': start, 'description_end': end,
                       'negation_scope': negation_scope, 'quantity_scope': quantities,
                       'unparsed_quantity_scope': scope(text, start, end) if malformed_quantity or unowned_prefix_quantity else None,
                       'quantity_text': quantity['raw'] if quantity else None, 'quantity': value,
                       'pass_scope': 'stated_local_checks_only' if status == 'explicit_pass' else None,
                       'overall_eligibility_not_inferred': True,
                       'condition_context_not_semantically_parsed': True})
    return events


def inspect_explicit_states(passages, candidates):
    occurrences = []
    for candidate in candidates:
        for source in candidate['sources']:
            index = source['passage_index']
            passage = passages[index]
            start, end = source['start'], source['end']
            if passage['id'] != source['passage_id'] or not (0 <= start < end <= len(passage['text'])) or passage['text'][start:end] != candidate['snapshot']:
                raise ValueError('候选位置或来源不一致')
            left, right = clause_bounds(passage['text'], start, end)
            occurrences.append({'snapshot': candidate['snapshot'], 'passage_index': index,
                                'passage_id': passage['id'], 'candidate_start': start,
                                'candidate_end': end, 'start': left, 'end': right})
    result = []
    for occurrence in occurrences:
        text = passages[occurrence['passage_index']]['text']
        left, right = occurrence['start'], occurrence['end']
        owners = [o for o in occurrences if o['passage_index'] == occurrence['passage_index'] and o['start'] == left and o['end'] == right]
        description_start = occurrence['candidate_end']
        description = text[description_start:right]
        row = {**occurrence, 'quote': text[left:right], 'events': [], 'unparsed_content': [],
               'qualification_not_checked': True, 'unclosed_count_not_defaulted_to_zero': True}
        if len(owners) != 1 or OTHER_OWNER.search(description):
            row.update(observed_state='unknown', association_reason='multiple_or_other_candidate_in_clause')
            row['unparsed_content'].append({**scope(text, description_start, right), 'reason': '归属不可靠'})
            result.append(row)
            continue
        for start, end in item_spans(description):
            start, end = start+description_start, end+description_start
            events = inspect_item(text, start, end)
            for event in events:
                event.update(quote=text[left:right], start=left, end=right)
            row['events'].extend(events)
            if not events or any(e['status'] == 'unknown' for e in events):
                row['unparsed_content'].append({**scope(text, start, end), 'reason': '没有可靠明示状态或作用范围不确定'})
        statuses = {e['status'] for e in row['events']}
        row['observed_state'] = ('explicit_defect' if 'explicit_defect' in statuses else
                                 'unknown' if 'unknown' in statuses or not statuses else
                                 'explicit_pass_only' if 'explicit_pass' in statuses else 'explicit_absence_only')
        result.append(row)
    return result
