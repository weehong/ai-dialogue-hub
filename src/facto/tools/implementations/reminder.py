"""Reminder tool implementation."""

from __future__ import annotations

from datetime import datetime

from facto.tools.base import Tool, ToolResult


class SetReminderTool(Tool):
    """Set a reminder for the user."""

    @property
    def name(self) -> str:
        return "set_reminder"

    @property
    def description(self) -> str:
        return (
            "Set a reminder for a specific time. "
            "Use this when the user asks to be reminded about something."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The reminder message",
                },
                "datetime_str": {
                    "type": "string",
                    "description": "When to remind, in ISO format (e.g., '2024-01-15T14:30:00')",
                },
            },
            "required": ["message", "datetime_str"],
        }

    async def execute(self, message: str, datetime_str: str) -> ToolResult:
        """Set a reminder."""
        try:
            reminder_time = datetime.fromisoformat(datetime_str)

            # In a real implementation, schedule the reminder
            # For now, return success with reminder details
            return ToolResult(
                success=True,
                result={
                    "message": message,
                    "scheduled_for": reminder_time.isoformat(),
                    "status": "scheduled",
                    "note": "This is a placeholder. Implement actual reminder scheduling.",
                },
            )
        except ValueError as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"Invalid datetime format: {e}. Use ISO format like '2024-01-15T14:30:00'",
            )
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))
