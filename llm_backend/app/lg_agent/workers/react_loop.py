"""Worker Agent — LangChain create_agent 薄封装"""
import logging
from operator import add
from typing import Annotated, Any, Dict, List

from langchain.agents import create_agent
from langgraph.graph import StateGraph, START, END, add_messages
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage
from typing_extensions import TypedDict

from app.lg_agent.supervisor.state import WorkerResult

_log = logging.getLogger(__name__)


class WorkerInternalState(TypedDict):
    """Worker 内部隔离状态 — 不会泄露到 Supervisor"""
    messages: Annotated[List[AnyMessage], add_messages]


class WorkerOutputState(TypedDict):
    """Worker 输出 — 只有 worker_results 会合并到 Supervisor"""
    worker_results: Annotated[List[WorkerResult], add]


def build_worker(llm: BaseChatModel, tools: list, system_prompt: str, worker_type: str) -> StateGraph:
    """构建 Worker Agent — create_agent + 结果提取"""

    react_agent = create_agent(
        llm,
        tools,
        system_prompt=system_prompt,
    )

    builder = StateGraph(WorkerInternalState, output_schema=WorkerOutputState)

    async def execute(state: WorkerInternalState) -> Dict[str, Any]:
        _log.info(f"Worker {worker_type}: executing react agent")

        result = await react_agent.ainvoke({"messages": state["messages"]})
        all_msgs = result.get("messages", [])

        # Extract final answer (last non-tool-call AIMessage)
        answer = ""
        for m in reversed(all_msgs):
            if isinstance(m, AIMessage) and not getattr(m, "tool_calls", None):
                content = getattr(m, "content", "") or ""
                if content:
                    answer = content
                    break

        if not answer:
            answer = "抱歉，我暂时无法处理这个问题，请稍后再试。"

        # Detect clarification/escalation from answer text
        status = "success"
        clarification_question = ""

        if "[CLARIFY]" in answer:
            status = "clarification_needed"
            clarification_question = answer.replace("[CLARIFY] ", "").strip()
        elif "[ESCALATE]" in answer:
            status = "escalated"

        return {
            "worker_results": [WorkerResult(
                task_id="",
                worker_type=worker_type,
                answer=answer,
                status=status,
                clarification_question=clarification_question,
                tool_calls_made=0,
                iterations_used=0,
            )],
        }

    builder.add_node("execute", execute)
    builder.add_edge(START, "execute")
    builder.add_edge("execute", END)

    return builder.compile()
