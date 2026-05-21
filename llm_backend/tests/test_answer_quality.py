"""答复质量评测 — LLM-as-judge (Layer 2)

评测 merge_results 节点的回答质量：
  1. 注入预设的 worker_results 文本，跳过图和工具调用，直接测 merge LLM
  2. 对每个案例生成合并答复
  3. 用 LLM judge 从 4 个维度打分（忠实度/相关性/语气/完整性），每维度 0-5
  4. 同时做确定性检查（must_contain / must_not_contain）

运行方式:
    pytest tests/test_answer_quality.py -v -s
    pytest tests/test_answer_quality.py -v -s -m integration
    pytest -m "not integration"           # CI 中跳过本文件
"""
import asyncio
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.services.llm_factory import LLMFactory
from app.lg_agent.prompts.supervisor.merge import MERGE_SYSTEM_PROMPT


# ── LLM Judge 定义 ────────────────────────────────────────────────────────────

JUDGE_SYSTEM_PROMPT = """你是严格的电商客服质量评委。根据「工具结果」和「客服回答」，从四个维度打分（每维度 0-5 分整数）。

## 评分维度

### 忠实度 (faithfulness)
回答中的事实是否全部来自工具结果？有无虚构？
- 5: 全部有来源，无虚构信息
- 3: 大部分有来源，1-2 处可疑
- 0: 有明显虚构（产品名/价格/规格不在工具结果中）

### 相关性 (relevance)
是否直接回答了用户问题？
- 5: 完整回答
- 3: 回答了主要问题，遗漏次要细节
- 0: 答非所问

### 语气 (tone)
是否符合电商客服风格？
- 5: 亲切专业，使用"亲～"等客服话术，有关怀感
- 3: 语气合适但不够客服化
- 0: 生硬、机械或不礼貌

### 完整性 (completeness)
工具结果中的关键信息是否被覆盖？
- 5: 核心信息全部覆盖
- 3: 覆盖主要信息，次要信息略有遗漏
- 0: 大量关键信息缺失

输出 JSON（不要有其他内容）:
{{"faithfulness": 4, "relevance": 5, "tone": 5, "completeness": 4, "reasoning": "评分理由"}}"""


class JudgeScore(BaseModel):
    faithfulness: int = Field(ge=0, le=5)
    relevance: int = Field(ge=0, le=5)
    tone: int = Field(ge=0, le=5)
    completeness: int = Field(ge=0, le=5)
    reasoning: str

    @property
    def total(self) -> int:
        return self.faithfulness + self.relevance + self.tone + self.completeness


# ── 测试用例 ──────────────────────────────────────────────────────────────────

@dataclass
class AnswerCase:
    case_id: str
    query: str
    worker_results: str       # 格式化好的 worker results 文本（匹配 merge prompt 格式）
    context: str              # 对话历史
    must_contain: List[str] = field(default_factory=list)
    must_not_contain: List[str] = field(default_factory=list)
    judge_criteria: str = ""
    min_total: int = 14       # 通过门槛（满分 20）


ANSWER_CASES = [
    # ── 商品推荐（单结果高置信）────────────────────────────────────────────
    AnswerCase(
        case_id="product_rec_laptop",
        query="推荐一款 5000 元以内的游戏笔记本",
        worker_results=(
            "[product_qa] (置信度: 90%)\n"
            "亲～为您推荐联想拯救者 Y7000P（型号 Y7000P-2024，售价 ¥4,999）：\n"
            "- CPU: Intel Core i7-13620H\n"
            "- GPU: NVIDIA RTX 4060 8GB\n"
            "- 内存: 16GB DDR5 4800MHz\n"
            "- 屏幕: 15.6寸 1080P 165Hz\n"
            "- 用户评分: 4.8/5（来自 2341 条评价）\n"
            "- 特色: 双风扇散热，游戏帧率稳定，5000 元内性价比最高"
        ),
        context="无",
        must_contain=["联想拯救者 Y7000P", "4,999"],
        must_not_contain=["华硕ROG Strix"],
        judge_criteria="应推荐联想拯救者 Y7000P，明确说明价格和游戏性能优势",
    ),
    # ── 订单查询（单结果高置信）─────────────────────────────────────────────
    AnswerCase(
        case_id="order_status",
        query="我的订单 #10088 现在到哪了",
        worker_results=(
            "[order_qa] (置信度: 95%)\n"
            "订单 #10088：iPhone 16 Pro Max 256GB 深空黑。\n"
            "状态：已发货。\n"
            "物流：顺丰快递 SF1234567890。\n"
            "当前位置：上海转运中心（2026-05-17 08:20 更新）。\n"
            "预计送达：2026-05-18。"
        ),
        context="无",
        must_contain=["#10088", "SF1234567890"],
        must_not_contain=["京东物流"],
        judge_criteria="应告知订单 #10088 的物流状态和快递单号，说明当前位置和预计到达时间",
    ),
    # ── 售后退货（单结果高置信）─────────────────────────────────────────────
    AnswerCase(
        case_id="after_sales_return",
        query="我买的手机收到就有划痕，想退货",
        worker_results=(
            "[after_sales] (置信度: 88%)\n"
            "根据平台政策，本情况（收货即有质量问题）适用「质量问题退货」通道：\n"
            "1. 30天内均可申请，运费由平台承担\n"
            "2. 操作路径：App「我的订单」→「申请售后」→「质量问题」\n"
            "3. 需上传：外包装照片 + 划痕特写照片\n"
            "4. 审核周期：2-3 个工作日"
        ),
        context="无",
        must_contain=["质量问题", "申请售后"],
        must_not_contain=["用户自付运费"],
        judge_criteria="应按质量问题途径指导退货，说明操作步骤，明确平台承担运费",
    ),
    # ── 多意图：订单 + 商品（两个 Worker 结果）────────────────────────────
    AnswerCase(
        case_id="multi_order_product",
        query="帮我查订单 #20001 的状态，另外推荐一款 TWS 耳机",
        worker_results=(
            "[order_qa] (置信度: 92%)\n"
            "订单 #20001：索尼 WH-1000XM5 头戴耳机，已签收（2026-05-10 14:23）。\n"
            "---\n"
            "[product_qa] (置信度: 85%)\n"
            "为您推荐 TWS 耳机：\n"
            "1. 索尼 WF-1000XM5（¥1,799）- 旗舰降噪，续航 8+36 小时\n"
            "2. AirPods Pro 2（¥1,899）- 苹果生态，通透模式出色\n"
            "3. 华为 FreeBuds Pro 3（¥999）- 性价比高，降噪媲美旗舰"
        ),
        context="无",
        must_contain=["#20001", "签收", "WF-1000XM5"],
        must_not_contain=["Bose 700"],
        judge_criteria="应同时回答两个问题：订单 #20001 已签收，并推荐至少 2 款 TWS 耳机（含价格）",
        min_total=13,
    ),
    # ── 闲聊（能力介绍）─────────────────────────────────────────────────────
    AnswerCase(
        case_id="general_chat",
        query="你好，请问你能帮我做什么",
        worker_results=(
            "[general_chat] (置信度: 100%)\n"
            "你好！我是灵犀智购智能客服，可以帮您：\n"
            "1. 商品咨询：手机/笔记本/平板/耳机等查询、对比、推荐\n"
            "2. 订单服务：状态查询、物流追踪\n"
            "3. 售后支持：退换货、保修、投诉处理\n"
            "有什么问题请直接说哦！"
        ),
        context="无",
        must_contain=["商品咨询", "订单"],
        must_not_contain=[],
        judge_criteria="应热情介绍能力范围，涵盖商品/订单/售后三个方面",
    ),
    # ── 低置信重写（工具结果稀疏，LLM 需二次加工）──────────────────────────
    AnswerCase(
        case_id="low_confidence_rewrite",
        query="有没有适合老人用的手机",
        worker_results=(
            "[product_qa] (置信度: 50%)\n"
            "老人手机应具备大字体、简单操作等特点。系统数据有限，建议用户提供更多需求。"
        ),
        context="无",
        must_contain=[],
        must_not_contain=["iPhone 16 Pro Max"],
        judge_criteria="工具结果置信度低，应在有限信息基础上给出有帮助的建议，可引导用户提供预算/具体需求",
        min_total=11,
    ),
]

PASS_RATE_THRESHOLD = 0.75   # 通过案例占比
_CONCURRENCY = 3             # 并发 LLM 调用上限


# ── 测试类 ─────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestAnswerQuality:
    """答复质量评测 — merge LLM 输出 + LLM-as-judge 评分"""

    @pytest.fixture(scope="class")
    def merge_chain(self):
        llm = LLMFactory.create_llm("flash")
        prompt = ChatPromptTemplate.from_messages([
            ("system", MERGE_SYSTEM_PROMPT),
            ("human", "Worker 执行结果:\n{worker_results}\n\n对话历史:\n{context}\n\n请生成用户回复:"),
        ])
        return prompt | llm

    @pytest.fixture(scope="class")
    def judge_chain(self):
        llm = LLMFactory.create_llm("flash")
        prompt = ChatPromptTemplate.from_messages([
            ("system", JUDGE_SYSTEM_PROMPT),
            ("human", (
                "用户问题: {query}\n\n"
                "工具结果:\n{worker_results}\n\n"
                "客服回答:\n{answer}\n\n"
                "评委标准: {criteria}"
            )),
        ])
        return prompt | llm.with_structured_output(JudgeScore)

    async def _run_one(self, merge_chain, judge_chain, sem, case: AnswerCase) -> dict:
        async with sem:
            # Step 1: 生成合并答复
            response = await merge_chain.ainvoke({
                "worker_results": case.worker_results,
                "context": case.context,
            })
            answer = response.content if hasattr(response, "content") else str(response)

            # Step 2: 确定性检查
            det_failures = []
            for s in case.must_contain:
                if s not in answer:
                    det_failures.append(f"missing: '{s}'")
            for s in case.must_not_contain:
                if s in answer:
                    det_failures.append(f"hallucinated: '{s}'")

            # Step 3: LLM judge 打分
            score: JudgeScore = await judge_chain.ainvoke({
                "query": case.query,
                "worker_results": case.worker_results,
                "answer": answer,
                "criteria": case.judge_criteria,
            })

            passed = score.total >= case.min_total and not det_failures
            return {
                "case_id": case.case_id,
                "answer": answer,
                "score": score,
                "det_failures": det_failures,
                "min_total": case.min_total,
                "passed": passed,
            }

    async def test_quality(self, merge_chain, judge_chain):
        sem = asyncio.Semaphore(_CONCURRENCY)
        results = await asyncio.gather(
            *[self._run_one(merge_chain, judge_chain, sem, c) for c in ANSWER_CASES]
        )

        total = len(results)
        n_passed = sum(1 for r in results if r["passed"])
        pass_rate = n_passed / total

        # ── 控制台报告 ──
        sep = "=" * 74
        print(f"\n{sep}")
        print(f"  ANSWER QUALITY REPORT   {n_passed}/{total} PASS = {pass_rate:.0%}")
        print(f"{'-' * 74}")
        print(f"  {'Case':<28}  {'F':>3} {'R':>3} {'T':>3} {'C':>3}  {'Tot':>4}  {'Min':>4}  Result")
        print(f"{'-' * 74}")
        for r in results:
            s = r["score"]
            result_str = "PASS" if r["passed"] else "FAIL"
            det = f" [{', '.join(r['det_failures'][:2])}]" if r["det_failures"] else ""
            print(
                f"  {r['case_id']:<28}  {s.faithfulness:>3} {s.relevance:>3} "
                f"{s.tone:>3} {s.completeness:>3}  {s.total:>4}/{20}  "
                f"{r['min_total']:>4}  {result_str}{det}"
            )
        print(f"{'-' * 74}")
        print(f"  TOTAL PASS RATE   {n_passed}/{total} = {pass_rate:.0%}")
        print(f"  THRESHOLD         {PASS_RATE_THRESHOLD:.0%}")
        print(f"  RESULT            {'PASS' if pass_rate >= PASS_RATE_THRESHOLD else 'FAIL'}")

        failures = [r for r in results if not r["passed"]]
        if failures:
            print(f"\n  Failures ({len(failures)}):")
            for r in failures:
                s = r["score"]
                print(f"    [{r['case_id']}] total={s.total}/{20} min={r['min_total']}")
                if r["det_failures"]:
                    print(f"      det: {r['det_failures']}")
                # Encode to GBK-safe ASCII to avoid Windows terminal crash
                safe_reason = s.reasoning[:120].encode("gbk", errors="replace").decode("gbk")
                safe_answer = r["answer"][:80].encode("gbk", errors="replace").decode("gbk")
                print(f"      reasoning: {safe_reason}")
                print(f"      answer[:80]: {safe_answer}")
        print(f"{sep}\n")

        assert pass_rate >= PASS_RATE_THRESHOLD, (
            f"答复质量通过率 {pass_rate:.0%} 未达阈值 {PASS_RATE_THRESHOLD:.0%}，"
            f"共 {len(failures)} 个案例失败"
        )
