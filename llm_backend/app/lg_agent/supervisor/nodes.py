"""Supervisor 节点实现"""
import logging
import uuid
from typing import Any, Dict, List

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.types import Send

from app.lg_agent.supervisor.state import SupervisorState, SubTask, WorkerResult
from app.lg_agent.prompts.supervisor.classify import CLASSIFY_SYSTEM_PROMPT, ClassifyOutput
from app.lg_agent.prompts.supervisor.decompose import DECOMPOSE_SYSTEM_PROMPT, DecomposeOutput
from app.lg_agent.prompts.supervisor.merge import MERGE_SYSTEM_PROMPT

_log = logging.getLogger(__name__)


def make_classify_node(llm: BaseChatModel):
    classify_prompt = ChatPromptTemplate.from_messages([
        ("system", CLASSIFY_SYSTEM_PROMPT),
        ("human", "{query}"),
    ])

    async def classify_intent(state: SupervisorState, *, config) -> Dict[str, Any]:
        msgs = state.get("messages", [])
        query = msgs[-1].content if msgs and hasattr(msgs[-1], "content") else str(msgs[-1])

        result = await (classify_prompt | llm.with_structured_output(ClassifyOutput)).ainvoke({"query": query})

        _log.info(f"Classify: intent={result.intent} out_of_scope={result.out_of_scope}")

        if result.out_of_scope:
            return {
                "intent": "out_of_scope",
                "next_action": "respond",
                "final_answer": "很抱歉，您的问题超出了我们的服务范围。我们专注于智能家居产品的咨询服务，如有相关问题欢迎继续提问。",
            }

        if result.intent == "general_chat":
            return {
                "intent": "general_chat",
                "workers": ["general_chat"],
                "sub_tasks": [SubTask(
                    task_id=str(uuid.uuid4()),
                    worker_type="general_chat",
                    description=query,
                    context={},
                    priority=1,
                )],
                "next_action": "dispatch",
            }

        if result.intent == "multi":
            return {
                "intent": "multi",
                "workers": result.workers,
                "next_action": "decompose",
            }

        # Single worker
        worker = result.intent
        return {
            "intent": result.intent,
            "workers": [worker],
            "sub_tasks": [SubTask(
                task_id=str(uuid.uuid4()),
                worker_type=worker,
                description=query,
                context={},
                priority=1,
            )],
            "next_action": "dispatch",
        }

    return classify_intent


def make_decompose_node(llm: BaseChatModel):
    decompose_prompt = ChatPromptTemplate.from_messages([
        ("system", DECOMPOSE_SYSTEM_PROMPT),
        ("human", "用户问题: {question}\n需要的 Worker: {workers}\n\n请拆解为子任务:"),
    ])

    async def decompose_tasks(state: SupervisorState, *, config) -> Dict[str, Any]:
        msgs = state.get("messages", [])
        query = msgs[-1].content if msgs and hasattr(msgs[-1], "content") else str(msgs[-1])
        workers = state.get("workers", [])

        result = await (decompose_prompt | llm.with_structured_output(DecomposeOutput)).ainvoke({
            "question": query,
            "workers": ", ".join(workers),
        })

        sub_tasks = []
        for t in result.sub_tasks:
            sub_tasks.append(SubTask(
                task_id=str(uuid.uuid4()),
                worker_type=t.worker_type,
                description=t.description,
                context=t.context,
                priority=t.priority,
            ))

        _log.info(f"Decompose: {len(sub_tasks)} sub-tasks")
        return {"sub_tasks": sub_tasks, "next_action": "dispatch"}

    return decompose_tasks


def dispatch_workers(state: SupervisorState, *, config) -> List[Send]:
    """使用 Send() 并行分发子任务到各 Worker 子图"""
    sub_tasks = state.get("sub_tasks", [])
    msgs = state.get("messages", [])

    sends = []
    for task in sub_tasks:
        worker_state = {
            "messages": list(msgs),
            "worker_type": task["worker_type"],
            "task": task["description"],
            "context": task.get("context", {}),
            "iteration_count": 0,
            "next_action": "think",
            "tool_call_history": [],
            "final_answer": "",
            "status": "",
            "clarification_question": "",
        }
        sends.append(Send(task["worker_type"], worker_state))

    _log.info(f"Dispatch: {len(sends)} workers -> {[s.node for s in sends]}")
    return sends


def make_merge_node(llm: BaseChatModel):
    merge_prompt = ChatPromptTemplate.from_messages([
        ("system", MERGE_SYSTEM_PROMPT),
        ("human", "Worker 执行结果:\n{worker_results}\n\n对话历史:\n{context}\n\n请生成用户回复:"),
    ])

    async def merge_results(state: SupervisorState, *, config) -> Dict[str, Any]:
        results = state.get("worker_results", [])
        if not results:
            return {"final_answer": "抱歉，处理过程中出现了问题，请稍后再试。", "next_action": "respond"}

        # Check for clarifications
        for r in results:
            if r.get("status") == "clarification_needed":
                return {
                    "pending_clarification": r.get("clarification_question", ""),
                    "needs_clarification": True,
                    "next_action": "clarify",
                }

        if len(results) == 1:
            return {
                "final_answer": results[0].get("answer", ""),
                "next_action": "respond",
            }

        # Multiple results: merge via LLM
        msgs = state.get("messages", [])
        context = "\n".join(
            str(m.content)[:200] for m in msgs[-4:]
        ) if msgs else "无"

        results_text = "\n---\n".join(
            f"[{r.get('worker_type', 'unknown')}] {r.get('answer', '')}"
            for r in results
        )

        response = await (merge_prompt | llm).ainvoke({
            "worker_results": results_text,
            "context": context,
        })

        answer = response.content if hasattr(response, "content") else str(response)
        return {"final_answer": answer, "next_action": "respond"}

    return merge_results


async def respond_node(state: SupervisorState, *, config) -> Dict[str, Any]:
    answer = state.get("final_answer", "抱歉，我暂时无法回答这个问题。")
    return {"messages": [AIMessage(content=answer)]}
