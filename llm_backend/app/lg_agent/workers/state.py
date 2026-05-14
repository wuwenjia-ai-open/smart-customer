"""Worker ReAct 循环状态定义"""
from operator import add
from typing import Annotated, Any, Dict, List
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from typing_extensions import TypedDict


class ToolCallRecord(TypedDict):
    """Observe 阶段记录的单次工具调用"""
    tool_name: str
    args: Dict[str, Any]
    result_summary: str
    record_count: int
    success: bool


class WorkerState(TypedDict):
    """Worker ReAct 循环状态"""
    messages: Annotated[List[AnyMessage], add_messages]
    worker_type: str
    task: str
    context: Dict[str, Any]
    iteration_count: int
    next_action: str
    tool_to_execute: str
    tool_call_history: Annotated[List[ToolCallRecord], add]
    final_answer: str
    status: str
    clarification_question: str
