from pydantic import BaseModel, Field
from dataclasses import dataclass, field
from typing import Annotated, Literal, TypedDict, List
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages


class Router(TypedDict):
    """对用户查询进行分类。"""
    logic: str
    type: Literal["general-query", "additional-query", "graphrag-query", "image-query"]


class GradeHallucinations(BaseModel):
    """对生成答案中是否存在幻觉进行二元评分。"""

    binary_score: str = Field(
        description="答案是否有事实依据，'1' 表示有依据，'0' 表示没有依据"
    )


# @dataclass(kw_only=True)：强制要求数据类中的所有字段必须以关键字参数的形式提供，不能以位置参数的方式传递。
@dataclass(kw_only=True)
class InputState:
    """表示 Agent 的输入状态。

    该类定义了输入状态的结构，包含用户与 Agent 之间交换的消息。
    """

    messages: Annotated[list[AnyMessage], add_messages]

    """messages 追踪 Agent 的主要执行状态。

    通常按照 人类/AI/人类/AI 的模式累积消息；
    如果将此模板与工具调用的 ReAct Agent 模式结合，消息序列可能如下：

    1. HumanMessage  - 用户输入
    2. AIMessage（含 .tool_calls）- Agent 选择要使用的工具来收集信息
    3. ToolMessage   - 工具执行后的响应（或错误信息）

        （根据需要重复步骤 2 和 3）

    4. AIMessage（不含 .tool_calls）- Agent 以非结构化格式回复用户

    5. HumanMessage  - 用户进行下一轮对话

        （根据需要重复步骤 2-5）


    合并两个消息列表，通过 ID 更新已有消息。

    默认情况下，这确保状态是"只追加"的，
    除非新消息与已有消息的 ID 相同（相同 ID 的消息会被替换）。

    返回：
        一个新的消息列表，将 right 中的消息合并到 left 中。
        如果 right 中的某条消息与 left 中的消息 ID 相同，
        则 right 中的消息会替换 left 中对应的消息。
    """


# @dataclass(kw_only=True)：强制要求数据类中的所有字段必须以关键字参数的形式提供，不能以位置参数的方式传递。
@dataclass(kw_only=True)
class AgentState(InputState):
    """检索图 / Agent 的完整状态。"""

    router: Router = field(default_factory=lambda: Router(type="general-query", logic=""))
    """路由器对用户查询的分类结果。"""

    steps: list[str] = field(default_factory=list)
    """由检索器填充，是 Agent 可以参考的文档列表（研究步骤）。"""

    question: str = field(default_factory=str)
    """当前用户问题。"""

    answer: str = field(default_factory=str)
    """最终生成的答案。"""

    hallucination: GradeHallucinations = field(default_factory=lambda: GradeHallucinations(binary_score="0"))
    """幻觉检测结果，binary_score='1' 表示答案有依据，'0' 表示存在幻觉。"""


# === Multi-Agent types (added for feat/multi-agent) ===
from app.lg_agent.workers.state import WorkerState, ToolCallRecord  # noqa: F401
from app.lg_agent.supervisor.state import SupervisorState, SubTask, WorkerResult  # noqa: F401
