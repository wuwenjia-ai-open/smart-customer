"""Guardrails — 判断问题是否在电商业务范围内"""
from typing import Any, Callable, Dict, Optional

from langchain_core.language_models import BaseChatModel
from langchain_neo4j import Neo4jGraph
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from ..state import OverallState


class GuardrailsOutput(BaseModel):
    decision: str = Field(description="'continue' 或 'end'")
    reason: str = Field(description="判断理由")


GUARDRAILS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是电商客服的门卫。判断用户问题是否与电子产品/智能家居相关。

业务范围（以下为允许）：
- 智能家居、消费电子产品（空气净化器、空调、门锁、手环、冰箱等）
- 产品查询、价格筛选、库存查询、订单查询、物流追踪
- 供应商管理、客户服务、员工管理

不在范围内（以下为拒绝）：
- 服装、食品、化妆品、体育用品等非电子产品
- 与电商客服无关的闲聊/编程/写作等

输出 decision="end"（拒绝）或 decision="continue"（放行）。"""),
    ("human", "用户问题：{question}\n范围描述：{scope}"),
])

SCOPE = "消费电子与智能家居产品。产品查询、产品详情、使用说明、退换货、保修、配送、支付、订单、物流、评价、常见问题FAQ、售后政策。"


def create_guardrails_node(
    llm: BaseChatModel,
    graph: Neo4jGraph = None,
    scope_description: Optional[str] = None,
) -> Callable:
    chain = GUARDRAILS_PROMPT | llm.with_structured_output(GuardrailsOutput)

    async def guardrails(state: OverallState) -> Dict[str, Any]:
        question = state.get("question", "")
        result = await chain.ainvoke({"question": question, "scope": scope_description or SCOPE})

        if result.decision == "end":
            return {"next_action": "end", "summary": "抱歉，我家暂时没有这方面的商品，可以在别家看看哦~", "answer": "抱歉，我家暂时没有这方面的商品，可以在别家看看哦~", "steps": ["guardrails"]}

        return {"next_action": "planner", "steps": ["guardrails"]}

    return guardrails
