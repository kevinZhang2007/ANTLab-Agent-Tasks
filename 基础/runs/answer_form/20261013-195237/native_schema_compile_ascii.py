from pathlib import Path
from datetime import datetime
import subprocess,json,re,hashlib
work=Path(__file__).parent;folder=Path((work/'answer_form_folder.txt').read_text(encoding='utf-8'));root=Path(r'C:\Users\86186\AppData\Local\ANTLabLocalModel')
records=[]
for kind in ['number','percent']:
 src=folder/('schema-self-'+kind+'.json');dst=work/('schema-probe-'+kind+'.json');dst.write_bytes(src.read_bytes())
 args=[str(root/'llama-b11429/llama-completion.exe'),'-m',str(root/'models/Qwen3-0.6B-Q8_0.gguf'),'-ngl','0','-t','4','-c','512','-b','128','-ub','64','--no-warmup','--no-conversation','--no-display-prompt','-n','0','-p','Synthetic schema compilation only.','--json-schema-file',str(dst),'-lv','5']
 p=subprocess.run(args,capture_output=True,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
 (folder/('native-ascii-'+kind+'.stdout.txt')).write_bytes(p.stdout);(folder/('native-ascii-'+kind+'.stderr.txt')).write_bytes(p.stderr)
 text=(p.stdout+p.stderr).decode('utf-8',errors='replace')
 record={'recorded_at':datetime.now().astimezone().isoformat(),'kind':kind,'returncode':p.returncode,'output_budget':0,'counts_as_generation':False,'source_schema_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'ascii_copy_sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'path_fix':'原Schema字节不变，仅把编译检查输入放到仓库外ASCII路径；原失败保留。','arguments':[a.replace(str(root),'%LOCALAPPDATA%/ANTLabLocalModel').replace(str(work),'WORKSPACE/work') for a in args],'fallback_warning':bool(re.search(r'pattern.*not supported|accepting any string|Invalid pattern',text)),'grammar_related_lines':[line for line in text.splitlines() if 'grammar' in line.lower()],'performance_lines':[line for line in text.splitlines() if ('eval time' in line or 'sample time' in line or 'sampling time' in line)]}
 records.append(record);(folder/'native-compile-ascii-check.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(record,ensure_ascii=False,indent=2),flush=True)
 assert p.returncode==0 and not record['fallback_warning'],'实际Schema解析失败，停止'
