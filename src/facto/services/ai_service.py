"""Unified AI service supporting multiple providers, streaming, and tools."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, AsyncIterator, Optional

from facto.config import Config
from facto.providers import (
    AIProvider,
    CompletionResponse,
    Message,
    ProviderFactory,
    StreamChunk,
    ToolCall,
)
from facto.tools import ToolExecutor, ToolRegistry

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class AIService:
    """
    Unified AI service supporting multiple providers, streaming, and tools.

    This is the main interface for AI interactions in the application.
    """

    def __init__(
        self,
        config: Config,
        tool_registry: Optional[ToolRegistry] = None,
    ):
        self.config = config
        self.provider = ProviderFactory.create(config)
        self.tool_registry = tool_registry
        self.tool_executor = (
            ToolExecutor(tool_registry, config.tools.max_tool_iterations)
            if tool_registry
            else None
        )

    def switch_provider(self, provider_name: str) -> None:
        """Switch to a different provider at runtime."""
        self.provider = ProviderFactory.create_by_name(provider_name, self.config)
        logger.info(f"Switched to provider: {provider_name}")

    @property
    def current_provider_name(self) -> str:
        """Get the name of the current provider."""
        return self.provider.provider_name

    def _convert_dict_messages(self, messages: list[dict]) -> list[Message]:
        """Convert dictionary messages to Message objects."""
        return [
            Message(role=m["role"], content=m.get("content", ""))
            for m in messages
        ]

    def _get_tools(self) -> Optional[list[dict]]:
        """Get tools in OpenAI format if available and enabled."""
        if (
            self.tool_registry
            and self.config.tools.enabled
            and self.provider.supports_tools
        ):
            return self.tool_registry.get_openai_schemas()
        return None

    async def get_response(
        self,
        messages: list[dict],
        use_tools: bool = True,
    ) -> str:
        """
        Get a complete response (non-streaming).
        Handles tool calls automatically if enabled.

        Args:
            messages: List of message dicts with 'role' and 'content'
            use_tools: Whether to enable tool calling

        Returns:
            The AI response content as a string
        """
        converted_messages = self._convert_dict_messages(messages)
        tools = self._get_tools() if use_tools else None

        response = await self.provider.complete(converted_messages, tools)

        # Handle tool calls
        if response.tool_calls and self.tool_executor:
            return await self._handle_tool_calls(converted_messages, response)

        return response.content

    async def stream_response(
        self,
        messages: list[dict],
        use_tools: bool = True,
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream a response chunk by chunk.

        Args:
            messages: List of message dicts with 'role' and 'content'
            use_tools: Whether to enable tool calling

        Yields:
            StreamChunk objects containing content deltas
        """
        converted_messages = self._convert_dict_messages(messages)
        tools = self._get_tools() if use_tools else None

        accumulated_content = ""
        tool_calls: list[ToolCall] = []

        async for chunk in self.provider.stream(converted_messages, tools):
            accumulated_content += chunk.content

            if chunk.tool_calls:
                tool_calls.extend(chunk.tool_calls)

            yield chunk

            # If stream ended with tool calls, handle them
            if chunk.is_complete and tool_calls and self.tool_executor:
                # Execute tools and continue conversation
                async for continuation_chunk in self._handle_tool_calls_streaming(
                    converted_messages,
                    accumulated_content,
                    tool_calls,
                ):
                    yield continuation_chunk

    async def _handle_tool_calls(
        self,
        messages: list[Message],
        response: CompletionResponse,
    ) -> str:
        """Handle tool calls and return final response."""
        iteration = 0
        current_messages = messages.copy()
        current_response = response
        max_iterations = self.config.tools.max_tool_iterations

        while current_response.tool_calls and iteration < max_iterations:
            iteration += 1
            tool_names = [tc.name for tc in current_response.tool_calls]
            logger.info(f"Tool iteration {iteration}: {tool_names}")

            # Add assistant message with tool calls
            current_messages.append(
                Message(
                    role="assistant",
                    content=current_response.content,
                    tool_calls=current_response.tool_calls,
                )
            )

            # Execute tools
            results = await self.tool_executor.execute_all(current_response.tool_calls)

            # Add tool result messages
            for tool_call, result in results:
                current_messages.append(
                    Message(
                        role="tool",
                        content=result.to_message_content(),
                        tool_call_id=tool_call.id,
                    )
                )

            # Get next response
            current_response = await self.provider.complete(
                current_messages,
                self.tool_registry.get_openai_schemas() if self.tool_registry else None,
            )

        return current_response.content

    async def _handle_tool_calls_streaming(
        self,
        messages: list[Message],
        assistant_content: str,
        tool_calls: list[ToolCall],
    ) -> AsyncIterator[StreamChunk]:
        """Handle tool calls during streaming."""
        current_messages = messages.copy()

        # Add assistant message with tool calls
        current_messages.append(
            Message(
                role="assistant",
                content=assistant_content,
                tool_calls=tool_calls,
            )
        )

        # Execute tools
        results = await self.tool_executor.execute_all(tool_calls)

        # Yield tool execution info
        for tool_call, result in results:
            status = "completed" if result.success else "failed"
            yield StreamChunk(
                content=f"\n[Tool: {tool_call.name} - {status}]\n",
            )
            current_messages.append(
                Message(
                    role="tool",
                    content=result.to_message_content(),
                    tool_call_id=tool_call.id,
                )
            )

        # Continue with streaming response
        tools = self.tool_registry.get_openai_schemas() if self.tool_registry else None
        async for chunk in self.provider.stream(current_messages, tools):
            yield chunk


# Backward compatibility: synchronous wrapper
def get_response_sync(service: AIService, messages: list[dict]) -> str:
    """
    Backward-compatible synchronous wrapper.
    Note: This blocks and should be avoided in async contexts.
    """
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None:
        # We're in an async context, create a new thread
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run, service.get_response(messages)
            )
            return future.result()
    else:
        return asyncio.run(service.get_response(messages))
