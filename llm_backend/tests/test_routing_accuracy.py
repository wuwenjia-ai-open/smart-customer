"""路由分类准确率评测

对 classify_intent 的 LLM 分类能力做端到端打分，不启动完整图，
直接调 DeepSeek flash 分类链，消耗约 44 次 LLM 调用。

运行方式:
    pytest tests/test_routing_accuracy.py -v -s
    pytest tests/test_routing_accuracy.py -v -s -m integration
    pytest -m "not integration"           # CI 中跳过本文件
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from langchain_core.prompts import ChatPromptTemplate

from app.services.llm_factory import LLMFactory
from app.lg_agent.prompts.supervisor.classify import CLASSIFY_SYSTEM_PROMPT, ClassifyOutput

# ─── 评测集 ──────────────────────────────────────────────────────────────────
# (query, expected_intent)
# out_of_scope 案例用字符串 "out_of_scope"；其余与 ClassifyOutput.intent 对应
ROUTING_CASES = [
    # ── product_qa ─────────────────────────────────────────────
    ("小米15 Ultra 和 iPhone 16 Pro 哪个好",           "product_qa"),
    ("推荐一款 5000 块以内的笔记本电脑",               "product_qa"),
    ("华为 Mate 70 Pro 的摄像头参数是多少",             "product_qa"),
    ("有没有适合老人用的手机推荐",                     "product_qa"),
    ("MacBook Pro 和 ThinkPad X1 对比一下",            "product_qa"),
    ("扫地机器人哪个品牌好用",                         "product_qa"),
    ("1000 元左右的 TWS 耳机推荐",                     "product_qa"),
    ("这款手机的防水等级是多少",                        "product_qa"),
    ("iPad Pro 和安卓平板哪个更适合画画",              "product_qa"),
    ("笔记本续航最长的是哪款",                         "product_qa"),
    ("有没有 256GB 存储的手机",                        "product_qa"),
    ("智能手表哪款续航好",                             "product_qa"),
    # ── order_qa ───────────────────────────────────────────────
    ("我的订单到哪了",                                 "order_qa"),
    ("订单 #12345 现在什么状态",                       "order_qa"),
    ("快递还要多久到",                                 "order_qa"),
    ("我昨天下的单发货了吗",                           "order_qa"),
    ("快递单号是多少",                                 "order_qa"),
    ("我的包裹什么时候能到",                           "order_qa"),
    ("为什么还没发货",                                 "order_qa"),
    ("快递显示已签收但我没收到",                       "order_qa"),
    # ── after_sales ────────────────────────────────────────────
    ("怎么退货",                                       "after_sales"),
    ("我想申请退款",                                   "after_sales"),
    ("这个产品保修多久",                               "after_sales"),
    ("手机屏幕碎了能换吗",                             "after_sales"),
    ("七天无理由退货怎么申请",                          "after_sales"),
    ("产品有质量问题怎么处理",                          "after_sales"),
    ("我要投诉客服态度",                               "after_sales"),
    ("已发货的订单还能退吗",                           "after_sales"),
    ("保修期内维修需要多长时间",                        "after_sales"),
    ("人为损坏能走保修吗",                             "after_sales"),
    # ── general_chat ───────────────────────────────────────────
    ("你好",                                           "general_chat"),
    ("在吗",                                           "general_chat"),
    ("谢谢你的帮助",                                   "general_chat"),
    ("你是什么 AI",                                   "general_chat"),
    ("再见",                                           "general_chat"),
    ("你能帮我做什么",                                 "general_chat"),
    ("好的明白了",                                     "general_chat"),
    # ── out_of_scope ───────────────────────────────────────────
    ("今天天气怎么样",                                 "out_of_scope"),
    ("帮我写一首关于春天的诗",                          "out_of_scope"),
    ("最近股票行情怎么样",                             "out_of_scope"),
    ("推荐一部好看的科幻电影",                          "out_of_scope"),
    ("附近有什么好吃的餐厅",                           "out_of_scope"),
    ("帮我订一张明天的机票",                           "out_of_scope"),
    # ── multi ──────────────────────────────────────────────────
    ("帮我查一下订单状态，顺便推荐一款新手机",          "multi"),
    ("我的快递到了吗，另外有没有同款耳机推荐",          "multi"),
]

ACCURACY_THRESHOLD = 0.90
_CONCURRENCY = 5  # 并发 LLM 调用上限，防止 429


@pytest.mark.integration
class TestRoutingAccuracy:
    """端到端路由准确率 — 直接调 DeepSeek flash 分类链"""

    @pytest.fixture(scope="class")
    def chain(self):
        llm = LLMFactory.create_llm("flash")
        prompt = ChatPromptTemplate.from_messages([
            ("system", CLASSIFY_SYSTEM_PROMPT),
            ("human", "{query}"),
        ])
        return prompt | llm.with_structured_output(ClassifyOutput)

    async def _run_one(self, chain, sem, query: str, expected: str) -> dict:
        async with sem:
            result: ClassifyOutput = await chain.ainvoke({"query": query})
            got = "out_of_scope" if result.out_of_scope else result.intent
            if expected == "out_of_scope":
                correct = result.out_of_scope is True
            else:
                correct = (not result.out_of_scope) and (result.intent == expected)
            return {"query": query, "expected": expected, "got": got, "correct": correct}

    async def test_accuracy(self, chain):
        sem = asyncio.Semaphore(_CONCURRENCY)
        results = await asyncio.gather(
            *[self._run_one(chain, sem, q, e) for q, e in ROUTING_CASES]
        )

        total = len(results)
        n_correct = sum(1 for r in results if r["correct"])
        accuracy = n_correct / total

        # ── 按 intent 分组统计 ──
        by_intent: dict[str, dict] = {}
        for r in results:
            k = r["expected"]
            by_intent.setdefault(k, {"correct": 0, "total": 0})
            by_intent[k]["total"] += 1
            if r["correct"]:
                by_intent[k]["correct"] += 1

        # ── 控制台报告 ──
        failures = [r for r in results if not r["correct"]]
        sep = "=" * 62
        print(f"\n{sep}")
        print(f"  ROUTING ACCURACY REPORT   {n_correct}/{total} = {accuracy:.1%}")
        print(f"{'-' * 62}")
        for intent, stat in sorted(by_intent.items()):
            pct = stat["correct"] / stat["total"]
            bar = "o" * stat["correct"] + "x" * (stat["total"] - stat["correct"])
            print(f"  {intent:<16} {stat['correct']}/{stat['total']}  {pct:5.0%}  {bar}")
        print(f"{'-' * 62}")
        print(f"  TOTAL             {n_correct}/{total}  {accuracy:.0%}")
        print(f"  THRESHOLD         {ACCURACY_THRESHOLD:.0%}")
        print(f"  RESULT            {'PASS' if accuracy >= ACCURACY_THRESHOLD else 'FAIL'}")
        if failures:
            print(f"\n  Failures ({len(failures)}):")
            for f in failures:
                print(f"    [x] expected [{f['expected']:<12}] got [{f['got']:<12}]  \"{f['query']}\"")
        print(f"{sep}\n")

        assert accuracy >= ACCURACY_THRESHOLD, (
            f"路由准确率 {accuracy:.1%} 未达阈值 {ACCURACY_THRESHOLD:.0%}，"
            f"共 {len(failures)} 个失败案例"
        )
