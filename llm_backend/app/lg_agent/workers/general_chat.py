"""GeneralChat Worker — 闲聊/接待"""
from app.lg_agent.workers.react_loop import build_worker_graph
from app.lg_agent.workers.tools.schemas import ask_clarification
from app.lg_agent.prompts.workers.think_base import build_think_prompt

IDENTITY = """你是灵犀智购的接待客服。负责闲聊和接待。

核心能力：友好问候、引导用户说明需求、模糊问题时追问澄清。

你没有产品/订单查询工具。如果用户问具体业务问题，告知用户正在转接给专业同事处理。"""

TOOLS = [ask_clarification]


def build(llm):
    return build_worker_graph("general_chat", llm, TOOLS, identity=IDENTITY)
