"""Configuration management for WorkLog AI."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import pytz
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Application configuration for WorkLog AI."""

    telegram_bot_token: str
    allowed_user_id: int
    user_timezone: str
    mongodb_uri: str
    mongodb_database: str = "worklog_db"

    # DeepSeek for AI summarization
    deepseek_api_key: Optional[str] = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # OpenAI for voice transcription
    openai_api_key: Optional[str] = None

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        token = os.getenv("WORKLOG_TOKEN")
        if not token:
            raise ValueError("WORKLOG_TOKEN environment variable is required")

        allowed_user_id = os.getenv("ALLOWED_USER_ID")
        if not allowed_user_id:
            raise ValueError("ALLOWED_USER_ID environment variable is required")

        user_timezone = os.getenv("USER_TIMEZONE")
        if not user_timezone:
            raise ValueError("USER_TIMEZONE environment variable is required")

        # Validate timezone
        try:
            pytz.timezone(user_timezone)
        except pytz.UnknownTimeZoneError:
            raise ValueError(f"Invalid timezone: {user_timezone}")

        mongodb_uri = os.getenv("MONGODB_URI")
        if not mongodb_uri:
            raise ValueError("MONGODB_URI environment variable is required")

        return cls(
            telegram_bot_token=token,
            allowed_user_id=int(allowed_user_id),
            user_timezone=user_timezone,
            mongodb_uri=mongodb_uri,
            mongodb_database=os.getenv("WORKLOG_DATABASE", "worklog_db"),
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
            deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )

    @property
    def pytz_timezone(self):
        """Get the pytz timezone object."""
        return pytz.timezone(self.user_timezone)
