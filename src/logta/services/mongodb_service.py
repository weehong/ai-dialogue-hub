"""MongoDB service for storing Telegram messages."""

import logging
from datetime import datetime, timezone
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

logger = logging.getLogger(__name__)


# Event fields that indicate a system event rather than user content
EVENT_FIELDS = {
    "new_chat_member",
    "new_chat_members",
    "left_chat_member",
    "new_chat_participant",
    "left_chat_participant",
    "new_chat_title",
    "new_chat_photo",
    "delete_chat_photo",
    "group_chat_created",
    "supergroup_chat_created",
    "channel_chat_created",
    "migrate_to_chat_id",
    "migrate_from_chat_id",
    "pinned_message",
}


class MongoDBService:
    """Service for storing messages in MongoDB."""

    def __init__(
        self,
        uri: str,
        database_name: str = "telegram_logs",
    ):
        """Initialize MongoDB connection.

        Args:
            uri: MongoDB connection URI
            database_name: Name of the database
        """
        self.client: MongoClient = MongoClient(uri)
        self.db: Database = self.client[database_name]
        self.messages: Collection = self.db["messages"]
        self.events: Collection = self.db["events"]
        self.activated_chats: Collection = self.db["activated_chats"]

        # Load activated chats into memory for fast lookup
        self._activated_chat_ids: set[int] = set()
        self._load_activated_chats()

        # Create indexes for efficient querying
        self._create_indexes()

    def _create_indexes(self) -> None:
        """Create indexes for efficient querying."""
        # Indexes for messages collection
        self.messages.create_index(
            [("message_id", 1), ("chat_id", 1)],
            unique=True,
            name="message_chat_unique",
        )
        self.messages.create_index("chat_id", name="chat_id_idx")
        self.messages.create_index("date", name="date_idx")
        self.messages.create_index("from_user.id", name="user_id_idx")
        self.messages.create_index("message_thread_id", name="thread_id_idx")

        # Indexes for events collection
        self.events.create_index(
            [("message_id", 1), ("chat_id", 1)],
            unique=True,
            name="event_chat_unique",
        )
        self.events.create_index("chat_id", name="chat_id_idx")
        self.events.create_index("date", name="date_idx")

        logger.info("MongoDB indexes created for messages and events collections")

    def _load_activated_chats(self) -> None:
        """Load activated chat IDs from database into memory."""
        try:
            chats = self.activated_chats.find({}, {"chat_id": 1})
            self._activated_chat_ids = {doc["chat_id"] for doc in chats}
            logger.info(f"Loaded {len(self._activated_chat_ids)} activated chats")
        except Exception as e:
            logger.error(f"Failed to load activated chats: {e}")

    def is_chat_activated(self, chat_id: int) -> bool:
        """Check if a chat is activated for logging."""
        return chat_id in self._activated_chat_ids

    def activate_chat(self, chat_id: int, chat_title: str) -> bool:
        """Activate a chat for logging.

        Returns:
            True if newly activated, False if already active
        """
        if chat_id in self._activated_chat_ids:
            return False

        try:
            self.activated_chats.update_one(
                {"chat_id": chat_id},
                {
                    "$set": {
                        "chat_id": chat_id,
                        "chat_title": chat_title,
                        "activated_at": datetime.now(timezone.utc),
                    }
                },
                upsert=True,
            )
            self._activated_chat_ids.add(chat_id)
            logger.info(f"Activated chat: {chat_title} ({chat_id})")
            return True
        except Exception as e:
            logger.error(f"Failed to activate chat: {e}")
            return False

    def deactivate_chat(self, chat_id: int) -> bool:
        """Deactivate a chat from logging.

        Returns:
            True if deactivated, False if wasn't active
        """
        if chat_id not in self._activated_chat_ids:
            return False

        try:
            self.activated_chats.delete_one({"chat_id": chat_id})
            self._activated_chat_ids.discard(chat_id)
            logger.info(f"Deactivated chat: {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to deactivate chat: {e}")
            return False

    def _is_event(self, message_data: dict[str, Any]) -> bool:
        """Check if the message is a system event."""
        return any(message_data.get(field) for field in EVENT_FIELDS)

    def save_message(self, message_data: dict[str, Any]) -> bool:
        """Save a message or event to the appropriate MongoDB collection.

        Args:
            message_data: The message data dictionary from Telegram

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Add server timestamp for when we logged this
            message_data["logged_at"] = datetime.now(timezone.utc)

            # Determine which collection to use
            is_event = self._is_event(message_data)
            collection = self.events if is_event else self.messages
            doc_type = "event" if is_event else "message"

            # Use upsert to handle duplicates gracefully
            result = collection.update_one(
                {
                    "message_id": message_data.get("message_id"),
                    "chat_id": message_data.get("chat_id"),
                },
                {"$set": message_data},
                upsert=True,
            )

            if result.upserted_id:
                logger.debug(f"Inserted new {doc_type}: {message_data.get('message_id')}")
            else:
                logger.debug(f"Updated existing {doc_type}: {message_data.get('message_id')}")

            return True

        except Exception as e:
            logger.error(f"Failed to save {doc_type}: {e}")
            return False

    def save_edited_message(self, message_data: dict[str, Any]) -> bool:
        """Save an edited message, preserving the original.

        Args:
            message_data: The edited message data

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            message_id = message_data.get("message_id")
            chat_id = message_data.get("chat_id")

            # Edited messages are always content, use messages collection
            original = self.messages.find_one(
                {"message_id": message_id, "chat_id": chat_id}
            )

            if original:
                # Initialize edit history if not exists
                edit_history = original.get("edit_history", [])

                # Add the previous version to history (preserve text or caption edits)
                if "text" in original or "caption" in original:
                    edit_history.append(
                        {
                            "text": original.get("text"),
                            "caption": original.get("caption"),
                            "edited_at": original.get("edit_date") or original.get("logged_at"),
                        }
                    )

                message_data["edit_history"] = edit_history

            message_data["logged_at"] = datetime.now(timezone.utc)
            message_data["was_edited"] = True

            result = self.messages.update_one(
                {"message_id": message_id, "chat_id": chat_id},
                {"$set": message_data},
                upsert=True,
            )

            logger.debug(f"Saved edited message: {message_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save edited message: {e}")
            return False

    def get_messages_by_chat(
        self, chat_id: int, limit: int = 100, skip: int = 0
    ) -> list[dict[str, Any]]:
        """Retrieve messages for a specific chat.

        Args:
            chat_id: The Telegram chat ID
            limit: Maximum number of messages to return
            skip: Number of messages to skip (for pagination)

        Returns:
            List of message documents
        """
        cursor = (
            self.messages.find({"chat_id": chat_id})
            .sort("date", -1)
            .skip(skip)
            .limit(limit)
        )
        return list(cursor)

    def get_messages_by_user(
        self, user_id: int, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Retrieve messages from a specific user.

        Args:
            user_id: The Telegram user ID
            limit: Maximum number of messages to return

        Returns:
            List of message documents
        """
        cursor = (
            self.messages.find({"from_user.id": user_id})
            .sort("date", -1)
            .limit(limit)
        )
        return list(cursor)

    def get_messages_by_topic(
        self, chat_id: int, thread_id: int, limit: int = 500
    ) -> list[dict[str, Any]]:
        """Retrieve messages from a specific forum topic.

        Args:
            chat_id: The Telegram chat ID
            thread_id: The forum topic thread ID
            limit: Maximum number of messages to return

        Returns:
            List of message documents sorted by date (oldest first)
        """
        cursor = (
            self.messages.find({
                "chat_id": chat_id,
                "message_thread_id": thread_id
            })
            .sort("date", 1)
            .limit(limit)
        )
        return list(cursor)

    def get_message_count(self, chat_id: int | None = None) -> int:
        """Get the total count of logged messages.

        Args:
            chat_id: Optional chat ID to filter by

        Returns:
            Number of messages
        """
        filter_query = {"chat_id": chat_id} if chat_id else {}
        return self.messages.count_documents(filter_query)

    def get_event_count(self, chat_id: int | None = None) -> int:
        """Get the total count of logged events.

        Args:
            chat_id: Optional chat ID to filter by

        Returns:
            Number of events
        """
        filter_query = {"chat_id": chat_id} if chat_id else {}
        return self.events.count_documents(filter_query)

    def close(self) -> None:
        """Close the MongoDB connection."""
        self.client.close()
        logger.info("MongoDB connection closed")
