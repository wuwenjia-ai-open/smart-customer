"""Planner 节点 — LLM 将问题拆解为并行子任务"""
from typing import Any, Callable, Dict, List

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import PydanticToolsParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from ..models import Task
from ..state import OverallState


class SubTask(BaseModel):
    """LLM 拆解出的单个子任务"""
    question: str = Field(description="子任务的具体问题，可直接用于工具查询")
    parent_task: str = Field(description="原始用户问题")


PLANNER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是电商查询规划专家。将用户的复杂问题拆解为 1-3 个独立的子任务，每个子任务可以独立执行 Neo4j 图数据库查询。

拆解规则：
- 简单问题 → 1 个子任务（直接复用原问题）
- 中等复杂 → 2 个子任务（如"查产品 + 看评价"）
- 复杂对比/跨类 → 最多 3 个子任务
- 每个子任务必须是独立的、可执行的查询
- 保留原问题的关键约束（价格、类别、数量等）

数据库包含：Product, Category, Supplier, Order, Customer, Review, Employee, Shipper 及其关系。
"""),
    ("human", "用户问题：{question}\n\n请拆解为子任务："),
])


def create_planner_node(llm: BaseChatModel) -> Callable:
    """创建 Planner 节点"""
    chain = PLANNER_PROMPT | llm.bind_tools([SubTask]) | PydanticToolsParser(tools=[SubTask])

    async def planner(state: OverallState) -> Dict[str, Any]:
        question = state.get("question", "")
        raw = await chain.ainvoke({"question": question})

        tasks = []
        if raw:
            tasks = [Task(question=t.question, parent_task=t.parent_task) for t in raw if isinstance(t, SubTask)]
        if not tasks:
            tasks = [Task(question=question, parent_task=question)]

        print(f"  Planner: {len(tasks)} sub-tasks")
        return {"tasks": tasks, "steps": ["planner"]}

    return planner
