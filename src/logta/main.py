"""Main entry point for the Telegram Message Logger Bot.

This bot logs all messages from groups to MongoDB, preserving them
even if users delete the messages from Telegram.

IMPORTANT: You must disable "Group Privacy" mode in @BotFather settings
for this bot to receive all messages in groups.
"""

import logging
import sys

from telegram import BotCommand, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    TypeHandler,
    filters,
)

from logta.config import LoggerConfig
from logta.handlers import MessageLoggerHandlers
from logta.services.mongodb_service import MongoDBService
from logta.services.ai_service import AIService

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def log_all_updates(update: Update, context):
    """Debug handler to log all updates."""
    if update.message:
        logger.info(f"DEBUG: Received message: {update.message.text or '[Non-text msg]'} from {update.message.from_user.first_name}")
    else:
        logger.info(f"DEBUG: Received update: {update}")


async def post_init(application) -> None:
    """Set bot commands after initialization."""
    commands = [
        BotCommand("worklog", "Start a work log with custom title"),
        BotCommand("list", "Show all entries in current work log"),
        BotCommand("edit", "Edit an entry by number"),
        BotCommand("remove", "Remove an entry by number"),
        BotCommand("done", "Generate work log summary (with confirmation)"),
        BotCommand("close", "Delete the current topic"),
        BotCommand("stats", "Show message and event statistics"),
        BotCommand("topic", "Create a forum topic with AI-generated title"),
        BotCommand("history", "Get conversation history for current topic"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands registered with Telegram")


def main() -> None:
    """Initialize and run the message logger bot."""
    # Load configuration
    try:
        config = LoggerConfig.from_env()
        logger.info("Configuration loaded successfully")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Initialize MongoDB service
    try:
        mongodb_service = MongoDBService(
            uri=config.mongodb_uri,
            database_name=config.database_name,
        )
        logger.info(
            f"Connected to MongoDB: {config.database_name} (messages + events collections)"
        )
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        sys.exit(1)

    # Initialize AI service (optional)
    ai_service = None
    if config.openai_api_key:
        ai_service = AIService(
            api_key=config.openai_api_key,
            base_url=config.openai_base_url,
            model_name=config.model_name,
        )
        logger.info(f"AI service initialized with model: {config.model_name}")
    else:
        logger.info("AI service not configured (OPENAI_API_KEY not set)")

    # Initialize handlers
    handlers = MessageLoggerHandlers(
        mongodb_service,
        owner_id=config.owner_id,
        ai_service=ai_service,
    )

    # Build the Telegram application
    application = (
        ApplicationBuilder()
        .token(config.telegram_token)
        .post_init(post_init)
        .build()
    )

    # Debug: Log all updates
    application.add_handler(TypeHandler(Update, log_all_updates), group=-1)

    # Register handlers

    # Command handlers (group=0, processed first)
    # Work log commands
    application.add_handler(
        CommandHandler("worklog", handlers.worklog_command)
    )
    application.add_handler(
        CommandHandler("list", handlers.list_command)
    )
    application.add_handler(
        CommandHandler("edit", handlers.edit_command)
    )
    application.add_handler(
        CommandHandler("remove", handlers.remove_command)
    )
    application.add_handler(
        CommandHandler("done", handlers.done_command)
    )
    application.add_handler(
        CommandHandler("close", handlers.close_command)
    )
    # Existing commands
    application.add_handler(
        CommandHandler("stats", handlers.stats_command)
    )
    application.add_handler(
        CommandHandler("topic", handlers.topic_command)
    )
    application.add_handler(
        CommandHandler("history", handlers.history_command)
    )

    # Work log message handler (group=0.5, processed after commands but before logging)
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS,
            handlers.handle_worklog_message,
        ),
    )

    # Message logging handlers (group=1, processed after commands)
    # This ensures commands are handled first, then logged
    application.add_handler(
        MessageHandler(
            filters.UpdateType.MESSAGE,
            handlers.log_message,
        ),
        group=1,
    )
    application.add_handler(
        MessageHandler(
            filters.UpdateType.EDITED_MESSAGE,
            handlers.log_edited_message,
        ),
        group=1,
    )
    application.add_handler(
        MessageHandler(
            filters.UpdateType.CHANNEL_POST,
            handlers.log_channel_post,
        ),
        group=1,
    )

    # Start the bot
    logger.info("Message Logger Bot starting...")
    logger.info(
        "REMINDER: Make sure 'Group Privacy' is DISABLED in @BotFather settings!"
    )

    try:
        application.run_polling(allowed_updates=["message", "edited_message", "channel_post"])
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        mongodb_service.close()


if __name__ == "__main__":
    main()
