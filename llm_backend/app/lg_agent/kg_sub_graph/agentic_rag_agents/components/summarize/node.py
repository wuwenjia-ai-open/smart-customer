"""Summarize — 汇总 Cypher 查询结果，生成自然语言回复"""
from typing import Any, Callable, Dict, List

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from ..state import OverallState

SUMMARIZE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是专业电商客服。将查询结果整理为亲切的回复。

规则:
- 开场用"亲～"或"您好～"
- 适当用 emoji 增加亲和力
- 列出关键信息时用清晰格式
- 有多个产品时按价格/评分排序推荐
- 结果为空时礼貌告知，引导用户提供更多信息
- 只使用查询结果数据，不编造"""),
    ("human", "查询结果: {results}\n\n对话历史: {context}\n\n用户问题: {question}\n\n请回答:"),
])

FALLBACK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是专业电商客服。数据库没有查到结果，请参考对话历史回答。

规则:
- 如果历史中提过产品，引用历史信息
- 如果用户问题模糊，追问确认需求
- 不要编造不存在的产品"""),
    ("human", "对话历史: {context}\n\n用户问题: {question}\n\n请回答:"),
])


def create_summarization_node(llm: BaseChatModel) -> Callable:
    """创建 Summarize 节点"""
    chain = SUMMARIZE_PROMPT | llm | StrOutputParser()
    fallback = FALLBACK_PROMPT | llm | StrOutputParser()

    async def summarize(state: OverallState) -> Dict[str, Any]:
        results = []
        for c in state.get("cyphers", []):
            recs = c.get("records") if isinstance(c, dict) else getattr(c, "records", [])
            if recs:
                results.extend(recs)

        question = state.get("question", "")
        msgs = state.get("messages", [])
        context = "\n".join([f"{'用户' if isinstance(m, HumanMessage) else '客服'}: {str(m.content)[:200]}" for m in msgs[-6:]]) if msgs else "无"

        if results and not all(isinstance(r, dict) and "error" in r for r in results):
            summary = await chain.ainvoke({"results": str(results)[:4000], "context": context, "question": question})
        else:
            summary = await fallback.ainvoke({"context": context, "question": question})

        return {"summary": summary, "answer": summary, "steps": ["summarize"]}

    return summarize
