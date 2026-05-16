"""工具注册表 — 工具名到执行器的映射"""
import json
from typing import Any, Dict, Protocol, runtime_checkable


class ToolResult:
    """工具执行结果"""
    def __init__(self, records: list = None, summary: str = "", error: str = "",
                 success: bool = True, control: dict = None):
        self.records = records or []
        self.summary = summary
        self.error = error
        self.success = success
        self.control = control  # {"action": "clarify"|"escalate"|"reroute", ...}

    def to_dict(self) -> dict:
        d = {"records": self.records, "summary": self.summary, "success": self.success}
        if self.error:
            d["error"] = self.error
        if self.control:
            d["control"] = self.control
        return d


@runtime_checkable
class ToolExecutor(Protocol):
    """工具执行器协议 — 所有执行器必须实现 invoke 方法"""
    def invoke(self, args: Dict[str, Any]) -> ToolResult:
        ...


# 全局注册表，按 Worker 拥有不同工具集
TOOL_REGISTRY: Dict[str, ToolExecutor] = {}


def register_tool(name: str, executor: ToolExecutor) -> None:
    TOOL_REGISTRY[name] = executor


def get_tool_executor(name: str) -> ToolExecutor:
    if name not in TOOL_REGISTRY:
        raise KeyError(f"Tool '{name}' not registered. Available: {list(TOOL_REGISTRY.keys())}")
    return TOOL_REGISTRY[name]


def create_tool(schema_cls):
    """从 Pydantic schema 创建 LangChain 可执行工具 — 自动绑定 TOOL_REGISTRY 中的执行器"""
    from langchain_core.tools import StructuredTool

    name = schema_cls.__name__
    executor = get_tool_executor(name)

    def _run(**kwargs):
        result = executor.invoke(kwargs)
        return json.dumps(result.to_dict(), ensure_ascii=False)

    async def _arun(**kwargs):
        return _run(**kwargs)

    return StructuredTool.from_function(
        func=_run,
        coroutine=_arun,
        name=name,
        description=schema_cls.__doc__ or "",
        args_schema=schema_cls,
    )
