"""OrderQA Worker — 订单查询/物流追踪"""
from app.lg_agent.workers.react_loop import build_worker
from app.lg_agent.workers.tools.schemas import track_shipment, ask_clarification
from app.lg_agent.workers.tools.registry import create_tool
from app.lg_agent.prompts.workers.think_base import build_think_prompt

IDENTITY = """你是灵犀智购的订单管家。负责订单查询和物流追踪。

工作流:
1. 用户消息里**有订单号**(如"订单 #1001"、"1001 号订单") → 立即调 track_shipment(order_id=该数字),
   它一次返回全部订单信息(下单/发货时间、收件人、商品明细、物流)。
   **不要**先调 ask_clarification——已经给你订单号了。
2. 用户消息里**没订单号** → 调 ask_clarification 索取:
   - 这是「缺参数」场景,订单查询本身就是你的分内事
   - 只填 question 和 missing_field='order_id'
   - **不要**填 reroute_to——不是转工作,只是请用户补信息"""

TOOL_SCHEMAS = [track_shipment, ask_clarification]


def build(llm):
    tools = [create_tool(t) for t in TOOL_SCHEMAS]
    tool_descriptions = "\n".join(
        f"- **{t.name}**: {t.description or 'No description'}"
        for t in tools
    )
    system_prompt = build_think_prompt("order_qa", tool_descriptions, identity=IDENTITY)
    return build_worker(llm, tools, system_prompt, "order_qa")
