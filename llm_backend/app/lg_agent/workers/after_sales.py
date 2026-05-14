"""AfterSales Worker — 售后/FAQ/工单"""
from app.lg_agent.workers.react_loop import build_worker
from app.lg_agent.workers.tools.schemas import (
    create_ticket, escalate_to_human, predefined_cypher, cypher_query, ask_clarification,
)
from app.lg_agent.prompts.workers.think_base import build_think_prompt

IDENTITY = """你是灵犀智购的售后专员。负责处理售后问题。

核心能力：查询退换货政策和保修条款、搜索 FAQ 知识库、创建售后工单、必要时转接人工客服。

处理流程：先查 FAQ → 无法解决 → 创建工单 → 仍无法解决 → 调用 escalate_to_human 转人工。"""

TOOLS = [create_ticket, escalate_to_human, predefined_cypher, cypher_query, ask_clarification]


def build(llm):
    tool_descriptions = "\n".join(
        f"- **{t.__name__}**: {t.__doc__ or 'No description'}"
        for t in TOOLS
    )
    system_prompt = build_think_prompt("after_sales", tool_descriptions, identity=IDENTITY)
    return build_worker(llm, TOOLS, system_prompt, "after_sales")
