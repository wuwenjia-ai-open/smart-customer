"""Worker ReAct 内部逻辑单测 — 控制信号解析 + 置信度计算"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from langchain_core.messages import AIMessage, ToolMessage


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
