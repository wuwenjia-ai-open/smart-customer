"""子图路由：条件边 + 并行分发 + 幻觉循环"""
from typing import List, Literal

from langgraph.types import Send

from ...components.state import OverallState


def guardrails_conditional_edge(
    state: OverallState,
) -> Literal["planner", "__end__"]:
    if state.get("next_action") == "end":
        return "__end__"
    return "planner"


def map_reduce_planner_to_tool_selection(state: OverallState) -> List[Send]:
    """Planner → Send() 并行分发每个子任务到 tool_selection"""
    tasks = state.get("tasks", [])
    if not tasks:
        return []
    return [
        Send("tool_selection", {
            "question": t.question, "parent_task": t.parent_task,
            "steps": ["planner"],
        })
        for t in tasks
    ]


def summarize_conditional_edge(
    state: OverallState,
) -> Literal["check_hallucinations", "__end__"]:
    """Summarize 后可跳过幻觉检测或进入检查"""
    # 如果没有查询结果（guardrails 直接拒绝），跳过
    if not state.get("cyphers"):
        return "__end__"
    return "check_hallucinations"


def predefined_fallback_edge(
    state: OverallState,
) -> Literal["summarize", "cypher_query"]:
    """预定义查询无结果 → 降级到动态 Cypher"""
    cyphers = state.get("cyphers", [])
    if cyphers:
        first = cyphers[0]
        records = first.get("records") if isinstance(first, dict) else getattr(first, "records", None)
        if records:
            return "summarize"
    return "cypher_query"


def hallucination_conditional_edge(
    state: OverallState,
) -> Literal["summarize", "__end__"]:
    """幻觉检测: 通过→结束, 不通过→回到 summarize 重生成"""
    action = state.get("next_action", "end")
    if action == "summarize":
        return "summarize"
    return "__end__"
