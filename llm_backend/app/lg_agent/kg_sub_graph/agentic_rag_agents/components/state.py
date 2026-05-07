"""子图状态定义"""
from operator import add
from typing import Annotated, Any, Dict, List

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from typing_extensions import TypedDict

from .models import Task


class CypherOutputState(TypedDict):
    """单次 Cypher 查询的输出"""
    task: str
    statement: str
    parameters: Dict[str, Any]
    errors: List[str]
    records: List[Dict[str, Any]]
    steps: List[str]


class InputState(TypedDict):
    """子图输入"""
    question: str
    messages: Annotated[List[AnyMessage], add_messages]
    steps: Annotated[List[str], add]


class OverallState(TypedDict):
    """子图全局状态"""
    question: str
    messages: Annotated[List[AnyMessage], add_messages]
    tasks: Annotated[List[Task], add]
    next_action: str
    cyphers: Annotated[List[CypherOutputState], add]
    summary: str
    answer: str
    steps: Annotated[List[str], add]
    hallucination_count: int


class OutputState(TypedDict):
    """子图输出"""
    answer: str
    question: str
    steps: List[str]
    cyphers: List[CypherOutputState]


class ToolSelectionInputState(TypedDict):
    """Tool Selection 节点输入"""
    question: str
    parent_task: str
    context: Any
