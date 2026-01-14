"""Configuration management for Facto."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AIProviderType(Enum):
    """Supported AI providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"


@dataclass
class ProviderConfig:
    """Configuration for a single AI provider."""
    api_key: str
    model_name: str
    base_url: Optional[str] = None
    timeout: float = 120.0
    max_retries: int = 3


@dataclass
class StreamingConfig:
    """Streaming response configuration."""
    enabled: bool = True
    update_interval_ms: int = 500  # Telegram rate limit consideration
    min_chars_per_update: int = 50  # Minimum chars before updating


@dataclass
class ToolConfig:
    """Tool calling configuration."""
    enabled: bool = True
    max_tool_iterations: int = 5  # Prevent infinite loops


@dataclass
class Config:
    """Application configuration."""
    telegram_bot_token: str
    mongodb_uri: str = ""

    # Active provider selection
    active_provider: AIProviderType = AIProviderType.DEEPSEEK

    # Provider configurations
    providers: dict[AIProviderType, ProviderConfig] = field(default_factory=dict)

    # Feature configs
    streaming: StreamingConfig = field(default_factory=StreamingConfig)
    tools: ToolConfig = field(default_factory=ToolConfig)

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        token = os.getenv("TEST_FACTO_TOKEN") or os.getenv("FACTO_TOKEN")
        if not token:
            raise ValueError("FACTO_TOKEN environment variable is required")

        # Build provider configs from environment
        providers: dict[AIProviderType, ProviderConfig] = {}

        # DeepSeek (existing, primary)
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        if deepseek_key:
            providers[AIProviderType.DEEPSEEK] = ProviderConfig(
                api_key=deepseek_key,
                base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                model_name=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            )

        # OpenAI
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            providers[AIProviderType.OPENAI] = ProviderConfig(
                api_key=openai_key,
                model_name=os.getenv("OPENAI_MODEL", "gpt-4o"),
            )

        # Anthropic
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            providers[AIProviderType.ANTHROPIC] = ProviderConfig(
                api_key=anthropic_key,
                model_name=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
            )

        # Determine active provider
        active_str = os.getenv("AI_PROVIDER", "deepseek").lower()
        try:
            active_provider = AIProviderType(active_str)
        except ValueError:
            raise ValueError(f"Unknown AI provider: {active_str}")

        if not providers:
            raise ValueError(
                "At least one AI provider must be configured. "
                "Set DEEPSEEK_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY."
            )

        if active_provider not in providers:
            # Fall back to first available provider
            active_provider = next(iter(providers.keys()))

        return cls(
            telegram_bot_token=token,
            mongodb_uri=os.getenv("MONGODB_URI", ""),
            active_provider=active_provider,
            providers=providers,
            streaming=StreamingConfig(
                enabled=os.getenv("STREAMING_ENABLED", "true").lower() == "true",
                update_interval_ms=int(os.getenv("STREAMING_INTERVAL_MS", "500")),
                min_chars_per_update=int(os.getenv("STREAMING_MIN_CHARS", "50")),
            ),
            tools=ToolConfig(
                enabled=os.getenv("TOOLS_ENABLED", "true").lower() == "true",
                max_tool_iterations=int(os.getenv("MAX_TOOL_ITERATIONS", "5")),
            ),
        )

    def get_active_provider_config(self) -> Optional[ProviderConfig]:
        """Get the configuration for the active provider."""
        return self.providers.get(self.active_provider)

    # Backward compatibility properties
    @property
    def deepseek_api_key(self) -> str:
        """Backward compatible access to DeepSeek API key."""
        config = self.providers.get(AIProviderType.DEEPSEEK)
        if config:
            return config.api_key
        # Fall back to active provider
        active_config = self.get_active_provider_config()
        return active_config.api_key if active_config else ""

    @property
    def openai_base_url(self) -> str:
        """Backward compatible access to OpenAI base URL."""
        config = self.providers.get(AIProviderType.DEEPSEEK)
        if config and config.base_url:
            return config.base_url
        return "https://api.deepseek.com"

    @property
    def model_name(self) -> str:
        """Backward compatible access to model name."""
        active_config = self.get_active_provider_config()
        return active_config.model_name if active_config else "deepseek-chat"
