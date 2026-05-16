"""Supervisor routing unit tests"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from app.lg_agent.supervisor.state import SupervisorState, SubTask, WorkerResult
from app.lg_agent.prompts.supervisor.classify import CLASSIFY_SYSTEM_PROMPT
from app.lg_agent.prompts.supervisor.decompose import DECOMPOSE_SYSTEM_PROMPT
from app.lg_agent.prompts.supervisor.merge import MERGE_SYSTEM_PROMPT


class TestPromptContent:
    def test_classify_prompt_has_all_intents(self):
        for intent in ["general_chat", "product_qa", "order_qa", "after_sales", "multi"]:
            assert intent in CLASSIFY_SYSTEM_PROMPT, f"Missing intent: {intent}"

    def test_classify_mentions_out_of_scope(self):
        assert "out_of_scope" in CLASSIFY_SYSTEM_PROMPT

    def test_decompose_prompt_mentions_priority(self):
        assert "priority" in DECOMPOSE_SYSTEM_PROMPT

    def test_merge_prompt_style(self):
        assert "亲～" in MERGE_SYSTEM_PROMPT

    def test_merge_prompt_mentions_confidence(self):
        assert "置信度" in MERGE_SYSTEM_PROMPT


class TestStateTypes:
    def test_subtask_creation(self):
        st = SubTask(
            task_id="1",
            worker_type="product_qa",
            description="search for robot vacuums",
            context={},
            priority=1,
        )
        assert st["worker_type"] == "product_qa"

    def test_worker_result_creation(self):
        wr = WorkerResult(
            task_id="1",
            worker_type="product_qa",
            answer="Found 3 products",
            status="success",
            clarification_question="",
            tool_calls_made=2,
            iterations_used=3,
            confidence=0.8,
            reroute_to="",
            control_action="",
        )
        assert wr["status"] == "success"
        assert wr["iterations_used"] == 3
        assert wr["confidence"] == 0.8

    def test_worker_result_reroute(self):
        wr = WorkerResult(
            task_id="1",
            worker_type="product_qa",
            answer="这是售后问题",
            status="reroute",
            clarification_question="",
            tool_calls_made=0,
            iterations_used=1,
            confidence=0.0,
            reroute_to="after_sales",
            control_action="reroute",
        )
        assert wr["reroute_to"] == "after_sales"
        assert wr["control_action"] == "reroute"

    def test_worker_results_accumulate_with_add(self):
        r1 = WorkerResult(task_id="1", worker_type="a", answer="ok", status="success",
                          clarification_question="", tool_calls_made=1, iterations_used=1,
                          confidence=0.9, reroute_to="", control_action="")
        r2 = WorkerResult(task_id="2", worker_type="b", answer="ok", status="success",
                          clarification_question="", tool_calls_made=1, iterations_used=1,
                          confidence=0.7, reroute_to="", control_action="")
        combined = [r1] + [r2]
        assert len(combined) == 2


class TestToolResultControl:
    def test_tool_result_with_control(self):
        from app.lg_agent.workers.tools.registry import ToolResult
        tr = ToolResult(
            records=[{"question": "test"}],
            summary="test question",
            control={"action": "clarify", "question": "test"}
        )
        assert tr.control is not None
        assert tr.control["action"] == "clarify"

    def test_tool_result_no_control(self):
        from app.lg_agent.workers.tools.registry import ToolResult
        tr = ToolResult(
            records=[{"product_name": "X"}],
            summary="found product X"
        )
        assert tr.control is None


class TestExecutorControl:
    def test_ask_clarification_has_control(self):
        from app.lg_agent.workers.tools.executors import AskClarificationExecutor
        ex = AskClarificationExecutor()
        result = ex.invoke({"question": "请问您的订单号是？", "missing_field": "order_id"})
        assert result.control is not None
        assert result.control["action"] == "clarify"
        assert "[CLARIFY]" not in result.summary  # 不再依赖文本标记

    def test_ask_clarification_reroute_control(self):
        from app.lg_agent.workers.tools.executors import AskClarificationExecutor
        ex = AskClarificationExecutor()
        result = ex.invoke({
            "question": "这是售后问题，正在转接",
            "missing_field": "",
            "reroute_to": "after_sales"
        })
        assert result.control["action"] == "reroute"
        assert result.control["reroute_to"] == "after_sales"

    def test_escalate_has_control(self):
        from app.lg_agent.workers.tools.executors import EscalateToHumanExecutor
        ex = EscalateToHumanExecutor()
        result = ex.invoke({"reason": "需要人工退款", "summary": "退款请求"})
        assert result.control is not None
        assert result.control["action"] == "escalate"
        assert "[ESCALATE]" not in result.summary
