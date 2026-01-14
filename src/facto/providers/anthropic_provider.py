"""Anthropic Claude API provider."""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Optional

from anthropic import AsyncAnthropic

from .base import AIProvider, CompletionResponse, Message, StreamChunk, ToolCall

logger = logging.getLogger(__name__)


class AnthropicProvider(AIProvider):
    """Anthropic Claude API provider."""

    def __init__(
        self,
        api_key: str,
        model_name: str,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
        max_retries: int = 3,
    ):
        super().__init__(api_key, model_name, base_url, timeout, max_retries)
        self.client = AsyncAnthropic(
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )

    @property
    def supports_tools(self) -> bool:
        return True

    @property
    def supports_streaming(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def _extract_system_message(
        self, messages: list[Message]
    ) -> tuple[Optional[str], list[Message]]:
        """Anthropic requires system message as separate parameter."""
        system = None
        filtered = []
        for msg in messages:
            if msg.role == "system":
                system = msg.content
            else:
                filtered.append(msg)
        return system, filtered

    def _convert_messages(self, messages: list[Message]) -> list[dict]:
        """Convert Message objects to Anthropic format."""
        return [msg.to_anthropic_format() for msg in messages]

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
        """Convert OpenAI tool format to Anthropic format."""
        return [
            {
                "name": t["function"]["name"],
                "description": t["function"]["description"],
                "input_schema": t["function"]["parameters"],
            }
            for t in tools
        ]

    async def complete(
        self,
        messages: list[Message],
        tools: Optional[list[dict]] = None,
    ) -> CompletionResponse:
        """Generate a complete response."""
        system, filtered_messages = self._extract_system_message(messages)

        kwargs: dict = {
            "model": self.model_name,
            "messages": self._convert_messages(filtered_messages),
            "max_tokens": 4096,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        try:
            response = await self.client.messages.create(**kwargs)

            content = ""
            tool_calls: list[ToolCall] = []

            for block in response.content:
                if block.type == "text":
                    content += block.text
                elif block.type == "tool_use":
                    tool_calls.append(
                        ToolCall(
                            id=block.id,
                            name=block.name,
                            arguments=block.input if isinstance(block.input, dict) else {},
                        )
                    )

            return CompletionResponse(
                content=content,
                tool_calls=tool_calls,
                finish_reason=response.stop_reason or "end_turn",
                usage={
                    "input": response.usage.input_tokens,
                    "output": response.usage.output_tokens,
                },
            )
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise RuntimeError(f"AI service error: {e}") from e

    async def stream(
        self,
        messages: list[Message],
        tools: Optional[list[dict]] = None,
    ) -> AsyncIterator[StreamChunk]:
        """Generate a streaming response."""
        system, filtered_messages = self._extract_system_message(messages)

        kwargs: dict = {
            "model": self.model_name,
            "messages": self._convert_messages(filtered_messages),
            "max_tokens": 4096,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = self._convert_tools(tools)

        current_tool_call: Optional[dict] = None

        try:
            async with self.client.messages.stream(**kwargs) as stream:
                async for event in stream:
                    if event.type == "content_block_start":
                        block = event.content_block
                        if hasattr(block, "type") and block.type == "tool_use":
                            current_tool_call = {
                                "id": block.id,
                                "name": block.name,
                                "arguments": "",
                            }

                    elif event.type == "content_block_delta":
                        delta = event.delta
                        if hasattr(delta, "text"):
                            yield StreamChunk(content=delta.text)
                        elif hasattr(delta, "partial_json"):
                            if current_tool_call:
                                current_tool_call["arguments"] += delta.partial_json

                    elif event.type == "content_block_stop":
                        if current_tool_call:
                            try:
                                arguments = json.loads(current_tool_call["arguments"])
                            except json.JSONDecodeError:
                                arguments = {}
                            yield StreamChunk(
                                tool_calls=[
                                    ToolCall(
                                        id=current_tool_call["id"],
                                        name=current_tool_call["name"],
                                        arguments=arguments,
                                    )
                                ]
                            )
                            current_tool_call = None

                    elif event.type == "message_stop":
                        yield StreamChunk(
                            is_complete=True,
                            finish_reason="end_turn",
                        )

        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")
            raise RuntimeError(f"AI service error: {e}") from e
