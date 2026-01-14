"""OpenAI and OpenAI-compatible API provider."""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Optional

import httpx
from openai import AsyncOpenAI

from .base import AIProvider, CompletionResponse, Message, StreamChunk, ToolCall

logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    """OpenAI and OpenAI-compatible API provider."""

    def __init__(
        self,
        api_key: str,
        model_name: str,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
        max_retries: int = 3,
    ):
        super().__init__(api_key, model_name, base_url, timeout, max_retries)
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=httpx.Timeout(timeout, connect=30.0),
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
        return "openai"

    def _convert_messages(self, messages: list[Message]) -> list[dict]:
        """Convert Message objects to OpenAI format."""
        return [msg.to_openai_format() for msg in messages]

    def _parse_tool_calls(self, tool_calls) -> list[ToolCall]:
        """Parse tool calls from OpenAI response."""
        if not tool_calls:
            return []
        result = []
        for tc in tool_calls:
            try:
                arguments = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                arguments = {}
            result.append(
                ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=arguments,
                )
            )
        return result

    async def complete(
        self,
        messages: list[Message],
        tools: Optional[list[dict]] = None,
    ) -> CompletionResponse:
        """Generate a complete response."""
        kwargs: dict = {
            "model": self.model_name,
            "messages": self._convert_messages(messages),
        }
        if tools:
            kwargs["tools"] = tools

        try:
            response = await self.client.chat.completions.create(**kwargs)
            choice = response.choices[0]

            return CompletionResponse(
                content=choice.message.content or "",
                tool_calls=self._parse_tool_calls(choice.message.tool_calls),
                finish_reason=choice.finish_reason or "stop",
                usage=dict(response.usage) if response.usage else None,
            )
        except httpx.TimeoutException as e:
            raise RuntimeError("AI request timed out. Please try again.") from e
        except httpx.ConnectError as e:
            raise RuntimeError("Could not connect to AI service.") from e
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise RuntimeError(f"AI service error: {e}") from e

    async def stream(
        self,
        messages: list[Message],
        tools: Optional[list[dict]] = None,
    ) -> AsyncIterator[StreamChunk]:
        """Generate a streaming response."""
        kwargs: dict = {
            "model": self.model_name,
            "messages": self._convert_messages(messages),
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools

        accumulated_tool_calls: dict[int, dict] = {}

        try:
            stream = await self.client.chat.completions.create(**kwargs)
            async for chunk in stream:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                finish_reason = chunk.choices[0].finish_reason

                content = delta.content or "" if delta else ""
                tool_calls: list[ToolCall] = []

                # Handle streaming tool calls
                if delta and delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in accumulated_tool_calls:
                            accumulated_tool_calls[idx] = {
                                "id": tc.id or "",
                                "name": tc.function.name if tc.function else "",
                                "arguments": "",
                            }
                        if tc.function and tc.function.arguments:
                            accumulated_tool_calls[idx]["arguments"] += tc.function.arguments

                # If finished with tool calls, parse them
                if finish_reason == "tool_calls":
                    for tc_data in accumulated_tool_calls.values():
                        try:
                            arguments = json.loads(tc_data["arguments"])
                        except json.JSONDecodeError:
                            arguments = {}
                        tool_calls.append(
                            ToolCall(
                                id=tc_data["id"],
                                name=tc_data["name"],
                                arguments=arguments,
                            )
                        )

                yield StreamChunk(
                    content=content,
                    tool_calls=tool_calls,
                    finish_reason=finish_reason,
                    is_complete=finish_reason is not None,
                )

        except httpx.TimeoutException as e:
            raise RuntimeError("AI request timed out. Please try again.") from e
        except httpx.ConnectError as e:
            raise RuntimeError("Could not connect to AI service.") from e
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise RuntimeError(f"AI service error: {e}") from e
