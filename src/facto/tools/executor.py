"""Tool executor for running tool calls."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from facto.providers.base import Message, ToolCall

from .base import ToolResult
from .registry import ToolRegistry

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Executes tool calls and manages tool conversation flow."""

    def __init__(self, registry: ToolRegistry, max_iterations: int = 5):
        self.registry = registry
        self.max_iterations = max_iterations

    async def execute_tool_call(self, tool_call: ToolCall) -> ToolResult:
        """Execute a single tool call."""
        tool = self.registry.get(tool_call.name)

        if tool is None:
            return ToolResult(
                success=False,
                result=None,
                error=f"Unknown tool: {tool_call.name}",
            )

        try:
            result = await tool.execute(**tool_call.arguments)
            logger.info(f"Tool {tool_call.name} executed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool {tool_call.name} failed: {e}")
            return ToolResult(
                success=False,
                result=None,
                error=str(e),
            )

    async def execute_all(
        self, tool_calls: list[ToolCall]
    ) -> list[tuple[ToolCall, ToolResult]]:
        """Execute multiple tool calls, potentially in parallel."""
        tasks = [self.execute_tool_call(tc) for tc in tool_calls]
        results = await asyncio.gather(*tasks)
        return list(zip(tool_calls, results))

    def create_tool_result_messages(
        self,
        tool_calls: list[ToolCall],
        results: list[ToolResult],
    ) -> list[Message]:
        """Create messages containing tool results for the conversation."""
        return [
            Message(
                role="tool",
                content=result.to_message_content(),
                tool_call_id=tool_call.id,
            )
            for tool_call, result in zip(tool_calls, results)
        ]
