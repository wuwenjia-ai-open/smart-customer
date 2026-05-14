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


class TestWorkerModules:
    def test_all_workers_importable(self):
        from app.lg_agent.workers import product_qa, order_qa, after_sales, general_chat
        assert hasattr(product_qa, "build")
        assert hasattr(order_qa, "build")
        assert hasattr(after_sales, "build")
        assert hasattr(general_chat, "build")
        assert product_qa.TOOLS is not None
        assert order_qa.TOOLS is not None
        assert after_sales.TOOLS is not None
        assert general_chat.TOOLS is not None
