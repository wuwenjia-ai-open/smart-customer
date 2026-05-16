"""OrderQA Worker — 订单查询/物流追踪"""
from app.lg_agent.workers.react_loop import build_worker
from app.lg_agent.workers.tools.schemas import track_shipment, ask_clarification
from app.lg_agent.workers.tools.registry import create_tool
from app.lg_agent.prompts.workers.think_base import build_think_prompt

IDENTITY = """你是灵犀智购的订单管家。负责订单查询和物流追踪。

核心能力：根据订单号查询订单详情、追踪物流状态。

需要订单号才能查询。如果没有订单号，调用 ask_clarification 让用户提供。"""

TOOL_SCHEMAS = [track_shipment, ask_clarification]


def build(llm):
    tools = [create_tool(t) for t in TOOL_SCHEMAS]
    tool_descriptions = "\n".join(
        f"- **{t.name}**: {t.description or 'No description'}"
        for t in tools
    )
    system_prompt = build_think_prompt("order_qa", tool_descriptions, identity=IDENTITY)
    return build_worker(llm, tools, system_prompt, "order_qa")
