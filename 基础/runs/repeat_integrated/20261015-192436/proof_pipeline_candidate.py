"""独立完整入口：引用证明与比例计算独立保存，最终输出明确标记来源。"""
import copy
import hashlib
import inspect
import json
import time
from pathlib import Path
import scope_candidate as base
import general_citation_proof as proof
import ratio_calculation_proof as ratio
import difference_calculation_proposal as difference

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
    install(proof.snapshot, 'audit_occurrences', 'proof_scope_identity_check')
    install(proof.snapshot, 'constrain_revised_roles', 'proof_type_source_check')
    install(proof.snapshot, 'requirements', 'positive_release_requirements')
    install(proof, 'linked_pairs', 'proof_visible_pair_and_scope_check')
    install(proof, 'difference', 'decimal_difference_proof')
    install(proof, 'selection', 'qualification_selection_proof')
    install(proof, 'prove_answer', 'positive_proof_and_citation_assembly')
    install(ratio, 'propose', 'ratio_calculation_proposal')
    install(difference, 'propose', 'difference_calculation_proposal')
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
            try:
                parsed = json.loads(result['raw_answer'])
                valid = (isinstance(parsed, dict) and set(parsed)=={'answer','citations'}
                    and isinstance(parsed['answer'], str) and isinstance(parsed['citations'], list)
                    and all(isinstance(i,str) for i in parsed['citations']))
            except (ValueError, TypeError):
                valid = False
            if valid:
                result['proof_record'] = proof.prove_answer(question, result['used_passages'], result['raw_answer'], universe=result['original_passages'])
                result['derived_response'] = copy.deepcopy(result['proof_record']['derived_response'])
            else:
                result['proof_record'] = {'proof_established': False, 'proof_status': 'refused',
                    'proof_kind': None, 'reason': 'invalid_raw_answer_quality_failure', 'derived_response': None}
            result['derived_response_kind'] = ('local_rule_citation_assembly_not_model_output'
                if result['derived_response'] is not None else 'not_derived_original_result_preserved')
            if result['derived_response'] is not None:
                assert result['derived_response']['answer'] == json.loads(result['raw_answer'])['answer']
        else:
            result['proof_not_run_reason'] = 'upstream_selection_output_failure'
            result['proof_record'] = {'proof_established': False, 'proof_status': 'not_run',
                'proof_kind': None, 'reason': 'upstream_selection_output_failure', 'derived_response': None}
            result['raw_response'] = None
        result['proof'] = copy.deepcopy(result['proof_record'])
        final_passages = result.get('used_passages', [])
        final_ids = {p['id'] for p in final_passages}
        originals = result['original_passages']
        extra = [p for p in originals if p['id'] not in final_ids]
        facts = []
        if result['derived_response'] is not None:
            record = result['proof_record']
            if record['proof_kind'] == 'snapshot':
                facts = position_records(record['snapshot_proof']['conditions'])
            else:
                facts = position_records([t for t in record['trace']
                    if t['stage'] in ('difference_proof', 'selection_sources')])
            sources = {p['id']:p['text'] for p in final_passages}
            assert facts and all(e['passage_id'] in sources and sources[e['passage_id']][e['start']:e['end']]==e['quote'] for e in facts)
            assert set(result['derived_response']['citations']) <= final_ids
        result['proof_fact_sources'] = facts
        result['reference_derived_response'] = copy.deepcopy(result['derived_response'])
        if result['status']=='completed' and valid:
            result['ratio_proof'] = ratio.propose(question, final_passages, result['raw_answer'], universe=originals)
        else:
            result['ratio_proof'] = {'applicable': False, 'status':'not_run', 'proof_established': False,
                'reason':'upstream_selection_or_raw_format_failure','proposed_response':None,'answer_changed':False}
        result['proposed_response'] = copy.deepcopy(result['ratio_proof']['proposed_response'])
        ratio_facts = position_records({k:result['ratio_proof'][k] for k in
            ['definition','denominator','category_counts','statistical_scope','category_assignment','numerator'] if k in result['ratio_proof']})
        sources = {p['id']:p['text'] for p in final_passages}
        assert all(e['passage_id'] in sources and sources[e['passage_id']][e['start']:e['end']]==e['quote'] for e in ratio_facts)
        if result['proposed_response'] is not None:
            assert set(result['proposed_response']['citations'])<=final_ids
        result['ratio_fact_sources'] = ratio_facts
        result['ratio_proposed_response'] = copy.deepcopy(result['ratio_proof']['proposed_response'])
        if result['status']=='completed' and valid:
            result['difference_proposal'] = difference.propose(question, final_passages, result['raw_answer'], universe=originals)
        else:
            result['difference_proposal'] = {'applicable':False,'status':'not_run','proof_established':False,
                'reason':'upstream_selection_or_raw_format_failure','proposed_response':None,'trace':[],'answer_changed':False}
        assert not(result['ratio_proposed_response'] is not None and result['difference_proposal']['proposed_response'] is not None)
        difference_facts = position_records([t for t in result['difference_proposal']['trace'] if t.get('stage')=='difference_proof'])
        assert all(e['passage_id'] in sources and sources[e['passage_id']][e['start']:e['end']]==e['quote'] for e in difference_facts)
        result['difference_fact_sources'] = difference_facts
        if result['difference_proposal']['proposed_response'] is not None:
            result['proposed_response'] = copy.deepcopy(result['difference_proposal']['proposed_response'])
            assert set(result['proposed_response']['citations'])<=final_ids
        result['rule_proofs'] = {'reference_proof':copy.deepcopy(result['proof_record']), 'ratio_proof':copy.deepcopy(result['ratio_proof']), 'difference_proof':copy.deepcopy(result['difference_proposal'])}
        result['material_scope'] = {
            'model_final_input_passages': copy.deepcopy(final_passages),
            'audit_only_original_visible_passages': copy.deepcopy(extra),
            'model_final_input_ids': [p['id'] for p in final_passages],
            'original_visible_ids': [p['id'] for p in originals],
            'audit_only_ids': [p['id'] for p in extra],
            'proof_fact_and_derived_citation_ids_subset_of_final_model_input': True,
            'policy': '额外原始可见资料仅供范围、实体和唯一性审计；不得将其当作最终回答模型输入或派生事实来源。定位阶段输入另存selection_passages。'}
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
        if result['proposed_response'] is not None:
            result['actual_final_output'] = copy.deepcopy(result['proposed_response'])
            result['actual_final_raw_content'] = None
            if result['difference_proposal']['proposed_response'] is not None:
                result['actual_final_output_source'] = ('local_rule_difference_new_answer' if result['difference_proposal']['answer_changed'] else 'local_rule_difference_confirmed_answer_and_citations')
            else:
                result['actual_final_output_source'] = ('local_rule_ratio_new_answer' if result['ratio_proof']['answer_changed'] else 'local_rule_ratio_confirmed_answer_and_citations')
        result['answer_changed_from_model_raw'] = bool(result['actual_final_output'] is not None and raw_parsed is not None
            and result['actual_final_output']['answer'] != raw_parsed.get('answer'))
        result['system_derived_response'] = copy.deepcopy(result['actual_final_output']) if result['actual_final_output_source']!='raw_model_response' else None
        result['output_policy'] = '差值或比例证明成立采用独立计算建议；否则引用证明；否则原答。原始、计算和引用组装分别保留。'
        save(copy.deepcopy(result))
        return result
    finally:
        for owner, name, original in reversed(hooks):
            setattr(owner, name, original)
