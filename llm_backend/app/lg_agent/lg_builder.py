"""Multi-Agent Supervisor Graph — 替代原单 Agent Pipeline"""
import logging

from langgraph.checkpoint.memory import MemorySaver
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
from app.lg_agent.workers import product_qa, order_qa, after_sales, general_chat
from app.lg_agent.workers.tools.registry import register_tool
from app.lg_agent.workers.tools.executors import (
    AskClarificationExecutor, EscalateToHumanExecutor,
)

_log = logging.getLogger(__name__)


# ── Lazy tool registry initialization ──
def _init_tool_registry():
    """延迟初始化工具注册表（需要 Neo4j/Milvus 连接）"""
    try:
        from app.lg_agent.data.neo4j_conn import get_neo4j_graph
        from app.lg_agent.data.cypher_dict import predefined_cypher_dict
        from app.lg_agent.workers.tools.executors import (
            SemanticSearchExecutor, CompareProductsExecutor, RecommendExecutor,
            TrackShipmentExecutor, CreateTicketExecutor,
        )

        neo4j = get_neo4j_graph()

        # These require Milvus + embedding — create if available
        milvus = None
        embed = None
        try:
            from app.lg_agent.data.vector_matcher import create_vector_query_matcher
            from app.lg_agent.data.descriptions import QUERY_DESCRIPTIONS
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
        register_tool("create_ticket", CreateTicketExecutor(None))

    except Exception as e:
        _log.warning(f"Tool registry partial init: {e}")

    # These don't need external services
    register_tool("ask_clarification", AskClarificationExecutor())
    register_tool("escalate_to_human", EscalateToHumanExecutor())

    # Register existing tools as pass-through (they're handled by the old sub-graph internally)
    # The predefined_cypher and cypher_query tools are registered when the old sub-graph initializes


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
    for worker in [product_qa, order_qa, after_sales, general_chat]:
        worker_graph = worker.build(llm)
        # extract worker_type from module name: "product_qa" etc.
        worker_type = worker.__name__.split(".")[-1]
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
    checkpointer = MemorySaver()

    return builder.compile(checkpointer=checkpointer)


# ── Module-level graph instance (replaces old `graph`) ──
try:
    supervisor_graph = build_supervisor_graph()
    _log.info("Supervisor graph compiled successfully")
except Exception as e:
    _log.error(f"Failed to build supervisor graph: {e}")
    supervisor_graph = None
