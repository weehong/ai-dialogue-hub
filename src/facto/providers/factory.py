"""Factory for creating AI providers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .anthropic_provider import AnthropicProvider
from .base import AIProvider
from .deepseek_provider import DeepSeekProvider
from .openai_provider import OpenAIProvider

if TYPE_CHECKING:
    from facto.config import AIProviderType, Config


class ProviderFactory:
    """Factory for creating AI providers based on configuration."""

    @classmethod
    def create(cls, config: "Config") -> AIProvider:
        """Create a provider instance from config using the active provider."""
        from facto.config import AIProviderType

        provider_config = config.get_active_provider_config()
        if provider_config is None:
            raise ValueError(f"Active provider {config.active_provider} not configured")

        return cls._create_provider(
            config.active_provider,
            provider_config.api_key,
            provider_config.model_name,
            provider_config.base_url,
            provider_config.timeout,
            provider_config.max_retries,
        )

    @classmethod
    def create_by_name(cls, name: str, config: "Config") -> AIProvider:
        """Create a specific provider by name."""
        from facto.config import AIProviderType

        try:
            provider_type = AIProviderType(name.lower())
        except ValueError:
            raise ValueError(f"Unknown provider: {name}")

        if provider_type not in config.providers:
            raise ValueError(f"Provider {name} not configured")

        provider_config = config.providers[provider_type]
        return cls._create_provider(
            provider_type,
            provider_config.api_key,
            provider_config.model_name,
            provider_config.base_url,
            provider_config.timeout,
            provider_config.max_retries,
        )

    @classmethod
    def _create_provider(
        cls,
        provider_type: "AIProviderType",
        api_key: str,
        model_name: str,
        base_url: str | None,
        timeout: float,
        max_retries: int,
    ) -> AIProvider:
        """Create a provider instance."""
        from facto.config import AIProviderType

        if provider_type == AIProviderType.OPENAI:
            return OpenAIProvider(
                api_key=api_key,
                model_name=model_name,
                base_url=base_url,
                timeout=timeout,
                max_retries=max_retries,
            )
        elif provider_type == AIProviderType.ANTHROPIC:
            return AnthropicProvider(
                api_key=api_key,
                model_name=model_name,
                base_url=base_url,
                timeout=timeout,
                max_retries=max_retries,
            )
        elif provider_type == AIProviderType.DEEPSEEK:
            return DeepSeekProvider(
                api_key=api_key,
                model_name=model_name,
                base_url=base_url or "https://api.deepseek.com",
                timeout=timeout,
                max_retries=max_retries,
            )
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
