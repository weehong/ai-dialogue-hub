"""Enumerations for Facto."""

from enum import Enum


class ChatMode(Enum):
    """Available chat modes."""
    JOURNAL = "journal"
    ASSISTANT = "assistant"  # General purpose assistant
    CODE = "code"  # Code-focused mode
    RESEARCH = "research"  # Research/web search mode


class ToolCallStatus(Enum):
    """Status of a tool call."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
