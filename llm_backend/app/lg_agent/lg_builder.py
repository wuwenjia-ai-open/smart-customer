"""Multi-Agent Supervisor Graph — 替代原单 Agent Pipeline"""
import asyncio
import logging

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.core.config import settings
from app.services.llm_factory import LLMFactory
from app.lg_agent.supervisor.state import SupervisorState
from app.lg_agent.supervisor.nodes import (
    make_classify_node,
    make_decompose_node,
    make_merge_node,
    make_respond_node,
)
from app.lg_agent.workers import product_qa, order_qa, after_sales, general_chat
from app.lg_agent.workers.tools.registry import register_tool

_log = logging.getLogger(__name__)


def _create_embedding_model():
    """创建 Ollama embedding 封装，暴露 embed_query(text) -> list[float]"""
    import requests

    class OllamaEmbedding:
        def __init__(self, base_url: str, model: str):
            self._url = f"{base_url.rstrip('/')}/api/embed"
            self._model = model

        def embed_query(self, text: str) -> list:
            r = requests.post(self._url, json={"model": self._model, "input": [text]})
            r.raise_for_status()
            return r.json()["embeddings"][0]

    return OllamaEmbedding(settings.OLLAMA_BASE_URL, settings.OLLAMA_EMBEDDING_MODEL)


def _init_tool_registry():
    """初始化工具注册表 — 创建 DataService 并注册执行器"""
    from pymilvus import MilvusClient
    from app.lg_agent.data.neo4j_conn import get_neo4j_graph
    from app.lg_agent.data.data_service import ProductService, OrderService, PolicyService
    from app.lg_agent.workers.tools.executors import (
        SemanticSearchExecutor, CompareProductsExecutor, RecommendExecutor,
        TrackShipmentExecutor, CreateTicketExecutor, SearchFAQExecutor,
        AskClarificationExecutor, EscalateToHumanExecutor,
    )

    neo4j = get_neo4j_graph()

    # ── Milvus + embedding — 可用则注册语义搜索/推荐，不可用则降级 ──
    milvus = None
    embed = None
    try:
        milvus = MilvusClient(uri=f"http://{settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
        # 确保 product_descriptions collection 已加载
        if milvus.has_collection("product_descriptions"):
            milvus.load_collection("product_descriptions")
        embed = _create_embedding_model()
        # smoke test
        embed.embed_query("test")
    except Exception as e:
        _log.warning(f"Milvus/embedding not available — semantic_search and recommend disabled: {e}")
        milvus = None
        embed = None

    # ── DataService ──
    order_svc = OrderService(neo4j)

    # Neo4j-only tools — 不依赖 Milvus
    compare_svc = ProductService(neo4j, None, None)  # compare 只用 Neo4j
    register_tool("compare_products", CompareProductsExecutor(compare_svc))
    register_tool("track_shipment", TrackShipmentExecutor(order_svc))
    register_tool("create_ticket", CreateTicketExecutor(None))
    register_tool("search_faq", SearchFAQExecutor(PolicyService(neo4j)))

    if milvus and embed:
        product_svc = ProductService(neo4j, milvus, embed)
        register_tool("semantic_search", SemanticSearchExecutor(product_svc))
        register_tool("recommend", RecommendExecutor(product_svc))

    # 不依赖外部服务的工具
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
    builder.add_node("merge_results", make_merge_node(llm))
    builder.add_node("respond", make_respond_node())

    # ── Worker sub-graphs ──
    for worker in [product_qa, order_qa, after_sales, general_chat]:
        worker_graph = worker.build(llm)
        worker_type = worker.__name__.split(".")[-1]
        builder.add_node(worker_type, worker_graph)

    # ── Edges ──
    builder.add_edge(START, "classify_intent")
    # 所有 Worker 完成后汇集到 merge_results
    for worker in [product_qa, order_qa, after_sales, general_chat]:
        worker_type = worker.__name__.split(".")[-1]
        builder.add_edge(worker_type, "merge_results")

    def _build_sends(state: SupervisorState) -> list:
        """构建 Send 列表 — 用于 conditional edge 的 dispatch"""
        sub_tasks = state.get("sub_tasks", [])
        msgs = state.get("messages", [])
        sends = []
        for task in sub_tasks:
            sends.append(Send(task["worker_type"], {
                "messages": list(msgs),
                "worker_type": task["worker_type"],
                "task": task["description"],
                "context": task.get("context", {}),
                "iteration_count": 0,
                "next_action": "think",
                "tool_to_execute": "",
                "tool_call_history": [],
                "final_answer": "",
                "status": "",
                "clarification_question": "",
            }))
        return sends

    def route_after_classify(state: SupervisorState):
        action = state.get("next_action", "respond")
        if action == "decompose":
            return "decompose_tasks"
        elif action == "dispatch":
            return _build_sends(state)
        else:
            return "respond"

    builder.add_conditional_edges("classify_intent", route_after_classify, {
        "decompose_tasks": "decompose_tasks",
        "respond": "respond",
    })

    def route_after_decompose(state: SupervisorState):
        return _build_sends(state)

    builder.add_conditional_edges("decompose_tasks", route_after_decompose, {})

    def route_after_merge(state: SupervisorState):
        action = state.get("next_action", "respond")
        reroute_count = state.get("reroute_count", 0)

        if action == "dispatch" and reroute_count > 0:
            return _build_sends(state)

        if state.get("needs_clarification"):
            return "clarify"
        return "respond"

    builder.add_conditional_edges("merge_results", route_after_merge, {
        "clarify": "respond",
        "respond": "respond",
    })
    builder.add_edge("respond", END)

    # ── Checkpointer (SQLite 持久化) ──
    async def _create_checkpointer():
        import aiosqlite
        conn = await aiosqlite.connect(settings.CHECKPOINT_DB_PATH)
        return AsyncSqliteSaver(conn)

    return builder, _create_checkpointer


# ── Lazy graph instance ──
_graph_instance = None


async def get_graph():
    global _graph_instance
    if _graph_instance is None:
        builder, checkpointer_factory = build_supervisor_graph()
        checkpointer = await checkpointer_factory()
        _graph_instance = builder.compile(checkpointer=checkpointer)
        _log.info("Supervisor graph compiled successfully")
    return _graph_instance
