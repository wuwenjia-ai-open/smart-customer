"""Worker Agent unit tests"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.lg_agent.workers.state import WorkerState


def make_state(messages=None, **kwargs):
    return WorkerState(
        messages=messages or [HumanMessage(content="test")],
        worker_type="product_qa",
        task="test task",
        context={},
        iteration_count=0,
        next_action="think",
        tool_to_execute="",
        tool_call_history=[],
        final_answer="",
        status="",
        clarification_question="",
    )


class TestWorkerState:
    def test_state_creation(self):
        state = make_state()
        assert state["worker_type"] == "product_qa"
        assert state["task"] == "test task"

    def test_messages_default(self):
        state = make_state()
        assert len(state["messages"]) == 1
        assert state["messages"][0].content == "test"


class TestToolSchemas:
    def test_all_schemas_importable(self):
        from app.lg_agent.workers.tools.schemas import (
            semantic_search, compare_products, recommend,
            track_shipment, create_ticket, ask_clarification, escalate_to_human,
        )
        s = semantic_search(query="test")
        assert s.query == "test"
        assert s.top_k == 5

    def test_ask_clarification_schema(self):
        from app.lg_agent.workers.tools.schemas import ask_clarification
        a = ask_clarification(question="请问您的订单号是？", missing_field="order_id")
        assert a.missing_field == "order_id"

    def test_ask_clarification_reroute(self):
        from app.lg_agent.workers.tools.schemas import ask_clarification
        a = ask_clarification(
            question="这是售后问题，正在为您转接",
            missing_field="",
            reroute_to="after_sales"
        )
        assert a.reroute_to == "after_sales"


class TestWorkerModules:
    def test_all_workers_importable(self):
        from app.lg_agent.workers import product_qa, order_qa, after_sales, general_chat
        assert hasattr(product_qa, "build")
        assert hasattr(order_qa, "build")
        assert hasattr(after_sales, "build")
        assert hasattr(general_chat, "build")
        assert product_qa.TOOL_SCHEMAS is not None
        assert order_qa.TOOL_SCHEMAS is not None
        assert after_sales.TOOL_SCHEMAS is not None
        assert general_chat.TOOL_SCHEMAS is not None


class TestControlSignalParsing:
    def test_parse_clarify_json(self):
        from app.lg_agent.workers.react_loop import _parse_control_signal
        msg = ToolMessage(
            content='{"records": [], "summary": "请问您的订单号是？", "success": true, "control": {"action": "clarify", "question": "请问您的订单号是？", "missing_field": "order_id"}}',
            tool_call_id="call_1"
        )
        result = _parse_control_signal([msg])
        assert result is not None
        assert result["__ctrl__"] == "clarify"
        assert result["question"] == "请问您的订单号是？"

    def test_parse_escalate_json(self):
        from app.lg_agent.workers.react_loop import _parse_control_signal
        msg = ToolMessage(
            content='{"records": [], "summary": "转人工", "success": true, "control": {"action": "escalate", "reason": "用户要求退款"}}',
            tool_call_id="call_1"
        )
        result = _parse_control_signal([msg])
        assert result is not None
        assert result["__ctrl__"] == "escalate"

    def test_parse_reroute_json(self):
        from app.lg_agent.workers.react_loop import _parse_control_signal
        msg = ToolMessage(
            content='{"records": [], "summary": "转接", "success": true, "control": {"action": "reroute", "reroute_to": "after_sales", "question": "这是售后问题"}}',
            tool_call_id="call_1"
        )
        result = _parse_control_signal([msg])
        assert result is not None
        assert result["__ctrl__"] == "reroute"
        assert result["reroute_to"] == "after_sales"

    def test_parse_no_control(self):
        from app.lg_agent.workers.react_loop import _parse_control_signal
        msg = ToolMessage(
            content="Found 3 products: A, B, C",
            tool_call_id="call_1"
        )
        result = _parse_control_signal([msg])
        assert result is None

    def test_parse_legacy_marker_fallback(self):
        from app.lg_agent.workers.react_loop import _parse_control_signal
        msg = ToolMessage(
            content="[CLARIFY] 请问您的预算是多少？",
            tool_call_id="call_1"
        )
        result = _parse_control_signal([msg])
        assert result is not None
        assert result["__ctrl__"] == "clarify"

    def test_parse_multiple_messages_first_wins(self):
        from app.lg_agent.workers.react_loop import _parse_control_signal
        msgs = [
            ToolMessage(content="OK got it", tool_call_id="call_1"),
            ToolMessage(content='{"records": [], "summary": "test?", "success": true, "control": {"action": "clarify", "question": "test?"}}', tool_call_id="call_2"),
        ]
        result = _parse_control_signal(msgs)
        assert result is not None
        assert result["__ctrl__"] == "clarify"


class TestConfidenceComputation:
    def test_json_success_true(self):
        from app.lg_agent.workers.react_loop import _compute_confidence
        msgs = [
            ToolMessage(content='{"records": [{"name": "A"}, {"name": "B"}], "summary": "found 2", "success": true}', tool_call_id="c1"),
            AIMessage(content="Here are your products..."),
        ]
        conf = _compute_confidence(msgs)
        assert conf == 1.0

    def test_json_success_false(self):
        from app.lg_agent.workers.react_loop import _compute_confidence
        msgs = [
            ToolMessage(content='{"records": [], "summary": "not found", "success": false, "error": "no_results"}', tool_call_id="c1"),
            AIMessage(content="Sorry, nothing found..."),
        ]
        conf = _compute_confidence(msgs)
        assert conf == 0.0

    def test_no_tools_neutral(self):
        from app.lg_agent.workers.react_loop import _compute_confidence
        msgs = [AIMessage(content="Hello! How can I help?")]
        conf = _compute_confidence(msgs)
        assert conf == 0.5

    def test_mixed_json_and_plain_text(self):
        from app.lg_agent.workers.react_loop import _compute_confidence
        msgs = [
            ToolMessage(content='{"success": true, "summary": "ok"}', tool_call_id="c1"),
            ToolMessage(content="Plain text result without JSON structure", tool_call_id="c2"),
            AIMessage(content="Results..."),
        ]
        conf = _compute_confidence(msgs)
        # tool1: JSON success=true → +1, tool2: plain text, neutral → +0.5
        # confidence = 1.5/2 = 0.75
        assert conf == 0.75

    def test_control_signal_tool_counts_as_success(self):
        from app.lg_agent.workers.react_loop import _compute_confidence
        msgs = [
            ToolMessage(content='{"records": [], "summary": "请问您的订单号是？", "success": true, "control": {"action": "clarify", "question": "请问您的订单号是？"}}', tool_call_id="c1"),
        ]
        conf = _compute_confidence(msgs)
        assert conf == 1.0

    def test_plain_text_with_error_marker(self):
        from app.lg_agent.workers.react_loop import _compute_confidence
        msgs = [
            ToolMessage(content='{"error":"connection timeout","success":false}', tool_call_id="c1"),
            AIMessage(content="Failed..."),
        ]
        conf = _compute_confidence(msgs)
        # JSON parse: success=false → 0
        assert conf == 0.0

    def test_mixed_success_and_failure(self):
        from app.lg_agent.workers.react_loop import _compute_confidence
        msgs = [
            ToolMessage(content='{"success": true, "summary": "ok"}', tool_call_id="c1"),
            ToolMessage(content='{"success": false, "error": "not_found"}', tool_call_id="c2"),
            AIMessage(content="Results..."),
        ]
        conf = _compute_confidence(msgs)
        # 1 success / 2 tools = 0.5
        assert conf == 0.5
