"""独立完整流程：新定位、唯一直接补页、答案形式/类型enum及可靠资格排除。"""
import copy
import re
import time
import general_candidate as previous
import direct_reference_candidate as completion
import two_step_candidate as selection
from typed_enum_role_revision import constrain_revised_roles, target_role
import explicit_state_checker as checker
import eligibility_exclusion_candidate as exclusion

student = previous.student
constrain_schema = previous.constrain_schema


def answer_request(question, passages, config, universe=None):
    messages, conf, form = previous.answer_request(question, passages, config)
    schema = conf['parameters']['response_format']['json_schema']['schema']
    schema, types = constrain_revised_roles(question, passages, schema)
    conf['parameters']['response_format']['json_schema']['schema'] = schema
    record = {'answer_form': form, 'type_enum': types, 'qualification_enabled': False,
              'qualification_status': 'not_applicable', 'no_remaining_candidate_qualification': True}
    if target_role(question) != ('other', '快照') or not types['enabled']:
        record['qualification_reason'] = 'question_does_not_explicitly_request_snapshot_identifier'
        return messages, conf, record
    full = copy.deepcopy(passages if universe is None else universe)
    candidates = []
    occurrences = {}
    for value in schema['properties']['answer']['enum']:
        if value == '证据不足':
            continue
        sources = []
        for index, passage in enumerate(full):
            for match in re.finditer(r'(?<![A-Za-z0-9_-])'+re.escape(value)+r'(?![A-Za-z0-9_-])', passage['text']):
                sources.append({'passage_id': passage['id'], 'passage_index': index,
                                'start': match.start(), 'end': match.end()})
        occurrences[value] = sources
        if sources:
            candidates.append({'snapshot': value, 'sources': sources})
    states = checker.inspect_explicit_states(full, candidates)
    audit = exclusion.constrain_eligibility(question, full, schema['properties']['answer']['enum'], states)
    record.update(rule_audit=audit, explicit_states=states)
    if audit['needs_manual_correspondence']:
        record.update(qualification_status='unknown_keep_original', qualification_reason='unresolved_rule_correspondence')
        return messages, conf, record
    visible = {p['id'] for p in passages}
    scope = completion.describe(question)['scope']
    removed = set()
    exclusions = []
    skipped = []
    for decision in audit['decisions']:
        value = decision['candidate']
        if not decision['excluded']:
            skipped.append({'candidate': value, 'reason': decision['reason']})
            continue
        if len(occurrences[value]) != 1:
            skipped.append({'candidate': value, 'reason': 'multiple_occurrences_or_scopes_unknown'})
            continue
        source = next(p for p in full if p['id'] == decision['passage_id'])
        source_scope = completion.describe(source['text'])['scope']
        if any(expected and (not source_scope[key] or source_scope[key] != expected) for key,expected in scope.items()):
            skipped.append({'candidate': value, 'reason': 'question_scope_not_proven_same'})
            continue
        matches = [m for m in decision['matches'] if m['rule']['passage_id'] in visible and decision['passage_id'] in visible]
        if not matches:
            skipped.append({'candidate': value, 'reason': 'required_rule_or_candidate_not_in_actual_final_input'})
            continue
        removed.add(value)
        exclusions.append({'candidate': value, 'matches': matches, 'question_scope': scope, 'source_scope': source_scope})
    original_values = schema['properties']['answer']['enum']
    new_values = [v for v in original_values if v not in removed]
    assert '证据不足' in new_values
    schema['properties']['answer']['enum'] = new_values
    record.update(qualification_enabled=bool(removed), qualification_status='exclusions_applied' if removed else 'unknown_keep_original',
                  qualification_reason='only_reliable_current_visible_rule_matches', excluded=exclusions,
                  kept_unknown=skipped, original_enum=original_values, final_enum=new_values)
    return messages, conf, record


def execute(question, passages, variant, answer_config, selection_config, dispatch=None, save=None):
    if variant != 'improved':
        raise ValueError('only_improved_in_this_round')
    original = copy.deepcopy(passages)
    if len({p['id'] for p in original}) != len(original):
        raise ValueError('duplicate_input_id')
    dispatch = dispatch or (lambda stage,messages,config,used: previous.call_model(messages,config))
    save = save or (lambda value: None)
    start = time.perf_counter()
    result = {'variant': variant, 'question': question, 'original_passages': original,
              'stages': [], 'status': 'pending', 'selection_is_fresh': True}
    save(copy.deepcopy(result))
    ordered = student.improve(question, copy.deepcopy(original))
    result['selection_passages'] = ordered
    selected = dispatch('selection', selection.prepare_selection_messages(question, ordered),
                        copy.deepcopy(selection_config), ordered)
    result['stages'].append(selected)
    raw = selected['response']['choices'][0]['message'].get('content', '')
    validation = selection.validate_selection(raw, ordered)
    result.update(raw_selection=raw, selection_validation=validation)
    save(copy.deepcopy(result))
    if not validation['valid']:
        result.update(status='selection_output_failure', answer_not_executed=True,
                      end_to_end_seconds=time.perf_counter()-start)
        save(copy.deepcopy(result))
        return result
    chosen, trace = completion.complete_passages(question, ordered, validation)
    included = {p['id'] for p in chosen}
    used = [copy.deepcopy(p) for p in original if p['id'] in included]
    result.update(association_trace=trace, added_ids=[r['supplement_id'] for r in trace if r['added']])
    messages, conf, rule = answer_request(question, used, answer_config, universe=original)
    result.update(used_passages=used, answer_form_rule=rule, answer_config=conf,
                  eligibility_rule_audit=rule, processing_status='completed_with_explicit_unknown_fallback')
    save(copy.deepcopy(result))
    answer = dispatch('answer', messages, conf, used)
    result['stages'].append(answer)
    result.update(status='completed', raw_answer=answer['response']['choices'][0]['message'].get('content', ''),
                  end_to_end_seconds=time.perf_counter()-start)
    save(copy.deepcopy(result))
    return result
