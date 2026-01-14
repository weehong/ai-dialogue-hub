"""Configuration for the Message Logger Bot."""

from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class LoggerConfig:
    """Configuration for the message logger bot."""

    telegram_token: str
    mongodb_uri: str
    owner_id: int
    database_name: str = "telegram_logs"
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    model_name: str = "gpt-4o-mini"

    @classmethod
    def from_env(cls) -> "LoggerConfig":
        """Create configuration from environment variables."""
        telegram_token = os.getenv("LOGTA_TOKEN")
        if not telegram_token:
            raise ValueError("LOGTA_TOKEN environment variable is required")

        mongodb_uri = os.getenv("MONGODB_URI")
        if not mongodb_uri:
            raise ValueError("MONGODB_URI environment variable is required")

        owner_id = os.getenv("OWNER_ID")
        if not owner_id:
            raise ValueError("OWNER_ID environment variable is required")

        return cls(
            telegram_token=telegram_token,
            mongodb_uri=mongodb_uri,
            owner_id=int(owner_id),
            database_name=os.getenv("MONGODB_DATABASE", "telegram_logs"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model_name=os.getenv("LOGTA_MODEL_NAME", "gpt-4o-mini"),
        )
