"""Tool Registry — 动态工具注册/查找/调用系统"""

import logging
from typing import Callable, Any

from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)


class ToolMeta:
    """工具元数据"""
    def __init__(self, name: str, description: str, tool: BaseTool, parameters_schema: dict | None = None):
        self.name = name
        self.description = description
        self.tool = tool
        self.parameters_schema = parameters_schema or {}


class ToolRegistry:
    """动态工具注册表（全局单例）

    用法:
        registry = get_tool_registry()
        registry.register(my_tool)
        tool = registry.get("search_knowledge_base")
        all_tools = registry.list_active()
    """

    def __init__(self):
        self._tools: dict[str, ToolMeta] = {}

    def register(self, tool: BaseTool, description: str | None = None):
        """注册一个 LangChain Tool"""
        name = tool.name
        desc = description or tool.description or ""
        meta = ToolMeta(
            name=name,
            description=desc,
            tool=tool,
            parameters_schema=tool.args_schema.schema() if hasattr(tool, 'args_schema') and tool.args_schema else {},
        )
        self._tools[name] = meta
        logger.info(f"Tool registered: {name}")

    def get(self, name: str) -> BaseTool | None:
        """按名称获取工具"""
        meta = self._tools.get(name)
        return meta.tool if meta else None

    def list_all(self) -> list[ToolMeta]:
        """列出所有已注册工具"""
        return list(self._tools.values())

    def list_active(self) -> list[BaseTool]:
        """获取所有活跃工具的 LangChain Tool 列表（供 Agent 使用）"""
        return [m.tool for m in self._tools.values() if m.tool]

    def get_tools_by_names(self, names: list[str]) -> list[BaseTool]:
        """按名称列表获取工具"""
        tools = []
        for name in names:
            t = self.get(name)
            if t:
                tools.append(t)
        return tools

    def count(self) -> int:
        return len(self._tools)


# 全局单例
_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def reset_tool_registry():
    """测试用：重置注册表"""
    global _registry
    _registry = ToolRegistry()
