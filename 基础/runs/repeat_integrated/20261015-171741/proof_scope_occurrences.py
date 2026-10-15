"""先核对显式范围，再确认同范围身份；仅合并全文一致的可靠记录复本。"""
import copy
import re
import direct_reference_candidate as relation


def explicit_scope(text):
    # 范围以“项目/版本”语境识别，不限定某个项目名或版本前缀。
    result = copy.deepcopy(relation.describe(text)['scope'])
    versions = re.findall(r'(?<![A-Za-z0-9_])(?:[A-Za-z][A-Za-z0-9_.-]*|[0-9]+(?:\.[0-9]+)*)版本', text)
    projects = re.findall(r'[一-鿿A-Za-z0-9]+项目(?=(?:[A-Za-z][A-Za-z0-9_.-]*版本|在?[0-9]{4}-|的|[，,:：]))', text)
    result['version'] = sorted(set(versions))
    result['project'] = sorted(set(result['project']+projects))
    return result


def scope_status(expected, actual):
    details = []
    conflict = False
    unknown = not any(expected.values())
    for key, required in expected.items():
        values = actual[key]
        status = 'not_specified_in_question'
        if required:
            if len(required) != 1 or len(values) > 1:
                status = 'unknown_multiple_scope_values'; unknown = True
            elif not values:
                status = 'unknown_missing_scope'; unknown = True
            elif values != required:
                status = 'explicit_scope_conflict'; conflict = True
            else:
                status = 'explicit_scope_match'
        details.append({'field': key, 'question': required, 'source': values, 'status': status})
    return ('conflict' if conflict else 'unknown' if unknown else 'matched'), details


def audit_occurrences(question, passages, values, visible_ids=()):
    from project_scope_resolution import resolve_question_scope
    expected, resolution = resolve_question_scope(question, passages, explicit_scope(question))
    if resolution['status'] != 'resolved':
        refused = {v: {'value': v, 'eligible_for_exclusion_check': False,
            'reason': 'question_project_entity_unknown', 'all_occurrences': [],
            'target_occurrences': [], 'unknown_occurrences': []} for v in values if v != '证据不足'}
        return copy.deepcopy(passages), refused, {'question_scope': expected,
            'question_project_resolution': resolution, 'removed_only_from_rule_analysis': [],
            'original_model_passages_not_changed': True, 'unknown_scope_passages_remain_in_analysis': True}
    contexts = [relation.describe(p['text']) for p in passages]
    audits = {}
    duplicates = {}
    for value in values:
        if value == '证据不足':
            continue
        entries = []
        for index, (passage, context) in enumerate(zip(passages, contexts)):
            for match in re.finditer(r'(?<![A-Za-z0-9_-])'+re.escape(value)+r'(?![A-Za-z0-9_-])', passage['text']):
                source_scope = explicit_scope(passage['text'])
                status, fields = scope_status(expected, source_scope)
                declarations = context['declarations']
                identity = [(d['object_type'], d['object_name'], d['code']) for d in declarations]
                statement = relation.extraction.statement(passage['text'], match.start(), match.end())
                entries.append({'value': value, 'passage_id': passage['id'], 'passage_index': index,
                    'source': passage['source'], 'start': match.start(), 'end': match.end(),
                    'scope_status': status, 'scope_fields': fields, 'source_scope': source_scope,
                    'quote': statement['text'], 'statement_start': statement['start'], 'statement_end': statement['end'],
                    'reliable_declarations': declarations, 'identity': identity,
                    'not_a_competitor': status == 'conflict'})
        target = [e for e in entries if e['scope_status'] == 'matched']
        uncertain = [e for e in entries if e['scope_status'] == 'unknown']
        allowed = not uncertain and bool(target)
        reason = 'single_target_scope_occurrence' if len(target) == 1 else 'no_target_scope_occurrence'
        if uncertain:
            reason = 'unknown_scope_occurrence_keep'
        elif len(target) > 1:
            identities = {tuple(tuple(i) for i in e['identity']) for e in target}
            all_single = all(len(e['identity']) == 1 for e in target)
            full_texts = {passages[e['passage_index']]['text'] for e in target}
            different_passages = len({e['passage_index'] for e in target}) == len(target)
            if all_single and len(identities) == 1 and len(full_texts) == 1 and different_passages:
                representative = next((e for e in target if e['passage_id'] in visible_ids), target[0])
                for entry in target:
                    if entry['passage_id'] != representative['passage_id']:
                        duplicates[entry['passage_id']] = representative['passage_id']
                reason = 'same_scoped_declaration_and_identical_full_text_copy'
            else:
                allowed = False
                reason = ('multiple_reliable_objects_keep' if len(identities) > 1 else
                          'same_scope_description_or_identity_not_confirmed_keep')
        audits[value] = {'value': value, 'all_occurrences': entries, 'target_occurrences': target,
                         'unknown_occurrences': uncertain, 'eligible_for_exclusion_check': allowed,
                         'reason': reason, 'merging_does_not_prove_real_world_identity': True}
    view = []
    removed = []
    for p, context in zip(passages, contexts):
        status, fields = scope_status(expected, explicit_scope(p['text']))
        reason = ('explicit_scope_conflict' if status == 'conflict' else
                  'confirmed_identical_scoped_record_copy' if p['id'] in duplicates else None)
        if reason:
            removed.append({'passage_id': p['id'], 'reason': reason, 'scope_fields': fields,
                            'duplicate_of': duplicates.get(p['id']), 'text': p['text']})
        else:
            view.append(copy.deepcopy(p))
    return view, audits, {'question_scope': expected, 'question_project_resolution': resolution, 'removed_only_from_rule_analysis': removed,
                         'original_model_passages_not_changed': True,
                         'unknown_scope_passages_remain_in_analysis': True}
