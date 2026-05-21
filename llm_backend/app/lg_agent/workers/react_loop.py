"""Worker Agent — LangChain create_agent 薄封装"""
import asyncio
import json
import re
from operator import add
from typing import Annotated, Any, Dict, List, Optional

from langgraph.errors import GraphRecursionError
from langgraph.graph import StateGraph, START, END, add_messages
from langgraph.prebuilt import create_react_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, ToolMessage
from typing_extensions import TypedDict
from loguru import logger as _log

from app.lg_agent.supervisor.state import WorkerResult

# 全局信号量，限制并行 LLM API 调用数，防止 429 限流
_LLM_SEMAPHORE = asyncio.Semaphore(3)

# ReAct 步数上限，防止无限 think-act 循环
MAX_RECURSION = 30  # 约 10-15 轮


def _parse_control_signal(tool_msgs: List[ToolMessage]) -> Optional[dict]:
    """从 ToolMessage 列表中提取结构化 control 信号"""
    for msg in tool_msgs:
        content = getattr(msg, "content", "") or ""
        if not content:
            continue
        # JSON 解析: {"control": {"action": "clarify", ...}}
        try:
            data = json.loads(content.strip())
            if isinstance(data, dict):
                ctrl = data.get("control")
                if ctrl and isinstance(ctrl, dict):
                    action = ctrl.get("action", "")
                    return {
                        "__ctrl__": action,
                        "question": ctrl.get("question", ""),
                        "reroute_to": ctrl.get("reroute_to", ""),
                        "reason": ctrl.get("reason", ""),
                    }
        except json.JSONDecodeError:
            pass
        # 兜底：旧版文本标记
        if "[CLARIFY]" in content:
            question = content.replace("[CLARIFY]", "").strip()
            return {"__ctrl__": "clarify", "question": question}
        if "[ESCALATE]" in content:
            return {"__ctrl__": "escalate", "reason": content.replace("[ESCALATE]", "").strip()}
    return None


def _collect_slots(tool_msgs: List[ToolMessage]) -> dict:
    """从 ToolMessage 列表中提取所有 slots,后写覆盖同 key。"""
    merged: dict = {}
    for msg in tool_msgs:
        content = getattr(msg, "content", "") or ""
        if not content:
            continue
        try:
            data = json.loads(content.strip())
            if isinstance(data, dict) and data.get("slots"):
                merged.update(data["slots"])
        except (json.JSONDecodeError, AttributeError):
            pass
    return merged


def _compute_confidence(all_msgs: list) -> float:
    """基于工具返回的 success 字段计算置信度"""
    tool_count = 0
    success_count = 0
    for msg in all_msgs:
        if isinstance(msg, ToolMessage):
            tool_count += 1
            content = getattr(msg, "content", "") or ""
            # 优先 JSON 解析 — 检查 ToolResult.success 字段
            try:
                data = json.loads(content.strip())
                if isinstance(data, dict):
                    if data.get("success") is True:
                        success_count += 1
                    elif data.get("success") is False:
                        pass  # 明确的失败
                    elif data.get("control"):
                        success_count += 1  # 控制信号工具调用视为成功
                    else:
                        success_count += 0.5  # JSON 但无 success 字段
                    continue
            except (json.JSONDecodeError, AttributeError):
                pass
            # 非 JSON 兜底：检查 error 标记
            if '"success":false' in content or '"error":"' in content:
                pass
            elif len(content.strip()) > 0:
                success_count += 0.5  # 纯文本无错误标记 — 中性
    if tool_count == 0:
        return 0.5
    confidence = max(0.0, min(1.0, success_count / tool_count))
    return round(confidence, 2)


class WorkerInternalState(TypedDict):
    """Worker 内部隔离状态 — 不会泄露到 Supervisor

    messages 不用 add_messages reducer：避免 checkpoint 把上轮 worker
    残留的对话追加到本轮 Send 传入的单条 HumanMessage，导致 ReAct agent
    看到上轮 AIMessage 后复用其内容。
    """
    messages: List[AnyMessage]


class WorkerOutputState(TypedDict):
    """Worker 输出 — 只有 worker_results 会合并到 Supervisor"""
    worker_results: Annotated[List[WorkerResult], add]


def _fallback(worker_type: str, message: str) -> Dict[str, Any]:
    """超时/异常时的降级返回"""
    return {
        "worker_results": [WorkerResult(
            task_id="",
            worker_type=worker_type,
            answer=message,
            status="error",
            clarification_question="",
            tool_calls_made=0,
            iterations_used=0,
            confidence=0.0,
            reroute_to="",
            control_action="",
            slots={},
        )],
    }


def build_worker(llm: BaseChatModel, tools: list, system_prompt: str, worker_type: str) -> StateGraph:
    """构建 Worker Agent — create_agent + 结果提取"""

    react_agent = create_react_agent(
        llm,
        tools,
        prompt=system_prompt,
    )

    builder = StateGraph(WorkerInternalState, output=WorkerOutputState)

    async def execute(state: WorkerInternalState) -> Dict[str, Any]:
        msg_summary = " | ".join(
            f"{type(m).__name__}:{(getattr(m, 'content', '') or '')[:30]}"
            for m in state["messages"]
        )
        _log.info(f"Worker {worker_type}: received {len(state['messages'])} msgs [{msg_summary}]")

        original_len = len(state["messages"])  # 记录原始历史长度，区分新生成内容

        async with _LLM_SEMAPHORE:
            try:
                result = await react_agent.ainvoke(
                    {"messages": state["messages"]},
                    config={"recursion_limit": MAX_RECURSION},
                )
            except GraphRecursionError:
                _log.warning(f"Worker {worker_type}: recursion limit {MAX_RECURSION} exceeded")
                return _fallback(worker_type, "处理步骤过多，已为您简化回答。")

        all_msgs = result.get("messages", [])
        # 只看本轮 react_agent 新追加的消息，避免误把上轮的 AIMessage 当成本轮答案
        new_msgs = all_msgs[original_len:]

        # 收集本轮 ToolMessage 用于 control 信号检测
        tool_msgs = [m for m in new_msgs if isinstance(m, ToolMessage)]

        # 结构化 control 信号检测
        control = _parse_control_signal(tool_msgs)
        # 提取本轮工具执行的 slots
        worker_slots = _collect_slots(tool_msgs)

        # 提取本轮最终回答（只在新消息里找）
        answer = ""
        for m in reversed(new_msgs):
            if isinstance(m, AIMessage) and not getattr(m, "tool_calls", None):
                content = getattr(m, "content", "") or ""
                if content:
                    answer = content
                    break

        if not answer:
            answer = "抱歉，我暂时无法处理这个问题，请稍后再试。"

        # 从回答中清理遗留的控制标记（兜底）
        answer = re.sub(r'\s*\[CLARIFY\]\s*', '', answer)
        answer = re.sub(r'\s*\[ESCALATE\]\s*', '', answer)
        answer = answer.strip()

        # 兜底：如果 answer 以第三人称分析语句开头，说明 prompt 指令未被遵守，
        # 截取第一个"亲～"之后的内容；若无则降级
        _ANALYSIS_PREFIXES = ("用户咨询", "用户表示", "用户想", "用户在", "根据分析", "分析：")
        if any(answer.startswith(p) for p in _ANALYSIS_PREFIXES):
            _log.warning(f"Worker {worker_type}: answer starts with analysis text, trimming: {answer[:60]!r}")
            idx = answer.find("亲～")
            answer = answer[idx:] if idx >= 0 else "抱歉，我暂时无法处理这个问题，请稍后再试。"

        # 计算置信度（只看本轮新消息，避免历史污染）
        confidence = _compute_confidence(new_msgs)

        # 确定状态
        status = "success"
        clarification_question = ""
        reroute_to = ""
        control_action = ""

        if control:
            action = control.get("__ctrl__", "")
            if action == "clarify":
                status = "clarification_needed"
                clarification_question = control.get("question", answer)
                control_action = "clarify"
                answer = clarification_question
            elif action == "reroute":
                reroute_to = control.get("reroute_to", "")
                status = "reroute" if reroute_to else "clarification_needed"
                control_action = "reroute"
                answer = control.get("question", answer)
                clarification_question = answer
            elif action == "escalate":
                status = "escalated"
                control_action = "escalate"
                answer = control.get("reason", answer)

        return {
            "worker_results": [WorkerResult(
                task_id="",
                worker_type=worker_type,
                answer=answer,
                status=status,
                clarification_question=clarification_question,
                tool_calls_made=len(tool_msgs),
                iterations_used=0,
                confidence=confidence,
                reroute_to=reroute_to,
                control_action=control_action,
                slots=worker_slots,
            )],
        }

    builder.add_node("execute", execute)
    builder.add_edge(START, "execute")
    builder.add_edge("execute", END)

    return builder.compile()
