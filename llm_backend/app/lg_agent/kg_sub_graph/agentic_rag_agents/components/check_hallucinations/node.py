"""幻觉检测节点 — 检查回答是否有数据依据，无依据则重新生成"""
from typing import Any, Callable, Dict

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from ..state import OverallState

HALLUCINATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是电商客服回答的审核员。检查回答是否基于查询结果，有没有编造数据。

判断标准：
- 有依据（yes）：回答中的所有产品名、价格、库存等数据都能在查询结果中找到
- 无依据（no/half）：回答编造了不存在的数据，或严重偏离查询结果

只输出一个词：yes 或 no 或 half"""),
    ("human", "查询结果：{records}\n\n回答：{summary}\n\n是否有数据依据？"),
])


class HallucinationResult(BaseModel):
    score: str = Field(description="yes / no / half")


def create_check_hallucinations_node(llm: BaseChatModel, max_retries: int = 3) -> Callable:
    """创建幻觉检测节点"""
    chain = HALLUCINATION_PROMPT | llm.with_structured_output(HallucinationResult)

    async def check_hallucinations(state: OverallState) -> Dict[str, Any]:
        count = state.get("hallucination_count", 0)

        records_data = []
        for c in state.get("cyphers", []):
            recs = c.get("records") if isinstance(c, dict) else getattr(c, "records", [])
            records_data.extend(recs if recs else [])

        summary = state.get("summary", "")

        result = await chain.ainvoke({"records": str(records_data)[:3000], "summary": summary})
        score = result.score if hasattr(result, "score") else "yes"

        if score in ("no", "half") and count < max_retries:
            print(f"  幻觉检测: {score} → 重新生成 (第{count+1}次)")
            return {"next_action": "summarize", "hallucination_count": count + 1, "steps": ["check_hallucinations"]}

        return {"next_action": "end", "steps": ["check_hallucinations"]}

    return check_hallucinations
