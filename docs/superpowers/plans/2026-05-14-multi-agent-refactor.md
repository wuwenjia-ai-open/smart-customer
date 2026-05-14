# Multi-Agent Architecture Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor single Agent Pipeline into Supervisor + 5 Worker Agents with ReAct loops, cutting serial LLM calls from 6 fixed to 1-5 on-demand.

**Architecture:** Supervisor handles intent classification + guardrails + task decomposition + result merging. Each Worker runs an independent ReAct loop (Think → Act → Observe) with domain-specific tools. Workers are LangGraph sub-graphs composed into the Supervisor main graph via `Send()` for parallel dispatch.

**Tech Stack:** Python 3.12, LangGraph, LangChain, DeepSeek API (ChatDeepSeek), Neo4j 5.x, Milvus 2.5, Ollama bge-m3

---

## File Map

### Create
```
lg_agent/workers/__init__.py
lg_agent/workers/state.py              # WorkerState, ToolCallRecord
lg_agent/workers/react_loop.py         # build_worker_graph() + think/act/observe/finish nodes
lg_agent/workers/tools/__init__.py
lg_agent/workers/tools/schemas.py      # 7 new + 2 existing tool Pydantic models
lg_agent/workers/tools/registry.py     # ToolExecutor base + TOOL_REGISTRY
lg_agent/workers/tools/executors.py    # 7 new tool executor implementations
lg_agent/prompts/__init__.py
lg_agent/prompts/workers/__init__.py
lg_agent/prompts/workers/think_base.py # Shared ReAct rules
lg_agent/prompts/workers/product_qa.py
lg_agent/prompts/workers/order_qa.py
lg_agent/prompts/workers/after_sales.py
lg_agent/prompts/workers/general_chat.py
lg_agent/prompts/supervisor/__init__.py
lg_agent/prompts/supervisor/classify.py
lg_agent/prompts/supervisor/decompose.py
lg_agent/prompts/supervisor/merge.py
lg_agent/supervisor/__init__.py
lg_agent/supervisor/state.py           # SupervisorState, SubTask, WorkerResult
lg_agent/supervisor/nodes.py           # classify/decompose/dispatch/merge/respond nodes
tests/test_worker_react.py
tests/test_supervisor_routing.py
```

### Modify
```
lg_agent/lg_states.py                  # Keep old types, add new state types
lg_agent/lg_builder.py                 # Rewrite: build_supervisor_graph() replaces old graph
api/langgraph.py:15                    # Change `from app.lg_agent.lg_builder import graph`
                                       #   to `from app.lg_agent.lg_builder import supervisor_graph`
```

### No Changes
```
core/config.py                         # Same DeepSeek/Neo4j/Milvus config
core/services/llm_factory.py           # Same ChatDeepSeek factory
kg_sub_graph/neo4j_conn.py             # Same Neo4j singleton
kg_sub_graph/agentic_rag_agents/components/predefined_cypher/cypher_dict.py  # Same 60 queries
kg_sub_graph/agentic_rag_agents/components/predefined_cypher/utils.py        # Same VectorQueryMatcher
kg_sub_graph/agentic_rag_agents/components/predefined_cypher/descriptions.py # Same descriptions
kg_sub_graph/agentic_rag_agents/components/cypher_tools/node.py             # Same Text2Cypher
api/langgraph.py (except line 15)      # Same SSE streaming + thread management
```

---

## Phase 1: Foundation (Types + Tools)

### Task 1: Shared State Types

**Files:**
- Create: `llm_backend/app/lg_agent/workers/state.py`
- Create: `llm_backend/app/lg_agent/supervisor/state.py`
- Modify: `llm_backend/app/lg_agent/lg_states.py`

- [ ] **Step 1: Create Worker state module**

```python
# llm_backend/app/lg_agent/workers/state.py
"""Worker ReAct 循环状态定义"""
from operator import add
from typing import Annotated, Any, Dict, List
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from typing_extensions import TypedDict


class ToolCallRecord(TypedDict):
    """Observe 阶段记录的单次工具调用"""
    tool_name: str
    args: Dict[str, Any]
    result_summary: str
    record_count: int
    success: bool


class WorkerState(TypedDict):
    """Worker ReAct 循环状态"""
    messages: Annotated[List[AnyMessage], add_messages]
    worker_type: str
    task: str
    context: Dict[str, Any]
    iteration_count: int
    next_action: str
    tool_to_execute: str
    tool_call_history: Annotated[List[ToolCallRecord], add]
    final_answer: str
    status: str
    clarification_question: str
```

- [ ] **Step 2: Create Supervisor state module**

```python
# llm_backend/app/lg_agent/supervisor/state.py
"""Supervisor 全局状态定义"""
from operator import add
from typing import Annotated, Any, Dict, List
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from typing_extensions import TypedDict


class SubTask(TypedDict):
    task_id: str
    worker_type: str
    description: str
    context: Dict[str, Any]
    priority: int


class WorkerResult(TypedDict):
    task_id: str
    worker_type: str
    answer: str
    status: str
    clarification_question: str
    tool_calls_made: int
    iterations_used: int


class SupervisorState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    intent: str
    guardrail_result: Dict[str, Any]
    sub_tasks: List[SubTask]
    worker_results: Annotated[List[WorkerResult], add]
    final_answer: str
    next_action: str
    needs_clarification: bool
    pending_clarification: str
```

- [ ] **Step 3: Append new types to lg_states.py (keep old types for reference)**

```python
# Append to llm_backend/app/lg_agent/lg_states.py

# === Multi-Agent types (added for feat/multi-agent) ===
from app.lg_agent.workers.state import WorkerState, ToolCallRecord  # noqa: F401
from app.lg_agent.supervisor.state import SupervisorState, SubTask, WorkerResult  # noqa: F401
```

- [ ] **Step 4: Verify imports**

Run: `cd llm_backend && python -c "from app.lg_agent.lg_states import SupervisorState, WorkerState, SubTask, WorkerResult, ToolCallRecord; print('OK')"`
Expected: `OK`

---

### Task 2: Tool Schemas

**Files:**
- Create: `llm_backend/app/lg_agent/workers/tools/__init__.py`
- Create: `llm_backend/app/lg_agent/workers/tools/schemas.py`

- [ ] **Step 1: Create package init**

```python
# llm_backend/app/lg_agent/workers/tools/__init__.py
"""Worker 工具包"""
```

- [ ] **Step 2: Write all tool schemas**

```python
# llm_backend/app/lg_agent/workers/tools/schemas.py
"""工具 Pydantic Schema 定义 — 用于 LLM bind_tools()"""
from typing import List, Optional, Tuple, Literal
from pydantic import BaseModel, Field


# ── 新工具 ──

class semantic_search(BaseModel):
    """【语义搜索】根据用户需求场景描述在产品知识库中语义搜索匹配产品。
    适用：用户描述需求但不知道具体产品名，如"适合小户型的智能门锁"。"""
    query: str = Field(..., description="用户需求场景的自然语言描述，不是产品名")
    top_k: int = Field(default=5, description="返回结果数量")


class compare_products(BaseModel):
    """【产品对比】并排对比两个或多个产品的价格、功能、评价。
    适用：用户问"A和B哪个好"、"帮我对比一下"。"""
    product_names: List[str] = Field(..., min_length=2, max_length=5, description="要对比的产品名称列表")
    aspects: Optional[List[str]] = Field(default=None, description="对比维度，如['价格','功能','评价']，不传则全维度")


class recommend(BaseModel):
    """【产品推荐】根据用户画像、预算和场景推荐产品。
    适用："预算2000想买扫地机器人"、"送父母的智能音箱推荐"。"""
    scenario: str = Field(..., description="使用场景描述")
    budget_min: Optional[float] = Field(default=None, description="预算下限")
    budget_max: Optional[float] = Field(default=None, description="预算上限")
    preferences: Optional[List[str]] = Field(default=None, description="偏好标签，如['安静','大容量','节能']")
    exclude: Optional[List[str]] = Field(default=None, description="排除的产品名")
    top_k: int = Field(default=3, description="推荐数量")


class track_shipment(BaseModel):
    """【物流追踪】查询订单的物流状态和预计到达时间。
    适用："我的订单发货了吗"、"订单到哪了"。"""
    order_id: int = Field(..., description="订单号")


class create_ticket(BaseModel):
    """【创建工单】为用户创建售后工单。
    适用：用户明确要求退货/换货/维修，且 FAQ 无法解决。"""
    issue_type: Literal["退货", "换货", "维修", "投诉", "其他"] = Field(..., description="工单类型")
    order_id: Optional[int] = Field(default=None, description="关联订单号")
    description: str = Field(..., description="问题描述")
    priority: Literal["normal", "urgent"] = Field(default="normal", description="优先级")


class ask_clarification(BaseModel):
    """【澄清提问】当任务信息不足时，向用户提出精准的澄清问题。
    此工具不执行查询，调用后 Worker 将暂停并等待用户回应。"""
    question: str = Field(..., description="向用户提出的澄清问题，单句，不超过30字")
    missing_field: str = Field(..., description="缺失的关键字段，如'order_id','product_name'")
    options: Optional[List[str]] = Field(default=None, description="可选澄清选项")


class escalate_to_human(BaseModel):
    """【转人工】将当前会话转接给人工客服。
    适用：用户明确要求人工、投诉升级、工具无法解决的问题。"""
    reason: str = Field(..., description="转接原因")
    summary: str = Field(..., description="问题摘要，供人工客服快速了解上下文")
    urgency: Literal["normal", "urgent", "critical"] = Field(default="normal", description="紧急程度")


# ── 复用现有工具（直接 re-export，不改原文件） ──
from app.lg_agent.kg_sub_graph.tools import predefined_cypher, cypher_query  # noqa: E402, F401
```

- [ ] **Step 3: Verify schemas parse**

Run: `cd llm_backend && python -c "from app.lg_agent.workers.tools.schemas import semantic_search, recommend, ask_clarification; s = semantic_search(query='test'); print(s.model_dump())"`
Expected: `{'query': 'test', 'top_k': 5}`

---

### Task 3: Tool Registry + Executor Base

**Files:**
- Create: `llm_backend/app/lg_agent/workers/tools/registry.py`

- [ ] **Step 1: Write registry module**

```python
# llm_backend/app/lg_agent/workers/tools/registry.py
"""工具注册表 — 工具名到执行器的映射"""
from typing import Any, Callable, Dict, Protocol, runtime_checkable


class ToolResult:
    """工具执行结果"""
    def __init__(self, records: list = None, summary: str = "", error: str = "", success: bool = True):
        self.records = records or []
        self.summary = summary
        self.error = error
        self.success = success


@runtime_checkable
class ToolExecutor(Protocol):
    """工具执行器协议 — 所有执行器必须实现 invoke 方法"""
    def invoke(self, args: Dict[str, Any]) -> ToolResult:
        ...


# 全局注册表，按 Worker 拥有不同工具集
TOOL_REGISTRY: Dict[str, ToolExecutor] = {}


def register_tool(name: str, executor: ToolExecutor) -> None:
    TOOL_REGISTRY[name] = executor


def get_tool_executor(name: str) -> ToolExecutor:
    if name not in TOOL_REGISTRY:
        raise KeyError(f"Tool '{name}' not registered. Available: {list(TOOL_REGISTRY.keys())}")
    return TOOL_REGISTRY[name]
```

- [ ] **Step 2: Verify registry works**

Run: `cd llm_backend && python -c "from app.lg_agent.workers.tools.registry import TOOL_REGISTRY, register_tool, get_tool_executor; print('OK')"`
Expected: `OK`

---

### Task 4: SemanticSearch Executor

**Files:**
- Create: `llm_backend/app/lg_agent/workers/tools/executors.py`

- [ ] **Step 1: Write SemanticSearchExecutor**

```python
# llm_backend/app/lg_agent/workers/tools/executors.py (first section)
"""工具执行器实现"""
import logging
from typing import Any, Dict, List
from .registry import ToolResult, register_tool

_log = logging.getLogger(__name__)


class SemanticSearchExecutor:
    """语义搜索执行器 — bge-m3 向量化 → Milvus COSINE 检索 → 返回产品列表"""

    def __init__(self, milvus_client, embedding_model, collection_name: str = "product_descriptions"):
        self._milvus = milvus_client
        self._embed = embedding_model
        self._collection = collection_name

    def invoke(self, args: Dict[str, Any]) -> ToolResult:
        query = args.get("query", "")
        top_k = args.get("top_k", 5)

        try:
            vector = self._embed.embed_query(query)
            results = self._milvus.search(
                collection_name=self._collection,
                data=[vector],
                limit=top_k,
                output_fields=["product_name", "description", "price", "category"]
            )
            records = []
            for hits in results:
                for hit in hits:
                    records.append({
                        "product_name": hit.get("product_name", ""),
                        "description": hit.get("description", ""),
                        "price": hit.get("price", ""),
                        "category": hit.get("category", ""),
                        "similarity": round(hit.get("distance", 0), 3),
                    })

            if not records:
                return ToolResult(
                    records=[], summary="未找到匹配的产品",
                    success=False, error="no_results"
                )

            summary = f"语义搜索 '{query[:30]}' 找到 {len(records)} 个产品"
            return ToolResult(records=records, summary=summary)

        except Exception as e:
            _log.error(f"SemanticSearch failed: {e}")
            return ToolResult(records=[], summary="", error=str(e), success=False)
```

- [ ] **Step 2: Verify executor instantiation**

Run: `cd llm_backend && python -c "from app.lg_agent.workers.tools.executors import SemanticSearchExecutor; print('import OK')"`
Expected: `import OK`

---

### Task 5: CompareProducts + Recommend Executors

**Files:**
- Modify: `llm_backend/app/lg_agent/workers/tools/executors.py` (append)

- [ ] **Step 1: Append CompareProductsExecutor**

```python
# Append to executors.py

class CompareProductsExecutor:
    """产品对比执行器 — Cypher 查产品属性 → 整理对比表"""

    def __init__(self, neo4j_graph, predefined_cypher_dict: Dict[str, str]):
        self._graph = neo4j_graph
        self._cypher_dict = predefined_cypher_dict

    def invoke(self, args: Dict[str, Any]) -> ToolResult:
        names = args.get("product_names", [])
        aspects = args.get("aspects")  # None = all aspects

        all_records = []
        for name in names:
            try:
                stmt = self._cypher_dict.get("product_by_name", "")
                if not stmt:
                    continue
                records = self._graph.query(stmt, params={"product_name": name})
                all_records.extend(records or [])
            except Exception as e:
                _log.warning(f"CompareProducts: failed for '{name}': {e}")

        if not all_records:
            return ToolResult(
                records=[], summary=f"未找到产品 {names} 的信息",
                success=False, error="no_results"
            )

        summary = f"已获取 {len(names)} 个产品的对比数据（{len(all_records)} 条记录）"
        return ToolResult(records=all_records, summary=summary)


class RecommendExecutor:
    """推荐执行器 — semantic_search + predefined_cypher 组合，多因子排序"""

    def __init__(self, milvus_client, embedding_model, neo4j_graph, predefined_cypher_dict: Dict[str, str]):
        self._semantic = SemanticSearchExecutor(milvus_client, embedding_model)
        self._graph = neo4j_graph
        self._cypher_dict = predefined_cypher_dict

    def invoke(self, args: Dict[str, Any]) -> ToolResult:
        scenario = args.get("scenario", "")
        budget_min = args.get("budget_min")
        budget_max = args.get("budget_max")
        preferences = args.get("preferences", [])
        exclude_names = set(args.get("exclude", []))
        top_k = args.get("top_k", 3)

        # Step 1: semantic search for candidates
        search_result = self._semantic.invoke({"query": scenario, "top_k": 15})
        if not search_result.success:
            return search_result

        # Step 2: filter by budget, exclude, preferences
        candidates = []
        for r in search_result.records:
            name = r.get("product_name", "")
            if name in exclude_names:
                continue
            price = float(r.get("price", 0) or 0)
            if budget_min is not None and price < budget_min:
                continue
            if budget_max is not None and price > budget_max:
                continue
            score = r.get("similarity", 0)
            # Boost if name matches preferences
            for pref in preferences:
                desc = r.get("description", "")
                if pref in desc:
                    score += 0.1
            candidates.append({**r, "score": score})

        candidates.sort(key=lambda x: x["score"], reverse=True)
        top = candidates[:top_k]

        if not top:
            return ToolResult(
                records=[], summary="未找到符合条件的产品",
                success=False, error="no_match"
            )

        # Step 3: enrich with structured data from Neo4j
        enriched = []
        for c in top:
            try:
                stmt = self._cypher_dict.get("product_by_name", "")
                neo4j_records = self._graph.query(stmt, params={"product_name": c["product_name"]}) if stmt else []
                enriched.append({
                    **c,
                    "details": neo4j_records[0] if neo4j_records else {},
                })
            except Exception:
                enriched.append(c)

        summary = f"推荐 {len(enriched)} 个产品: " + ", ".join(
            f"{e['product_name']}(¥{e.get('price', 'N/A')})" for e in enriched
        )
        return ToolResult(records=enriched, summary=summary)
```

- [ ] **Step 2: Verify imports**

Run: `cd llm_backend && python -c "from app.lg_agent.workers.tools.executors import CompareProductsExecutor, RecommendExecutor; print('OK')"`
Expected: `OK`

---

### Task 6: TrackShipment + CreateTicket Executors

**Files:**
- Modify: `llm_backend/app/lg_agent/workers/tools/executors.py` (append)

- [ ] **Step 1: Append TrackShipmentExecutor**

```python
# Append to executors.py

class TrackShipmentExecutor:
    """物流追踪执行器 — Cypher 查订单物流状态"""

    def __init__(self, neo4j_graph):
        self._graph = neo4j_graph

    def invoke(self, args: Dict[str, Any]) -> ToolResult:
        order_id = args.get("order_id")
        if not order_id:
            return ToolResult(records=[], error="missing order_id", success=False)

        try:
            records = self._graph.query(
                "MATCH (o:Order) WHERE o.orderId = $order_id "
                "RETURN o.orderId, o.OrderDate, o.ShippedDate, o.RequiredDate, "
                "o.ShipVia, o.ShipName, o.ShipAddress, o.ShipCity, o.ShipCountry, o.Freight",
                params={"order_id": order_id}
            )
            if not records:
                return ToolResult(
                    records=[], summary=f"未找到订单 #{order_id}",
                    success=False, error="not_found"
                )
            r = records[0]
            shipped = r.get("ShippedDate", "未发货")
            summary = f"订单 #{order_id}: 下单 {r.get('OrderDate','未知')}, 发货状态: {shipped}"
            return ToolResult(records=records, summary=summary)
        except Exception as e:
            _log.error(f"TrackShipment failed: {e}")
            return ToolResult(records=[], error=str(e), success=False)


class CreateTicketExecutor:
    """创建工单执行器 — 写入 MySQL 工单表"""

    def __init__(self, db_session_factory):
        self._db = db_session_factory

    def invoke(self, args: Dict[str, Any]) -> ToolResult:
        issue_type = args.get("issue_type", "其他")
        order_id = args.get("order_id")
        description = args.get("description", "")
        priority = args.get("priority", "normal")

        # TODO: replace with actual ticket table when available
        ticket_id = f"TKT-{hash(description) % 100000:05d}"
        summary = f"工单 {ticket_id} 已创建: [{issue_type}] {description[:50]} (优先级: {priority})"
        return ToolResult(
            records=[{"ticket_id": ticket_id, "issue_type": issue_type, "status": "open"}],
            summary=summary
        )
```

- [ ] **Step 2: Verify imports**

Run: `cd llm_backend && python -c "from app.lg_agent.workers.tools.executors import TrackShipmentExecutor, CreateTicketExecutor; print('OK')"`
Expected: `OK`

---

### Task 7: AskClarification + EscalateToHuman Executors

**Files:**
- Modify: `llm_backend/app/lg_agent/workers/tools/executors.py` (append)

- [ ] **Step 1: Append control tool executors**

```python
# Append to executors.py

class AskClarificationExecutor:
    """澄清工具 — 不执行查询，返回特殊标记让 ReAct 循环退出"""

    def invoke(self, args: Dict[str, Any]) -> ToolResult:
        question = args.get("question", "")
        missing_field = args.get("missing_field", "")
        options = args.get("options")
        return ToolResult(
            records=[{
                "__control__": "clarify",
                "question": question,
                "missing_field": missing_field,
                "options": options,
            }],
            summary=f"[CLARIFY] {question}",
        )


class EscalateToHumanExecutor:
    """转人工工具 — 标记会话为 pending_human"""

    def __init__(self, db_session_factory=None):
        self._db = db_session_factory

    def invoke(self, args: Dict[str, Any]) -> ToolResult:
        reason = args.get("reason", "")
        summary_text = args.get("summary", "")
        urgency = args.get("urgency", "normal")
        return ToolResult(
            records=[{
                "__control__": "escalate",
                "reason": reason,
                "summary": summary_text,
                "urgency": urgency,
            }],
            summary=f"[ESCALATE] {reason[:50]}",
        )
```

- [ ] **Step 2: Verify imports**

Run: `cd llm_backend && python -c "from app.lg_agent.workers.tools.executors import AskClarificationExecutor, EscalateToHumanExecutor; print('OK')"`
Expected: `OK`

---

## Phase 2: Prompts

### Task 8: Worker System Prompts

**Files:**
- Create: `llm_backend/app/lg_agent/prompts/__init__.py`
- Create: `llm_backend/app/lg_agent/prompts/workers/__init__.py`
- Create: `llm_backend/app/lg_agent/prompts/workers/think_base.py`
- Create: `llm_backend/app/lg_agent/prompts/workers/product_qa.py`
- Create: `llm_backend/app/lg_agent/prompts/workers/order_qa.py`
- Create: `llm_backend/app/lg_agent/prompts/workers/after_sales.py`
- Create: `llm_backend/app/lg_agent/prompts/workers/general_chat.py`

- [ ] **Step 1: Create think_base.py**

```python
# llm_backend/app/lg_agent/prompts/workers/think_base.py

REACT_RULES = """## 工作方式（ReAct 循环）

你会多轮思考和调用工具，直到有足够信息回答用户。每次你都可以：调用一个工具获取信息，或者直接输出最终答案。

### 首轮：分析任务
收到任务后先分析：
1. 用户到底想要什么？
2. 缺少哪些关键信息？
3. 如果信息足够 → 直接输出答案，不调工具
4. 如果信息不足 → 调用最合适的工具

### 后续轮次：基于结果推进
收到工具结果后：
1. 评估是否足够回答用户。如果够 → 直接输出答案
2. 不够 → 调用下一个工具
3. 工具返回空结果 → 换关键词或换工具重试一次

### 幻觉预防（关键）
在输出最终答案前自查：
- 提到的每个产品名都在工具结果中出现过吗？
- 提到的价格/评分/库存数字都来自工具结果吗？
- 如果有任何数据不是来自工具结果 → 不要输出，先调工具确认

### 何时停止
- 信息足够回答用户 → 直接输出答案（不带 tool_calls）
- 连续 2 次工具返回空结果 → 告知用户未找到，建议换个方式询问
- 需要用户澄清 → 调用 ask_clarification 工具
"""

IDENTITY_MAP = {
    "product_qa": """你是灵犀智购的产品顾问。负责帮用户找到最合适的智能家居产品。

核心能力：语义搜索产品、横向对比价格功能评价、基于预算和场景做个性化推荐。

产品数据库覆盖：智能门锁、摄像头、音箱、扫地机器人、空调、灯具、窗帘、净水器、加湿器、电饭煲、洗衣机、冰箱、电视、马桶、体重秤、门铃、手环、空气净化器等 20+ 品类。""",

    "order_qa": """你是灵犀智购的订单管家。负责订单查询和物流追踪。

核心能力：根据订单号查询订单详情、追踪物流状态、查询历史订单。

需要订单号才能查询。如果没有订单号，调用 ask_clarification 让用户提供。""",

    "after_sales": """你是灵犀智购的售后专员。负责处理售后问题。

核心能力：查询退换货政策和保修条款、搜索 FAQ 知识库、创建售后工单、必要时转接人工客服。

处理流程：先查 FAQ → 无法解决 → 创建工单 → 仍无法解决 → 调用 escalate_to_human 转人工。""",

    "general_chat": """你是灵犀智购的接待客服。负责闲聊和接待。

核心能力：友好问候、引导用户说明需求、模糊问题时追问澄清。

你没有产品/订单查询工具。如果用户问具体业务问题，告知用户正在转接给专业同事处理。""",

}


def build_think_prompt(worker_type: str, tool_descriptions: str) -> str:
    identity = IDENTITY_MAP.get(worker_type, IDENTITY_MAP["general_chat"])
    return f"""{identity}

## 可用工具
{tool_descriptions}

{REACT_RULES}

## 回复风格
- 电商客服风格，亲切专业
- 开场用"亲～"
- 推荐时说明理由
- 只使用工具结果中的数据，不编造
"""
```

- [ ] **Step 2: Verify builds**

Run: `cd llm_backend && python -c "from app.lg_agent.prompts.workers.think_base import build_think_prompt, IDENTITY_MAP; p = build_think_prompt('product_qa', '- semantic_search: search products'); assert 'ProductQA' in p or '产品顾问' in p; print(len(p)); print('OK')"`
Expected: prints character count and `OK`

---

## Phase 3: ReAct Loop

### Task 9: Worker ReAct Loop Factory

**Files:**
- Create: `llm_backend/app/lg_agent/workers/__init__.py`
- Create: `llm_backend/app/lg_agent/workers/react_loop.py`

- [ ] **Step 1: Create package init**

```python
# llm_backend/app/lg_agent/workers/__init__.py
"""Worker Agent 模块 — ReAct 循环 + 工具"""
```

- [ ] **Step 2: Write route_after_think**

```python
# llm_backend/app/lg_agent/workers/react_loop.py
"""Worker ReAct 循环 — build_worker_graph() 工厂函数"""
import logging
from typing import Any, Dict, List, Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from app.lg_agent.workers.state import WorkerState, ToolCallRecord
from app.lg_agent.workers.tools.registry import get_tool_executor
from app.lg_agent.prompts.workers.think_base import build_think_prompt

_log = logging.getLogger(__name__)

MAX_ITERATIONS = 7
MAX_EMPTY_RESULTS = 3
MAX_DUPLICATE_CALLS = 2


def route_after_think(state: WorkerState) -> Literal["act", "finish"]:
    last_msg = state["messages"][-1] if state["messages"] else None
    if isinstance(last_msg, AIMessage) and getattr(last_msg, "tool_calls", None):
        return "act"
    return "finish"


def route_after_observe(state: WorkerState) -> Literal["think", "finish"]:
    if state["next_action"] == "finish":
        return "finish"
    return "think"
```

- [ ] **Step 3: Write act_node and observe_node**

```python
# Continue in react_loop.py

async def act_node(state: WorkerState) -> Dict[str, Any]:
    """执行工具调用，无 LLM 调用"""
    last_msg = state["messages"][-1] if state["messages"] else None

    if not isinstance(last_msg, AIMessage) or not getattr(last_msg, "tool_calls", None):
        return {"next_action": "finish"}

    tool_call = last_msg.tool_calls[0]
    tool_name = tool_call["name"]
    tool_args = tool_call.get("args", {})

    _log.info(f"Act: calling {tool_name} with {tool_args}")

    try:
        executor = get_tool_executor(tool_name)
        result = executor.invoke(tool_args)
    except KeyError:
        result = type("R", (), {"success": False, "error": f"Unknown tool: {tool_name}", "records": [], "summary": ""})()

    content = result.summary if result.success else f"Error: {result.error}"
    if result.records:
        content += f"\nRecords ({len(result.records)}): {str(result.records)[:2000]}"

    tool_msg = ToolMessage(content=content, tool_call_id=tool_call["id"])
    return {
        "messages": [tool_msg],
        "tool_to_execute": tool_name,
    }


def observe_node(state: WorkerState, *, config: RunnableConfig) -> Dict[str, Any]:
    """程序化校验工具结果，无 LLM 调用"""
    tool_name = state.get("tool_to_execute", "unknown")
    iteration_count = state.get("iteration_count", 0) + 1

    # Get last tool message
    msgs = state.get("messages", [])
    last_tool_msg = None
    for m in reversed(msgs):
        if isinstance(m, ToolMessage):
            last_tool_msg = m
            break

    content = getattr(last_tool_msg, "content", "") if last_tool_msg else ""
    record_count = content.count("product_name") if "product_name" in content else (
        0 if "Error:" in content or not content.strip() else 1
    )
    success = not content.startswith("Error:")
    is_empty = record_count == 0

    # Check for control tools (clarify, escalate)
    if "[CLARIFY]" in content:
        return {
            "iteration_count": iteration_count,
            "next_action": "finish",
            "status": "clarification_needed",
            "clarification_question": content.replace("[CLARIFY] ", "").strip(),
            "tool_call_history": [ToolCallRecord(
                tool_name=tool_name,
                args={},
                result_summary=content[:200],
                record_count=0,
                success=True,
            )],
        }

    if "[ESCALATE]" in content:
        return {
            "iteration_count": iteration_count,
            "next_action": "finish",
            "status": "escalated",
            "final_answer": content.replace("[ESCALATE] ", "").strip(),
            "tool_call_history": [ToolCallRecord(
                tool_name=tool_name,
                args={},
                result_summary=content[:200],
                record_count=0,
                success=True,
            )],
        }

    # Check empty results
    history = list(state.get("tool_call_history", []))
    consecutive_empty = 0
    for h in reversed(history):
        if h.get("record_count", 0) == 0:
            consecutive_empty += 1
        else:
            break

    if is_empty:
        consecutive_empty += 1

    if consecutive_empty >= MAX_EMPTY_RESULTS:
        return {
            "iteration_count": iteration_count,
            "next_action": "finish",
            "status": "success",
            "final_answer": "抱歉，我暂时没有找到相关信息。您可以换个方式描述需求，或者联系人工客服获取帮助。",
            "tool_call_history": [ToolCallRecord(
                tool_name=tool_name, args={}, result_summary=content[:200],
                record_count=0, success=False,
            )],
        }

    # Check duplicate calls
    duplicate_count = sum(1 for h in history[-MAX_DUPLICATE_CALLS:] if h.get("tool_name") == tool_name)
    if duplicate_count >= MAX_DUPLICATE_CALLS and len(history) >= MAX_DUPLICATE_CALLS:
        return {
            "iteration_count": iteration_count,
            "next_action": "finish",
            "status": "success",
            "final_answer": "抱歉，我尝试了几次但没能找到对应的信息。建议您换个关键词试试，或联系人工客服协助。",
            "tool_call_history": [ToolCallRecord(
                tool_name=tool_name, args={}, result_summary=content[:200],
                record_count=record_count, success=success,
            )],
        }

    # Iteration limit
    if iteration_count >= MAX_ITERATIONS:
        _log.warning(f"Worker hit max iterations ({MAX_ITERATIONS}), force finish")
        return {
            "iteration_count": iteration_count,
            "next_action": "finish",
            "status": "success",
            "tool_call_history": [ToolCallRecord(
                tool_name=tool_name, args={}, result_summary=content[:200],
                record_count=record_count, success=success,
            )],
        }

    # Normal: continue loop
    return {
        "iteration_count": iteration_count,
        "next_action": "think",
        "tool_call_history": [ToolCallRecord(
            tool_name=tool_name, args={}, result_summary=content[:200],
            record_count=record_count, success=success,
        )],
    }
```

- [ ] **Step 4: Write think_node and finish_node**

```python
# Continue in react_loop.py

def make_think_node(llm: BaseChatModel, worker_type: str, tool_schemas: list):
    """创建 Think 节点 — 唯一的 LLM 调用"""

    from langchain_core.output_parsers.openai_tools import PydanticToolsParser

    # Build prompt with dynamic tool descriptions
    tool_descriptions = "\n".join(
        f"- **{t.__name__}**: {t.__doc__ or 'No description'}"
        for t in tool_schemas
    )
    system_prompt = build_think_prompt(worker_type, tool_descriptions)

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("placeholder", "{messages}"),
    ])

    llm_with_tools = llm.bind_tools(tool_schemas)

    async def think(state: WorkerState) -> Dict[str, Any]:
        iteration = state.get("iteration_count", 0)
        _log.info(f"Think: worker={worker_type} iteration={iteration}")

        result = await (prompt | llm_with_tools).ainvoke({"messages": state["messages"]})
        return {"messages": [result]}

    return think


def finish_node(state: WorkerState) -> Dict[str, Any]:
    """提取最终答案 — 从最后一条 AIMessage 获取 content"""
    msgs = state.get("messages", [])
    answer = ""
    for m in reversed(msgs):
        if isinstance(m, AIMessage) and not getattr(m, "tool_calls", None):
            answer = getattr(m, "content", "") or ""
            if answer:
                break

    if not answer:
        tools_used = len(state.get("tool_call_history", []))
        answer = f"已为您查询（共调用 {tools_used} 次工具），如有其他问题请随时问我～"

    return {
        "final_answer": answer,
        "status": state.get("status", "success"),
        "clarification_question": state.get("clarification_question", ""),
    }
```

- [ ] **Step 5: Write build_worker_graph**

```python
# Continue in react_loop.py

def build_worker_graph(worker_type: str, llm: BaseChatModel, tool_schemas: list) -> StateGraph:
    """构建 Worker ReAct 子图"""
    builder = StateGraph(WorkerState)

    think_node_fn = make_think_node(llm, worker_type, tool_schemas)

    builder.add_node("think", think_node_fn)
    builder.add_node("act", act_node)
    builder.add_node("observe", observe_node)
    builder.add_node("finish", finish_node)

    builder.add_edge(START, "think")
    builder.add_conditional_edges("think", route_after_think, {
        "act": "act",
        "finish": "finish",
    })
    builder.add_edge("act", "observe")
    builder.add_conditional_edges("observe", route_after_observe, {
        "think": "think",
        "finish": "finish",
    })
    builder.add_edge("finish", END)

    return builder.compile()
```

- [ ] **Step 6: Verify compilation**

Run: `cd llm_backend && python -c "from app.lg_agent.workers.react_loop import build_worker_graph, MAX_ITERATIONS; print(f'MAX_ITERATIONS={MAX_ITERATIONS}'); print('OK')"`
Expected: `MAX_ITERATIONS=7` then `OK`

---

## Phase 4: Supervisor

### Task 10: Supervisor Prompts

**Files:**
- Create: `llm_backend/app/lg_agent/prompts/supervisor/__init__.py`
- Create: `llm_backend/app/lg_agent/prompts/supervisor/classify.py`
- Create: `llm_backend/app/lg_agent/prompts/supervisor/decompose.py`
- Create: `llm_backend/app/lg_agent/prompts/supervisor/merge.py`

- [ ] **Step 1: Write classify prompt**

```python
# llm_backend/app/lg_agent/prompts/supervisor/classify.py

CLASSIFY_SYSTEM_PROMPT = """你是灵犀智购的智能路由 Supervisor。收到用户消息后，完成两件事：

## 1. 越界检测
判断用户问题是否在系统处理范围内。系统处理：
- 智能家居产品查询/对比/推荐（门锁、摄像头、音箱、扫地机器人、空调、灯具、窗帘等 20+ 品类）
- 订单查询/物流追踪
- 售后问题（退换货、保修、FAQ、投诉）

如果用户问题包含数字（如"50"、"100"），优先判断可能是订单号或价格，而不是直接视为无关。
如果明显无关（政治、娱乐、医疗、服装、食品等非智能家居品类），标记 out_of_scope=true。

## 2. 意图分类
在范围内的，分类到以下 Worker：

| Worker | 负责领域 | 典型问题 |
|--------|---------|---------|
| general_chat | 闲聊、问候 | "你好"、"在吗"、"谢谢" |
| product_qa | 产品查询/对比/推荐 | "扫地机器人推荐"、"X和Y哪个好" |
| order_qa | 订单状态/物流 | "我的订单到哪了"、"订单#12345详情" |
| after_sales | 售后/FAQ/退换货 | "怎么退货"、"保修多久" |
| multi | 跨领域组合 | "查订单+推荐产品" |

如果 multi，列出 workers[] 列表。

输出 JSON:
{"logic": "分类理由", "out_of_scope": false, "intent": "product_qa", "workers": ["product_qa"]}
"""

# Pydantic model for structured output
from pydantic import BaseModel, Field
from typing import List

class ClassifyOutput(BaseModel):
    logic: str = Field(description="分类理由")
    out_of_scope: bool = Field(default=False)
    intent: str = Field(description="general_chat | product_qa | order_qa | after_sales | multi")
    workers: List[str] = Field(default_factory=list)
```

- [ ] **Step 2: Write decompose prompt**

```python
# llm_backend/app/lg_agent/prompts/supervisor/decompose.py

DECOMPOSE_SYSTEM_PROMPT = """你是任务拆解专家。用户问题需要多个 Worker 协作。拆解为独立的子任务。

规则：
- 每个子任务分配给一个 Worker
- 子任务描述要自包含，Worker 不需要回头看原始问题
- 保留关键约束（订单号、预算、品类等）
- 能并行的任务标记相同 priority（1=最高）

输出 JSON 数组：
[
  {"worker_type": "order_qa", "description": "...", "context": {"order_id": 12345}, "priority": 1},
  {"worker_type": "product_qa", "description": "...", "context": {}, "priority": 1}
]
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class DecomposeSubTask(BaseModel):
    worker_type: str = Field(description="product_qa | order_qa | after_sales | general_chat")
    description: str = Field(description="自包含的任务描述")
    context: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=1)


class DecomposeOutput(BaseModel):
    sub_tasks: List[DecomposeSubTask] = Field(description="子任务列表")
```

- [ ] **Step 3: Write merge prompt**

```python
# llm_backend/app/lg_agent/prompts/supervisor/merge.py

MERGE_SYSTEM_PROMPT = """你是灵犀智购的客服主管。将多个 Worker 的回答合并为一条连贯的用户回复。

合并规则：
1. 如果只有一个 Worker 结果，直接使用其回答（可微调措辞）
2. 多个结果按逻辑顺序排列（先订单/售后，再产品推荐）
3. 如果有 worker 需要澄清，以澄清问题优先
4. 如果有 worker 转人工，告知用户正在转接
5. 不要编造 Workers 没有提供的信息

回复风格：电商客服，亲切专业，开场用"亲～"。
"""
```

- [ ] **Step 4: Verify imports**

Run: `cd llm_backend && python -c "from app.lg_agent.prompts.supervisor.classify import CLASSIFY_SYSTEM_PROMPT, ClassifyOutput; from app.lg_agent.prompts.supervisor.decompose import DECOMPOSE_SYSTEM_PROMPT, DecomposeOutput; from app.lg_agent.prompts.supervisor.merge import MERGE_SYSTEM_PROMPT; print(f'Classify prompt: {len(CLASSIFY_SYSTEM_PROMPT)} chars'); print('OK')"`
Expected: character count and `OK`

---

### Task 11: Supervisor Nodes

**Files:**
- Create: `llm_backend/app/lg_agent/supervisor/__init__.py`
- Create: `llm_backend/app/lg_agent/supervisor/nodes.py`

- [ ] **Step 1: Create package init**

```python
# llm_backend/app/lg_agent/supervisor/__init__.py
"""Supervisor 模块 — 意图分类、任务拆解、Worker 调度、结果合并"""
```

- [ ] **Step 2: Write classify_intent node**

```python
# llm_backend/app/lg_agent/supervisor/nodes.py
"""Supervisor 节点实现"""
import logging
import uuid
from typing import Any, Dict, List

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.types import Send

from app.lg_agent.supervisor.state import SupervisorState, SubTask, WorkerResult
from app.lg_agent.prompts.supervisor.classify import CLASSIFY_SYSTEM_PROMPT, ClassifyOutput
from app.lg_agent.prompts.supervisor.decompose import DECOMPOSE_SYSTEM_PROMPT, DecomposeOutput
from app.lg_agent.prompts.supervisor.merge import MERGE_SYSTEM_PROMPT

_log = logging.getLogger(__name__)


def make_classify_node(llm: BaseChatModel):
    classify_prompt = ChatPromptTemplate.from_messages([
        ("system", CLASSIFY_SYSTEM_PROMPT),
        ("human", "{query}"),
    ])

    async def classify_intent(state: SupervisorState, *, config) -> Dict[str, Any]:
        msgs = state.get("messages", [])
        query = msgs[-1].content if msgs and hasattr(msgs[-1], "content") else str(msgs[-1])

        result = await (classify_prompt | llm.with_structured_output(ClassifyOutput)).ainvoke({"query": query})

        _log.info(f"Classify: intent={result.intent} out_of_scope={result.out_of_scope}")

        if result.out_of_scope:
            return {
                "intent": "out_of_scope",
                "next_action": "respond",
                "final_answer": "很抱歉，您的问题超出了我们的服务范围。我们专注于智能家居产品的咨询服务，如有相关问题欢迎继续提问。",
            }

        if result.intent == "general_chat":
            return {
                "intent": "general_chat",
                "workers": ["general_chat"],
                "sub_tasks": [SubTask(
                    task_id=str(uuid.uuid4()),
                    worker_type="general_chat",
                    description=query,
                    context={},
                    priority=1,
                )],
                "next_action": "dispatch",
            }

        if result.intent == "multi":
            return {
                "intent": "multi",
                "workers": result.workers,
                "next_action": "decompose",
            }

        # Single worker
        worker = result.intent
        return {
            "intent": result.intent,
            "workers": [worker],
            "sub_tasks": [SubTask(
                task_id=str(uuid.uuid4()),
                worker_type=worker,
                description=query,
                context={},
                priority=1,
            )],
            "next_action": "dispatch",
        }

    return classify_intent
```

- [ ] **Step 3: Write decompose_tasks node**

```python
# Continue in nodes.py

def make_decompose_node(llm: BaseChatModel):
    decompose_prompt = ChatPromptTemplate.from_messages([
        ("system", DECOMPOSE_SYSTEM_PROMPT),
        ("human", "用户问题: {question}\n需要的 Worker: {workers}\n\n请拆解为子任务:"),
    ])

    async def decompose_tasks(state: SupervisorState, *, config) -> Dict[str, Any]:
        msgs = state.get("messages", [])
        query = msgs[-1].content if msgs and hasattr(msgs[-1], "content") else str(msgs[-1])
        workers = state.get("workers", [])

        result = await (decompose_prompt | llm.with_structured_output(DecomposeOutput)).ainvoke({
            "question": query,
            "workers": ", ".join(workers),
        })

        sub_tasks = []
        for t in result.sub_tasks:
            sub_tasks.append(SubTask(
                task_id=str(uuid.uuid4()),
                worker_type=t.worker_type,
                description=t.description,
                context=t.context,
                priority=t.priority,
            ))

        _log.info(f"Decompose: {len(sub_tasks)} sub-tasks")
        return {"sub_tasks": sub_tasks, "next_action": "dispatch"}

    return decompose_tasks
```

- [ ] **Step 4: Write dispatch_workers node**

```python
# Continue in nodes.py

def dispatch_workers(state: SupervisorState, *, config) -> List[Send]:
    """使用 Send() 并行分发子任务到各 Worker 子图"""
    sub_tasks = state.get("sub_tasks", [])
    msgs = state.get("messages", [])

    sends = []
    for task in sub_tasks:
        worker_state = {
            "messages": list(msgs),
            "worker_type": task["worker_type"],
            "task": task["description"],
            "context": task.get("context", {}),
            "iteration_count": 0,
            "next_action": "think",
            "tool_call_history": [],
            "final_answer": "",
            "status": "",
            "clarification_question": "",
        }
        sends.append(Send(task["worker_type"], worker_state))

    _log.info(f"Dispatch: {len(sends)} workers → {[s.node for s in sends]}")
    return sends
```

- [ ] **Step 5: Write merge_results + respond nodes**

```python
# Continue in nodes.py

def make_merge_node(llm: BaseChatModel):
    merge_prompt = ChatPromptTemplate.from_messages([
        ("system", MERGE_SYSTEM_PROMPT),
        ("human", "Worker 执行结果:\n{worker_results}\n\n对话历史:\n{context}\n\n请生成用户回复:"),
    ])

    async def merge_results(state: SupervisorState, *, config) -> Dict[str, Any]:
        results = state.get("worker_results", [])
        if not results:
            return {"final_answer": "抱歉，处理过程中出现了问题，请稍后再试。", "next_action": "respond"}

        # Check for clarifications
        for r in results:
            if r.get("status") == "clarification_needed":
                return {
                    "pending_clarification": r.get("clarification_question", ""),
                    "needs_clarification": True,
                    "next_action": "clarify",
                }

        if len(results) == 1:
            return {
                "final_answer": results[0].get("answer", ""),
                "next_action": "respond",
            }

        # Multiple results: merge via LLM
        msgs = state.get("messages", [])
        context = "\n".join(
            str(m.content)[:200] for m in msgs[-4:]
        ) if msgs else "无"

        results_text = "\n---\n".join(
            f"[{r.get('worker_type', 'unknown')}] {r.get('answer', '')}"
            for r in results
        )

        response = await (merge_prompt | llm).ainvoke({
            "worker_results": results_text,
            "context": context,
        })

        answer = response.content if hasattr(response, "content") else str(response)
        return {"final_answer": answer, "next_action": "respond"}

    return merge_results


async def respond_node(state: SupervisorState, *, config) -> Dict[str, Any]:
    answer = state.get("final_answer", "抱歉，我暂时无法回答这个问题。")
    return {"messages": [AIMessage(content=answer)]}
```

- [ ] **Step 6: Verify imports**

Run: `cd llm_backend && python -c "from app.lg_agent.supervisor.nodes import make_classify_node, make_decompose_node, dispatch_workers, make_merge_node, respond_node; print('OK')"`
Expected: `OK`

---

## Phase 5: Assembly

### Task 12: Supergraph Composition

**Files:**
- Rewrite: `llm_backend/app/lg_agent/lg_builder.py`

- [ ] **Step 1: Rewrite lg_builder.py**

```python
# llm_backend/app/lg_agent/lg_builder.py
"""Multi-Agent Supervisor Graph — 替代原单 Agent Pipeline"""
import sqlite3
import logging

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from app.core.config import settings
from app.services.llm_factory import LLMFactory
from app.lg_agent.supervisor.state import SupervisorState
from app.lg_agent.supervisor.nodes import (
    make_classify_node,
    make_decompose_node,
    dispatch_workers,
    make_merge_node,
    respond_node,
)
from app.lg_agent.workers.react_loop import build_worker_graph
from app.lg_agent.workers.tools.schemas import (
    semantic_search, compare_products, recommend,
    track_shipment, create_ticket, ask_clarification, escalate_to_human,
    predefined_cypher, cypher_query,
)
from app.lg_agent.workers.tools.registry import register_tool
from app.lg_agent.workers.tools.executors import (
    AskClarificationExecutor, EscalateToHumanExecutor,
)

_log = logging.getLogger(__name__)


# ── Tool → Worker mapping ──
WORKER_TOOL_MAP = {
    "product_qa": [semantic_search, compare_products, recommend, predefined_cypher, cypher_query, ask_clarification],
    "order_qa": [track_shipment, predefined_cypher, cypher_query, ask_clarification],
    "after_sales": [create_ticket, escalate_to_human, predefined_cypher, cypher_query, ask_clarification],
    "general_chat": [ask_clarification],
}


# ── Register tools (lazy init — executors created when Neo4j/Milvus available) ──
def _init_tool_registry():
    """延迟初始化工具注册表（需要 Neo4j/Milvus 连接）"""
    try:
        from app.lg_agent.kg_sub_graph.neo4j_conn import get_neo4j_graph
        from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.predefined_cypher.cypher_dict import predefined_cypher_dict
        from app.lg_agent.workers.tools.executors import (
            SemanticSearchExecutor, CompareProductsExecutor, RecommendExecutor,
            TrackShipmentExecutor, CreateTicketExecutor,
        )

        neo4j = get_neo4j_graph()

        # These require Milvus + embedding — create if available
        milvus = None
        embed = None
        try:
            from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.predefined_cypher.utils import create_vector_query_matcher
            from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.predefined_cypher.descriptions import QUERY_DESCRIPTIONS
            matcher = create_vector_query_matcher(predefined_cypher_dict, QUERY_DESCRIPTIONS)
            milvus = matcher._milvus
            embed = matcher._embedding
        except Exception:
            _log.warning("Milvus/embedding not available — semantic_search and recommend disabled")

        if milvus and embed:
            register_tool("semantic_search", SemanticSearchExecutor(milvus, embed))

        register_tool("compare_products", CompareProductsExecutor(neo4j, predefined_cypher_dict))
        if milvus and embed:
            register_tool("recommend", RecommendExecutor(milvus, embed, neo4j, predefined_cypher_dict))
        register_tool("track_shipment", TrackShipmentExecutor(neo4j))

        from app.core.database import AsyncSessionLocal
        register_tool("create_ticket", CreateTicketExecutor(AsyncSessionLocal))

    except Exception as e:
        _log.warning(f"Tool registry partial init: {e}")

    # These don't need external services
    register_tool("ask_clarification", AskClarificationExecutor())
    register_tool("escalate_to_human", EscalateToHumanExecutor())


def build_supervisor_graph() -> StateGraph:
    """构建 Supervisor + Workers 超级图"""
    _init_tool_registry()

    llm = LLMFactory.create_agent_llm()

    builder = StateGraph(SupervisorState)

    # ── Supervisor nodes ──
    builder.add_node("classify_intent", make_classify_node(llm))
    builder.add_node("decompose_tasks", make_decompose_node(llm))
    builder.add_node("dispatch_workers", dispatch_workers)
    builder.add_node("merge_results", make_merge_node(llm))
    builder.add_node("respond", respond_node)

    # ── Worker sub-graphs ──
    for worker_type, tool_schemas in WORKER_TOOL_MAP.items():
        worker_graph = build_worker_graph(worker_type, llm, tool_schemas)
        builder.add_node(worker_type, worker_graph)

    # ── Edges ──
    builder.add_edge(START, "classify_intent")

    def route_after_classify(state: SupervisorState):
        action = state.get("next_action", "respond")
        if action == "decompose":
            return "decompose_tasks"
        elif action == "dispatch":
            return "dispatch_workers"
        else:
            return "respond"

    builder.add_conditional_edges("classify_intent", route_after_classify, {
        "decompose_tasks": "decompose_tasks",
        "dispatch_workers": "dispatch_workers",
        "respond": "respond",
    })
    builder.add_edge("decompose_tasks", "dispatch_workers")
    builder.add_edge("dispatch_workers", "merge_results")

    def route_after_merge(state: SupervisorState):
        if state.get("needs_clarification"):
            return "clarify"
        return "respond"

    builder.add_conditional_edges("merge_results", route_after_merge, {
        "clarify": "respond",
        "respond": "respond",
    })
    builder.add_edge("respond", END)

    # ── Checkpointer ──
    conn = sqlite3.connect(settings.CHECKPOINT_DB_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    return builder.compile(checkpointer=checkpointer)


# ── Module-level graph instance (replaces old `graph`) ──
try:
    supervisor_graph = build_supervisor_graph()
    _log.info("Supervisor graph compiled successfully")
except Exception as e:
    _log.error(f"Failed to build supervisor graph: {e}")
    supervisor_graph = None
```

- [ ] **Step 2: Verify compilation**

Run: `cd llm_backend && python -c "from app.lg_agent.lg_builder import supervisor_graph; print(f'Graph: {supervisor_graph}')"`
Expected: prints graph object reference (may need Neo4j/Milvus running, mock if needed)

---

### Task 13: API Route Switch

**Files:**
- Modify: `llm_backend/app/api/langgraph.py:15`

- [ ] **Step 1: Change one line**

```python
# In llm_backend/app/api/langgraph.py, change line 15:
# OLD:
from app.lg_agent.lg_builder import graph
# NEW:
from app.lg_agent.lg_builder import supervisor_graph as graph
```

- [ ] **Step 2: Verify import**

Run: `cd llm_backend && python -c "from app.api.langgraph import router; print('OK')"`
Expected: `OK`

---

## Phase 6: Tests

### Task 14: Worker ReAct Unit Test

**Files:**
- Create: `llm_backend/tests/test_worker_react.py`

- [ ] **Step 1: Write test for route_after_think**

```python
# llm_backend/tests/test_worker_react.py
"""Worker ReAct loop unit tests"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

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
```

- [ ] **Step 2: Run tests**

Run: `cd llm_backend && python -m pytest tests/test_worker_react.py -v`
Expected: 4 tests PASS

- [ ] **Step 3: Write test for observe exit conditions**

```python
# Append to test_worker_react.py

class TestObserveExitConditions:
    def test_max_iterations_forces_finish(self):
        """When iteration_count >= MAX_ITERATIONS, observe should force finish"""
        from app.lg_agent.workers.react_loop import observe_node

        state = make_state(iteration_count=MAX_ITERATIONS - 1, tool_to_execute="semantic_search")
        state["messages"].append(
            ToolMessage(content="Records: [{'product_name': 'Test'}]", tool_call_id="1")
        )

        result = observe_node(state)
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
```

- [ ] **Step 4: Run all tests**

Run: `cd llm_backend && python -m pytest tests/test_worker_react.py -v`
Expected: 6-7 tests PASS

---

### Task 15: Supervisor Routing Test

**Files:**
- Create: `llm_backend/tests/test_supervisor_routing.py`

- [ ] **Step 1: Write routing logic tests**

```python
# llm_backend/tests/test_supervisor_routing.py
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

    def test_decompose_prompt_mentions_parallel(self):
        assert "并行" in DECOMPOSE_SYSTEM_PROMPT or "priority" in DECOMPOSE_SYSTEM_PROMPT

    def test_merge_prompt_style(self):
        assert "亲～" in MERGE_SYSTEM_PROMPT


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
        )
        assert wr["status"] == "success"
        assert wr["iterations_used"] == 3

    def test_worker_results_accumulate_with_add(self):
        # Verify the annotated List[WorkerResult, add] pattern
        r1 = WorkerResult(task_id="1", worker_type="a", answer="ok", status="success", clarification_question="", tool_calls_made=1, iterations_used=1)
        r2 = WorkerResult(task_id="2", worker_type="b", answer="ok", status="success", clarification_question="", tool_calls_made=1, iterations_used=1)
        # add operator concatenates: [r1] + [r2] = [r1, r2]
        combined = [r1] + [r2]
        assert len(combined) == 2
```

- [ ] **Step 2: Run tests**

Run: `cd llm_backend && python -m pytest tests/test_supervisor_routing.py -v`
Expected: 6 tests PASS

---

## Phase 7: Integration & Benchmark

### Task 16: Full Integration Smoke Test

- [ ] **Step 1: Start the API server**

Run: `cd llm_backend && timeout 10 python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 2>&1 || true`
Expected: server starts without import errors

- [ ] **Step 2: Test simple query via curl**

Run:
```bash
curl -s -X POST http://localhost:8000/api/langgraph/query \
  -F "query=你好" \
  -F "user_id=1" | head -5
```
Expected: SSE stream with JSON chunks, no 500 error

- [ ] **Step 3: Check logs for ReAct loop traces**

Run: `grep -E "(Classify|Think|Act|Observe|Worker|Dispatch)" logs/app.log | tail -20` (if logs exist)
Expected: classify/think/act traces visible

---

### Task 17: Performance Comparison

- [ ] **Step 1: Record baseline (old graph if still available)**

Note: old graph is preserved at `lg_builder.py` commit `5dced05`.

- [ ] **Step 2: Run 5 test queries on new graph**

Run manually via curl and record:
- "你好" → expected <5s
- "有什么智能门锁推荐" → expected <15s
- "订单#10248的物流状态" → expected <15s
- "怎么退货" → expected <12s
- "查一下订单#10248，顺便推荐一个扫地机器人" → expected <20s

- [ ] **Step 3: Compare with spec expectations**

| Query | Old (est.) | New Target | Actual |
|-------|-----------|------------|--------|
| "你好" | ~30s | <5s | ___s |
| 产品推荐 | ~35s | <15s | ___s |
| 订单查询 | ~35s | <15s | ___s |
| 售后FAQ | ~35s | <12s | ___s |
| 跨领域 | ~60s | <20s | ___s |

---

## Completion Checklist

- [ ] All 17 tasks complete
- [ ] 6/6 new tool schemas defined
- [ ] 7/7 tool executors implemented
- [ ] 5/5 worker types have prompts + ReAct loop config
- [ ] 3/3 supervisor nodes operational
- [ ] Supergraph compiles with all worker subgraphs
- [ ] API route switched (1 line)
- [ ] Unit tests pass (worker react + supervisor routing)
- [ ] Integration smoke test passes
- [ ] Performance meets target (3-5 LLM calls vs old 6)
