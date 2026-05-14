"""Worker ReAct loop unit tests"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from app.lg_agent.workers.react_loop import route_after_think, route_after_observe, MAX_ITERATIONS
from app.lg_agent.workers.state import WorkerState


def make_state(messages=None, iteration_count=0, next_action="think", **kwargs):
    return WorkerState(
        messages=messages or [HumanMessage(content="test")],
        worker_type="product_qa",
        task="test task",
        context={},
        iteration_count=iteration_count,
        next_action=next_action,
        tool_to_execute="",
        tool_call_history=[],
        final_answer="",
        status="",
        clarification_question="",
    )


class TestRouteAfterThink:
    def test_has_tool_calls_routes_to_act(self):
        msg = AIMessage(content="", tool_calls=[{"name": "semantic_search", "args": {"query": "test"}, "id": "1"}])
        state = make_state(messages=[HumanMessage(content="hi"), msg])
        assert route_after_think(state) == "act"

    def test_no_tool_calls_routes_to_finish(self):
        msg = AIMessage(content="Here is your answer")
        state = make_state(messages=[HumanMessage(content="hi"), msg])
        assert route_after_think(state) == "finish"

    def test_empty_messages_routes_to_finish(self):
        state = make_state(messages=[])
        assert route_after_think(state) == "finish"


class TestRouteAfterObserve:
    def test_continue_returns_think(self):
        state = make_state(next_action="think")
        assert route_after_observe(state) == "think"

    def test_finish_returns_finish(self):
        state = make_state(next_action="finish")
        assert route_after_observe(state) == "finish"


class TestObserveExitConditions:
    def test_max_iterations_forces_finish(self):
        """When iteration_count >= MAX_ITERATIONS, observe should force finish"""
        from app.lg_agent.workers.react_loop import observe_node

        state = make_state(iteration_count=MAX_ITERATIONS - 1, tool_to_execute="semantic_search")
        state["messages"].append(
            ToolMessage(content="Records: [{'product_name': 'Test'}]", tool_call_id="1")
        )

        result = observe_node(state, config=RunnableConfig())
        assert result["next_action"] == "finish"
        assert result["iteration_count"] == MAX_ITERATIONS


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
