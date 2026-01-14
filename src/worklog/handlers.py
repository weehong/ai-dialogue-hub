"""Telegram bot handlers for WorkLog AI."""

from __future__ import annotations

import asyncio
import logging
from functools import wraps
from typing import TYPE_CHECKING, Callable

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from worklog.services.timezone_service import (
    get_current_datetime,
    get_today_date_string,
)

if TYPE_CHECKING:
    from worklog.config import Config
    from worklog.services.ai_service import AIService
    from worklog.services.mongodb_service import MongoDBService

logger = logging.getLogger(__name__)


def require_authorized_user(config: "Config"):
    """Decorator to check if user is authorized."""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(
            self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
        ):
            if not update.effective_user:
                return
            if update.effective_user.id != config.allowed_user_id:
                # Silently ignore unauthorized users
                return
            return await func(self, update, context, *args, **kwargs)

        return wrapper

    return decorator


class WorkLogHandlers:
    """Handlers for WorkLog AI bot."""

    def __init__(
        self,
        config: "Config",
        mongodb_service: "MongoDBService",
        ai_service: "AIService",
    ):
        """Initialize handlers.

        Args:
            config: Application configuration
            mongodb_service: MongoDB service for storage
            ai_service: AI service for transcription and summarization
        """
        self.config = config
        self.db = mongodb_service
        self.ai = ai_service

        # Apply authorization decorator dynamically
        self._apply_auth_decorator()

    def _apply_auth_decorator(self):
        """Apply authorization check to all handler methods."""
        # We'll check authorization in each method instead
        pass

    def _is_authorized(self, update: Update) -> bool:
        """Check if user is authorized."""
        if not update.effective_user:
            return False
        return update.effective_user.id == self.config.allowed_user_id

    async def start_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /start command - show welcome message."""
        if not update.message or not self._is_authorized(update):
            return

        await update.message.reply_text(
            "Welcome to WorkLog AI!\n\n"
            "Simply send messages or voice notes to log your work.\n"
            "Each day gets its own topic automatically.\n\n"
            "Commands:\n"
            "/undo - Delete your last log entry\n"
            "/close - Generate summary and close today's log"
        )

    async def handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle incoming text or voice messages."""
        if not update.message or not self._is_authorized(update):
            return

        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        # Get current date in user's timezone
        date_str = get_today_date_string(self.config.user_timezone)
        timestamp = get_current_datetime(self.config.user_timezone)

        # Check if daily topic exists
        thread_id = self.db.get_daily_topic(user_id, chat_id, date_str)

        if thread_id is None:
            # Create new forum topic for today
            try:
                topic_name = f"Log: {date_str}"
                topic = await context.bot.create_forum_topic(
                    chat_id=chat_id, name=topic_name
                )
                thread_id = topic.message_thread_id

                # Save topic mapping
                self.db.save_daily_topic(
                    user_id, chat_id, date_str, thread_id, topic_name
                )

                # Send welcome message in new topic
                await context.bot.send_message(
                    chat_id=chat_id,
                    message_thread_id=thread_id,
                    text="Good day! What are you working on?",
                )
                logger.info(f"Created daily topic: {topic_name}")
            except Exception as e:
                logger.error(f"Failed to create topic: {e}")
                await update.message.reply_text(
                    "Failed to create daily topic. Make sure I have 'Manage Topics' permission."
                )
                return

        # Process message content
        content = None
        content_type = "text"

        if update.message.voice:
            # Handle voice message
            content_type = "voice"
            await context.bot.send_chat_action(
                chat_id=chat_id,
                message_thread_id=thread_id,
                action=ChatAction.TYPING,
            )

            try:
                # Download voice file
                voice_file = await context.bot.get_file(update.message.voice.file_id)
                voice_bytes = await voice_file.download_as_bytearray()

                # Transcribe using Whisper
                content = self.ai.transcribe_voice(bytes(voice_bytes), "ogg")

                if content:
                    # Reply with transcription in the daily topic
                    await context.bot.send_message(
                        chat_id=chat_id,
                        message_thread_id=thread_id,
                        text=f"[Voice] {content}",
                    )
                else:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        message_thread_id=thread_id,
                        text="Failed to transcribe voice message.",
                    )
                    return

            except Exception as e:
                logger.error(f"Voice processing error: {e}")
                await context.bot.send_message(
                    chat_id=chat_id,
                    message_thread_id=thread_id,
                    text="Failed to process voice message.",
                )
                return

        elif update.message.text:
            # Handle text message
            content = update.message.text

            # If message is not in a topic, forward to daily topic
            if update.message.message_thread_id != thread_id:
                await context.bot.send_message(
                    chat_id=chat_id,
                    message_thread_id=thread_id,
                    text=content,
                )

        if content:
            # Save log entry
            success = self.db.save_log_entry(
                user_id=user_id,
                chat_id=chat_id,
                thread_id=thread_id,
                date_str=date_str,
                content=content,
                content_type=content_type,
                timestamp=timestamp,
            )

            if success:
                # Send confirmation in daily topic
                await context.bot.send_message(
                    chat_id=chat_id,
                    message_thread_id=thread_id,
                    text="Logged",
                )

    async def undo_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /undo command - delete last log entry."""
        if not update.message or not self._is_authorized(update):
            return

        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        thread_id = update.message.message_thread_id

        if thread_id is None:
            await update.message.reply_text("This command only works inside a topic.")
            return

        # Get current date
        date_str = get_today_date_string(self.config.user_timezone)

        # Delete latest log
        deleted = await asyncio.to_thread(
            self.db.delete_latest_log, user_id, chat_id, date_str
        )

        if deleted:
            content = deleted.get("content", "")
            # Truncate if too long
            if len(content) > 50:
                content = content[:50] + "..."
            await update.message.reply_text(f"Deleted: '{content}'")
        else:
            await update.message.reply_text("No logs to delete for today.")

    async def close_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /close command - generate summary and close topic."""
        if not update.message or not self._is_authorized(update):
            return

        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        thread_id = update.message.message_thread_id

        if thread_id is None:
            await update.message.reply_text("This command only works inside a topic.")
            return

        # Get current date
        date_str = get_today_date_string(self.config.user_timezone)

        # Retrieve all logs for the date
        logs = await asyncio.to_thread(
            self.db.get_logs_for_date, user_id, chat_id, date_str
        )

        if not logs:
            await update.message.reply_text("No logs to summarize.")
            return

        # Show typing indicator
        await context.bot.send_chat_action(
            chat_id=chat_id,
            message_thread_id=thread_id,
            action=ChatAction.TYPING,
        )

        # Generate summary
        summary = self.ai.generate_summary(logs, date_str, self.config.user_timezone)

        if summary:
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    message_thread_id=thread_id,
                    text=summary,
                    parse_mode="Markdown",
                )
            except Exception:
                # Fallback without markdown if parsing fails
                await context.bot.send_message(
                    chat_id=chat_id,
                    message_thread_id=thread_id,
                    text=summary,
                )
        else:
            # Fallback: simple log count message
            await update.message.reply_text(
                f"Logged {len(logs)} entries today. AI summary not available."
            )

        # Mark topic as closed in database
        self.db.mark_topic_closed(thread_id)

        # Close the forum topic
        try:
            await context.bot.close_forum_topic(
                chat_id=chat_id, message_thread_id=thread_id
            )
            logger.info(f"Closed topic {thread_id}")
        except Exception as e:
            logger.error(f"Failed to close topic: {e}")
            await update.message.reply_text(
                "Summary sent but failed to close topic. You may close it manually."
            )
