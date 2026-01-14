"""Work log memory manager for tracking progressive work log entries."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pymongo.collection import Collection

logger = logging.getLogger(__name__)


class WorkLogState(Enum):
    """State of a work log conversation."""
    ACTIVE = "active"
    PENDING_CONFIRMATION = "pending_confirmation"


@dataclass
class TimestampedEntry:
    """A work log entry with timestamp."""
    text: str
    timestamp: datetime

    def format_time(self) -> str:
        """Format timestamp as HH:MM."""
        return self.timestamp.strftime("%H:%M")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        return {
            "text": self.text,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimestampedEntry":
        """Create from dictionary loaded from MongoDB."""
        return cls(
            text=data["text"],
            timestamp=data["timestamp"],
        )


@dataclass
class WorkLogSession:
    """Represents an active work log session."""
    entries: List[TimestampedEntry] = field(default_factory=list)
    msg_ids_to_delete: List[int] = field(default_factory=list)
    state: WorkLogState = WorkLogState.ACTIVE
    title: str = ""
    chat_id: int = 0
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self, thread_id: int) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        return {
            "thread_id": thread_id,
            "chat_id": self.chat_id,
            "title": self.title,
            "entries": [e.to_dict() for e in self.entries],
            "msg_ids_to_delete": self.msg_ids_to_delete,
            "state": self.state.value,
            "created_at": self.created_at,
            "updated_at": datetime.now(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkLogSession":
        """Create from dictionary loaded from MongoDB."""
        return cls(
            entries=[TimestampedEntry.from_dict(e) for e in data.get("entries", [])],
            msg_ids_to_delete=data.get("msg_ids_to_delete", []),
            state=WorkLogState(data.get("state", "active")),
            title=data.get("title", ""),
            chat_id=data.get("chat_id", 0),
            created_at=data.get("created_at", datetime.now()),
        )


class WorkLogMemory:
    """Manager for work log sessions with MongoDB persistence."""

    def __init__(self, collection: Optional[Collection] = None):
        """Initialize work log memory.

        Args:
            collection: Optional MongoDB collection for persistence.
                       If None, work logs are stored in memory only.
        """
        self._worklogs: Dict[int, WorkLogSession] = {}
        self._collection = collection

        if self._collection is not None:
            self._create_indexes()
            self._load_from_db()

    def _create_indexes(self) -> None:
        """Create MongoDB indexes."""
        if self._collection is None:
            return
        self._collection.create_index("thread_id", unique=True)
        self._collection.create_index("chat_id")
        self._collection.create_index("created_at")
        logger.info("WorkLogMemory: MongoDB indexes created")

    def _load_from_db(self) -> None:
        """Load existing work logs from MongoDB."""
        if self._collection is None:
            return
        try:
            for doc in self._collection.find():
                thread_id = doc["thread_id"]
                self._worklogs[thread_id] = WorkLogSession.from_dict(doc)
            logger.info(f"WorkLogMemory: Loaded {len(self._worklogs)} work logs from MongoDB")
        except Exception as e:
            logger.error(f"WorkLogMemory: Failed to load from MongoDB: {e}")

    def _persist(self, thread_id: int) -> None:
        """Persist a work log to MongoDB."""
        if self._collection is None or thread_id not in self._worklogs:
            return
        try:
            session = self._worklogs[thread_id]
            self._collection.update_one(
                {"thread_id": thread_id},
                {"$set": session.to_dict(thread_id)},
                upsert=True,
            )
        except Exception as e:
            logger.error(f"WorkLogMemory: Failed to persist thread {thread_id}: {e}")

    def _delete_from_db(self, thread_id: int) -> None:
        """Delete a work log from MongoDB."""
        if self._collection is None:
            return
        try:
            self._collection.delete_one({"thread_id": thread_id})
        except Exception as e:
            logger.error(f"WorkLogMemory: Failed to delete thread {thread_id}: {e}")

    def start_worklog(self, thread_id: int, title: str = "", chat_id: int = 0) -> None:
        """Start a new work log session for a topic."""
        self._worklogs[thread_id] = WorkLogSession(
            title=title,
            chat_id=chat_id,
            created_at=datetime.now(),
        )
        self._persist(thread_id)
        logger.info(f"Started work log for thread {thread_id}")

    def add_entry(self, thread_id: int, text: str) -> bool:
        """Add an entry to the work log with current timestamp.

        Returns:
            True if entry was added, False if no active work log exists.
        """
        if thread_id not in self._worklogs:
            return False
        entry = TimestampedEntry(text=text, timestamp=datetime.now())
        self._worklogs[thread_id].entries.append(entry)
        self._persist(thread_id)
        return True

    def get_entries(self, thread_id: int) -> List[TimestampedEntry]:
        """Get all entries for a work log."""
        if thread_id not in self._worklogs:
            return []
        return self._worklogs[thread_id].entries.copy()

    def get_entry_count(self, thread_id: int) -> int:
        """Get the number of entries in a work log."""
        if thread_id not in self._worklogs:
            return 0
        return len(self._worklogs[thread_id].entries)

    def remove_entry(self, thread_id: int, index: int) -> Optional[TimestampedEntry]:
        """Remove an entry by index (1-based).

        Returns:
            The removed entry, or None if invalid index or no work log.
        """
        if thread_id not in self._worklogs:
            return None
        entries = self._worklogs[thread_id].entries
        if index < 1 or index > len(entries):
            return None
        removed = entries.pop(index - 1)
        self._persist(thread_id)
        return removed

    def edit_entry(self, thread_id: int, index: int, new_text: str) -> Optional[str]:
        """Edit an entry by index (1-based). Updates timestamp.

        Returns:
            The old entry text, or None if invalid index or no work log.
        """
        if thread_id not in self._worklogs:
            return None
        entries = self._worklogs[thread_id].entries
        if index < 1 or index > len(entries):
            return None
        old_text = entries[index - 1].text
        entries[index - 1].text = new_text
        entries[index - 1].timestamp = datetime.now()
        self._persist(thread_id)
        return old_text

    def is_active(self, thread_id: int) -> bool:
        """Check if a work log is active for the given thread."""
        return thread_id in self._worklogs

    def is_pending_confirmation(self, thread_id: int) -> bool:
        """Check if work log is awaiting confirmation."""
        if thread_id not in self._worklogs:
            return False
        return self._worklogs[thread_id].state == WorkLogState.PENDING_CONFIRMATION

    def set_pending_confirmation(self, thread_id: int) -> None:
        """Set work log to pending confirmation state."""
        if thread_id in self._worklogs:
            self._worklogs[thread_id].state = WorkLogState.PENDING_CONFIRMATION
            self._persist(thread_id)

    def reset_to_active(self, thread_id: int) -> None:
        """Reset work log back to active state (user cancelled)."""
        if thread_id in self._worklogs:
            self._worklogs[thread_id].state = WorkLogState.ACTIVE
            self._persist(thread_id)

    def mark_message_for_deletion(self, thread_id: int, message_id: int) -> None:
        """Mark a message to be deleted when the work log is closed."""
        if thread_id in self._worklogs:
            self._worklogs[thread_id].msg_ids_to_delete.append(message_id)
            # Don't persist message IDs - they're transient

    def get_messages_to_delete(self, thread_id: int) -> List[int]:
        """Get all message IDs marked for deletion."""
        if thread_id not in self._worklogs:
            return []
        return self._worklogs[thread_id].msg_ids_to_delete.copy()

    def end_worklog(self, thread_id: int) -> None:
        """End and remove a work log session."""
        if thread_id in self._worklogs:
            del self._worklogs[thread_id]
            self._delete_from_db(thread_id)
            logger.info(f"Ended work log for thread {thread_id}")

    def get_formatted_log(self, thread_id: int) -> Optional[str]:
        """Get formatted work log entries for AI processing."""
        entries = self.get_entries(thread_id)
        if not entries:
            return None

        formatted = "Work Log Entries:\n"
        for i, entry in enumerate(entries, 1):
            formatted += f"\n{i}. [{entry.format_time()}] {entry.text}"
        return formatted
