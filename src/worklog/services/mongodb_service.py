"""MongoDB service for WorkLog AI storage."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from pymongo import MongoClient, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database

logger = logging.getLogger(__name__)


class MongoDBService:
    """Service for storing work logs in MongoDB."""

    def __init__(self, uri: str, database_name: str = "worklog_db"):
        """Initialize MongoDB connection.

        Args:
            uri: MongoDB connection URI
            database_name: Name of the database
        """
        self.client: MongoClient = MongoClient(uri)
        self.db: Database = self.client[database_name]
        self.work_logs: Collection = self.db["work_logs"]
        self.daily_topics: Collection = self.db["daily_topics"]

        self._create_indexes()
        logger.info(f"Connected to MongoDB: {database_name}")

    def _create_indexes(self) -> None:
        """Create indexes for efficient querying."""
        # Indexes for work_logs collection
        self.work_logs.create_index(
            [("user_id", 1), ("chat_id", 1), ("thread_id", 1), ("timestamp", 1)],
            name="user_chat_thread_time_idx",
        )
        self.work_logs.create_index("date_str", name="date_idx")

        # Indexes for daily_topics collection
        self.daily_topics.create_index(
            [("user_id", 1), ("chat_id", 1), ("date_str", 1)],
            unique=True,
            name="user_chat_date_unique",
        )
        self.daily_topics.create_index("date_str", name="date_idx")

        logger.info("MongoDB indexes created")

    def save_log_entry(
        self,
        user_id: int,
        chat_id: int,
        thread_id: int,
        date_str: str,
        content: str,
        content_type: str,
        timestamp: datetime,
    ) -> bool:
        """Save a work log entry.

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            thread_id: Forum topic thread ID
            date_str: Date string (YYYY-MM-DD)
            content: Log content (text or transcribed voice)
            content_type: "text" or "voice"
            timestamp: Timezone-aware timestamp

        Returns:
            True if saved successfully
        """
        try:
            doc = {
                "user_id": user_id,
                "chat_id": chat_id,
                "thread_id": thread_id,
                "date_str": date_str,
                "content": content,
                "content_type": content_type,
                "timestamp": timestamp,
                "logged_at": datetime.now(timezone.utc),
            }
            self.work_logs.insert_one(doc)
            logger.debug(f"Saved log entry for {date_str}")
            return True
        except Exception as e:
            logger.error(f"Failed to save log entry: {e}")
            return False

    def get_daily_topic(
        self, user_id: int, chat_id: int, date_str: str
    ) -> Optional[int]:
        """Get existing thread_id for a date.

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            date_str: Date string (YYYY-MM-DD)

        Returns:
            Thread ID if exists, None otherwise
        """
        try:
            doc = self.daily_topics.find_one(
                {"user_id": user_id, "chat_id": chat_id, "date_str": date_str}
            )
            if doc and not doc.get("is_closed", False):
                return doc.get("thread_id")
            return None
        except Exception as e:
            logger.error(f"Failed to get daily topic: {e}")
            return None

    def save_daily_topic(
        self,
        user_id: int,
        chat_id: int,
        date_str: str,
        thread_id: int,
        topic_name: str,
    ) -> bool:
        """Save new topic mapping.

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            date_str: Date string (YYYY-MM-DD)
            thread_id: Forum topic thread ID
            topic_name: Topic name

        Returns:
            True if saved successfully
        """
        try:
            self.daily_topics.update_one(
                {"user_id": user_id, "chat_id": chat_id, "date_str": date_str},
                {
                    "$set": {
                        "thread_id": thread_id,
                        "topic_name": topic_name,
                        "created_at": datetime.now(timezone.utc),
                        "is_closed": False,
                    }
                },
                upsert=True,
            )
            logger.info(f"Saved daily topic: {topic_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to save daily topic: {e}")
            return False

    def get_logs_for_date(
        self, user_id: int, chat_id: int, date_str: str
    ) -> list[dict[str, Any]]:
        """Retrieve all logs for a specific date.

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            date_str: Date string (YYYY-MM-DD)

        Returns:
            List of log documents sorted by timestamp
        """
        try:
            cursor = self.work_logs.find(
                {"user_id": user_id, "chat_id": chat_id, "date_str": date_str}
            ).sort("timestamp", 1)
            return list(cursor)
        except Exception as e:
            logger.error(f"Failed to get logs for date: {e}")
            return []

    def delete_latest_log(
        self, user_id: int, chat_id: int, date_str: str
    ) -> Optional[dict[str, Any]]:
        """Delete and return the most recent log entry.

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            date_str: Date string (YYYY-MM-DD)

        Returns:
            Deleted document or None if no logs found
        """
        try:
            # Find the latest log
            latest = self.work_logs.find_one(
                {"user_id": user_id, "chat_id": chat_id, "date_str": date_str},
                sort=[("timestamp", DESCENDING)],
            )
            if latest:
                self.work_logs.delete_one({"_id": latest["_id"]})
                logger.info(f"Deleted latest log for {date_str}")
                return latest
            return None
        except Exception as e:
            logger.error(f"Failed to delete latest log: {e}")
            return None

    def mark_topic_closed(self, thread_id: int) -> bool:
        """Mark a topic as closed.

        Args:
            thread_id: Forum topic thread ID

        Returns:
            True if marked successfully
        """
        try:
            self.daily_topics.update_one(
                {"thread_id": thread_id},
                {"$set": {"is_closed": True, "closed_at": datetime.now(timezone.utc)}},
            )
            logger.info(f"Marked topic {thread_id} as closed")
            return True
        except Exception as e:
            logger.error(f"Failed to mark topic closed: {e}")
            return False

    def close(self) -> None:
        """Close the MongoDB connection."""
        self.client.close()
        logger.info("MongoDB connection closed")
