import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from facto.core.enums import ChatMode

logger = logging.getLogger(__name__)


@dataclass
class ConversationState:
    history: List[Dict[str, str]]
    msg_ids_to_delete: List[int] = field(default_factory=list)


class MemoryManager:
    def __init__(self, mongodb_uri: str = None, database_name: str = "facto"):
        self._conversations: Dict[int, ConversationState] = {}
        self._chat_modes: Dict[int, ChatMode] = {}

        self._collection = None
        self._modes_collection = None

        if mongodb_uri:
            try:
                from pymongo import MongoClient
                client = MongoClient(mongodb_uri)
                db = client[database_name]
                self._collection = db["conversations"]
                self._modes_collection = db["chat_modes"]

                self._collection.create_index("thread_id", unique=True)
                self._modes_collection.create_index("chat_id", unique=True)

                self._load_from_db()
                logger.info("MemoryManager: MongoDB persistence enabled")
            except Exception as e:
                logger.warning(f"MemoryManager: MongoDB init failed, using in-memory only: {e}")

    def _load_from_db(self):
        if self._collection is None:
            return

        for doc in self._collection.find():
            thread_id = doc["thread_id"]
            self._conversations[thread_id] = ConversationState(
                history=doc.get("history", []),
                msg_ids_to_delete=doc.get("msg_ids_to_delete", [])
            )

        if self._modes_collection is not None:
            for doc in self._modes_collection.find():
                chat_id = doc["chat_id"]
                mode_str = doc.get("mode", "journal")
                self._chat_modes[chat_id] = ChatMode(mode_str)

        logger.info(f"Loaded {len(self._conversations)} conversations, {len(self._chat_modes)} chat modes")

    def _persist_conversation(self, thread_id: int):
        if self._collection is None or thread_id not in self._conversations:
            return

        conv = self._conversations[thread_id]
        self._collection.update_one(
            {"thread_id": thread_id},
            {"$set": {
                "thread_id": thread_id,
                "history": conv.history,
                "msg_ids_to_delete": conv.msg_ids_to_delete
            }},
            upsert=True
        )

    def _persist_chat_mode(self, chat_id: int):
        if self._modes_collection is None or chat_id not in self._chat_modes:
            return

        self._modes_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {
                "chat_id": chat_id,
                "mode": self._chat_modes[chat_id].value
            }},
            upsert=True
        )

    def set_chat_mode(self, chat_id: int, mode: ChatMode):
        self._chat_modes[chat_id] = mode
        self._persist_chat_mode(chat_id)

    def get_chat_mode(self, chat_id: int) -> ChatMode:
        return self._chat_modes.get(chat_id, ChatMode.JOURNAL)

    def start_conversation(self, thread_id: int, initial_history: List[Dict[str, str]]):
        self._conversations[thread_id] = ConversationState(history=initial_history)
        self._persist_conversation(thread_id)

    def get_conversation(self, thread_id: int) -> Optional[ConversationState]:
        return self._conversations.get(thread_id)

    def add_message(self, thread_id: int, role: str, content: str):
        if thread_id in self._conversations:
            self._conversations[thread_id].history.append({"role": role, "content": content})
            self._persist_conversation(thread_id)

    def mark_message_for_deletion(self, thread_id: int, message_id: int):
        if thread_id in self._conversations:
            self._conversations[thread_id].msg_ids_to_delete.append(message_id)

    def get_messages_to_delete(self, thread_id: int) -> List[int]:
        if thread_id in self._conversations:
            return self._conversations[thread_id].msg_ids_to_delete
        return []

    def end_conversation(self, thread_id: int):
        if thread_id in self._conversations:
            del self._conversations[thread_id]
            if self._collection is not None:
                self._collection.delete_one({"thread_id": thread_id})

    def is_conversation_active(self, thread_id: int) -> bool:
        return thread_id in self._conversations
