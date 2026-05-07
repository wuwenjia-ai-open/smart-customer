# 灵犀智购 — 智能客服系统

基于 **LangGraph + Neo4j + DeepSeek** 构建的智能电商客服系统，面向智能家居消费电子场景。用户登录后通过对话式 AI 客服查询产品、订单、物流、售后政策，Agent 内部通过"路由 → 守卫 → 规划 → 工具选择 → 查询执行 → 结果汇总 → 幻觉检测"的完整链路，自动从知识图谱检索数据并生成自然语言回复。

## 目录

- [系统架构](#系统架构)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [配置参考](#配置参考)
- [API 文档](#api-文档)
- [Agent 工作流详解](#agent-工作流详解)
- [预定义 Cypher 查询](#预定义-cypher-查询)
- [查询匹配策略](#查询匹配策略)
- [数据库迁移](#数据库迁移)
- [常见问题](#常见问题)
- [License](#license)

## 系统架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                          前端 (Vue 3 + Vite)                         │
│  LoginPage → ChatPage → ChatMessage                                 │
│  SSE 流式接收  |  FormData 提交 (文字 + 图片)                         │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ POST /api/langgraph/query (SSE)
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      后端 (FastAPI + Uvicorn)                        │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              LangGraph Agent (主图 + 子图)                     │   │
│  │                                                               │   │
│  │  用户问题                                                     │   │
│  │     │                                                        │   │
│  │     ▼                                                        │   │
│  │  ┌─────────┐    general-query ──→ respond_to_general_query    │   │
│  │  │ Router  │─── additional-query → Guardrails → get_additional│   │
│  │  │ (LLM)   │─── graphrag-query ──→ create_research_plan      │   │
│  │  └─────────┘─── image-query ────→ create_image_query          │   │
│  │                                    │                          │   │
│  │                                    ▼                          │   │
│  │  ┌──────────────────────────────────────────────────────┐    │   │
│  │  │  子图 (multi_tool_workflow)                           │    │   │
│  │  │                                                       │    │   │
│  │  │  Planner ──→ Tool Selection ──→ Query Execution       │    │   │
│  │  │  (LLM)        (LLM)              │                    │    │   │
│  │  │                                  ├─ predefined_cypher │    │   │
│  │  │                                  │   (60条, 关键词+向量)│   │   │
│  │  │                                  └─ cypher_query      │    │   │
│  │  │                                     (LLM 动态生成)     │    │   │
│  │  │                                          │            │    │   │
│  │  │                                          ▼            │    │   │
│  │  │  Summarize ──→ Hallucination Check ──→ answer         │    │   │
│  │  │  (LLM)          (LLM)                                  │    │   │
│  │  └──────────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
         │              │              │               │
         ▼              ▼              ▼               ▼
    ┌─────────┐   ┌─────────┐   ┌─────────┐    ┌──────────┐
    │ DeepSeek│   │ Neo4j   │   │ Milvus  │    │  MySQL   │
    │  (LLM)  │   │ (图数据) │   │ (向量)  │    │ (账户/会话)│
    └─────────┘   └─────────┘   └─────────┘    └──────────┘
                                            │
                                     ┌──────┴──────┐
                                     │    Ollama   │
                                     │  (bge-m3)   │
                                     └─────────────┘
```

## 技术栈

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 前端框架 | Vue 3 | 3.5+ | 电商页面 + 客服聊天界面 |
| 构建工具 | Vite | 6.x | 前端构建与开发服务器 |
| 后端框架 | FastAPI | 0.115+ | REST API + SSE 流式响应 |
| ASGI 服务器 | Uvicorn | 0.34+ | 异步 HTTP 服务器 |
| Agent 框架 | LangGraph | 0.3+ | StateGraph + 条件路由 + 嵌套子图 |
| LLM 接入 | LangChain | 0.3+ | ChatDeepSeek / Ollama Embeddings |
| 主 LLM | DeepSeek `deepseek-chat` | - | 文字对话、Agent 推理、Cypher 生成 |
| 视觉模型 | 通义千问 VL `qwen-vl-plus` | - | 用户上传图片分析 |
| 图数据库 | Neo4j | 5.26 | 知识图谱存储与 Cypher 查询 |
| 关系数据库 | MySQL | 8.0 | 用户/会话/消息持久化 |
| ORM | SQLAlchemy 2.0 (async) | 2.0+ | 异步数据库操作 |
| 向量数据库 | Milvus | 2.5 | 60 条预定义查询描述的向量存储与检索 |
| Embedding | Ollama `bge-m3` | - | 1024 维中文向量化 |
| 数据库迁移 | Alembic | 1.14+ | MySQL schema 版本管理 |
| 开发语言 | Python | 3.12+ | 后端全部逻辑 |
| 前端语言 | JavaScript ES Module | - | Vue 3 组件与组合式 API |

## 项目结构

```
customer/
├── frontend/                          # Vue 3 前端
│   ├── src/
│   │   ├── App.vue                    # 根组件
│   │   ├── main.js                    # 入口
│   │   ├── components/
│   │   │   ├── ChatPage.vue           # 客服聊天页面 (SSE 流式接收)
│   │   │   ├── ChatMessage.vue        # 单条消息渲染
│   │   │   ├── LoginPage.vue          # 登录/注册页
│   │   │   └── ProductCard.vue        # 产品卡片组件
│   │   └── composables/
│   │       ├── useChat.js             # 聊天逻辑 (SSE, FormData, conversation_id)
│   │       ├── useAuth.js             # 认证逻辑 (JWT token)
│   │       └── useProducts.js         # 产品数据
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── llm_backend/                       # FastAPI 后端 + LangGraph Agent
│   ├── main.py                        # FastAPI 应用入口 (挂载路由 + 静态文件)
│   ├── run.py                         # Uvicorn 启动脚本
│   ├── .env                           # 环境变量 (不入 git)
│   ├── .env.example                   # 环境变量模板
│   ├── Dockerfile                     # Docker 镜像
│   │
│   ├── app/
│   │   ├── api/                       # REST API 路由层
│   │   │   ├── auth.py                # 登录 / 注册
│   │   │   ├── chat.py                # DeepSeek 通用对话 (备用)
│   │   │   ├── langgraph.py           # Agent 对话主入口 (SSE 流式)
│   │   │   ├── conversations.py       # 会话管理 CRUD
│   │   │   └── upload.py              # 文件上传
│   │   │
│   │   ├── core/                      # 基础设施层
│   │   │   ├── config.py              # Pydantic Settings (自动读取 .env)
│   │   │   ├── database.py            # SQLAlchemy async engine + session
│   │   │   ├── security.py            # JWT 生成与验证 + OAuth2
│   │   │   ├── hashing.py             # 密码哈希 (bcrypt)
│   │   │   ├── logger.py              # Loguru 日志配置
│   │   │   └── middleware.py           # 请求日志中间件
│   │   │
│   │   ├── lg_agent/                  # LangGraph Agent 核心
│   │   │   ├── lg_builder.py          # 主图构建 (5 节点 + 条件路由)
│   │   │   │   ├── analyze_and_route_query  # 节点1: LLM 路由分类
│   │   │   │   ├── respond_to_general_query # 节点2: 闲聊回复
│   │   │   │   ├── get_additional_info       # 节点3: Guardrails + 补充信息
│   │   │   │   ├── create_image_query        # 节点4: 图片分析
│   │   │   │   └── create_research_plan      # 节点5: 知识图谱子图入口
│   │   │   ├── lg_prompts.py          # 4 套 System Prompt 模板
│   │   │   ├── lg_states.py           # AgentState / Router / InputState
│   │   │   ├── utils.py               # UUID 生成
│   │   │   │
│   │   │   └── kg_sub_graph/          # 知识图谱子图 (核心查询逻辑)
│   │   │       ├── neo4j_conn.py      # Neo4jGraph 单例
│   │   │       ├── tools.py           # predefined_cypher / cypher_query Schema
│   │   │       └── agentic_rag_agents/
│   │   │           ├── components/
│   │   │           │   ├── state.py                # 子图状态定义 (11 个 TypedDict)
│   │   │           │   ├── models.py               # Task 数据类
│   │   │           │   ├── guardrails/             # Guardrails 节点
│   │   │           │   ├── planner/                # Planner 节点 (任务拆解)
│   │   │           │   ├── tool_selection/         # 工具选择节点 (LLM function call)
│   │   │           │   ├── predefined_cypher/      # 预定义查询
│   │   │           │   │   ├── node.py             # 匹配执行 (关键词→向量→动态)
│   │   │           │   │   ├── utils.py            # VectorQueryMatcher (Milvus)
│   │   │           │   │   ├── cypher_dict.py      # 60 条预定义 Cypher
│   │   │           │   │   └── descriptions.py     # 60 条中文描述
│   │   │           │   ├── cypher_tools/           # 动态 Cypher 生成
│   │   │           │   ├── summarize/              # 结果汇总 (LLM)
│   │   │           │   └── check_hallucinations/   # 幻觉检测 (循环重试)
│   │   │           └── workflows/
│   │   │               └── multi_agent/
│   │   │                   ├── multi_tool.py       # 子图构建 (5 节点)
│   │   │                   └── edges.py            # 条件边 + Send 并行
│   │   │
│   │   ├── models/                    # SQLAlchemy ORM
│   │   │   ├── user.py                # User
│   │   │   ├── conversation.py        # Conversation (+DialogueType enum)
│   │   │   ├── message.py             # Message
│   │   │   └── __init__.py
│   │   │
│   │   └── services/                  # 业务逻辑层
│   │       ├── llm_factory.py         # LLM 工厂 (ChatDeepSeek 创建)
│   │       ├── deepseek_service.py    # DeepSeek 通用对话服务 (备用)
│   │       ├── conversation_service.py# 会话管理 CRUD
│   │       └── user_service.py        # 用户管理
│   │
│   ├── data/                          # 数据导入脚本
│   │   ├── import_neo4j_from_csv.py   # CSV → Neo4j 批量导入 (Northwind 数据)
│   │   ├── import_consumer_data.py    # 消费者向数据 (ProductDetail/FAQ/Policy)
│   │   └── add_more_products.py       # 批量添加产品 (52 款)
│   │
│   ├── alembic/                       # 数据库迁移
│   │   ├── env.py                     # Alembic 环境配置
│   │   ├── script.py.mako             # 迁移脚本模板
│   │   └── versions/
│   │       ├── 1ca69f29aad9_initial_schema.py
│   │       └── a1304eeb2d47_add_thread_id_and_update_dialogue_type.py
│   │
│   ├── uploads/                       # 用户上传图片 (gitignore)
│   ├── logs/                          # 应用日志 (gitignore)
│   └── static/dist/                   # 前端构建产物
│
├
├
└── README.md
```


### 节点属性

| 标签 | 关键属性 |
|------|----------|
| Product | ProductName, UnitPrice, UnitsInStock, CategoryName, SupplierName, QuantityPerUnit |
| Category | CategoryName, Description |
| Order | orderId, OrderDate, RequiredDate, ShippedDate, Freight, ShipCountry |
| Customer | CompanyName, ContactName, Phone, City, Country |
| Review | CustomerName, Rating, ReviewText, ReviewDate |
| Supplier | CompanyName, ContactName, Phone, Country |
| Shipper | CompanyName, Phone |
| Employee | FirstName, LastName, Title, HireDate, BirthDate, HomePhone |
| ProductDetail | KeyFeatures, Specifications, SuitableFor, Description |
| FAQ | category, question, answer |
| AfterSalesPolicy | policyType, content |

## 快速开始

### 1. 环境要求

- **Python** 3.12+
- **Node.js** 18+
- **Docker Desktop** (运行 Neo4j, Milvus, MySQL)
- **DeepSeek API Key** ([获取地址](https://platform.deepseek.com/))

### 2. 创建虚拟环境

```bash
cd customer
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r llm_backend/requirements.txt
```

### 3. 启动基础服务

```bash
# Neo4j 图数据库
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/12345678 \
  -e NEO4J_PLUGINS='["apoc"]' \
  neo4j:5

# Milvus 向量数据库 (包含 etcd + MinIO)
docker compose -f docker-compose-milvus.yml up -d

# MySQL
docker run -d --name mysql \
  -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=123456 \
  -e MYSQL_DATABASE=constomer \
  mysql:8.0

# Ollama + bge-m3 模型
ollama serve                    # 如果已安装
ollama pull bge-m3
```

### 4. 配置环境变量

```bash
cd llm_backend
cp .env.example .env
```

编辑 `.env`，至少填入：

```env
DEEPSEEK_API_KEY=sk-your-key-here
```

其他配置项均有默认值，可直接使用。

### 5. 初始化数据库

```bash
# MySQL 建表
cd llm_backend
../.venv/Scripts/python.exe -m alembic upgrade head

# Neo4j 导入数据 (按顺序执行)
../.venv/Scripts/python.exe data/import_neo4j_from_csv.py
../.venv/Scripts/python.exe data/import_consumer_data.py
../.venv/Scripts/python.exe data/add_more_products.py
```

### 6. 启动后端

```bash
cd llm_backend
../.venv/Scripts/python.exe run.py
```

访问 `http://localhost:8000` 即可使用。

### 7. 前端开发（可选）

后端已托管前端静态文件。如需修改前端：

```bash
cd frontend
npm install
npm run dev       # 开发模式 (localhost:5173)
npm run build     # 构建到 ../llm_backend/static/dist/
```

## 配置参考

### 环境变量 (.env)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | (必填) | DeepSeek API 密钥 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com/v1` | DeepSeek API 地址 |
| `DEEPSEEK_MODEL` | `deepseek-chat` | 使用的模型 |
| `VISION_API_KEY` | (可选) | 通义千问 VL API 密钥 |
| `VISION_BASE_URL` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | 视觉模型地址 |
| `VISION_MODEL` | `qwen-vl-plus` | 视觉模型名称 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 服务地址 |
| `OLLAMA_EMBEDDING_MODEL` | `bge-m3` | Embedding 模型名称 |
| `DB_HOST` | `localhost` | MySQL 主机 |
| `DB_PORT` | `3306` | MySQL 端口 |
| `DB_USER` | `root` | MySQL 用户名 |
| `DB_PASSWORD` | (必填) | MySQL 密码 |
| `DB_NAME` | `constomer` | 数据库名 |
| `NEO4J_URL` | `bolt://localhost:7687` | Neo4j Bolt 地址 |
| `NEO4J_USERNAME` | `neo4j` | Neo4j 用户名 |
| `NEO4J_PASSWORD` | `12345678` | Neo4j 密码 |
| `NEO4J_DATABASE` | `neo4j` | Neo4j 数据库名 |
| `MILVUS_HOST` | `localhost` | Milvus 主机 |
| `MILVUS_PORT` | `19530` | Milvus 端口 |
| `MILVUS_COLLECTION` | `predefined_cypher_vectors` | Milvus Collection 名 |
| `SECRET_KEY` | (必填) | JWT 签名密钥 |
| `EMBEDDING_THRESHOLD` | `0.90` | 向量相似度阈值 |
| `CHECKPOINT_DB_PATH` | `checkpoints.db` | LangGraph 对话记忆路径 |

### 服务端口总览

| 服务 | 端口 | 说明 |
|------|------|------|
| FastAPI 后端 | 8000 | Web 页面 + API |
| Neo4j Browser | 7474 | 图数据库可视化 |
| Neo4j Bolt | 7687 | Cypher 查询协议 |
| Milvus | 19530 | 向量数据库 |
| MySQL | 3306 | 关系数据库 |
| Ollama | 11434 | Embedding 模型服务 |

## API 文档

启动后访问 `http://localhost:8000/docs` 查看 Swagger UI。

### 核心端点

**`POST /api/langgraph/query`** — Agent 对话（SSE 流式）

```
请求 (multipart/form-data):
  query: "有哪些智能空调"
  user_id: 1
  conversation_id: (可选，用于保持对话上下文)

响应 (SSE):
  data: {"status":"thinking","msg":"对方正在输入..."}
  data: "您好～亲..."
  data: "谷歌 智能空调 Basic..."
  ...

响应头:
  X-Conversation-ID: <UUID>  (前端保存此 ID 用于后续对话)
```

**`GET /health`** — 健康检查

```json
{
  "status": "ok",
  "neo4j": true,
  "mysql": true
}
```

### 其他端点

| 端点 | 方法 | 认证 | 说明 |
|------|------|------|------|
| `/api/token` | POST | 否 | 登录，返回 JWT |
| `/api/register` | POST | 否 | 用户注册 |
| `/api/chat` | POST | 否 | DeepSeek 通用对话 (SSE, 备用) |
| `/api/conversations` | GET | 是 | 获取用户的所有会话 |
| `/api/conversations` | POST | 是 | 创建新会话 |
| `/api/conversations/{id}` | DELETE | 是 | 删除会话 |
| `/api/conversations/{id}/messages` | GET | 是 | 获取会话消息 |
| `/api/validate-token` | GET | 是 | 验证 JWT 有效性 |

## Agent 工作流详解

### 路由分类 (Router)

LLM 将用户问题分为 4 类：

| 类型 | 触发条件 | 后续处理 |
|------|----------|----------|
| `general-query` | 闲聊、问候 | 直接 LLM 回复 |
| `additional-query` | 信息不足、非经营范围 | Guardrails 拦截 + 引导补充 |
| `graphrag-query` | 需要查询知识库 | 进入子图查询流程 |
| `image-query` | 用户上传图片 | 通义千问 VL 分析 |

### 守卫拦截 (Guardrails)

位于 `get_additional_info` 节点，拦截超出经营范围的问题（如服饰、食品、体育用品）。带对话历史上下文，避免"50"被误判。

### 任务拆解 (Planner)

LLM 将复杂问题拆为 1-3 个独立子任务：

```
"对比小米和华为的智能手环" → [
  "查询小米智能手环的价格和功能",
  "查询华为智能手环的价格和功能"
]
```

### 工具选择 (Tool Selection)

LLM function call 为每个子任务选择工具：

| 工具 | 适用场景 | 特点 |
|------|----------|------|
| `predefined_cypher` | 90% 常见问题 | 快 (60 条预制查询) |
| `cypher_query` | 复杂自定义查询 | 准 (LLM 动态生成 Cypher) |

### 查询执行

三层降级策略：

```
关键词匹配 (优先) → Milvus 向量检索 (备用) → LLM 动态生成 Cypher (最终)
     ↓ 命中                  ↓ 命中                    ↓
  Neo4j 执行             Neo4j 执行              Neo4j 执行
```

关键词匹配覆盖：订单、物流、价格、评价、员工、产品详情、退货、保修、FAQ、支付。有明确约束(数字/品类名)的任务跳过兜底，直接交给动态 Cypher。

### 结果汇总 (Summarize)

LLM 将查询结果整理为客服风格的自然语言：

- 开场用"亲～"或"您好～"
- 适当使用 emoji
- 产品信息清晰列出
- 无结果时礼貌引导

### 幻觉检测 (Hallucination Check)

LLM 审核回答是否基于查询结果，防止编造数据。如果检测到幻觉（score: no/half），回到 Summarize 重新生成（最多重试 3 次）。

## 预定义 Cypher 查询

**60 条**预定义查询，覆盖 11 个类别：

| 类别 | 条数 | 示例查询 |
|------|------|----------|
| 产品查询 | 10 | product_by_name, products_price_range, expensive_products |
| 订单查询 | 8 | order_by_id, recent_orders, orders_by_country |
| 客户查询 | 5 | customer_by_name, customers_by_country, all_customers |
| 员工查询 | 5 | employee_list, employee_orders, employee_subordinates |
| 评价查询 | 4 | product_reviews, low_rated_reviews, recent_reviews |
| 销售分析 | 4 | category_sales, product_sales, sales_trend |
| 供应商 | 3 | supplier_products, all_suppliers |
| 类别 | 3 | all_categories, category_products |
| 物流 | 3 | order_shipping, shipper_list |
| 消费者 | 10 | product_detail, faq_search, return_policy, warranty_policy |
| 其他 | 5 | smart_home_products, also_bought, inventory_summary |

完整列表见 `llm_backend/app/lg_agent/kg_sub_graph/agentic_rag_agents/components/predefined_cypher/cypher_dict.py`

## 查询匹配策略

查询执行采用 **关键词优先 + 向量兜底 + 动态降级** 的三层策略：

```
用户问题 → 参数提取 (订单号/金额/产品名)
         → 关键词匹配 (60 条正则规则)
            ├── 命中 → Neo4j 执行 → 返回
            └── 未命中
                → Milvus 向量检索 (bge-m3, top-5)
                   ├── 命中 → Neo4j 执行 → 返回
                   └── 未命中
                       → 有约束(数字/品类) → 降级到 LLM 动态生成 Cypher
                       → 无约束 → 兜底 smart_home_products
```

设计理念：
- **关键词主力**：准确率高，零延迟，覆盖 90% 常见问法
- **Milvus 兜底**：向量语义匹配，覆盖变体问法
- **动态降级**：复杂跨实体查询交给 LLM 现场写 Cypher

## 数据库迁移

使用 Alembic 管理 MySQL schema 版本：

```bash
cd llm_backend

# 生成新迁移 (自动检测 model 变更)
python -m alembic revision --autogenerate -m "描述"

# 升级到最新版本
python -m alembic upgrade head

# 回滚一个版本
python -m alembic downgrade -1

# 查看当前版本
python -m alembic current
```

当前迁移历史：
- `1ca69f29aad9` — initial_schema (users, conversations, messages)
- `a1304eeb2d47` — 添加 thread_id 列 + 更新 DialogueType 枚举

## 部署

```bash
# 1. 构建前端
cd frontend && npm run build && cd ..

# 2. 配置环境
cp llm_backend/.env.example llm_backend/.env
vim llm_backend/.env   # 填入 DEEPSEEK_API_KEY

# 3. 启动全部服务
docker compose up -d

# 4. 初始化数据库 (首次)
docker exec constomer-backend python -m alembic upgrade head
```

| 服务 | 容器名 | 说明 |
|------|--------|------|
| mysql | constomer-mysql | MySQL 8.0 (端口 3306) |
| ollama | constomer-ollama | Ollama + bge-m3 (端口 11434) |
| backend | constomer-backend | FastAPI (端口 8000) |


## 常见问题

### Q: 为什么回复很慢 (30-60 秒)?

每次对话调用 5-6 次 DeepSeek API（路由、守卫、规划、工具选择、汇总、幻觉检测），每次 5-15 秒。已关闭子图 Guardrails 减少一次调用。如需进一步加速，考虑换用更快的模型或关闭幻觉检测。

### Q: 为什么有时说"暂时无法回答"?

- 守卫拦截了非经营范围问题（如买衣服）
- 查询执行失败且动态 Cypher 也未成功
- LLM 返回空内容

### Q: 如何添加新的预定义查询?

1. 在 `cypher_dict.py` 添加 Cypher 语句
2. 在 `descriptions.py` 添加中文描述
3. 删除 Milvus collection 让向量重新生成
4. 如需要，在 `node.py` 的 fallback 关键词中添加匹配规则

### Q: 如何添加新产品?

运行 `data/add_more_products.py` 或直接在 Neo4j Browser 中执行 Cypher：

```cypher
CREATE (p:Product {ProductName:'新产品', UnitPrice:'999', UnitsInStock:'100', CategoryName:'智能空调', SupplierName:'小米智能家居'})
WITH p
MATCH (c:Category {CategoryName:'智能空调'}), (s:Supplier {CompanyName:'小米智能家居'})
CREATE (p)-[:BELONGS_TO]->(c), (p)-[:SUPPLIED_BY]->(s)
```

新数据即时生效，无需重启。

### Q: Ollama 启动后需要手动拉模型吗?

首次启动时需要：`ollama pull bge-m3`。Docker Compose 版本会自动拉取。

### Q: Milvus collection 什么时候需要重建?

修改了 `cypher_dict.py` 或 `descriptions.py` 后，需要删除 collection 让向量重新生成：

```python
from pymilvus import MilvusClient
MilvusClient(uri='http://localhost:19530').drop_collection('predefined_cypher_vectors')
```

下次 Agent 查询时会自动重建。

## License

MIT
