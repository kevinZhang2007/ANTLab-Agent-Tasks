"""复用现有模型/页面生命周期；只接入本轮独立候选。"""
import sys,json
from pathlib import Path
import launch,server
from runtime import load,write,HERE
from short_enum_candidate import Engine,offline_checks,QUERY_PROMPT,ANSWER_PROMPT

class Handler(server.Handler):
    def do_GET(self):
        if self.path=='/':
            text=(HERE/'index.html').read_text(encoding='utf-8')
            text=text.replace('<h1>进阶A：同章节邻段补全</h1>','<h1>进阶A：短判断与输入ID约束开发候选</h1><p>当前候选：共同查询提示＋短判断＋动态ID enum；检索公式和邻段规则不变。引用核验不是语义支持。</p>')
            text=text.replace('run_id:a.raw_record.run_id,raw_content:','source_validation:a.source_validation,run_id:a.raw_record.run_id,raw_content:')
            raw=text.replace('__TOKEN__',server.TOKEN).encode();self.send_response(200);self.send_header('Content-Type','text/html;charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
        return super().do_GET()

def main():
    folder=Path(sys.argv[sys.argv.index('--out')+1]).resolve()
    assert load(folder/'candidate-offline-checks.json')['passed']
    assert load(folder/'native-id-enum-validation.json')['passed']
    assert offline_checks()['passed']
    plan=load(folder/'candidate-plan.json')
    original_write=launch.write
    def record(path,value):
        if Path(path).name=='development-plan.json':
            value.update(kind='本轮独立开发整体候选，非正式冻结',candidate_plan='candidate-plan.json',actual_query_prompt=QUERY_PROMPT,actual_answer_prompt=ANSWER_PROMPT,answer_schema='按每侧实际输入ID派生enum；空输入evidence maxItems=0',baseline_cumulative=561,A_used_before=27,A_remaining_before=27,selection=plan['selection'],changes=plan['changes'])
        return original_write(path,value)
    launch.Engine=Engine;launch.Handler=Handler;launch.write=record
    launch.main()

if __name__=='__main__':main()
