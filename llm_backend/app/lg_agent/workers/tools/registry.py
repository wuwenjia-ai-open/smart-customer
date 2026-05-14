"""工具注册表 — 工具名到执行器的映射"""
from typing import Any, Dict, Protocol, runtime_checkable


class ToolResult:
    """工具执行结果"""
    def __init__(self, records: list = None, summary: str = "", error: str = "", success: bool = True):
        self.records = records or []
        self.summary = summary
        self.error = error
        self.success = success


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
