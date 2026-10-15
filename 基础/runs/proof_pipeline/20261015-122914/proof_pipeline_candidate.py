"""仅快照题的独立完整入口；证明通过才派生引用，保留原始响应。"""
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
    if target_role(question) != ('other', '快照'):
        raise ValueError('snapshot_qualification_branch_only_no_generation')
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
                    'timers_may_include_nested_operations': True})
        setattr(owner, name, wrapped)
        hooks.append((owner, name, original))
    install(base.student, 'improve', 'lexical_ordering')
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
            result['proof_record'] = proof.prove_answer(question, result['used_passages'], result['raw_answer'], universe=result['original_passages'])
            result['derived_response'] = copy.deepcopy(result['proof_record']['final_response'])
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
        save(copy.deepcopy(result))
        return result
    finally:
        for owner, name, original in reversed(hooks):
            setattr(owner, name, original)
