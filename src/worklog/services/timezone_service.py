"""Timezone utilities for WorkLog AI."""

from datetime import datetime
from functools import lru_cache

import pytz


@lru_cache(maxsize=16)
def _get_timezone(timezone_str: str):
    """Get cached timezone object."""
    return pytz.timezone(timezone_str)


def get_current_datetime(timezone_str: str) -> datetime:
    """Get current datetime in the specified timezone.

    Args:
        timezone_str: IANA timezone string (e.g., "Asia/Singapore")

    Returns:
        Timezone-aware datetime
    """
    tz = _get_timezone(timezone_str)
    return datetime.now(tz)


def get_today_date_string(timezone_str: str) -> str:
    """Get today's date as ISO format string (YYYY-MM-DD).

    Args:
        timezone_str: IANA timezone string

    Returns:
        Date string in ISO format
    """
    return get_current_datetime(timezone_str).strftime("%Y-%m-%d")


def format_timestamp(dt: datetime, timezone_str: str) -> str:
    """Format datetime for display.

    Args:
        dt: Datetime to format (can be naive or aware)
        timezone_str: Target timezone string

    Returns:
        Formatted timestamp string (HH:MM)
    """
    tz = _get_timezone(timezone_str)
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    local_dt = dt.astimezone(tz)
    return local_dt.strftime("%H:%M")


def format_datetime_full(dt: datetime, timezone_str: str) -> str:
    """Format datetime with full date and time.

    Args:
        dt: Datetime to format
        timezone_str: Target timezone string

    Returns:
        Formatted string (YYYY-MM-DD HH:MM)
    """
    tz = _get_timezone(timezone_str)
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    local_dt = dt.astimezone(tz)
    return local_dt.strftime("%Y-%m-%d %H:%M")
