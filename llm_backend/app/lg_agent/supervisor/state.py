"""Supervisor 全局状态定义"""
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
    slots: Dict[str, Any]  # 本轮工具执行中提取的对话槽位


def add_or_reset_worker_results(
    left: List[WorkerResult] | None,
    right: List[WorkerResult] | None,
) -> List[WorkerResult]:
    """worker_results reducer：[] = 重置（merge 节点消费完后清零）；其他 = 追加。

    checkpoint 跨轮持久化 SupervisorState，若用 operator.add 会让上一轮的 worker
    结果泄露到下一轮 merge_results，导致回复重复历史内容。merge_results 在产出
    final_answer 时返回 worker_results=[]，本 reducer 把空列表视作显式 reset。
    """
    if right is None:
        return left or []
    if right == []:
        return []
    return (left or []) + right


class SupervisorState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    intent: str
    guardrail_result: Dict[str, Any]
    workers: List[str]  # 当前分发的 Worker 列表
    sub_tasks: List[SubTask]
    worker_results: Annotated[List[WorkerResult], add_or_reset_worker_results]
    final_answer: str
    next_action: str
    needs_clarification: bool
    pending_clarification: str
    reroute_count: int  # 重路由次数，上限 2 防止死循环
    segment_id: int  # 当前话题段 ID，由 classify_intent 写入，merge_results 读取
