from pathlib import Path
from datetime import datetime
import subprocess,json,re,hashlib
work=Path(__file__).parent;folder=Path((work/'answer_form_folder.txt').read_text(encoding='utf-8'))
root=Path(r'C:\Users\86186\AppData\Local\ANTLabLocalModel')
records=[]
for kind in ['number','percent']:
 args=[str(root/'llama-b11429/llama-completion.exe'),'-m',str(root/'models/Qwen3-0.6B-Q8_0.gguf'),'-ngl','0','-t','4','-c','512','-b','128','-ub','64','--no-warmup','--no-conversation','--no-display-prompt','-n','0','-p','Synthetic schema compilation only.','--json-schema-file',str(folder/('schema-self-'+kind+'.json')),'-lv','5']
 started=datetime.now().astimezone().isoformat()
 p=subprocess.run(args,capture_output=True,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
 (folder/('native-'+kind+'.stdout.txt')).write_bytes(p.stdout)
 (folder/('native-'+kind+'.stderr.txt')).write_bytes(p.stderr)
 text=(p.stdout+p.stderr).decode('utf-8',errors='replace')
 record={'started_at':started,'arguments':[a.replace(str(root),'%LOCALAPPDATA%/ANTLabLocalModel') for a in args],'returncode':p.returncode,'output_budget':0,'counts_as_generation':False,
  'schema_sha256':hashlib.sha256((folder/('schema-self-'+kind+'.json')).read_bytes()).hexdigest(),
  'fallback_warning':bool(re.search(r'pattern.*not supported|accepting any string|Invalid pattern',text)),
  'grammar_lines':[line for line in text.splitlines() if 'grammar' in line.lower()][:30],
  'performance_lines':[line for line in text.splitlines() if 'tokens' in line and ('eval time' in line or 'sample time' in line or 'sampling time' in line)]}
 records.append(record)
 (folder/'native-compile-check.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(record,ensure_ascii=False,indent=2),flush=True)
 assert p.returncode==0 and not record['fallback_warning'],'原生Schema编译失败或pattern回退，停止'
