"""有限声明兼容回归；仅自造资料，不读取题库或答案。"""
import copy, json, random
from pathlib import Path
import direct_reference_candidate as relation

def run():
    rows=[]
    def check(name,tail,expected,extra=None,main_scope='杉原项目R2版本在2026-01的记录：',supp_scope='',seed='a',remap=False):
        main={'id':'a','source':'任意/甲','text':main_scope+'检验批次AZ82'+tail}
        supplement={'id':'b','source':'无关目录/乙','text':supp_scope+'批次AZ82的复核补页：这里是原始补充资料。'}
        ps=[main,supplement]+copy.deepcopy(extra or [])
        if remap:
            ps=[{**p,'id':'renamed-'+p['id'],'text':p['text'].replace('AZ82','ZX904')} for p in ps];seed='renamed-'+seed
        before=copy.deepcopy(ps)
        out,trace=relation.complete_passages('检查当前记录。',ps,{'valid':True,'selected_ids':[seed]})
        wanted=('renamed-b' if remap else 'b') in {p['id'] for p in out}
        assert ps==before and len({p['id'] for p in out})==len(out)
        assert out==[p for p in ps if p['id'] in {x['id'] for x in out}]
        row={'name':name,'expected_added':expected,'actual_added':wanted,'passed':wanted==expected,'passages':ps,'trace':trace}
        rows.append(row)
        shuffled=list(reversed(ps));out2,_=relation.complete_passages('',shuffled,{'valid':True,'selected_ids':[seed]})
        assert {p['id'] for p in out2}=={p['id'] for p in out}
    for prefix in ['共','共计','累计','总计','合计']:
        for verb in ['收录','登记','处理','统计']:
            check(prefix+verb,'，'+prefix+verb+'23个问题。',True)
    for punctuation in ['，',',','：',':','']:
        for phrase in ['共收录23个问题。','记录17项样本。','以固定顺序处理19个问题。']:
            check('标点与计数过程'+punctuation+phrase,punctuation+phrase,True)
    for way in ['以','按']:
        for how in ['同一','相同','固定','给定','指定']:
            for order in ['顺序','次序']:
                check(way+how+order,way+how+order+'处理19项记录。',True)
    for tail in ['，没有收录23个问题。','未共收录23个问题。','，共收录。','，共收录23。','。共收录23个问题。','；共收录23个问题。','，可能共收录23个问题。','，以随机方式处理19项记录。','，编号被提及。']:
        check('拒绝不可靠声明'+tail,tail,False)
    check('假设语境','，共收录23个问题。',False,main_scope='假设')
    check('仅提及语境','，共收录23个问题。',False,main_scope='参见')
    check('重复可靠主段','，共收录23个问题。',False,extra=[{'id':'c','source':'另目录','text':'杉原项目R2版本在2026-01的记录：批次AZ82登记23个问题。'}])
    check('跨版本编号复用','，共收录23个问题。',False,extra=[{'id':'c','source':'另目录','text':'杉原项目R1版本在2026-01的记录：批次AZ82登记23个问题。'}])
    check('补页明确版本冲突','，共收录23个问题。',False,supp_scope='杉原项目R1版本在2026-01的记录：')
    check('补页明确项目冲突','，共收录23个问题。',False,supp_scope='遥川项目R2版本在2026-01的记录：')
    check('补页缺范围保持未知','，共收录23个问题。',True)
    check('主段多范围','，共收录23个问题。',False,main_scope='杉原项目R2版本在2026-01、2026-02的记录：')
    check('多主对象','，共收录23个问题；主测BQ64登记9个问题。',False)
    check('编号ID映射','，共收录23个问题。',True,remap=True)
    # 补入段不能作为新种子继续扩展；同目录和共同编号提及也不能造关系。
    for name,text in [('无直接指称','这里只提到批次AZ82，另记资料。'),('多指称','批次AZ82的复核补页，同时批次BQ64的复核补页。'),('明确否认','批次AZ82的复核补页：不是该记录。')]:
        ps=[{'id':'x','source':'same','text':'批次AZ82，共登记23项问题。'},{'id':'y','source':'same','text':text}]
        out,trace=relation.complete_passages('',ps,{'valid':True,'selected_ids':['x']})
        rows.append({'name':name,'expected_added':False,'actual_added':len(out)>1,'passed':len(out)==1,'trace':trace})
    ps=[{'id':'x','source':'same','text':'批次AZ82，共登记23项问题。'},
        {'id':'y','source':'same','text':'批次AZ82的复核补页：批次BQ64登记6项问题。'},
        {'id':'z','source':'same','text':'批次BQ64的复核补页：更多原文。'}]
    out,trace=relation.complete_passages('',ps,{'valid':True,'selected_ids':['x']})
    rows.append({'name':'禁止多跳','passed':'z' not in {p['id'] for p in out},'trace':trace})
    return {'passed':all(r['passed'] for r in rows),'count':len(rows),'rows':rows,'generation_calls':0}

if __name__=='__main__':
    value=run();Path(__file__).with_name('association-compat-self-tests.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'passed':value['passed'],'count':value['count'],'failed':[r['name'] for r in value['rows'] if not r['passed']]},ensure_ascii=False))
    raise SystemExit(0 if value['passed'] else 1)
