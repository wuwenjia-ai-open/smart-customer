"""Tool Executor 行为单测 — slots 输出 + control 信号

合并自原 test_slot_tracker.py + test_supervisor_routing.py。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


# ── Slots 输出 ────────────────────────────────────────────────────────────────

class TestExecutorSlots:
    def test_track_shipment_executor_emits_order_slot(self):
        from app.lg_agent.workers.tools.executors import TrackShipmentExecutor

        class StubOrderSvc:
            def track_shipment(self, order_id):
                return {"o.orderId": order_id, "o.ShippedDate": "2026-05-01", "o.OrderDate": "2026-04-28"}

        ex = TrackShipmentExecutor(StubOrderSvc())
        result = ex.invoke({"order_id": 1001})
        assert result.success
        assert result.slots == {"last_order_id": 1001}

    def test_compare_products_executor_emits_product_slots(self):
        from app.lg_agent.workers.tools.executors import CompareProductsExecutor

        class StubProductSvc:
            def compare(self, names):
                return [{"p.ProductName": n} for n in names]

        ex = CompareProductsExecutor(StubProductSvc())
        result = ex.invoke({"product_names": ["iPhone 16", "小米 15"]})
        assert result.success
        assert result.slots == {"products_mentioned": ["iPhone 16", "小米 15"]}

    def test_recommend_executor_emits_budget_slot(self):
        from app.lg_agent.workers.tools.executors import RecommendExecutor

        class StubProductSvc:
            def recommend(self, scenario, budget_min, budget_max, preferences, exclude_names, top_k):
                return [{"product_name": "X", "price": 4999}]

        ex = RecommendExecutor(StubProductSvc())
        result = ex.invoke({"scenario": "送父母", "budget_max": 5000})
        assert result.success
        assert result.slots.get("budget_max") == 5000


# ── Control 信号 ──────────────────────────────────────────────────────────────

class TestExecutorControl:
    def test_ask_clarification_emits_clarify(self):
        from app.lg_agent.workers.tools.executors import AskClarificationExecutor
        ex = AskClarificationExecutor()
        result = ex.invoke({"question": "请问您的订单号是？", "missing_field": "order_id"})
        assert result.control is not None
        assert result.control["action"] == "clarify"
        assert "[CLARIFY]" not in result.summary  # 不依赖文本标记

    def test_ask_clarification_with_reroute_to_emits_reroute(self):
        from app.lg_agent.workers.tools.executors import AskClarificationExecutor
        ex = AskClarificationExecutor()
        result = ex.invoke({
            "question": "这是售后问题，正在转接",
            "missing_field": "",
            "reroute_to": "after_sales",
        })
        assert result.control["action"] == "reroute"
        assert result.control["reroute_to"] == "after_sales"

    def test_escalate_emits_escalate(self):
        from app.lg_agent.workers.tools.executors import EscalateToHumanExecutor
        ex = EscalateToHumanExecutor()
        result = ex.invoke({"reason": "需要人工退款", "summary": "退款请求"})
        assert result.control is not None
        assert result.control["action"] == "escalate"
        assert "[ESCALATE]" not in result.summary
