"""Save note tool implementation."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from facto.tools.base import Tool, ToolResult

if TYPE_CHECKING:
    from facto.services.memory import MemoryManager


class SaveNoteTool(Tool):
    """Save a note for the user."""

    def __init__(self, memory_manager: Optional["MemoryManager"] = None):
        self._memory = memory_manager

    @property
    def name(self) -> str:
        return "save_note"

    @property
    def description(self) -> str:
        return (
            "Save a note for the user. "
            "Use this when the user asks to remember something or save information."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Short title for the note",
                },
                "content": {
                    "type": "string",
                    "description": "The note content to save",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tags for categorization",
                },
            },
            "required": ["title", "content"],
        }

    async def execute(
        self, title: str, content: str, tags: Optional[list[str]] = None
    ) -> ToolResult:
        """Save a note."""
        try:
            # Generate a unique note ID
            timestamp = datetime.now().isoformat()
            hash_input = f"{title}{content}{timestamp}"
            note_id = hashlib.sha256(hash_input.encode()).hexdigest()[:12]

            # In a real implementation, save to database
            # For now, return success with note details
            note = {
                "note_id": note_id,
                "title": title,
                "content": content,
                "tags": tags or [],
                "created_at": timestamp,
            }

            return ToolResult(
                success=True,
                result={
                    "message": f"Note '{title}' saved successfully",
                    "note": note,
                },
            )
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))
