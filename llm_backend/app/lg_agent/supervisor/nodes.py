"""Supervisor 节点实现"""
import json
import logging
import uuid
from typing import Any, AsyncIterator, Dict, List

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.prompts import ChatPromptTemplate
from langgraph.types import Command, Send

from app.lg_agent.supervisor.state import SupervisorState, SubTask, WorkerResult
from app.lg_agent.prompts.supervisor.classify import CLASSIFY_SYSTEM_PROMPT, ClassifyOutput
from app.lg_agent.prompts.supervisor.decompose import DECOMPOSE_SYSTEM_PROMPT, DecomposeOutput
from app.lg_agent.prompts.supervisor.merge import MERGE_SYSTEM_PROMPT

_log = logging.getLogger(__name__)

MAX_REROUTE = 2  # 重路由上限


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
                "reroute_count": 0,
            }

        if result.intent == "multi":
            return {
                "intent": "multi",
                "workers": result.workers,
                "next_action": "decompose",
                "reroute_count": 0,
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
            "reroute_count": 0,
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

        _log.info(f"Decompose: {len(sub_tasks)} sub-tasks -> {[t['worker_type'] for t in sub_tasks]}")
        return {"sub_tasks": sub_tasks, "next_action": "dispatch"}

    return decompose_tasks


def dispatch_workers(state: SupervisorState) -> Command:
    """使用 Command(goto=[Send]) 并行分发子任务到各 Worker 子图"""
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
            "tool_to_execute": "",
            "tool_call_history": [],
            "final_answer": "",
            "status": "",
            "clarification_question": "",
        }
        sends.append(Send(task["worker_type"], worker_state))

    _log.info(f"Dispatch: {len(sends)} workers -> {[s.node for s in sends]}")
    return Command(goto=sends)


def make_merge_node(llm: BaseChatModel):
    merge_prompt = ChatPromptTemplate.from_messages([
        ("system", MERGE_SYSTEM_PROMPT),
        ("human", "Worker 执行结果:\n{worker_results}\n\n对话历史:\n{context}\n\n请生成用户回复:"),
    ])

    async def merge_results(state: SupervisorState, *, config) -> Dict[str, Any]:
        results = state.get("worker_results", [])
        reroute_count = state.get("reroute_count", 0)

        if not results:
            return {"final_answer": "抱歉，处理过程中出现了问题，请稍后再试。", "next_action": "respond"}

        # 检查 reroute：Worker 判断分错类，建议转给其他 Worker
        for r in results:
            if r.get("control_action") == "reroute" and r.get("reroute_to"):
                if reroute_count < MAX_REROUTE:
                    target = r["reroute_to"]
                    _log.info(f"Reroute: {r['worker_type']} -> {target} (count={reroute_count + 1})")
                    msgs = state.get("messages", [])
                    query = msgs[-1].content if msgs and hasattr(msgs[-1], "content") else str(msgs[-1])
                    return {
                        "workers": [target],
                        "reroute_count": reroute_count + 1,
                        "sub_tasks": [SubTask(
                            task_id=str(uuid.uuid4()),
                            worker_type=target,
                            description=query,
                            context={"reroute_reason": r.get("answer", "")},
                            priority=1,
                        )],
                        "next_action": "dispatch",
                    }
                else:
                    _log.warning(f"Max reroute exceeded, responding with current results")

        # 检查澄清
        for r in results:
            if r.get("status") == "clarification_needed":
                return {
                    "pending_clarification": r.get("clarification_question", ""),
                    "needs_clarification": True,
                    "next_action": "clarify",
                    "worker_results": [],
                }

        # 单结果快速通道：高置信 + 无兜底话术 + 长度合理 → 直接透传
        if len(results) == 1:
            r = results[0]
            confidence = r.get("confidence", 0.5)
            answer = r.get("answer", "")

            # 规则门禁：检测兜底/失败话术
            _low_quality_markers = [
                "抱歉，我暂时无法",
                "无法处理这个问题",
                "系统开小差",
            ]
            is_fallback = any(m in answer for m in _low_quality_markers)
            is_too_short = len(answer.strip()) < 20

            if confidence >= 0.7 and not is_fallback and not is_too_short:
                return {"final_answer": answer, "next_action": "respond", "worker_results": []}

            # 不满足快速通道 → 走 LLM 合成做二次加工
            _log.info(
                f"Single result gate failed: confidence={confidence} "
                f"fallback={is_fallback} short={is_too_short} — routing to LLM merge"
            )

        # LLM 合成（多结果 或 不满足快速通道的单结果）：按置信度排序合并
        sorted_results = sorted(results, key=lambda x: x.get("confidence", 0), reverse=True)

        msgs = state.get("messages", [])
        context = "\n".join(
            str(m.content)[:200] for m in msgs[-4:]
        ) if msgs else "无"

        results_text = "\n---\n".join(
            f"[{r.get('worker_type', 'unknown')}] (置信度: {r.get('confidence', 0):.0%})\n{r.get('answer', '')}"
            for r in sorted_results
        )

        response = await (merge_prompt | llm).ainvoke({
            "worker_results": results_text,
            "context": context,
        })

        answer = response.content if hasattr(response, "content") else str(response)
        return {"final_answer": answer, "next_action": "respond", "worker_results": []}

    return merge_results


def make_respond_node(llm: BaseChatModel = None):
    """生成最终回复节点 — 支持流式输出"""

    async def respond_node(state: SupervisorState, *, config) -> Dict[str, Any]:
        answer = state.get("final_answer", "抱歉，我暂时无法回答这个问题。")
        return {"messages": [AIMessage(content=answer)]}

    return respond_node


async def respond_node_stream(state: SupervisorState, *, config) -> AsyncIterator[Dict[str, Any]]:
    """流式版 respond_node — yield AIMessageChunk"""
    answer = state.get("final_answer", "抱歉，我暂时无法回答这个问题。")
    # 按 8 字符块输出，模拟 token 级流式
    for i in range(0, len(answer), 8):
        chunk = answer[i:i + 8]
        yield {"messages": [AIMessageChunk(content=chunk)]}
