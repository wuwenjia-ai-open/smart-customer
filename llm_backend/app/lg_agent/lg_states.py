from pydantic import BaseModel, Field
from dataclasses import dataclass, field
from typing import Annotated, Literal, TypedDict, List
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages


@dataclass(kw_only=True)
class InputState:
    """Agent 输入状态。"""
    messages: Annotated[list[AnyMessage], add_messages]


# === Multi-Agent types (added for feat/multi-agent) ===
from app.lg_agent.workers.state import WorkerState, ToolCallRecord  # noqa: F401
from app.lg_agent.supervisor.state import SupervisorState, SubTask, WorkerResult  # noqa: F401
