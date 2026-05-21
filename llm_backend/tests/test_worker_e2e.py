"""Worker 端到端工具链评测 — Layer 3

测试每个 Worker 在 ReAct 循环中的工具选择、调用、整合能力：
  1. 注入 Mock 工具执行器（CountingProxy 包装），跳过真实 DB
  2. 用真实 LLM (按 tier 路由) 驱动 ReAct 循环
  3. 验证：
     - 期望工具是否被调用 / 禁止的工具是否未被调用
     - status / control_action 是否符合预期
     - 答案是否包含/不包含特定字符串（防幻觉）

运行方式:
    pytest tests/test_worker_e2e.py -v -s -m integration
    pytest tests/test_worker_e2e.py::TestWorkerE2E::test_worker_e2e -v -s -m integration
"""
import asyncio
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from langchain_core.messages import HumanMessage

from app.services.llm_factory import LLMFactory
from app.lg_agent.workers import product_qa, order_qa, after_sales, general_chat
from app.lg_agent.workers.tools.registry import TOOL_REGISTRY, ToolResult, register_tool
from app.lg_agent.workers.tools.executors import (
    AskClarificationExecutor, EscalateToHumanExecutor,
)


# ── Mock / Proxy 执行器 ──────────────────────────────────────────────────────

class MockExecutor:
    """返回预设响应的执行器。多个响应按调用顺序返回，超出后重复最后一个。"""

    def __init__(self, *responses: dict):
        self.responses = responses or ({},)
        self._idx = 0

    def invoke(self, args: Dict[str, Any]) -> ToolResult:
        idx = min(self._idx, len(self.responses) - 1)
        self._idx += 1
        r = self.responses[idx]
        return ToolResult(
            records=r.get("records", []),
            summary=r.get("summary", ""),
            success=r.get("success", True),
            error=r.get("error", ""),
            control=r.get("control"),
            slots=r.get("slots"),
        )


class CountingProxy:
    """代理执行器：记录所有调用 + 委托给内部 executor"""

    def __init__(self, inner):
        self._inner = inner
        self.calls: List[Dict[str, Any]] = []

    def invoke(self, args: Dict[str, Any]) -> ToolResult:
        self.calls.append(args)
        return self._inner.invoke(args)


# ── 测试用例 ──────────────────────────────────────────────────────────────────

@dataclass
class WorkerCase:
    case_id: str
    worker_type: str
    query: str
    # 工具名 -> 多次调用的响应列表
    mock_responses: Dict[str, List[dict]] = field(default_factory=dict)
    # 必须被调用至少一次的工具
    expected_called: List[str] = field(default_factory=list)
    # 不应被调用的工具
    forbidden: List[str] = field(default_factory=list)
    expected_status: str = ""          # success / clarification_needed / escalated / reroute / error
    expected_control: str = ""         # clarify / escalate / reroute / ""
    must_contain: List[str] = field(default_factory=list)
    must_not_contain: List[str] = field(default_factory=list)


WORKER_CASES: List[WorkerCase] = [
    # ── product_qa: 推荐 — 单工具调用 ──────────────────────────────────────────
    WorkerCase(
        case_id="product_recommend",
        worker_type="product_qa",
        query="推荐一款 5000 元以内的游戏笔记本",
        mock_responses={
            "recommend": [{
                "records": [
                    {"product_name": "联想拯救者 Y7000P", "price": 4999,
                     "score": 4.8, "summary": "RTX 4060 + i7-13620H + 16GB"},
                    {"product_name": "ROG 魔霸新锐", "price": 4799,
                     "score": 4.7, "summary": "RTX 4060 + R7-7735H"},
                ],
                "summary": "推荐 联想拯救者 Y7000P(¥4999), ROG 魔霸新锐(¥4799)",
                "slots": {"products_mentioned": ["联想拯救者 Y7000P", "ROG 魔霸新锐"]},
            }],
        },
        expected_called=["recommend"],
        forbidden=["compare_products"],
        expected_status="success",
        must_contain=["联想拯救者"],
    ),
    # ── product_qa: 对比 — compare_products 调用 ───────────────────────────────
    WorkerCase(
        case_id="product_compare",
        worker_type="product_qa",
        query="iPhone 16 Pro 和小米 15 Ultra 哪个更值得买，对比一下",
        mock_responses={
            "compare_products": [{
                "records": [
                    {"product_name": "iPhone 16 Pro", "price": 7999,
                     "score": 4.9, "battery_mah": 3582, "chip": "A18 Pro"},
                    {"product_name": "小米 15 Ultra", "price": 6499,
                     "score": 4.8, "battery_mah": 5410, "chip": "骁龙 8 Gen 4"},
                ],
                "summary": "已获取 2 个产品的对比数据",
            }],
        },
        expected_called=["compare_products"],
        expected_status="success",
        must_contain=["iPhone 16 Pro", "小米 15 Ultra"],
    ),
    # ── product_qa: 工具返回空 — 不应虚构 (允许调澄清或直接告知未找到) ────
    WorkerCase(
        case_id="product_no_match",
        worker_type="product_qa",
        query="推荐一款火星专用智能手机",
        mock_responses={
            "recommend": [{
                "records": [], "summary": "未找到符合条件的产品",
                "success": False, "error": "no_match",
            }],
            "semantic_search": [{
                "records": [], "summary": "未找到匹配的产品",
                "success": False, "error": "no_results",
            }],
        },
        # 不检查 status — 搜索失败后调澄清(clarification_needed)或直接答(success)都合理
        must_not_contain=["华为 Mate 70", "iPhone 16 Pro", "小米 15 Ultra"],
    ),
    # ── order_qa: 缺少订单号 — 触发澄清 ───────────────────────────────────────
    WorkerCase(
        case_id="order_no_id_clarify",
        worker_type="order_qa",
        query="我的订单到哪了",
        mock_responses={},
        expected_called=["ask_clarification"],
        expected_status="clarification_needed",
        expected_control="clarify",
        must_contain=["订单"],
    ),
    # ── order_qa: 有订单号 — track_shipment 调用 ──────────────────────────────
    WorkerCase(
        case_id="order_track",
        worker_type="order_qa",
        query="查询订单 #10088 的物流状态",
        mock_responses={
            "track_shipment": [{
                "records": [{
                    "o.OrderNo": 10088,
                    "o.OrderDate": "2026-05-15",
                    "o.ShippedDate": "2026-05-16",
                    "o.TrackingNo": "SF1234567890",
                    "o.Status": "运输中",
                }],
                "summary": "订单 #10088: 下单 2026-05-15, 已发货",
                "slots": {"last_order_id": 10088},
            }],
        },
        expected_called=["track_shipment"],
        expected_status="success",
        must_contain=["10088"],
    ),
    # ── after_sales: FAQ 查询 ─────────────────────────────────────────────────
    WorkerCase(
        case_id="after_sales_faq",
        worker_type="after_sales",
        query="你们的退货政策是什么",
        mock_responses={
            "search_faq": [{
                "records": [{
                    "q": "退货政策",
                    "a": "支持七天无理由退货；30 天内质量问题免运费退换；签收 48 小时内反馈外观/破损问题。",
                }],
                "summary": "找到 1 条关于'退货政策'的常见问题",
            }],
        },
        expected_called=["search_faq"],
        expected_status="success",
        must_contain=["天无理由"],  # 允许"七天"或"7天"
    ),
    # ── after_sales: 转人工 ─────────────────────────────────────────────────
    WorkerCase(
        case_id="after_sales_escalate",
        worker_type="after_sales",
        query="我已经投诉过两次了，必须立刻转人工客服处理",
        mock_responses={
            # search_faq 提供一个无关的兜底，让 LLM 倾向于直接转人工
            "search_faq": [{
                "records": [], "summary": "未找到相关 FAQ",
                "success": False, "error": "no_results",
            }],
        },
        expected_called=["escalate_to_human"],
        expected_status="escalated",
        expected_control="escalate",
    ),
    # ── general_chat: 简单问候 — 不应调用工具 ──────────────────────────────────
    WorkerCase(
        case_id="general_greeting",
        worker_type="general_chat",
        query="你好，谢谢",
        mock_responses={},
        forbidden=["ask_clarification"],
        expected_status="success",
    ),
]


PASS_RATE_THRESHOLD = 0.75
_CONCURRENCY = 2  # 并发上限，控制 LLM 429


# ── Worker 配置 ────────────────────────────────────────────────────────────────

# Worker → (模块, LLM tier, 用到的工具)
_WORKER_CONFIG = {
    "product_qa":   (product_qa,   "tool",   ["semantic_search", "compare_products", "recommend", "ask_clarification"]),
    "order_qa":     (order_qa,     "tool",   ["track_shipment", "ask_clarification"]),
    "after_sales":  (after_sales,  "reason", ["search_faq", "create_ticket", "escalate_to_human", "ask_clarification"]),
    "general_chat": (general_chat, "flash",  ["ask_clarification"]),
}

# 不需要 mock 的真实控制信号执行器
def _real_executor(name: str):
    if name == "ask_clarification":
        return AskClarificationExecutor()
    if name == "escalate_to_human":
        return EscalateToHumanExecutor()
    return None


def _install_proxies(case: WorkerCase) -> Dict[str, CountingProxy]:
    """为 case 对应 worker 的所有工具安装 CountingProxy + Mock/真实 executor"""
    _, _, needed = _WORKER_CONFIG[case.worker_type]
    proxies: Dict[str, CountingProxy] = {}
    for name in needed:
        if name in case.mock_responses:
            inner = MockExecutor(*case.mock_responses[name])
        elif _real_executor(name) is not None:
            inner = _real_executor(name)
        else:
            # 数据工具未配 mock → 默认空响应，让 LLM 自行决定回退
            inner = MockExecutor({
                "records": [], "summary": "暂无数据",
                "success": False, "error": "no_data",
            })
        proxy = CountingProxy(inner)
        register_tool(name, proxy)
        proxies[name] = proxy
    return proxies


# ── 测试 ───────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestWorkerE2E:
    """Worker 端到端工具链评测"""

    def _build_worker(self, worker_type: str):
        module, tier, _ = _WORKER_CONFIG[worker_type]
        llm = LLMFactory.create_llm(tier)
        return module.build(llm)

    async def _run_one(self, sem, case: WorkerCase) -> dict:
        async with sem:
            original = dict(TOOL_REGISTRY)
            proxies = _install_proxies(case)
            try:
                worker = self._build_worker(case.worker_type)
                state = {"messages": [HumanMessage(content=case.query)]}
                result = await worker.ainvoke(state)
            finally:
                TOOL_REGISTRY.clear()
                TOOL_REGISTRY.update(original)

            wr = result["worker_results"][0]
            answer = wr.get("answer", "") or ""

            tool_call_counts = {name: len(p.calls) for name, p in proxies.items()}

            failures: List[str] = []
            for name in case.expected_called:
                if name not in proxies:
                    failures.append(f"unknown_tool: {name}")
                elif len(proxies[name].calls) == 0:
                    failures.append(f"not_called: {name}")
            for name in case.forbidden:
                if name in proxies and len(proxies[name].calls) > 0:
                    failures.append(f"forbidden_called: {name}")
            if case.expected_status and wr.get("status") != case.expected_status:
                failures.append(f"status: want={case.expected_status} got={wr.get('status')}")
            if case.expected_control and wr.get("control_action") != case.expected_control:
                failures.append(f"control: want={case.expected_control} got={wr.get('control_action')}")
            for s in case.must_contain:
                if s not in answer:
                    failures.append(f"missing: '{s}'")
            for s in case.must_not_contain:
                if s in answer:
                    failures.append(f"hallucinated: '{s}'")

            return {
                "case_id": case.case_id,
                "worker_type": case.worker_type,
                "answer": answer,
                "status": wr.get("status"),
                "control_action": wr.get("control_action"),
                "confidence": wr.get("confidence"),
                "tool_calls_made": wr.get("tool_calls_made"),
                "tool_call_counts": tool_call_counts,
                "failures": failures,
                "passed": len(failures) == 0,
            }

    async def test_worker_e2e(self):
        sem = asyncio.Semaphore(_CONCURRENCY)
        results = await asyncio.gather(
            *[self._run_one(sem, c) for c in WORKER_CASES]
        )

        total = len(results)
        n_passed = sum(1 for r in results if r["passed"])
        pass_rate = n_passed / total

        # ── 报告 ──
        sep = "=" * 86
        print(f"\n{sep}")
        print(f"  WORKER E2E REPORT   {n_passed}/{total} PASS = {pass_rate:.0%}")
        print(f"{'-' * 86}")
        print(f"  {'Case':<28} {'Worker':<14} {'Status':<22} {'Ctrl':<10} Result")
        print(f"{'-' * 86}")
        for r in results:
            res_str = "PASS" if r["passed"] else "FAIL"
            print(
                f"  {r['case_id']:<28} {r['worker_type']:<14} "
                f"{str(r['status']):<22} {str(r['control_action'] or '-'):<10} {res_str}"
            )
            calls = [f"{k}={v}" for k, v in r["tool_call_counts"].items() if v > 0]
            if calls:
                print(f"      tool_calls: {' '.join(calls)}")
            if not r["passed"]:
                for f in r["failures"]:
                    safe = f.encode("gbk", errors="replace").decode("gbk")
                    print(f"      FAIL: {safe}")
                safe_ans = (r["answer"][:80] or "").encode("gbk", errors="replace").decode("gbk")
                print(f"      answer[:80]: {safe_ans}")
        print(f"{'-' * 86}")
        print(f"  TOTAL PASS RATE   {n_passed}/{total} = {pass_rate:.0%}")
        print(f"  THRESHOLD         {PASS_RATE_THRESHOLD:.0%}")
        print(f"  RESULT            {'PASS' if pass_rate >= PASS_RATE_THRESHOLD else 'FAIL'}")
        print(f"{sep}\n")

        assert pass_rate >= PASS_RATE_THRESHOLD, (
            f"Worker 端到端通过率 {pass_rate:.0%} 未达阈值 {PASS_RATE_THRESHOLD:.0%}，"
            f"{total - n_passed} 个案例失败"
        )
