# Multi-Agent Architecture Refactor Spec

## Status: Design Complete

---

## 1. Overview

将灵犀智购智能客服系统从单 Agent Pipeline 架构重构为 Supervisor + Worker Agents 的多 Agent 架构。

### 当前架构（Pipeline）

```
Router → Guardrails → Planner → ToolSelection → Execute → Summarize → HalluCheck
  │         │            │           │           │           │           │
 LLM#1     LLM#2        LLM#3       LLM#4       Neo4j       LLM#5       LLM#6
```

固定 6 次串行 LLM 调用，简单问题（"你好"）也要走完 6 步，30-60s。

### 目标架构（Multi-Agent）

```
                    Supervisor
                   /     |     \
            OrderQA  ProductQA  AfterSales  GeneralChat
           (ReAct)   (ReAct)    (ReAct)      (direct)
```

Supervisor 负责意图分类、越界拦截、任务拆解、结果合并。Worker 按领域独立执行 ReAct 循环。预估 3-5 次串行 LLM 调用，12-25s。

### 改动范围

| 层 | 改动 |
|---|------|
| API 路由 | 一行 import 变更 |
| 基础设施 (core/) | 零改动 |
| lg_agent/lg_states.py | 重写 |
| lg_agent/lg_builder.py | 重写 |
| lg_agent/kg_sub_graph/ | 部分复用（tools, cypher_dict, neo4j_conn） |
| lg_agent/supervisor/ | **新增**：classify, decompose, merge |
| lg_agent/workers/ | **新增**：react_loop, tools/, prompts/ |
| 前端 | 零改动 |
| API 接口 | 不变 |

---

## 2. Supervisor Design

### 2.1 Flow

```
START → classify_intent → decompose_tasks → dispatch_workers → merge_results → respond → END
                                                    |                ↑
                                              Send() × N            |
                                              (parallel)     clarify (if needed)
```

### 2.2 classify_intent（替代原 Router + Guardrails）

单次 LLM 调用，同时完成：
- 越界检测（替代 Guardrails）
- 意图分类（替代 Router）：general_chat | product_qa | order_qa | after_sales | multi

Output: `{logic, out_of_scope, intent, workers[]}`

### 2.3 decompose_tasks（替代原 Planner）

仅 multi 场景触发。将用户问题拆解为 1-3 个 SubTask，每个分配给一个 Worker。

SubTask schema:
```python
class SubTask(TypedDict):
    task_id: str
    worker_type: Literal["product_qa", "order_qa", "after_sales", "general_chat"]
    description: str
    context: Dict[str, Any]
    priority: int
```

### 2.4 dispatch_workers

使用 LangGraph `Send()` 向 Worker 子图并行分发 SubTask。

### 2.5 merge_results（替代原 Summarize + HalluCheck）

单次 LLM 调用，合并 Worker 结果。Worker 已在 ReAct 中内置幻觉预防，不再需要独立的 HalluCheck。

---

## 3. Worker ReAct Loop Design

### 3.1 Core Loop

```
START → think → (tool_call?) → act → observe → think → ... → finish → END
                                    ↑_______________|                  |
                                                                 escalate → END
```

- **think**：唯一的 LLM 调用节点。首次包含 Planner 逻辑（任务拆解），后续包含 HalluCheck 逻辑（结果校验）
- **act**：纯工具执行，无 LLM 调用
- **observe**：纯数据转换 + 程序化校验，无 LLM 调用

### 3.2 Think Phase

首次 Think（Planner 融入）：分析任务 → 决定第一步 → 调用工具或直接回答

后续 Think（HalluCheck 融入）：评估工具结果 → 自检"提到的数据是否都在结果中" → 决定继续还是结束

### 3.3 Observe Phase（程序化校验）

纯 Python 逻辑，不做 LLM 调用：

| 校验 | 动作 |
|------|------|
| 记录工具调用 | 追加到 tool_call_history |
| 空结果检测 | 标记 last_tool_empty |
| 迭代计数 | iteration_count += 1 |
| 上限检查 | iteration_count >= 7 → force finish |
| 重复检测 | 连续 2 次相同调用 → 提示 LLM 换工具 |
| 空结果连续 3 次 | 提前结束，告知无数据 |

### 3.4 Loop Exit Conditions

| 条件 | 触发方 | 结果 |
|------|-------|------|
| LLM 输出 final_answer（无 tool_calls） | Think | 正常结束 |
| iteration_count >= 7 | Observe | 强制结束 + 警告 |
| LLM 调用 ask_clarification | Act | 返回澄清请求给 Supervisor |
| LLM 调用 escalate_to_human | Act | 挂起 + 通知人工 |
| 连续 3 次空结果 | Observe | 提前结束 |
| 连续 2 次相同工具调用 | Observe | 跳过执行，提示 LLM |

---

## 4. Tool Interfaces

### 4.1 New Tools

```python
class semantic_search(BaseModel):
    """语义搜索产品。LLM 生成自然语言描述 → bge-m3 向量化 → Milvus COSINE 检索"""
    query: str = Field(..., description="用户需求场景的自然语言描述")
    top_k: int = Field(default=5)

class compare_products(BaseModel):
    """并排对比产品"""
    product_names: List[str] = Field(..., min_length=2, max_length=5)
    aspects: Optional[List[str]] = Field(default=None, description="对比维度")

class recommend(BaseModel):
    """个性化推荐。内部组合 semantic_search + predefined_cypher，多因子排序"""
    scenario: str = Field(...)
    budget_range: Optional[Tuple[float, float]] = Field(default=None)
    preferences: Optional[List[str]] = Field(default=None)
    exclude: Optional[List[str]] = Field(default=None)
    top_k: int = Field(default=3)

class track_shipment(BaseModel):
    """物流追踪"""
    order_id: int = Field(...)

class create_ticket(BaseModel):
    """创建售后工单"""
    issue_type: Literal["退货", "换货", "维修", "投诉", "其他"] = Field(...)
    order_id: Optional[int] = Field(default=None)
    description: str = Field(...)
    priority: Literal["normal", "urgent"] = Field(default="normal")

class ask_clarification(BaseModel):
    """澄清提问。不执行查询，改变循环退出条件"""
    question: str = Field(..., description="向用户提出的澄清问题，单句，不超过30字")
    missing_field: str = Field(...)
    options: Optional[List[str]] = Field(default=None)

class escalate_to_human(BaseModel):
    """转人工"""
    reason: str = Field(...)
    summary: str = Field(...)
    urgency: Literal["normal", "urgent", "critical"] = Field(default="normal")
```

### 4.2 Existing Tools (Reused)

- `predefined_cypher` — 按 Worker 取子集，keyword → Milvus → fallback
- `cypher_query` — Text2Cypher 动态生成，统一兜底
### 4.3 Tool Distribution by Worker

| Worker | Tools |
|--------|-------|
| ProductQA | semantic_search, compare_products, recommend, predefined_cypher[product], cypher_query, ask_clarification |
| OrderQA | lookup_order, track_shipment, predefined_cypher[order], cypher_query, ask_clarification |
| AfterSales | search_faq, create_ticket, escalate_to_human, predefined_cypher[aftersales], cypher_query, ask_clarification |
| GeneralChat | ask_clarification |

### 4.4 Tool Registry Pattern

```python
# lg_agent/workers/tools/registry.py
class ToolExecutor:
    def invoke(self, args: dict) -> ToolResult: ...

TOOL_REGISTRY: Dict[str, ToolExecutor] = {
    "semantic_search": SemanticSearchExecutor(milvus, embed),
    "compare_products": CompareProductsExecutor(neo4j, cypher_dict),
    ...
}
```

Act 节点查注册表 → 调 invoke → 返回 ToolMessage，不感知具体工具逻辑。

---

## 5. State Schemas

### 5.1 SupervisorState

```python
class SupervisorState(TypedDict):
    # 对话
    messages: Annotated[List[AnyMessage], add_messages]
    # 路由
    intent: str
    guardrail_result: Dict[str, Any]
    # 任务拆解
    sub_tasks: List[SubTask]
    # Worker 结果（add 支持并行自动合并）
    worker_results: Annotated[List[WorkerResult], add]
    # 输出
    final_answer: str
    # 控制流
    next_action: str
    needs_clarification: bool
    pending_clarification: str
```

### 5.2 WorkerState

```python
class WorkerState(TypedDict):
    # 对话
    messages: Annotated[List[AnyMessage], add_messages]
    # Worker 身份
    worker_type: str
    task: str
    context: Dict[str, Any]
    # ReAct 循环控制
    iteration_count: int
    next_action: str  # "think" | "act" | "observe" | "finish" | "escalate"
    tool_to_execute: str
    # 审计追踪
    tool_call_history: Annotated[List[ToolCallRecord], add]
    # 输出
    final_answer: str
    status: str  # "success" | "clarification_needed" | "escalated" | "error"
    clarification_question: str
```

### 5.3 Supporting Types

```python
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
    status: Literal["success", "clarification_needed", "escalated", "error"]
    clarification_question: str
    tool_calls_made: int
    iterations_used: int

class ToolCallRecord(TypedDict):
    tool_name: str
    args: Dict[str, Any]
    result_summary: str
    record_count: int
    success: bool
```

---

## 6. System Prompts

### 6.1 File Structure

```
lg_agent/prompts/
├── supervisor/
│   ├── classify.py       # 意图分类 + 越界检测
│   ├── decompose.py      # 任务拆解
│   └── merge.py          # 结果合并
└── workers/
    ├── think_base.py     # 通用 ReAct 规则（共用）
    ├── product_qa.py     # ProductQA 身份
    ├── order_qa.py       # OrderQA 身份
    ├── after_sales.py    # AfterSales 身份
    └── general_chat.py   # GeneralChat 身份
```

Worker prompt 运行时组装：身份 Prompt + 工具清单（动态注入）+ ReAct 规则（共用）。

### 6.2 Key Design Decisions

- Think 阶段是唯一的 LLM 调用节点。Planner 逻辑（首次）和 HalluCheck 逻辑（后续）都通过 prompt 指令融入，不单独调 LLM
- HalluCheck 拆为两块：prompt 前置指令（"提到的东西必须能在工具结果中找到"）+ Observe 阶段程序化校验（实体存在性检查）
- 每个 Worker 只看到自己的工具子集，减少 LLM 选择困难
- Worker prompt 包含领域知识（品类列表、订单字段、售后政策等），让 LLM 判断更准确

---

## 7. Graph Architecture

### 7.1 Main Graph (Supervisor)

```python
# lg_agent/lg_builder.py
def build_supervisor_graph() -> StateGraph:
    builder = StateGraph(SupervisorState)

    builder.add_node("classify_intent", classify_node)
    builder.add_node("decompose_tasks", decompose_node)
    builder.add_node("dispatch_workers", dispatch_node)
    builder.add_node("merge_results", merge_node)
    builder.add_node("respond", respond_node)

    builder.add_edge(START, "classify_intent")
    builder.add_conditional_edges("classify_intent", route_after_classify, {
        "decompose": "decompose_tasks",
        "dispatch": "dispatch_workers",
        "respond": "respond",  # out_of_scope or general_chat
    })
    builder.add_edge("decompose_tasks", "dispatch_workers")
    builder.add_edge("dispatch_workers", "merge_results")  # 等待所有 Send() 完成
    builder.add_conditional_edges("merge_results", route_after_merge, {
        "clarify": END,   # 需要用户回应，等待下次请求
        "respond": "respond",
    })
    builder.add_edge("respond", END)

    return builder.compile(checkpointer=sqlite_saver)
```

### 7.2 Worker Sub-Graph

```python
# lg_agent/workers/react_loop.py
def build_worker_graph(worker_type: str, tools: List[BaseTool]) -> StateGraph:
    builder = StateGraph(WorkerState)

    builder.add_node("think", make_think_node(worker_type, tools))
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

### 7.3 Supergraph Composition

```python
# Supervisor graph dynamically adds Worker subgraphs as nodes
for worker_type, tools in WORKER_TOOL_MAP.items():
    worker_graph = build_worker_graph(worker_type, tools)
    supervisor_graph.add_node(worker_type, worker_graph)
```

---

## 8. Reusable Components (No Changes Needed)

| Component | Path | Reason |
|-----------|------|--------|
| Neo4j connector | kg_sub_graph/neo4j_conn.py | Singleton unchanged |
| Cypher dictionary | cypher_dict.py (60 queries) | Queries unchanged, subset for each Worker |
| Query descriptions | descriptions.py | Used for Milvus vector matching |
| VectorQueryMatcher | predefined_cypher/utils.py | Keyword → vector matching logic reused |
| LLM factory | core/services/llm_factory.py | Same ChatDeepSeek, same config |
| LLM config | core/config.py | Same API keys, model names |
| API routes | api/langgraph.py | Import `supervisor_graph` instead of `graph` |
| Checkpointer | SqliteSaver | Same checkpoint DB, same thread_id pattern |

---

## 9. Implementation Order

1. Worker ReAct loop factory (`workers/react_loop.py`)
2. Tool executors (`workers/tools/`)
3. Worker think prompts (`prompts/workers/`)
4. Each Worker sub-graph (5 workers)
5. Supervisor state + classify node
6. Supervisor decompose + dispatch + merge
7. Supergraph composition in `lg_builder.py`
8. API route switch (one-line import change)
9. Integration test with real queries
10. Performance comparison (old vs new latency)

---

## 10. Performance Expectations

| Metric | Current Pipeline | Multi-Agent Target |
|--------|-----------------|-------------------|
| Simple query ("你好") | 6 LLM calls, ~30s | 1-2 LLM calls, ~5s |
| Single domain query | 6 LLM calls, ~35s | 3-4 LLM calls, ~12s |
| Multi-domain query | 6 LLM calls × N pass, ~60s | 5 LLM calls, ~18s |
| Serial LLM calls (critical path) | 6 | Supervisor(1) + max(Worker 2-3) + Merge(1) = 4-5 |
| Hallucination check cost | 1 full LLM call every query | 0 separate LLM calls (prompt-embedded) |
