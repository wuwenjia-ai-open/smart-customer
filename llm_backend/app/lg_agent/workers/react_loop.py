"""Worker ReAct 循环 — build_worker_graph() 工厂函数"""
import logging
from typing import Any, Dict, List, Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from app.lg_agent.workers.state import WorkerState, ToolCallRecord
from app.lg_agent.workers.tools.registry import get_tool_executor
from app.lg_agent.prompts.workers.think_base import build_think_prompt

_log = logging.getLogger(__name__)

MAX_ITERATIONS = 7
MAX_EMPTY_RESULTS = 3
MAX_DUPLICATE_CALLS = 2


def route_after_think(state: WorkerState) -> Literal["act", "finish"]:
    last_msg = state["messages"][-1] if state["messages"] else None
    if isinstance(last_msg, AIMessage) and getattr(last_msg, "tool_calls", None):
        return "act"
    return "finish"


def route_after_observe(state: WorkerState) -> Literal["think", "finish"]:
    if state["next_action"] == "finish":
        return "finish"
    return "think"


async def act_node(state: WorkerState) -> Dict[str, Any]:
    """执行工具调用，无 LLM 调用"""
    last_msg = state["messages"][-1] if state["messages"] else None

    if not isinstance(last_msg, AIMessage) or not getattr(last_msg, "tool_calls", None):
        return {"next_action": "finish"}

    tool_call = last_msg.tool_calls[0]
    tool_name = tool_call["name"]
    tool_args = tool_call.get("args", {})

    _log.info(f"Act: calling {tool_name} with args keys={list(tool_args.keys())}")

    try:
        executor = get_tool_executor(tool_name)
        result = executor.invoke(tool_args)
    except KeyError:
        content = f"Error: Unknown tool '{tool_name}'. Available: see tool list."
    else:
        content = result.summary if result.success else f"Error: {result.error}"
        if result.records:
            content += f"\nRecords ({len(result.records)}): {str(result.records)[:2000]}"

    tool_msg = ToolMessage(content=content, tool_call_id=tool_call["id"])
    return {
        "messages": [tool_msg],
        "tool_to_execute": tool_name,
    }


def observe_node(state: WorkerState, *, config: RunnableConfig) -> Dict[str, Any]:
    """程序化校验工具结果，无 LLM 调用"""
    tool_name = state.get("tool_to_execute", "unknown")
    iteration_count = state.get("iteration_count", 0) + 1

    # Get last tool message content
    msgs = state.get("messages", [])
    last_tool_content = ""
    for m in reversed(msgs):
        if isinstance(m, ToolMessage):
            last_tool_content = getattr(m, "content", "") or ""
            break

    record_count = 0
    if "product_name" in last_tool_content:
        record_count = last_tool_content.count("product_name")
    elif last_tool_content and not last_tool_content.startswith("Error:"):
        record_count = 1
    success = not last_tool_content.startswith("Error:")
    is_empty = record_count == 0

    record = ToolCallRecord(
        tool_name=tool_name,
        args={},
        result_summary=last_tool_content[:200],
        record_count=record_count,
        success=success,
    )

    # Check for control tools (clarify, escalate)
    if "[CLARIFY]" in last_tool_content:
        return {
            "iteration_count": iteration_count,
            "next_action": "finish",
            "status": "clarification_needed",
            "clarification_question": last_tool_content.replace("[CLARIFY] ", "").strip(),
            "tool_call_history": [record],
        }

    if "[ESCALATE]" in last_tool_content:
        return {
            "iteration_count": iteration_count,
            "next_action": "finish",
            "status": "escalated",
            "final_answer": last_tool_content.replace("[ESCALATE] ", "").strip(),
            "tool_call_history": [record],
        }

    # Check empty results
    history = list(state.get("tool_call_history", []))
    consecutive_empty = 0
    for h in reversed(history):
        if h.get("record_count", 0) == 0:
            consecutive_empty += 1
        else:
            break
    if is_empty:
        consecutive_empty += 1

    if consecutive_empty >= MAX_EMPTY_RESULTS:
        return {
            "iteration_count": iteration_count,
            "next_action": "finish",
            "status": "success",
            "final_answer": "抱歉，我暂时没有找到相关信息。您可以换个方式描述需求，或者联系人工客服获取帮助。",
            "tool_call_history": [record],
        }

    # Check duplicate calls
    duplicate_count = sum(1 for h in history[-MAX_DUPLICATE_CALLS:] if h.get("tool_name") == tool_name)
    if duplicate_count >= MAX_DUPLICATE_CALLS and len(history) >= MAX_DUPLICATE_CALLS:
        return {
            "iteration_count": iteration_count,
            "next_action": "finish",
            "status": "success",
            "final_answer": "抱歉，我尝试了几次但没能找到对应的信息。建议您换个关键词试试，或联系人工客服协助。",
            "tool_call_history": [record],
        }

    # Iteration limit
    if iteration_count >= MAX_ITERATIONS:
        _log.warning(f"Worker hit max iterations ({MAX_ITERATIONS}), force finish")
        return {
            "iteration_count": iteration_count,
            "next_action": "finish",
            "status": "success",
            "tool_call_history": [record],
        }

    # Normal: continue loop
    return {
        "iteration_count": iteration_count,
        "next_action": "think",
        "tool_call_history": [record],
    }


def make_think_node(llm: BaseChatModel, worker_type: str, tool_schemas: list):
    """创建 Think 节点 — 唯一的 LLM 调用"""

    # Build prompt with dynamic tool descriptions
    tool_descriptions = "\n".join(
        f"- **{t.__name__}**: {t.__doc__ or 'No description'}"
        for t in tool_schemas
    )
    system_prompt = build_think_prompt(worker_type, tool_descriptions)

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("placeholder", "{messages}"),
    ])

    llm_with_tools = llm.bind_tools(tool_schemas)

    async def think(state: WorkerState) -> Dict[str, Any]:
        iteration = state.get("iteration_count", 0)
        _log.info(f"Think: worker={worker_type} iteration={iteration}")

        result = await (prompt | llm_with_tools).ainvoke({"messages": state["messages"]})
        return {"messages": [result]}

    return think


def finish_node(state: WorkerState) -> Dict[str, Any]:
    """提取最终答案 — 从最后一条无 tool_calls 的 AIMessage 获取 content"""
    msgs = state.get("messages", [])
    answer = ""
    for m in reversed(msgs):
        if isinstance(m, AIMessage) and not getattr(m, "tool_calls", None):
            answer = getattr(m, "content", "") or ""
            if answer:
                break

    if not answer:
        tools_used = len(state.get("tool_call_history", []))
        answer = f"已为您查询（共调用 {tools_used} 次工具），如有其他问题请随时问我～"

    return {
        "final_answer": answer,
        "status": state.get("status", "success"),
        "clarification_question": state.get("clarification_question", ""),
    }


def build_worker_graph(worker_type: str, llm: BaseChatModel, tool_schemas: list) -> StateGraph:
    """构建 Worker ReAct 子图"""
    builder = StateGraph(WorkerState)

    think_node_fn = make_think_node(llm, worker_type, tool_schemas)

    builder.add_node("think", think_node_fn)
    builder.add_node("act", act_node)
    builder.add_node("observe", observe_node)
    builder.add_node("finish", finish_node)

    builder.add_edge(START, "think")
    builder.add_conditional_edges("think", route_after_think, {
        "act": "act",
        "finish": "finish",
    })
    builder.add_edge("act", "observe")
    builder.add_conditional_edges("observe", route_after_observe, {
        "think": "think",
        "finish": "finish",
    })
    builder.add_edge("finish", END)

    return builder.compile()
