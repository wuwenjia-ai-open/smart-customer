"""Worker Agent 状态定义"""
from typing import Annotated, Any, Dict, List
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from typing_extensions import TypedDict


class WorkerState(TypedDict):
    """Worker 状态（Supervisor dispatch 时传递）"""
    messages: Annotated[List[AnyMessage], add_messages]
    worker_type: str
    task: str
    context: Dict[str, Any]
    iteration_count: int
    next_action: str
    tool_to_execute: str
    final_answer: str
    status: str
    clarification_question: str
