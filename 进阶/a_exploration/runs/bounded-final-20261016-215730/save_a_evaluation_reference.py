from pathlib import Path
import sys
ROOT=Path(r'C:\Users\86186\Projects\ANTLab-Agent-Tasks');sys.path.insert(0,str(ROOT/'进阶/a_exploration'))
from runtime import load,write,now
from engine import Corpus,public
b=Path(Path('a-bounded-root.txt').read_text(encoding='utf-8').strip());assert (b/'final-freeze.json').exists();tasks=load(b/'evaluation-tasks.json');c=Corpus(load(ROOT/'进阶/materials/sections.json'));byid={x['block_id']:x for x in c.blocks}
spec={
 'AT01':('insufficient',['P1-S07-p01','P1-S04-p01'],'随机步骤记录seed的建议，不等于任意远程LLM API的字节级确定性服务契约。原文没有这种API实验；不能把缺失当作已经证明其反面。','原文描述同seed随机数序列相同，另要求注意版本/依赖；向远程API保证外推缺少实现、环境等条件。'),
 'AT02':('supported',['P2-S09-p02'],'大小或隐私限制下，分层公开中型匿名数据和进一步处理数据，使没有全量raw data的人能复用latter stages。','需同时覆盖限制、分层办法和后续阶段复用，不能只引一般数据分享。'),
 'AT03':('contradicted',['P1-S02-p01','P1-S10-p02','P1-S10-p03','P1-S10-p04'],'Rule1要求记录影响每个步骤的细节和生成过程；Rule9把文字解释连到对应精确结果。因此最终一个数值链接不能豁免生成过程。','允许有充分替代原文，不要求固定引用ID；反驳的是无需过程，不要求每条结论必须多于一个数值。'),
 'AT04':('supported',['P2-S08-p02','P2-S01-p03'],'运行较快时，重启内核、重跑全部cells可检查是否清理时漏删步骤，亦是最终测试；引言说明交互可能引入hidden state。','这是检查办法而非保证发现所有缺陷；不能把建议改成无例外强制。'),
 'AT05':('supported',['P1-S02-p01','P1-S10-p02','P1-S10-p03','P2-S03-p02'],'P1追踪生成步骤并关联文字与结果；P2明确代码可能自动捕获，但reasoning and intuition未必记录。','多项合取需覆盖两文档及P1两个层次；只证其中一层属于部分覆盖，不按部分支持判完整。'),
 'AT06':('contradicted',['P2-S03-p01','P2-S08-p03'],'P2要求记录all explorations，尤其dead ends；之后面向流水线或受众可精简，不意味着研究过程无需记录失败。','阶段和用途不能混同；不能把允许删展示性评论推成全程不记录。'),
 'AT07':('insufficient',['P1-S01-p04','P1-S01-p08','P2-S01-p04','P2-S13-p01'],'两文为可复现性与Notebook实践规则，没有给定三协作模块及准确率提升20百分点的对照实验。','此为全文材料范围核查，不代表外部世界不存在该实验；不能因没有提到直接判contradicted。引用应是有效检查来源，不引用无关20年或参数数字凑数。')}
rows=[]
for t in tasks:
 label,ids,basis,limits=spec[t['id']];blocks=[]
 for bid in ids:
  x=byid[bid];assert x['doc_id'] in t['doc_ids'];blocks.append({'block':public(x),'start':0,'end':len(x['text']),'original_excerpt':x['text']})
 rows.append({'id':t['id'],'claim':t['claim'],'doc_ids':t['doc_ids'],'provisional_reference_label':label,'source_evidence':blocks,'basis':basis,'limits':limits,'official_gold':False})
assert not (b/'evaluation-original-evidence.json').exists();write(b/'evaluation-original-evidence.json',{'at':now(),'source':'Codex依据指定原文推导，尚待本人确认；非官方标准答案。','built_before_inspecting_formal_model_responses':True,'freeze_already_saved':True,'rows':rows,'not_read_by_runtime':True})
print('SEVEN_REFERENCE_RECORDS_SAVED')
