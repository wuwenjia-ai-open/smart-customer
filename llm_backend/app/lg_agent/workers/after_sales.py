"""AfterSales Worker — 售后/FAQ/工单"""
from app.lg_agent.workers.react_loop import build_worker
from app.lg_agent.workers.tools.schemas import (
    create_ticket, escalate_to_human, ask_clarification, search_faq,
)
from app.lg_agent.workers.tools.registry import create_tool
from app.lg_agent.prompts.workers.think_base import build_think_prompt

IDENTITY = """你是灵犀智购的售后专员。负责处理售后问题。

核心能力：查询退换货政策和保修条款、搜索 FAQ 知识库、创建售后工单、必要时转接人工客服。

处理流程：先查 FAQ → 无法解决 → 创建工单 → 仍无法解决 → 调用 escalate_to_human 转人工。"""

TOOL_SCHEMAS = [search_faq, create_ticket, escalate_to_human, ask_clarification]


def build(llm):
    tools = [create_tool(t) for t in TOOL_SCHEMAS]
    tool_descriptions = "\n".join(
        f"- **{t.name}**: {t.description or 'No description'}"
        for t in tools
    )
    system_prompt = build_think_prompt("after_sales", tool_descriptions, identity=IDENTITY)
    return build_worker(llm, tools, system_prompt, "after_sales")
