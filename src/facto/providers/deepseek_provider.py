"""DeepSeek provider - extends OpenAI provider with DeepSeek defaults."""

from typing import Optional

from .openai_provider import OpenAIProvider


class DeepSeekProvider(OpenAIProvider):
    """DeepSeek provider using OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com",
        timeout: float = 120.0,
        max_retries: int = 3,
    ):
        super().__init__(
            api_key=api_key,
            model_name=model_name,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )

    @property
    def provider_name(self) -> str:
        return "deepseek"

    @property
    def supports_tools(self) -> bool:
        # DeepSeek supports function calling
        return True
