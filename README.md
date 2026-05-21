# 灵犀智购 — 智能客服系统

基于 **LangGraph Multi-Agent + DeepSeek + GPT** 构建的智能电商客服系统，面向消费电子场景。Supervisor 节点先做意图分类，再把任务派发给 4 个并行的 ReAct Worker（产品咨询 / 订单查询 / 售后处理 / 闲聊），每个 Worker 在自己的工具集里循环推理，最终由 Supervisor 合成回复。前后端通过 SSE 流式输出 + JWT 登录 + 分段式记忆持久化。

> **当前分支**: `feat/multi-agent`
> 本文档对应已重构后的 Supervisor + Worker 多 Agent 架构。如果你之前看过单图 + 子图版本（Router → Guardrails → Planner → Cypher），那是 pre-refactor 设计，已废弃。

---

## 目录

- [架构总览](#架构总览)
- [核心特性](#核心特性)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [配置参考](#配置参考)
- [关键模块详解](#关键模块详解)
  - [Supervisor + 4 Worker](#supervisor--4-worker)
  - [三档 LLM 路由](#三档-llm-路由)
  - [DataService 数据层](#dataservice-数据层)
  - [工具注册表](#工具注册表)
  - [记忆系统 v2-lite](#记忆系统-v2-lite)
  - [登录与会话恢复](#登录与会话恢复)
- [API 文档](#api-文档)
- [数据库迁移](#数据库迁移)
- [项目不变量（看代码前先读这里）](#项目不变量看代码前先读这里)
- [常见问题](#常见问题)
- [License](#license)

---

## 架构总览

```
┌──────────────────────── 前端 (Vue 3 + Vite + Tailwind v4) ────────────────────────┐
│  Login.vue → Shop.vue / Chat.vue                                                  │
│  composables: useAuth (JWT) · useChat (SSE)                                       │
│  beforeEach 守卫:未登录 → /login                                                  │
└──────────────────────────────────────┬───────────────────────────────────────────┘
                                       │ POST /api/langgraph/query  (SSE)
                                       │ Authorization: Bearer <JWT>
                                       │ X-Conversation-ID: <thread_id>
                                       ▼
┌────────────────────── 后端 (FastAPI + Uvicorn :8000) ─────────────────────────────┐
│                                                                                   │
│  ┌─── LangGraph Multi-Agent (lg_builder.build_supervisor_graph) ──────────────┐  │
│  │                                                                            │  │
│  │   classify_intent  ─multi?─→  decompose_tasks  ─Send─→  Workers (并行)     │  │
│  │   (flash)                     (flash)                   │                  │  │
│  │                                                          ▼                  │  │
│  │                              respond ◀── merge_results ◀── 4 个 ReAct      │  │
│  │                              (token   ←   (flash 或    ←    sub-graph      │  │
│  │                               stream)      fast-path)                       │  │
│  │                                                                            │  │
│  │   Workers (每个都是 create_react_agent 包了一层 StateGraph):              │  │
│  │     product_qa   (tier=tool)   tools: semantic_search/compare/recommend    │  │
│  │     order_qa     (tier=tool)   tools: track_shipment/order lookup          │  │
│  │     after_sales  (tier=reason) tools: search_faq/create_ticket/escalate    │  │
│  │     general_chat (tier=flash)  tools: ask_clarification only               │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                   │
│  Services: LLMFactory (3-tier) · MemoryService (v2-lite) · SegmentManager        │
│  Data    : ProductService · OrderService · PolicyService → Neo4j + Milvus        │
└───────────────────────────────────────────────────────────────────────────────────┘
       │                │                  │                    │
       ▼                ▼                  ▼                    ▼
  ┌─────────┐    ┌──────────┐       ┌──────────┐         ┌──────────┐
  │ DeepSeek│    │   GPT    │       │  Neo4j   │         │  MySQL   │
  │  flash  │    │ tool/    │       │ (产品/订单 │         │ (用户/会话 │
  │         │    │ reason   │       │  FAQ 图谱)│         │ /消息/槽位)│
  └─────────┘    └──────────┘       └──────────┘         └──────────┘
                                          │
                                    ┌─────┴─────┐
                                    │  Milvus   │
                                    │ (产品向量) │
                                    └───────────┘
                                          │
                                    ┌─────┴─────┐
                                    │  Ollama   │
                                    │ (bge-m3)  │
                                    └───────────┘
```

---

## 核心特性

- **多 Agent 并行**: Supervisor 把多意图任务通过 `Send` API 并发派发给多个 Worker，单意图直接走单 Worker。
- **三档 LLM 路由**: `flash`(DeepSeek 主力) / `tool`(GPT-5.4 Mini 工具调用) / `reason`(GPT-5.5 推理共情) 按 Worker 职责分配，平衡成本 / 工具稳定性 / 推理质量。
- **ReAct + 工具自治**: 每个 Worker 通过 `create_react_agent` 在固定工具集内循环 (`MAX_RECURSION=30`)，能自己决定是否再调一次工具、是否求助、是否升级人工。
- **结构化控制信号**: 工具返回 `{success, error, control}`，`control.action ∈ {clarify, escalate, reroute}` 反馈给 Supervisor。
- **分段式记忆**: `(segment_id, worker_type)` 二维隔离槽位，product_qa 和 order_qa 不再互相污染。
- **会话恢复**: 退出登录后再回来，自动从 `/conversations/latest` 拉历史，连续对话不丢上下文。
- **SSE 流式 + 自愈**: 后端发现 `conversation_id` 在 DB 里找不到会自动建一条，前端 localStorage 不同步也不会崩。

---

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 前端框架 | Vue 3.5 + Vite 8 + Vue Router 5 | SPA + 路由守卫 |
| UI / 样式 | Tailwind CSS v4 + shadcn-vue + motion-v | 暗色 + 珊瑚/薰衣草配色 |
| 后端框架 | FastAPI 0.115 + Uvicorn | REST + SSE |
| Agent 框架 | LangGraph 0.3 + langgraph-checkpoint | Supervisor StateGraph + ReAct 子图 + SQLite checkpoint |
| LLM (主力) | DeepSeek `deepseek-chat` (via `langchain-deepseek`) | classify / decompose / merge / general_chat |
| LLM (工具) | GPT-5.4 Mini (via `langchain-openai` + aihubmix) | product_qa / order_qa |
| LLM (推理) | GPT-5.5 (via `langchain-openai` + aihubmix) | after_sales |
| 图数据库 | Neo4j 5.26 | 产品 / 订单 / FAQ 知识图谱 |
| 关系数据库 | MySQL 8.0 | 用户 / 会话 / 消息 / 槽位 / 段 |
| ORM | SQLAlchemy 2.0 async | 异步 DB 访问 |
| 向量数据库 | Milvus 2.5 (+ etcd + MinIO) | 产品描述向量 |
| Embedding | Ollama `bge-m3` | 1024 维中文向量 |
| Migration | Alembic 1.14 | MySQL schema 版本 |
| 认证 | JWT (HS256) + bcrypt + SHA256(前端) | 登录态 |
| 日志 | Loguru | 强制 UTF-8 stdout 兼容 Windows GBK |
| 容器编排 | Docker Compose | MySQL / Neo4j / Milvus / etcd / MinIO |

---

## 项目结构

```
customer/
├── frontend/                          Vue 3 前端
│   ├── src/
│   │   ├── App.vue                    根组件
│   │   ├── main.js                    入口
│   │   ├── router/index.js            路由 + beforeEach 守卫
│   │   ├── views/
│   │   │   ├── Login.vue              登录 / 注册 (welcome back hero)
│   │   │   ├── Shop.vue               电商首页
│   │   │   └── Chat.vue               客服对话 (SSE 接收 + 新对话按钮 + 退出)
│   │   ├── components/
│   │   │   ├── PhoneDashboard.vue
│   │   │   └── ProductCard.vue
│   │   └── composables/
│   │       ├── useAuth.js             JWT 登录 / SHA256 / 自动恢复 thread_id
│   │       ├── useChat.js             SSE + Bearer + loadHistory
│   │       └── useScrollReveal.js
│   ├── vite.config.js                 /api → http://localhost:8000
│   └── package.json
│
├── llm_backend/                       FastAPI 后端 + LangGraph Multi-Agent
│   ├── main.py                        FastAPI app (CORS + 路由)
│   ├── run.py                         Uvicorn 启动 (不要 --reload)
│   ├── .env.example                   环境模板
│   │
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py                /register · /token · /users/me (差异化错误)
│   │   │   ├── langgraph.py           /langgraph/query (SSE) · conversation 自愈
│   │   │   └── conversations.py       /conversations/latest · /by-thread/{id}/messages
│   │   │
│   │   ├── core/
│   │   │   ├── config.py              pydantic-settings 单例 (改 .env 必须重启)
│   │   │   ├── database.py            async engine + AsyncSessionLocal
│   │   │   ├── security.py            JWT + OAuth2 dependency
│   │   │   ├── hashing.py             bcrypt + 脏数据 try/except 兜底
│   │   │   └── logger.py              Loguru + sys.stdout.reconfigure utf-8
│   │   │
│   │   ├── lg_agent/                  LangGraph Multi-Agent 核心
│   │   │   ├── lg_builder.py          build_supervisor_graph + 工具注册表初始化 + checkpointer
│   │   │   │
│   │   │   ├── supervisor/
│   │   │   │   ├── state.py           SupervisorState · SubTask · WorkerResult · 合并 reducer
│   │   │   │   └── nodes.py           classify_intent / decompose_tasks / merge_results / respond
│   │   │   │
│   │   │   ├── workers/
│   │   │   │   ├── react_loop.py      通用 Worker 构造器 (create_react_agent + 控制信号解析)
│   │   │   │   ├── state.py           WorkerInternalState (注意:无 add_messages reducer)
│   │   │   │   ├── product_qa.py      产品咨询 (语义搜索 / 对比 / 推荐)
│   │   │   │   ├── order_qa.py        订单查询 / 物流追踪
│   │   │   │   ├── after_sales.py     售后 (FAQ / 工单 / 升级人工)
│   │   │   │   ├── general_chat.py    闲聊 (只能 ask_clarification)
│   │   │   │   └── tools/
│   │   │   │       ├── schemas.py     Pydantic 工具 schema
│   │   │   │       ├── executors.py   薄包装 → DataService
│   │   │   │       └── registry.py    register_tool / create_tool
│   │   │   │
│   │   │   ├── data/
│   │   │   │   ├── data_service.py    ProductService · OrderService · PolicyService
│   │   │   │   └── neo4j_conn.py      Neo4jGraph 单例
│   │   │   │
│   │   │   └── prompts/
│   │   │       ├── supervisor/        classify · decompose · merge prompts
│   │   │       └── workers/           think_base 共享提示
│   │   │
│   │   ├── models/                    SQLAlchemy ORM
│   │   │   ├── user.py                User
│   │   │   ├── conversation.py        Conversation (含 summary)
│   │   │   ├── message.py             Message
│   │   │   ├── dialogue_state.py      DialogueState (PK = segment_id + worker_type)
│   │   │   ├── topic_segment.py       TopicSegment (话题段)
│   │   │   └── user_profile.py        UserProfile (长期画像)
│   │   │
│   │   └── services/
│   │       ├── llm_factory.py         LLMFactory.create_llm(tier)
│   │       ├── memory_service.py      write_slot / get_*_segment_slots / get_classify_context
│   │       ├── segment_manager.py     get_or_open_segment(thread_id) / end_segment
│   │       ├── profile_builder.py     段结束后压缩 → user_profile
│   │       ├── conversation_service.py
│   │       ├── user_service.py
│   │       └── deepseek_service.py    备用裸调用
│   │
│   ├── alembic/versions/
│   │   ├── 1ca69f29aad9_initial_schema.py
│   │   ├── a1304eeb2d47_add_thread_id_and_update_dialogue_type.py
│   │   ├── 618835c30a0e_add_memory_tables_dialogue_states_user_.py
│   │   └── d4f9c2a1e8b3_segment_scoped_slots.py
│   │
│   ├── scripts/
│   │   ├── init_db.py
│   │   └── seed_electronics.py        Neo4j + Milvus demo 数据 (28 产品 / 5 订单 / 14 FAQ)
│   │
│   └── tests/
│       ├── test_memory_service.py
│       └── test_worker_react.py
│
├── docker-compose.yml                 MySQL :3307 / Neo4j :7474+7687 / Milvus :19530
├── docs/
│   └── memory-system-v2-recap.md      记忆系统 v2-lite 重构总结
├── CLAUDE.md                          项目约定 + 不变量 (Claude Code 优先读这里)
└── README.md                          本文件
```

---

## 快速开始

### 1. 环境要求

- **Python** 3.12+
- **Node.js** 18+
- **Docker Desktop** (跑 MySQL / Neo4j / Milvus)
- **Ollama** + `bge-m3` 模型 (本地 embedding，约 1.2GB)
- **DeepSeek API Key** ([获取地址](https://platform.deepseek.com/))
- **GPT (aihubmix) API Key** — 用于 product_qa / order_qa / after_sales

### 2. 启动基础设施

```powershell
docker compose up -d
```

这会拉起：
- MySQL 8.0 (host :3307 → container :3306)
- Neo4j 5.26 (:7474 / :7687，账号 `neo4j` / `12345678`)
- Milvus 2.5 (:19530) + etcd + MinIO

> **注意**: docker-compose 把 MySQL 映射到 **3307**(host)，因为本地 MySQL 通常占着 3306。所以下面 `.env` 里要写 `DB_PORT=3307`。

### 3. Ollama embedding 模型

```powershell
ollama serve
ollama pull bge-m3
```

### 4. Python 虚拟环境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r llm_backend\requirements.txt
```

### 5. 配置 `.env`

```powershell
cd llm_backend
Copy-Item .env.example .env
notepad .env
```

至少需要填：

```env
DEEPSEEK_API_KEY=sk-xxx
GPT_API_KEY=sk-xxx              # aihubmix
GPT_BASE_URL=https://aihubmix.com/v1
GPT_TOOL_MODEL=gpt-5-mini       # 实际型号见 services/llm_factory.py 注释
GPT_REASON_MODEL=gpt-5
DB_PORT=3307                    # Docker MySQL 暴露的是 3307
DB_PASSWORD=123456              # 匹配 docker-compose.yml 里的 MYSQL_ROOT_PASSWORD
NEO4J_PASSWORD=12345678
SECRET_KEY=<openssl rand -hex 32 的输出>
```

### 6. 初始化数据库

```powershell
cd llm_backend
python -m alembic upgrade head
python scripts\seed_electronics.py
```

`seed_electronics.py` 会往 Neo4j + Milvus 写入 28 款消费电子 / 5 条订单 / 14 条 FAQ。

### 7. 启动后端

```powershell
cd llm_backend
python run.py
# 或 python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

> 不要加 `--reload`。`pydantic-settings` 是缓存单例，`--reload` 只监听 `.py`，改 `.env` 不会被发现。

### 8. 启动前端

```powershell
cd frontend
npm install
npm run dev
```

打开 `http://localhost:5173`，注册一个账号即可进入聊天页。

---

## 配置参考

### 主要环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | (必填) | DeepSeek API 密钥 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com/v1` | DeepSeek endpoint |
| `DEEPSEEK_MODEL` | `deepseek-chat` | **不要改成 `deepseek-v4-flash` 之类，会触发 reasoner 检测,工具调用直接 500** |
| `GPT_API_KEY` | (必填) | GPT 工具/推理档密钥 (aihubmix) |
| `GPT_BASE_URL` | `https://aihubmix.com/v1` | aihubmix 中转 |
| `GPT_TOOL_MODEL` | (必填) | 工具档模型名 (`gpt-5.4-mini` 类) |
| `GPT_REASON_MODEL` | (必填) | 推理档模型名 (`gpt-5.5`) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 地址 |
| `OLLAMA_EMBEDDING_MODEL` | `bge-m3` | 1024 维 embedding |
| `DB_HOST` / `DB_PORT` | `localhost` / `3307` | MySQL (Docker 映射) |
| `DB_USER` / `DB_PASSWORD` / `DB_NAME` | `root` / (必填) / `constomer` | MySQL 连接 |
| `NEO4J_URL` | `bolt://localhost:7687` | Neo4j Bolt |
| `NEO4J_PASSWORD` | (必填) | 默认 `12345678` |
| `MILVUS_HOST` / `MILVUS_PORT` | `localhost` / `19530` | Milvus |
| `SECRET_KEY` | (必填) | JWT 签名密钥 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT 有效期 |
| `ALLOWED_ORIGINS` | `*` | CORS,生产改成实际域名 |
| `LANGCHAIN_TRACING_V2` | `false` | LangSmith 追踪开关 |
| `LANGCHAIN_API_KEY` | (可选) | LangSmith 密钥 |

### 服务端口

| 服务 | Host 端口 | 容器端口 | 说明 |
|------|-----------|----------|------|
| FastAPI | 8000 | — | 后端 API |
| Vite 前端 | 5173 | — | 开发模式 |
| MySQL | **3307** | 3306 | docker-compose 映射 |
| Neo4j Browser | 7474 | 7474 | http://localhost:7474 |
| Neo4j Bolt | 7687 | 7687 | bolt:// 协议 |
| Milvus | 19530 | 19530 | gRPC |
| MinIO Console | 9001 | 9001 | (内部用) |
| Ollama | 11434 | — | 本地装的，不在 docker-compose 里 |

---

## 关键模块详解

### Supervisor + 4 Worker

**Supervisor 图**(`app/lg_agent/lg_builder.py` + `supervisor/nodes.py`)：

| 节点 | 职责 | 用的 LLM |
|------|------|----------|
| `classify_intent` | 把用户消息分到 1-N 个 Worker，重写 query (带历史指代解析) | flash |
| `decompose_tasks` | 多 Worker 场景下拆成 `SubTask[]` | flash (条件触发) |
| Send dispatch | LangGraph `Send` API 并行启动 Worker 子图 | — |
| `merge_results` | 合并多 Worker 结果。fast-path(confidence ≥ 0.5 且非 fallback)直接透传；否则 LLM 合成 | flash |
| `respond` | token-by-token 流式输出 `final_answer` | flash (复用 merge 产物) |

**Worker 子图**(`workers/react_loop.py:build_worker`):

每个 Worker = `create_react_agent` + 一层薄 StateGraph 壳。壳子负责：
- 注入身份提示 (`prompts/workers/think_base.py` + Worker 自己的）
- 限制工具集 (`product_qa` 只能调 product 相关工具)
- 解析最后一条工具结果的 `control` 字段（`clarify` / `escalate` / `reroute`）
- 算 `confidence`（基于工具调用次数 + 是否返回 fallback 文案）
- 提取 `slots`（工具结果里的结构化字段)
- 输出 `WorkerResult { final_answer, confidence, control, slots, worker_type }`

### 三档 LLM 路由

`services/llm_factory.py::LLMFactory.create_llm(tier)`：

| Tier | 模型 | 用在哪 | 为什么 |
|------|------|--------|--------|
| `flash` | DeepSeek `deepseek-chat` | classify / decompose / merge / general_chat / respond | 中文强、便宜、不/弱工具调用够用 |
| `tool` | GPT-5.4 Mini (aihubmix) | product_qa / order_qa | 工具调用最稳，多步 ReAct 不漂 |
| `reason` | GPT-5.5 (aihubmix) | after_sales | 退换货/赔付场景要推理 + 同理心 |

Worker → tier 映射在 `lg_builder.build_supervisor_graph` 的 `_worker_llm_map` dict 里改。

### DataService 数据层

`app/lg_agent/data/data_service.py` 用三个 Service 类把所有 Milvus + Neo4j 访问收口：

- `ProductService` — `semantic_search` / `compare_products` / `recommend`
- `OrderService` — `track_shipment` / 订单查询
- `PolicyService` — `search_faq`

工具执行器 (`workers/tools/executors.py`) 只做参数提取 + 调 Service。**加新数据访问写在 Service 层，不要写在 executor 或散落的 Cypher 字典里。**

> `app/lg_agent/data/cypher_dict.py` / `descriptions.py` / `vector_matcher.py` 是 pre-refactor 残留，**不在主流程上**，不要给新代码用。

### 工具注册表

`workers/tools/registry.py` 提供两个 API：

```python
register_tool(name, executor)        # 启动时绑定 executor
create_tool(schema_cls)              # 用 Pydantic schema + executor 拼成 StructuredTool 给 ReAct
```

工具返回值统一格式：

```json
{
  "success": true | false,
  "error": "msg" | null,
  "control": { "action": "clarify" | "escalate" | "reroute" } | null,
  "...payload": ...
}
```

`control.action` 是 Worker → Supervisor 的反馈通道。

### 记忆系统 v2-lite

设计目标是修掉 v1 的**跨 Worker 槽位污染**，同时保留分段抽象给未来扩展。

**核心存储**(MySQL)：

| 表 | 主键 | 作用 |
|----|------|------|
| `conversations` | id | 一条完整对话(含 summary) |
| `topic_segments` | id (FK conversation) | 话题段。`ended_at IS NULL` 表示当前活跃段。v2-lite 没触发 end_segment，所以**一条 conversation = 一个永久段** |
| `dialogue_states` | **(segment_id, worker_type)** | 槽位。product_qa 和 order_qa 各占一行，互不污染 |
| `user_profiles` | user_id | 跨段沉淀的偏好画像 |
| `messages` | id | 原始消息 |

**调用流**：

```
classify_intent
  ├── SegmentManager.get_or_open_segment(thread_id) → segment_id
  ├── MemoryService.get_classify_context(thread_id, segment_id, user_id)
  │     返回带标签的分组槽位:
  │       [order_qa记录]   {"last_order_id": "1001"}
  │       [product_qa记录] {"products_mentioned": ["iPhone16"]}
  │       [用户偏好]       {"budget_max": 5000}
  │       [对话摘要]       "上一段聊了什么"
  └── LLM 读这些上下文做 query rewrite

merge_results
  └── 对每个 worker_result:
        MemoryService.write_slot(segment_id, worker_type, slots)
        → (segment_id, worker_type) 行被 UPSERT
```

**关键修复**(`merge_results`)：

- **去掉 merge_prompt 里的"对话历史"字段** — 它是污染源（上轮订单 #1001 会被混进本轮 iPhone 推荐）。
- **fast-path 阈值 0.7 → 0.5** — 中性置信度直接透传 Worker 答案，跳过 LLM 二次合成。

完整设计与"刻意没做的事"清单见 [docs/memory-system-v2-recap.md](docs/memory-system-v2-recap.md)。

### 登录与会话恢复

| 端点 | 行为 |
|------|------|
| `POST /api/register` | 注册，前端先 SHA256 一次 |
| `POST /api/token` | 登录,**区分** "该邮箱未注册" / "密码错误，请重试" (demo 优先 UX,生产可改成统一文案防枚举) |
| `GET /api/conversations/latest` | 返回当前用户最近一条对话的 `thread_id`，登录后自动调，存到 localStorage |
| `GET /api/conversations/by-thread/{thread_id}/messages` | JWT 鉴权后拉历史消息,Chat.vue `onMounted` 调 |

前端 `useAuth.login()` 成功后会立即拉 `/conversations/latest` 写到 `localStorage.lingxi_conversation_id`，Chat 页 mount 时 `loadHistory()` 把消息打回界面。退出再登回来对话不丢。

后端 `/api/langgraph/query` 拿到 `conversation_id` 时先查 DB，找不到就 INSERT 一条（**自愈机制** — 解决浏览器 localStorage 与 DB 不同步，比如 DB 被重置后浏览器还存着旧 thread_id）。

---

## API 文档

启动后端后访问 `http://localhost:8000/docs` 看 Swagger UI。

### 核心端点

**`POST /api/langgraph/query`** — Multi-Agent 对话 (SSE)

```
请求 (multipart/form-data):
  query: "对比小米15和iPhone16"
  user_id: 1
  conversation_id: <thread_id>      (可选,首次请求留空)

请求头:
  Authorization: Bearer <JWT>

响应 (SSE event-stream):
  event: status
  data: {"phase":"classify","msg":"理解意图中..."}

  event: status
  data: {"phase":"workers","msg":"调用 product_qa..."}

  data: "您好~亲~"
  data: "小米15..."
  ...

响应头:
  X-Conversation-ID: <thread_id>
```

**`GET /api/users/me`** — 当前登录用户信息 (JWT)

### 认证端点

| 端点 | 方法 | 认证 | 说明 |
|------|------|------|------|
| `/api/register` | POST | 否 | 注册 |
| `/api/token` | POST | 否 | 登录 → JWT (差异化错误) |
| `/api/users/me` | GET | 是 | 获取当前用户 |

### 会话端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/conversations/latest` | GET | 最近一条对话(用于登录恢复) |
| `/api/conversations/by-thread/{tid}/messages` | GET | 按 thread_id 拉历史 |

---

## 数据库迁移

```powershell
cd llm_backend

# 升级到最新
python -m alembic upgrade head

# 自动生成迁移
python -m alembic revision --autogenerate -m "<描述>"

# 回滚一步
python -m alembic downgrade -1

# 当前版本
python -m alembic current
```

迁移历史：

| Revision | 说明 |
|----------|------|
| `1ca69f29aad9` | initial — users / conversations / messages |
| `a1304eeb2d47` | conversations.thread_id + DialogueType 枚举 |
| `618835c30a0e` | 记忆 v1 — dialogue_states / user_profiles |
| `d4f9c2a1e8b3` | **记忆 v2-lite** — topic_segments + dialogue_states.PK 改为 (segment_id, worker_type) |

---

## 项目不变量（看代码前先读这里）

> 这些约定来自 `CLAUDE.md`。改代码之前先确认这些事情不会被你打破。

1. **`DEEPSEEK_MODEL=deepseek-chat`** — 不要改成 `deepseek-v4-flash` 之类。`langchain-deepseek` 按模型名 pattern match，"v4-flash" 会被误判成 reasoner，工具调用直接 `tool_choice not supported` 500。
2. **`WorkerInternalState.messages` 没有 `add_messages` reducer** — SQLite checkpointer 跨轮持久化 state，加 reducer 会让上一轮 Worker 的 AIMessage 漏进本轮 Send，ReAct agent 会去 replay。
3. **`merge_results` 每条路径都必须写 `final_answer`** — `respond_node` 读 `state["final_answer"]`，漏写会读上轮缓存。
4. **`_build_sends` 只塞一条 `HumanMessage(task.description)`** — 不传历史。多轮上下文通过 classify 改写后的 description 传，不通过 messages 列表。
5. **日志一律用 `loguru`** — `from loguru import logger as _log`。Windows PowerShell stdout 默认 GBK，`print` 或 stdlib `logging` 输出 emoji 会 `UnicodeEncodeError`。
6. **`main.py` 不挂前端静态资源** — 后端只跑 API on :8000，前端独立 Vite dev :5173。
7. **`uvicorn` 不开 `--reload`** — `pydantic-settings` 是缓存单例，`--reload` 只监听 `*.py`，改 `.env` 必须整个重启。

资源限制：`MAX_RECURSION=30` (Worker ReAct 步数)、`MAX_REROUTE=2` (Supervisor 重路由次数)、`_LLM_SEMAPHORE=3` (并发 LLM 调用,挡 429)。

---

## 常见问题

### Q: 为什么不用 `git add -A`?

`.env` 含 secrets，`uploads/` 是用户图，`logs/` 是运行时日志，都不该入库。一律按名字 `git add file1 file2 ...` 显式 stage。

### Q: 启动报 `bcrypt.checkpw ValueError: Invalid salt`?

数据库里有 demo 用户的 `password_hash` 字段是非 bcrypt 格式(比如手动 seed 写了 `'x'`)。`core/hashing.py` 已加 `try/except` 兜底，登录会正常返回 401 而不是 500。需要清掉脏数据 → `DELETE FROM users WHERE password_hash NOT LIKE '$2b$%'`。

### Q: 改了 `.env` 没生效?

`pydantic-settings` 缓存单例 + `--reload` 不监听 `.env`。**必须**结束 uvicorn 进程整个重启。

### Q: 回复夹杂上轮内容(比如问 iPhone 推荐却看到上轮的订单 #1001)?

记忆 v2-lite 已修了三个污染源：
1. 跨 Worker 槽位隔离 `(segment_id, worker_type)`
2. `merge_prompt` 不再注入对话历史
3. `fast-path` 阈值 0.7 → 0.5,中性置信度直接透传

如果还出现，先看 `merge_results` 节点的 fast-path 是否被跳过（`logs/` 里看 `confidence` 值），然后看 `dialogue_states` 表确认槽位没串。

### Q: Milvus 起不来 / collection 不存在?

```powershell
docker compose restart milvus
python llm_backend\scripts\seed_electronics.py  # 重新灌数据 + 建 collection
```

如果 collection schema 改了，需要先在 Python 里 drop 再 seed：

```python
from pymilvus import MilvusClient
MilvusClient(uri='http://localhost:19530').drop_collection('product_descriptions')
```

### Q: 前端 5173 起不来?

```powershell
cd frontend
npm install   # 如果是新克隆
npm run dev
```

确认 `vite.config.js` 里的代理还是 `'/api': 'http://localhost:8000'`。

### Q: 退出登录后历史聊天还能看到吗?

能。登录后 `useAuth.login` 会拉 `/api/conversations/latest`，把 `thread_id` 存到 `localStorage.lingxi_conversation_id`,进到 Chat.vue `onMounted` 时调 `loadHistory(thread_id)` 把消息打回。

### Q: 想清掉所有数据从头开始?

```powershell
docker compose down -v     # 注意 -v 会清 volume,MySQL/Neo4j/Milvus 全清空
docker compose up -d
cd llm_backend
python -m alembic upgrade head
python scripts\seed_electronics.py
```

---

## License

MIT
