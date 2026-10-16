"""导入、页面语法及失败启动门禁；无模型调用。"""
from pathlib import Path
import argparse,ast,importlib,json,subprocess,sys

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();folder=a.out.resolve();here=Path(__file__).resolve().parent
    output=folder/'import-and-failure-gate.json'
    if output.exists():raise FileExistsError(output)
    report={'generation_calls':0,'passed':False}
    try:
        files=list(here.glob('*.py'))
        for file in files:ast.parse(file.read_text(encoding='utf-8'))
        for module in ['engine','locator','runtime','server','launch','development','preflight','checks','checks_extended']:importlib.import_module(module)
        fixture=folder/'blocked-startup-fixture';fixture.mkdir()
        (fixture/'offline-preflight.json').write_text(json.dumps({'passed':False}),encoding='utf-8')
        command=[sys.executable,'-X','utf8','-B',str(here/'launch.py'),'--out',str(fixture)]
        result=subprocess.run(command,capture_output=True)
        (fixture/'actual.stderr.txt').write_bytes(result.stderr)
        assert result.returncode!=0 and not (fixture/'owned-service.json').exists()
        js=(here/'index.html').read_text(encoding='utf-8').split('<script>',1)[1].split('</script>',1)[0]
        jsfile=folder/'page-syntax.js';jsfile.write_text(js,encoding='utf-8')
        node=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
        syntax=subprocess.run([str(node),'--check',str(jsfile)],capture_output=True)
        (folder/'page-syntax.stderr.txt').write_bytes(syntax.stderr)
        assert syntax.returncode==0
        report.update(passed=True,syntax_files=len(files),imports_ok=True,negative_gate_command=command,negative_gate_exit=result.returncode,owned_service_created=False,javascript_syntax_exit=syntax.returncode)
    except Exception as error:
        report['error']=repr(error);raise
    finally:output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
