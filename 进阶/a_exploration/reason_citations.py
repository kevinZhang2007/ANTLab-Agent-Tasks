"""独立共同判断提示候选；仅追加说明，不修改模型输出。"""
import copy
NOTE='\nreason直接说明证据为何支持、反驳或不足以判断原主张，不重新改写主张；若reason声称原主张与原文冲突，label不能同时表示supported。sentence_ids只选择判断所需片段，不能因同主题就加入；可组合多个必要片段，不要求引用越少越好。reason不重复段落ID，来源由句子索引展开。'
def adapt(messages):
    result=copy.deepcopy(messages)
    assert result[0]["role"]=="system"
    result[0]["content"]+=NOTE
    return result
