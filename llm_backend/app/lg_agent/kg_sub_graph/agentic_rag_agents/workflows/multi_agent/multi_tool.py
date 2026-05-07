"""子图构建: 5 节点 · 2 工具 · 并行 · 校验链（Guardrails 已由主图负责）"""
from typing import Dict, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_neo4j import Neo4jGraph
from langgraph.constants import END, START
from langgraph.graph.state import CompiledStateGraph, StateGraph
from pydantic import BaseModel

from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.state import (
    InputState, OutputState, OverallState,
)

from .edges import (
    map_reduce_planner_to_tool_selection,
    summarize_conditional_edge,
    hallucination_conditional_edge,
    predefined_fallback_edge,
)


def create_multi_tool_workflow(
    llm: BaseChatModel,
    graph: Neo4jGraph,
    tool_schemas: List[type[BaseModel]],
    predefined_cypher_dict: Dict[str, str],
    scope_description: Optional[str] = None,
) -> CompiledStateGraph:
    """构建子图（Guardrails 已由主图 get_additional_info 负责）"""

    # ── 节点 ──
    from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.planner import create_planner_node
    planner = create_planner_node(llm=llm)

    from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.tool_selection import create_tool_selection_node
    tool_selection = create_tool_selection_node(llm=llm, tool_schemas=tool_schemas)

    from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.predefined_cypher import create_predefined_cypher_node
    predefined = create_predefined_cypher_node(graph=graph, predefined_cypher_dict=predefined_cypher_dict)

    from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.cypher_tools import create_cypher_query_node
    cypher_query = create_cypher_query_node(llm=llm, graph=graph)

    from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.summarize import create_summarization_node
    summarize = create_summarization_node(llm=llm)

    from app.lg_agent.kg_sub_graph.agentic_rag_agents.components.check_hallucinations import create_check_hallucinations_node
    check = create_check_hallucinations_node(llm=llm, max_retries=3)

    # ── 图 ──
    builder = StateGraph(OverallState, input=InputState, output=OutputState)

    builder.add_node(planner)
    builder.add_node("tool_selection", tool_selection)
    builder.add_node("predefined_cypher", predefined)
    builder.add_node("cypher_query", cypher_query)
    builder.add_node(summarize)
    builder.add_node("check_hallucinations", check)

    builder.add_edge(START, "planner")
    builder.add_conditional_edges("planner", map_reduce_planner_to_tool_selection, ["tool_selection"])
    builder.add_conditional_edges("predefined_cypher", predefined_fallback_edge, ["summarize", "cypher_query"])
    builder.add_edge("cypher_query", "summarize")
    builder.add_conditional_edges("summarize", summarize_conditional_edge)
    builder.add_conditional_edges("check_hallucinations", hallucination_conditional_edge)

    return builder.compile()
