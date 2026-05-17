"""GeneralChat Worker — 闲聊/接待"""
from app.lg_agent.workers.react_loop import build_worker
from app.lg_agent.workers.tools.schemas import ask_clarification
from app.lg_agent.workers.tools.registry import create_tool
from app.lg_agent.prompts.workers.think_base import build_think_prompt

IDENTITY = """你是灵犀智购的接待客服。负责闲聊和接待。

核心能力：友好问候、引导用户说明需求、模糊问题时追问澄清。

你没有产品/订单查询工具。如果用户问具体业务问题，告知用户正在转接给专业同事处理。"""

TOOL_SCHEMAS = [ask_clarification]


def build(llm):
    tools = [create_tool(ask_clarification)]
    tool_descriptions = "\n".join(
        f"- **{t.name}**: {t.description or 'No description'}"
        for t in tools
    )
    system_prompt = build_think_prompt("general_chat", tool_descriptions, identity=IDENTITY)
    return build_worker(llm, tools, system_prompt, "general_chat")
