from pathlib import Path
import sys,json,copy,ast,shutil
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');HERE=ROOT/'进阶/a_exploration';sys.path.insert(0,str(HERE))
from runtime import load,write,sha,now
from sentence_selection import offline_checks as s_checks
from compact_factorial import offline_checks as c_checks
from audited_health import offline_checks as h_checks
from thinking_modes import offline_checks as t_checks
from sentence_interface import offline_checks as i_checks
from checks_extended import run as old_checks
from bounded_candidate import BoundedEngine
batch=Path(Path('a-bounded-root.txt').read_text(encoding='utf-8').strip());name=sys.argv[1];kind=sys.argv[2];profilepath=Path(sys.argv[3]);taskpath=Path(sys.argv[4]);cap=int(sys.argv[5]);phase=sys.argv[6] if len(sys.argv)>6 else 'development'
folder=batch/name;folder.mkdir();profile=load(profilepath);tasks=load(taskpath)
if phase!='development':assert (batch/'final-freeze.json').is_file()
checks={'sentence':s_checks(),'compact':c_checks(),'health':h_checks(),'thinking':t_checks(),'interface':i_checks(),'existing':old_checks(folder)};assert all(x['passed'] for x in checks.values())
e=BoundedEngine.__new__(BoundedEngine);e.profile=profile
blocks=[{'block_id':'sample-one','doc_id':'sample','snapshot':'published','section_id':'section-a','heading':'Plot records','paragraph_index':0,'text':'Keep plotting records.','_order':(0,0)},{'block_id':'sample-two','doc_id':'sample','snapshot':'published','section_id':'section-a','heading':'Plot records','paragraph_index':1,'text':'Store their sources.','_order':(0,1)},{'block_id':'sample-other','doc_id':'other','snapshot':'published','section_id':'section-b','heading':'Software versions','paragraph_index':0,'text':'An image of the environment.','_order':(1,0)}]
before=copy.deepcopy(blocks);a,sc=e.retrieve('plot records',blocks);remapped=[{**b,'block_id':'mapped-'+str(n)} for n,b in enumerate(blocks)];b,ss=e.retrieve('plot records',list(reversed(remapped)));assert [x['text'] for x in a]==[x['text'] for x in b] and before==blocks
assert e.retrieve('unmatchedzzq',blocks)[0]==[]
for p in HERE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
write(folder/'profile.json',profile);write(folder/'tasks.json',tasks);write(folder/'offline-checks.json',{'at':now(),'passed':True,'groups':checks,'additional_checks':['retrieval_id_remap_and_order','input_unchanged','empty_retrieval'],'generation_calls':0})
target={'round1':'具体对象遗漏与主题近似命中；联合对象查询和标题/正文检索。','round2':'背景/授权无关引用与必要证据漏引；整体选句要求。','round3':'否定及理由label方向错误；解释先行与关键断言核对。','round4':'合并胜出部分的相互作用；三题两侧完整覆盖。'}.get(name,'冻结后验证')
plan={'at':now(),'phase':phase,'kind':kind,'generation_cap':cap,'goal':target,'profile':profile,'prediction':'可能改善完整成功，也可能影响标签或引入其他无关引用；所有退步逐题保留。','counterexamples':['仅主题相关不支持断言','条件不明不是通过','建议不等于强制','未知ID及重映射','跨范围或章节不得补段'],'selection':'严格成功优先，其次标签正确；同分保留更简单前版，标签退步单列，不逐题拼接。','comparison':'新查询为新调用；旧侧历史复用均明确标记；固定查询阶段不是端到端重跑。','strict_formula':load(batch/'batch-plan.json')['strict_formula'],'reason_quality_separate':True,'code_hashes':{p.relative_to(ROOT).as_posix():sha(p) for p in HERE.glob('*.py')},'data_hashes':load(batch/'configuration.json')['data_hashes'],'no_AT_read_for_development':phase=='development','baseline_batch':630,'no_technical_retry':True}
write(folder/'plan.json',plan);shutil.copy2(__file__,folder/Path(__file__).name)
print(str(folder))
