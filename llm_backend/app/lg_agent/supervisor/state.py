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
    status: str
    clarification_question: str
    tool_calls_made: int
    iterations_used: int


class SupervisorState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    intent: str
    guardrail_result: Dict[str, Any]
    sub_tasks: List[SubTask]
    worker_results: Annotated[List[WorkerResult], add]
    final_answer: str
    next_action: str
    needs_clarification: bool
    pending_clarification: str
