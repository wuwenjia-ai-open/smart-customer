"""Supervisor 全局状态定义"""
from operator import add
from typing import Annotated, Any, Dict, List
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from typing_extensions import TypedDict


class SubTask(TypedDict):
    task_id: str
    worker_type: str
    description: str
    context: Dict[str, Any]
    priority: int


class WorkerResult(TypedDict):
    task_id: str
    worker_type: str
    answer: str
    status: str  # success | clarification_needed | escalated | reroute
    clarification_question: str
    tool_calls_made: int
    iterations_used: int
    confidence: float  # 0.0-1.0，工具成功率越高越可信
    reroute_to: str  # 非空时 Supervisor 重新分发到此 Worker
    control_action: str  # clarify | escalate | reroute | ""


class SupervisorState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    intent: str
    guardrail_result: Dict[str, Any]
    workers: List[str]  # 当前分发的 Worker 列表
    sub_tasks: List[SubTask]
    worker_results: Annotated[List[WorkerResult], add]
    final_answer: str
    next_action: str
    needs_clarification: bool
    pending_clarification: str
    reroute_count: int  # 重路由次数，上限 2 防止死循环
