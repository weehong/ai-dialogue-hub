"""Main entry point for WorkLog AI bot."""

import logging
import sys

from telegram import BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from worklog.config import Config
from worklog.handlers import WorkLogHandlers
from worklog.services.ai_service import AIService
from worklog.services.mongodb_service import MongoDBService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def post_init(application) -> None:
    """Set bot commands after initialization."""
    commands = [
        BotCommand("start", "Show welcome message and usage"),
        BotCommand("undo", "Delete your last log entry"),
        BotCommand("delete", "Alias for /undo"),
        BotCommand("close", "Generate summary and close today's log"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands registered with Telegram")


def main():
    """Initialize and run the WorkLog AI bot."""
    # 1. Load Configuration
    try:
        config = Config.from_env()
        logger.info("Configuration loaded successfully")
        logger.info(f"Timezone: {config.user_timezone}")
        logger.info(f"Allowed user: {config.allowed_user_id}")
        logger.info(f"Database: {config.mongodb_database}")
    except ValueError as e:
        logger.error(f"Configuration Error: {e}")
        sys.exit(1)

    # 2. Initialize MongoDB Service
    try:
        mongodb_service = MongoDBService(
            uri=config.mongodb_uri,
            database_name=config.mongodb_database,
        )
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        sys.exit(1)

    # 3. Initialize AI Service
    ai_service = AIService(
        deepseek_api_key=config.deepseek_api_key,
        deepseek_base_url=config.deepseek_base_url,
        deepseek_model=config.deepseek_model,
        openai_api_key=config.openai_api_key,
    )

    if not config.deepseek_api_key:
        logger.warning("DeepSeek API key not set - summarization disabled")
    if not config.openai_api_key:
        logger.warning("OpenAI API key not set - voice transcription disabled")

    # 4. Initialize Handlers
    handlers = WorkLogHandlers(config, mongodb_service, ai_service)

    # 5. Build Application
    application = (
        Application.builder()
        .token(config.telegram_bot_token)
        .post_init(post_init)
        .build()
    )

    # 6. Register Handlers
    application.add_handler(CommandHandler("start", handlers.start_command))
    application.add_handler(CommandHandler("undo", handlers.undo_command))
    application.add_handler(CommandHandler("delete", handlers.undo_command))  # alias
    application.add_handler(CommandHandler("close", handlers.close_command))

    # Message handlers for text and voice
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handlers.handle_message,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.VOICE,
            handlers.handle_message,
        )
    )

    # 7. Start Bot
    logger.info("WorkLog AI Bot starting...")
    logger.info("Commands: /start, /undo, /delete, /close")

    try:
        application.run_polling(allowed_updates=["message"])
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        mongodb_service.close()


if __name__ == "__main__":
    main()
