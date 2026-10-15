"""独立完整入口；仅快照分支证明通过才派生引用，其他输入保留原始响应。"""
import copy
import hashlib
import inspect
import json
import time
from pathlib import Path
import scope_candidate as base
import eligibility_proof_checker as proof
from typed_enum_role_revision import target_role

student = base.student
selection = base.selection
constrain_schema = base.constrain_schema
answer_request = base.answer_request


def position_records(value):
    records = []
    if isinstance(value, dict):
        if all(k in value for k in ['passage_id', 'start', 'end', 'quote']):
            start = value.get('statement_start', value['start'])
            end = value.get('statement_end', value['end'])
            records.append({'passage_id': value['passage_id'], 'start': start, 'end': end, 'quote': value['quote']})
        for item in value.values():
            records.extend(position_records(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            records.extend(position_records(item))
    unique = {}
    for record in records:
        unique[(record['passage_id'], record['start'], record['end'], record['quote'])] = record
    return list(unique.values())


def execute(question, passages, variant, answer_config, selection_config, dispatch=None, save=None):
    start = time.perf_counter()
    save = save or (lambda value: None)
    events = []
    hooks = []
    seen = set()
    inputs = [{'passage_id': p['id'], 'start': 0, 'end': len(p['text']), 'quote': p['text'], 'role': '完整输入位置非语义支持标签'} for p in passages]

    def install(owner, name, label):
        key = (id(owner), name)
        if key in seen:
            return
        seen.add(key)
        original = getattr(owner, name)
        path = Path(inspect.getsourcefile(original))
        version = {'file': path.name, 'function': original.__name__,
                   'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        def wrapped(*args, **kwargs):
            begin = time.perf_counter()
            status = 'ok'
            output = None
            try:
                output = original(*args, **kwargs)
                return output
            except Exception:
                status = 'exception'
                raise
            finally:
                events.append({'judgment_source': 'local_rule', 'operation': label,
                    'rule_version': version, 'elapsed_seconds': time.perf_counter()-begin,
                    'status': status, 'original_text_positions': position_records(output),
                    'relative_start_seconds': begin-start, 'relative_end_seconds': time.perf_counter()-start,
                    'position_note': '无直接摘录的格式/ID校验不制造原文证据，完整输入位置另存；资格证据以proof_record逐条件摘录为准。',
                    'timers_may_include_nested_operations': True})
        setattr(owner, name, wrapped)
        hooks.append((owner, name, original))
    install(base.student, 'improve', 'lexical_ordering')
    install(base.selection, 'validate_selection', 'selection_id_validation')
    install(base.selection, 'select_original_passages', 'validated_original_passage_selection')
    install(base.previous, 'constrain_schema', 'generic_answer_form_constraint')
    install(base.completion, 'complete_passages', 'direct_supplement_relation')
    install(base, 'audit_occurrences', 'scope_identity_occurrence_check')
    install(base, 'constrain_revised_roles', 'type_enum_constraint')
    install(base.checker, 'inspect_explicit_states', 'explicit_state_check')
    install(base.exclusion, 'constrain_eligibility', 'qualification_exclusion')
    install(base, 'answer_request', 'answer_schema_and_qualification')
    install(proof, 'audit_occurrences', 'proof_scope_identity_check')
    install(proof, 'constrain_revised_roles', 'proof_type_source_check')
    install(proof, 'requirements', 'positive_release_requirements')
    install(proof, 'prove_answer', 'positive_proof_and_citation_assembly')
    try:
        def progress(value):
            save({**value, 'local_rule_processing': copy.deepcopy(events),
                  'local_rule_input_positions': inputs,
                  'raw_response_preserved': True, 'derived_response': None})
        result = base.execute(question, passages, variant, answer_config, selection_config, dispatch, progress)
        result['model_flow_end_to_end_seconds'] = result['end_to_end_seconds']
        result['derived_response'] = None
        if result['status'] == 'completed':
            result['raw_response'] = copy.deepcopy(result['stages'][-1]['response'])
            if target_role(question) == ('other', '快照'):
                result['proof_record'] = proof.prove_answer(question, result['used_passages'], result['raw_answer'], universe=result['original_passages'])
                result['derived_response'] = copy.deepcopy(result['proof_record']['final_response'])
            else:
                result['proof_record'] = {'proof_established': False, 'proof_status': 'not_applicable',
                    'reason': 'question_not_supported_snapshot_branch', 'final_response': None}
                result['proof_not_run_reason'] = 'question_not_supported_snapshot_branch'
            result['derived_response_kind'] = ('local_rule_citation_assembly_not_model_output'
                if result['derived_response'] is not None else 'not_derived_original_result_preserved')
            if result['derived_response'] is not None:
                assert result['derived_response']['answer'] == json.loads(result['raw_answer'])['answer']
        else:
            result['proof_not_run_reason'] = 'upstream_selection_output_failure'
        result['local_rule_processing'] = copy.deepcopy(events)
        result['local_rule_input_positions'] = inputs
        result['end_to_end_seconds'] = time.perf_counter()-start
        result['raw_response_preserved'] = True
        intervals = sorted((e['relative_start_seconds'], e['relative_end_seconds']) for e in events)
        merged = []
        for left, right in intervals:
            if merged and left <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], right)
            else:
                merged.append([left, right])
        result['timing_summary'] = {
            'selection_seconds': sum(s.get('elapsed_seconds', 0) for s in result['stages'] if s['stage']=='selection'),
            'answer_seconds': sum(s.get('elapsed_seconds', 0) for s in result['stages'] if s['stage']=='answer'),
            'tracked_local_rule_wall_seconds': sum(right-left for left,right in merged),
            'rule_timing_note': '已跟踪规则调用区间取并集，嵌套不重复相加；端到端另含模板容量、日志和其他处理。',
            'end_to_end_seconds': result['end_to_end_seconds']}
        try:
            raw_parsed = json.loads(result.get('raw_answer', ''))
        except (ValueError, TypeError):
            raw_parsed = None
        result['actual_final_output'] = copy.deepcopy(result['derived_response'] if result['derived_response'] is not None else raw_parsed)
        result['actual_final_raw_content'] = result.get('raw_answer') if result['derived_response'] is None else None
        result['actual_final_output_source'] = 'local_rule_citation_assembly' if result['derived_response'] is not None else 'raw_model_response'
        save(copy.deepcopy(result))
        return result
    finally:
        for owner, name, original in reversed(hooks):
            setattr(owner, name, original)
