"""Tool registry for managing available tools."""

from __future__ import annotations

from typing import Optional

from .base import Tool


class ToolRegistry:
    """Registry for managing available tools."""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """Unregister a tool."""
        self._tools.pop(name, None)

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        """Get all registered tools."""
        return list(self._tools.values())

    def get_openai_schemas(self) -> list[dict]:
        """Get all tools in OpenAI format."""
        return [tool.to_openai_schema() for tool in self._tools.values()]

    def get_anthropic_schemas(self) -> list[dict]:
        """Get all tools in Anthropic format."""
        return [tool.to_anthropic_schema() for tool in self._tools.values()]

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)
