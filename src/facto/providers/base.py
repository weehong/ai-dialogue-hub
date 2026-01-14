"""Base classes for AI providers."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional


@dataclass
class ToolCall:
    """Represents a tool call from the AI."""
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class Message:
    """Represents a message in the conversation."""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: Optional[str] = None  # For tool result messages

    def to_openai_format(self) -> dict:
        """Convert to OpenAI API message format."""
        msg: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments),
                    },
                }
                for tc in self.tool_calls
            ]
        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id
        return msg

    def to_anthropic_format(self) -> dict:
        """Convert to Anthropic API message format."""
        if self.role == "tool":
            return {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": self.tool_call_id,
                        "content": self.content,
                    }
                ],
            }
        return {"role": self.role, "content": self.content}


@dataclass
class StreamChunk:
    """Represents a chunk of streamed response."""
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: Optional[str] = None
    is_complete: bool = False


@dataclass
class CompletionResponse:
    """Represents a complete AI response."""
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: Optional[dict] = None


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(
        self,
        api_key: str,
        model_name: str,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
        max_retries: int = 3,
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        tools: Optional[list[dict]] = None,
    ) -> CompletionResponse:
        """Generate a complete response (non-streaming)."""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        tools: Optional[list[dict]] = None,
    ) -> AsyncIterator[StreamChunk]:
        """Generate a streaming response yielding chunks."""
        pass

    @property
    @abstractmethod
    def supports_tools(self) -> bool:
        """Whether this provider supports tool calling."""
        pass

    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Whether this provider supports streaming."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier for this provider."""
        pass
