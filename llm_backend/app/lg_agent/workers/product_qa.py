"""ProductQA Worker — 产品查询/对比/推荐"""
from app.lg_agent.workers.react_loop import build_worker
from app.lg_agent.workers.tools.schemas import (
    semantic_search, compare_products, recommend, ask_clarification,
)
from app.lg_agent.workers.tools.registry import create_tool
from app.lg_agent.prompts.workers.think_base import build_think_prompt

IDENTITY = """你是灵犀智购的产品顾问。负责帮用户找到最合适的电子产品。

核心能力：语义搜索产品、横向对比价格功能评价、基于预算和场景做个性化推荐。

产品库覆盖：智能手机、笔记本、平板、真无线耳机、智能手表、充电配件等品类。"""

TOOL_SCHEMAS = [semantic_search, compare_products, recommend, ask_clarification]


def build(llm):
    tools = [create_tool(t) for t in TOOL_SCHEMAS]
    tool_descriptions = "\n".join(
        f"- **{t.name}**: {t.description or 'No description'}"
        for t in tools
    )
    system_prompt = build_think_prompt("product_qa", tool_descriptions, identity=IDENTITY)
    return build_worker(llm, tools, system_prompt, "product_qa")
