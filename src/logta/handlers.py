"""Telegram message handlers for the logger bot."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from logta.services.mongodb_service import MongoDBService
from logta.services.worklog_memory import WorkLogMemory

if TYPE_CHECKING:
    from logta.services.ai_service import AIService

logger = logging.getLogger(__name__)


class MessageLoggerHandlers:
    """Handlers for logging Telegram messages."""

    def __init__(
        self,
        mongodb_service: MongoDBService,
        owner_id: int,
        ai_service: AIService | None = None,
    ):
        """Initialize handlers with MongoDB service.

        Args:
            mongodb_service: The MongoDB service for storing messages
            owner_id: Telegram user ID of the bot owner
            ai_service: Optional AI service for title generation
        """
        self.db = mongodb_service
        self.owner_id = owner_id
        self.ai_service = ai_service
        # Initialize work log memory with MongoDB collection for persistence
        worklogs_collection = mongodb_service.db["worklogs"]
        self.worklog_memory = WorkLogMemory(collection=worklogs_collection)

    async def log_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Log any incoming message to MongoDB.

        This handler captures all message types: text, photos, videos,
        documents, stickers, etc. Automatically activates chats.
        """
        if not update.message:
            return

        # Automatically activate chat if not already activated
        chat_title = update.message.chat.title or "Private Chat"
        self.db.activate_chat(update.message.chat_id, chat_title)

        try:
            # Convert the Telegram message object to a dictionary
            message_data = update.message.to_dict()

            # Add chat_id at root level for easier indexing
            message_data["chat_id"] = update.message.chat_id

            # Add user info at root level for easier querying
            if update.message.from_user:
                message_data["from_user"] = update.message.from_user.to_dict()

            # Save to MongoDB (run in thread to avoid blocking event loop)
            success = await asyncio.to_thread(self.db.save_message, message_data)

            if success:
                user_name = (
                    update.message.from_user.first_name
                    if update.message.from_user
                    else "Unknown"
                )
                chat_title = update.message.chat.title or "Private Chat"
                logger.info(
                    f"Logged message from {user_name} in '{chat_title}' "
                    f"(msg_id: {update.message.message_id})"
                )

        except Exception as e:
            logger.error(f"Error logging message: {e}")

    async def log_edited_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Log edited messages, preserving the edit history."""
        if not update.edited_message:
            return

        # Automatically activate chat if not already activated
        chat_title = update.edited_message.chat.title or "Private Chat"
        self.db.activate_chat(update.edited_message.chat_id, chat_title)

        try:
            message_data = update.edited_message.to_dict()
            message_data["chat_id"] = update.edited_message.chat_id

            if update.edited_message.from_user:
                message_data["from_user"] = update.edited_message.from_user.to_dict()

            success = await asyncio.to_thread(self.db.save_edited_message, message_data)

            if success:
                user_name = (
                    update.edited_message.from_user.first_name
                    if update.edited_message.from_user
                    else "Unknown"
                )
                logger.info(
                    f"Logged edited message from {user_name} "
                    f"(msg_id: {update.edited_message.message_id})"
                )

        except Exception as e:
            logger.error(f"Error logging edited message: {e}")

    async def log_channel_post(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Log channel posts."""
        if not update.channel_post:
            return

        # Automatically activate chat if not already activated
        chat_title = update.channel_post.chat.title or "Unknown Channel"
        self.db.activate_chat(update.channel_post.chat_id, chat_title)

        try:
            message_data = update.channel_post.to_dict()
            message_data["chat_id"] = update.channel_post.chat_id
            message_data["is_channel_post"] = True

            success = await asyncio.to_thread(self.db.save_message, message_data)

            if success:
                channel_title = update.channel_post.chat.title or "Unknown Channel"
                logger.info(
                    f"Logged channel post in '{channel_title}' "
                    f"(msg_id: {update.channel_post.message_id})"
                )

        except Exception as e:
            logger.error(f"Error logging channel post: {e}")

    async def stats_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Show logging statistics. Only works for bot owner."""
        if not update.message or not update.message.from_user:
            return

        # Only respond to owner
        if update.message.from_user.id != self.owner_id:
            return

        try:
            chat_id = update.message.chat_id
            total_messages = await asyncio.to_thread(self.db.get_message_count)
            chat_messages = await asyncio.to_thread(self.db.get_message_count, chat_id)
            total_events = await asyncio.to_thread(self.db.get_event_count)
            chat_events = await asyncio.to_thread(self.db.get_event_count, chat_id)

            await update.message.reply_text(
                f"Message Logger Stats:\n"
                f"This chat:\n"
                f"  - Messages: {chat_messages:,}\n"
                f"  - Events: {chat_events:,}\n"
                f"Total:\n"
                f"  - Messages: {total_messages:,}\n"
                f"  - Events: {total_events:,}"
            )

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            await update.message.reply_text("Failed to retrieve statistics.")

    async def topic_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Create a new forum topic with AI-generated title from the message."""
        if not update.message or not update.message.from_user:
            return

        # Check if message content is provided
        if not context.args:
            await update.message.reply_text(
                "Usage: `/topic <your message>`\n\n"
                "Example: `/topic How do I fix the database connection issue?`",
                parse_mode="Markdown",
            )
            return

        user_message = " ".join(context.args)
        chat_id = update.message.chat_id
        user = update.message.from_user

        # Show typing indicator
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

        try:
            # Generate topic title
            if self.ai_service:
                topic_title = await asyncio.to_thread(
                    self.ai_service.generate_topic_title, user_message
                )
            else:
                # Fallback to truncation if no AI service
                topic_title = (
                    (user_message[:57] + "...") if len(user_message) > 60 else user_message
                )

            # Create the forum topic
            topic = await context.bot.create_forum_topic(
                chat_id=chat_id, name=topic_title
            )
            thread_id = topic.message_thread_id

            # Send the original message in the new topic
            await context.bot.send_message(
                chat_id=chat_id,
                message_thread_id=thread_id,
                text=f"Topic created by {user.mention_html()}\n\n{user_message}",
                parse_mode="HTML",
            )

            logger.info(
                f"Created topic '{topic_title}' by {user.first_name} in chat {chat_id}"
            )

        except Exception as e:
            logger.error(f"Error creating topic: {e}")
            await update.message.reply_text(
                "Failed to create topic. Make sure the bot has 'Manage Topics' permission."
            )

    async def history_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Retrieve conversation history for the current topic. Only works for bot owner."""
        if not update.message or not update.message.from_user:
            return

        # Only respond to owner
        if update.message.from_user.id != self.owner_id:
            return

        thread_id = update.message.message_thread_id
        if thread_id is None:
            await update.message.reply_text("This command only works inside a forum topic.")
            return

        try:
            chat_id = update.message.chat_id
            messages = await asyncio.to_thread(
                self.db.get_messages_by_topic, chat_id, thread_id
            )

            if not messages:
                await update.message.reply_text("No messages found for this topic.")
                return

            # Format conversation
            lines = [f"Topic Conversation ({len(messages)} messages):\n"]
            for msg in messages:
                user = msg.get("from_user", {})
                name = user.get("first_name", "Unknown")
                text = msg.get("text") or msg.get("caption") or "[media]"
                # Truncate long messages
                if len(text) > 100:
                    text = text[:100] + "..."
                lines.append(f"• {name}: {text}")

            response = "\n".join(lines)

            # Telegram message limit
            if len(response) > 4096:
                response = response[:4093] + "..."

            await update.message.reply_text(response)

        except Exception as e:
            logger.error(f"Error retrieving topic conversation: {e}")
            await update.message.reply_text("Failed to retrieve topic conversation.")

    # =========================================================================
    # Work Log Commands
    # =========================================================================

    async def worklog_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Start a new work log session in a forum topic."""
        if not update.message or not update.message.from_user:
            return

        chat_id = update.message.chat_id
        user = update.message.from_user

        # Get topic title from user input
        topic_title = " ".join(context.args) if context.args else None

        if not topic_title:
            await update.message.reply_text(
                "Usage: `/worklog <title>`\n\n"
                "Example: `/worklog 2024-01-10 Project meeting`\n"
                "Example: `/worklog Sprint Review`",
                parse_mode="Markdown",
            )
            return

        # Truncate if too long (Telegram limit is ~128 chars for topic names)
        if len(topic_title) > 120:
            topic_title = topic_title[:117] + "..."

        try:
            # Create the forum topic
            topic = await context.bot.create_forum_topic(
                chat_id=chat_id, name=topic_title
            )
            thread_id = topic.message_thread_id

            # Start work log session with title and chat_id for persistence
            self.worklog_memory.start_worklog(thread_id, title=topic_title, chat_id=chat_id)

            # Send welcome message
            welcome_text = (
                f"Work Log started by {user.mention_html()}\n\n"
                "Add entries by sending messages in this topic.\n"
                "Commands:\n"
                "  /list - Show all entries\n"
                "  /edit <n> <text> - Edit entry #n\n"
                "  /remove <n> - Remove entry #n\n"
                "  /done - Generate summary\n"
                "  /close - Delete this topic"
            )

            welcome_msg = await context.bot.send_message(
                chat_id=chat_id,
                message_thread_id=thread_id,
                text=welcome_text,
                parse_mode="HTML",
            )
            self.worklog_memory.mark_message_for_deletion(thread_id, welcome_msg.message_id)

            logger.info(f"Created work log topic '{topic_title}' by {user.first_name} in chat {chat_id}")

        except Exception as e:
            logger.error(f"Error creating work log topic: {e}")
            await update.message.reply_text(
                "Failed to create work log. Make sure the bot has 'Manage Topics' permission."
            )

    async def handle_worklog_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle messages in an active work log topic."""
        if not update.message or not update.message.text:
            return

        thread_id = update.message.message_thread_id
        if thread_id is None:
            return

        # Check if this is an active work log
        if not self.worklog_memory.is_active(thread_id):
            return

        chat_id = update.message.chat_id
        text = update.message.text.strip()

        # Handle confirmation responses
        if self.worklog_memory.is_pending_confirmation(thread_id):
            if text.lower() in ("yes", "y", "confirm"):
                await self._generate_worklog_summary(chat_id, thread_id, context)
            else:
                self.worklog_memory.reset_to_active(thread_id)
                await context.bot.send_message(
                    chat_id=chat_id,
                    message_thread_id=thread_id,
                    text="Summary cancelled. Continue adding entries or use /done again.",
                )
            return

        # Add entry to work log
        self.worklog_memory.add_entry(thread_id, text)
        self.worklog_memory.mark_message_for_deletion(thread_id, update.message.message_id)

        # Send confirmation
        entry_count = self.worklog_memory.get_entry_count(thread_id)
        confirm_msg = await context.bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text=f"Entry #{entry_count} added.",
        )
        self.worklog_memory.mark_message_for_deletion(thread_id, confirm_msg.message_id)

    async def list_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """List all work log entries in the current topic."""
        if not update.message:
            return

        thread_id = update.message.message_thread_id
        chat_id = update.message.chat_id

        if thread_id is None:
            await update.message.reply_text("This command only works inside a topic.")
            return

        if not self.worklog_memory.is_active(thread_id):
            await update.message.reply_text("No active work log in this topic.")
            return

        entries = self.worklog_memory.get_entries(thread_id)
        if not entries:
            await update.message.reply_text("No entries in this work log yet.")
            return

        # Format entries list with timestamps
        entries_text = f"Work Log Entries ({len(entries)} total):\n"
        for i, entry in enumerate(entries, 1):
            # Truncate long entries for display
            text = entry.text
            display_text = text if len(text) <= 80 else text[:77] + "..."
            entries_text += f"\n{i}. [{entry.format_time()}] {display_text}"

        await context.bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text=entries_text,
        )

    async def remove_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Remove an entry from the work log by its number."""
        if not update.message:
            return

        thread_id = update.message.message_thread_id
        chat_id = update.message.chat_id

        if thread_id is None:
            await update.message.reply_text("This command only works inside a topic.")
            return

        if not self.worklog_memory.is_active(thread_id):
            await update.message.reply_text("No active work log in this topic.")
            return

        # Parse entry number from args
        if not context.args:
            await update.message.reply_text(
                "Usage: `/remove <number>`\n\n"
                "Example: `/remove 3` to remove entry #3\n"
                "Use `/list` to see entry numbers.",
                parse_mode="Markdown",
            )
            return

        try:
            entry_num = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Please provide a valid entry number.")
            return

        # Remove the entry
        removed = self.worklog_memory.remove_entry(thread_id, entry_num)
        if removed is None:
            entry_count = self.worklog_memory.get_entry_count(thread_id)
            if entry_count == 0:
                await update.message.reply_text("No entries to remove.")
            else:
                await update.message.reply_text(
                    f"Invalid entry number. Use 1-{entry_count}."
                )
            return

        # Truncate for display
        text = removed.text
        display_text = text if len(text) <= 50 else text[:47] + "..."
        remaining = self.worklog_memory.get_entry_count(thread_id)

        await context.bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text=f"Removed entry #{entry_num} [{removed.format_time()}]: {display_text}\n({remaining} entries remaining)",
        )

    async def edit_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Edit an entry in the work log by its number."""
        if not update.message:
            return

        thread_id = update.message.message_thread_id
        chat_id = update.message.chat_id

        if thread_id is None:
            await update.message.reply_text("This command only works inside a topic.")
            return

        if not self.worklog_memory.is_active(thread_id):
            await update.message.reply_text("No active work log in this topic.")
            return

        # Parse entry number and new text from args
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "Usage: `/edit <number> <new text>`\n\n"
                "Example: `/edit 2 Updated task description`\n"
                "Use `/list` to see entry numbers.",
                parse_mode="Markdown",
            )
            return

        try:
            entry_num = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Please provide a valid entry number.")
            return

        # Get new text (everything after the number)
        new_text = " ".join(context.args[1:])

        # Edit the entry
        old_text = self.worklog_memory.edit_entry(thread_id, entry_num, new_text)
        if old_text is None:
            entry_count = self.worklog_memory.get_entry_count(thread_id)
            if entry_count == 0:
                await update.message.reply_text("No entries to edit.")
            else:
                await update.message.reply_text(
                    f"Invalid entry number. Use 1-{entry_count}."
                )
            return

        # Truncate for display
        old_display = old_text if len(old_text) <= 40 else old_text[:37] + "..."
        new_display = new_text if len(new_text) <= 40 else new_text[:37] + "..."

        await context.bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text=f"Updated entry #{entry_num}:\n"
                 f"Old: {old_display}\n"
                 f"New: {new_display}",
        )

    async def done_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Ask for confirmation before generating work log summary."""
        if not update.message:
            return

        thread_id = update.message.message_thread_id
        chat_id = update.message.chat_id

        if thread_id is None:
            await update.message.reply_text("This command only works inside a topic.")
            return

        if not self.worklog_memory.is_active(thread_id):
            await update.message.reply_text("No active work log in this topic.")
            return

        entries = self.worklog_memory.get_entries(thread_id)
        if not entries:
            await update.message.reply_text("No entries in this work log yet.")
            return

        # Show preview and ask for confirmation
        self.worklog_memory.set_pending_confirmation(thread_id)

        preview = f"Current entries ({len(entries)} total):\n"
        for i, entry in enumerate(entries, 1):
            preview += f"\n{i}. [{entry.format_time()}] {entry.text}"

        preview += "\n\nGenerate summary? Reply 'yes' to confirm or anything else to cancel."

        await context.bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text=preview,
        )

    async def close_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Delete the current work log topic."""
        if not update.message:
            return

        chat_id = update.message.chat_id
        thread_id = update.message.message_thread_id

        if thread_id is None:
            await update.message.reply_text("This command only works inside a topic.")
            return

        # Clean up messages marked for deletion
        msg_ids = self.worklog_memory.get_messages_to_delete(thread_id)
        if msg_ids:
            context.application.create_task(
                self._delete_messages(context.bot, chat_id, msg_ids)
            )

        # End work log session
        self.worklog_memory.end_worklog(thread_id)

        try:
            # Delete the command message
            await context.bot.delete_message(
                chat_id=chat_id, message_id=update.message.message_id
            )
            # Delete the topic
            await context.bot.delete_forum_topic(
                chat_id=chat_id, message_thread_id=thread_id
            )
            logger.info(f"Deleted work log topic {thread_id} in chat {chat_id}")
        except Exception as e:
            logger.error(f"Error deleting topic: {e}")
            await update.message.reply_text(
                "Error: Could not delete topic. Check permissions."
            )

    async def _generate_worklog_summary(
        self, chat_id: int, thread_id: int, context
    ) -> None:
        """Generate and send the work log summary."""
        await context.bot.send_chat_action(
            chat_id=chat_id,
            message_thread_id=thread_id,
            action=ChatAction.TYPING,
        )

        formatted_log = self.worklog_memory.get_formatted_log(thread_id)
        if not formatted_log:
            await context.bot.send_message(
                chat_id=chat_id,
                message_thread_id=thread_id,
                text="No entries to summarize.",
            )
            return

        # Generate summary
        if self.ai_service:
            summary = await asyncio.to_thread(
                self.ai_service.generate_worklog_summary, formatted_log
            )
        else:
            # Fallback without AI
            summary = f"**Work Log Summary**\n\n{formatted_log}"

        # Delete old messages
        msg_ids = self.worklog_memory.get_messages_to_delete(thread_id)
        if msg_ids:
            context.application.create_task(
                self._delete_messages(context.bot, chat_id, msg_ids)
            )

        # Send summary
        await context.bot.send_message(
            chat_id=chat_id,
            message_thread_id=thread_id,
            text=summary,
            parse_mode="Markdown",
        )

        # End the work log session
        self.worklog_memory.end_worklog(thread_id)

    async def _delete_messages(self, bot, chat_id: int, msg_ids: list[int]) -> None:
        """Delete messages in background."""
        for mid in msg_ids:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=mid)
            except Exception:
                pass

