"""Telegram streaming handler for progressive message updates."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from telegram import Bot
from telegram.error import BadRequest, RetryAfter

logger = logging.getLogger(__name__)


class TelegramStreamingHandler:
    """Handles streaming AI responses to Telegram with rate limiting."""

    def __init__(
        self,
        bot: Bot,
        chat_id: int,
        thread_id: Optional[int] = None,
        update_interval_ms: int = 500,
        min_chars_per_update: int = 50,
    ):
        self.bot = bot
        self.chat_id = chat_id
        self.thread_id = thread_id
        self.update_interval_ms = update_interval_ms
        self.min_chars_per_update = min_chars_per_update

        self.message_id: Optional[int] = None
        self.accumulated_text = ""
        self.last_update_time: float = 0
        self.last_sent_length = 0

    async def start(self, initial_text: str = "...") -> int:
        """Send initial message and return message ID."""
        msg = await self.bot.send_message(
            chat_id=self.chat_id,
            message_thread_id=self.thread_id,
            text=initial_text,
        )
        self.message_id = msg.message_id
        self.last_update_time = time.time() * 1000
        return self.message_id

    async def append(self, text: str) -> None:
        """Append text to the accumulated response."""
        self.accumulated_text += text
        await self._maybe_update()

    async def _maybe_update(self) -> None:
        """Update the Telegram message if conditions are met."""
        if self.message_id is None:
            return

        current_time = time.time() * 1000
        time_since_update = current_time - self.last_update_time
        chars_since_update = len(self.accumulated_text) - self.last_sent_length

        # Update if enough time has passed AND enough new content
        should_update = (
            time_since_update >= self.update_interval_ms
            and chars_since_update >= self.min_chars_per_update
        )

        if should_update:
            await self._update_message()

    async def _update_message(self, is_final: bool = False) -> None:
        """Actually update the Telegram message."""
        if not self.accumulated_text or self.message_id is None:
            return

        # Add typing indicator if not final
        display_text = self.accumulated_text
        if not is_final:
            display_text = self.accumulated_text + " ..."

        try:
            await self.bot.edit_message_text(
                chat_id=self.chat_id,
                message_id=self.message_id,
                text=display_text,
            )
            self.last_sent_length = len(self.accumulated_text)
            self.last_update_time = time.time() * 1000

        except RetryAfter as e:
            # Telegram rate limit - wait and retry
            logger.warning(f"Rate limited, waiting {e.retry_after}s")
            await asyncio.sleep(e.retry_after)
            await self._update_message(is_final)

        except BadRequest as e:
            error_msg = str(e).lower()
            if "message is not modified" in error_msg:
                # Content unchanged, ignore
                pass
            elif "message to edit not found" in error_msg:
                # Message was deleted, ignore
                logger.warning("Message to edit not found")
            else:
                logger.error(f"Failed to update message: {e}")

    async def finalize(self, parse_mode: Optional[str] = "Markdown") -> None:
        """Send final update with complete text."""
        if self.message_id is None:
            return

        if not self.accumulated_text:
            self.accumulated_text = "No response generated."

        try:
            await self.bot.edit_message_text(
                chat_id=self.chat_id,
                message_id=self.message_id,
                text=self.accumulated_text,
                parse_mode=parse_mode,
            )
        except BadRequest as e:
            # Fallback without parse mode if markdown fails
            if "can't parse" in str(e).lower():
                try:
                    await self.bot.edit_message_text(
                        chat_id=self.chat_id,
                        message_id=self.message_id,
                        text=self.accumulated_text,
                    )
                except Exception as e2:
                    logger.error(f"Failed to finalize message (plain): {e2}")
            else:
                logger.error(f"Failed to finalize message: {e}")

    def get_text(self) -> str:
        """Get the accumulated text."""
        return self.accumulated_text

    def reset(self) -> None:
        """Reset the handler state for reuse."""
        self.message_id = None
        self.accumulated_text = ""
        self.last_update_time = 0
        self.last_sent_length = 0
