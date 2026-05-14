"""OrderQA Worker — 订单查询/物流追踪"""
from app.lg_agent.workers.react_loop import build_worker_graph
from app.lg_agent.workers.tools.schemas import (
    track_shipment, predefined_cypher, cypher_query, ask_clarification,
)
from app.lg_agent.prompts.workers.think_base import build_think_prompt

IDENTITY = """你是灵犀智购的订单管家。负责订单查询和物流追踪。

核心能力：根据订单号查询订单详情、追踪物流状态、查询历史订单。

需要订单号才能查询。如果没有订单号，调用 ask_clarification 让用户提供。"""

TOOLS = [track_shipment, predefined_cypher, cypher_query, ask_clarification]


def build(llm):
    return build_worker_graph("order_qa", llm, TOOLS, identity=IDENTITY)
