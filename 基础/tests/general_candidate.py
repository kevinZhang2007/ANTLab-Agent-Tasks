"""独立通用入口：原资料回答，或重新定位并补入唯一直接补页。"""
import argparse
import copy
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'starter'))
import student
from provider import call_model
import two_step_candidate as selection
import two_step_linked_candidate as completion
from answer_form_candidate import constrain_schema


def answer_request(question, passages, config):
    conf = copy.deepcopy(config)
    schema, rule = constrain_schema(
        question, conf['parameters']['response_format']['json_schema']['schema'])
    conf['parameters']['response_format']['json_schema']['schema'] = schema
    return student.prepare_messages(question, copy.deepcopy(passages)), conf, rule


def execute(question, passages, variant, answer_config, selection_config, dispatch=None, save=None):
    """dispatch/save供记录层接入；本函数不读取题库、答案或历史选择。"""
    if variant not in ('baseline', 'improved'):
        raise ValueError('unknown_variant')
    original = copy.deepcopy(passages)
    if len({p['id'] for p in original}) != len(original):
        raise ValueError('duplicate_input_id')
    dispatch = dispatch or (lambda stage, messages, config, used: call_model(messages, config))
    save = save or (lambda value: None)
    start = time.perf_counter()
    result = {'variant': variant, 'question': question, 'original_passages': original,
              'stages': [], 'status': 'pending', 'selection_is_fresh': variant == 'improved'}
    save(copy.deepcopy(result))
    used = original
    if variant == 'improved':
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
                          end_to_end_seconds=time.perf_counter() - start)
            save(copy.deepcopy(result))
            return result
        chosen, trace = completion.complete_passages(question, ordered, validation)
        # 最终段落以当前原输入相对顺序呈现，不采用模型返回ID的顺序。
        included = {p['id'] for p in chosen}
        used = [copy.deepcopy(p) for p in original if p['id'] in included]
        result.update(association_trace=trace, added_ids=[r['supplement_id'] for r in trace if r['added']])
    messages, config, rule = answer_request(question, used, answer_config)
    result.update(used_passages=used, answer_form_rule=rule, answer_config=config)
    save(copy.deepcopy(result))
    answer = dispatch('answer', messages, config, used)
    result['stages'].append(answer)
    result.update(status='completed', raw_answer=answer['response']['choices'][0]['message'].get('content', ''),
                  end_to_end_seconds=time.perf_counter() - start)
    save(copy.deepcopy(result))
    return result


def main():
    parser = argparse.ArgumentParser(description='独立本机入口；服务须先启动，每次运行会产生真实请求。')
    parser.add_argument('--input', required=True, help='只含question/passages的JSON文件')
    parser.add_argument('--answer-config', required=True)
    parser.add_argument('--selection-config', required=True)
    parser.add_argument('--variant', choices=['baseline', 'improved'], required=True)
    parser.add_argument('--output', required=True, help='新记录文件；已有文件拒绝覆盖')
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        parser.error('输出已存在，不覆盖')
    load = lambda path: json.loads(Path(path).read_text(encoding='utf-8-sig'))
    payload = load(args.input)
    if set(payload) != {'question', 'passages'}:
        parser.error('输入只允许question/passages')
    def save(value):
        output.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    execute(payload['question'], payload['passages'], args.variant,
            load(args.answer_config), load(args.selection_config), save=save)


if __name__ == '__main__':
    main()
