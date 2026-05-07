"""Tool Selection 节点 — LLM 为每个子任务选择最合适的工具"""
from typing import Any, Callable, Dict, List

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import PydanticToolsParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.types import Command, Send
from pydantic import BaseModel

from ..state import ToolSelectionInputState

TOOL_SELECT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是电商查询工具选择专家。为每个子任务选择最合适的查询工具：

- predefined_cypher【首选，快】：适合明确的产品/订单/物流评价查询。包含 52 条预定义查询。
- cypher_query【备选，准】：适合复杂/跨多跳的自定义查询，LLM 动态生成 Cypher。

选择原则：能走预定义就走预定义，不能才走动态生成。"""),
    ("human", "子任务：{question}\n请选择工具："),
])


def create_tool_selection_node(
    llm: BaseChatModel,
    tool_schemas: List[type[BaseModel]],
) -> Callable:
    """创建 Tool Selection 节点"""
    chain = TOOL_SELECT_PROMPT | llm.bind_tools(tools=tool_schemas) | PydanticToolsParser(tools=tool_schemas, first_tool_only=True)

    async def tool_selection(state: ToolSelectionInputState) -> Command:
        question = state.get("question", "")
        result = await chain.ainvoke({"question": question})

        if result is not None:
            tool_name = result.__class__.__name__
            if tool_name == "predefined_cypher":
                return Command(goto=Send("predefined_cypher", {
                    "task": question, "query_parameters": result.model_dump(), "steps": ["tool_selection"]
                }))
            elif tool_name == "cypher_query":
                return Command(goto=Send("cypher_query", {
                    "task": question, "steps": ["tool_selection"]
                }))

        # 默认走 predefined_cypher（无结果会降级到 cypher_query）
        return Command(goto=Send("predefined_cypher", {
            "task": question, "query_parameters": {}, "steps": ["tool_selection"]
        }))

    return tool_selection
