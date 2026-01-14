"""Main entry point for Facto AI bot."""

import logging
import sys

from telegram import BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from facto.bot.handlers import TelegramBotHandlers
from facto.config import Config
from facto.services.ai_service import AIService
from facto.services.memory import MemoryManager
from facto.tools import ToolRegistry
from facto.tools.implementations import SaveNoteTool, SetReminderTool, WebSearchTool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def setup_tools(memory_manager: MemoryManager) -> ToolRegistry:
    """Initialize and register all available tools."""
    registry = ToolRegistry()

    # Register available tools
    registry.register(WebSearchTool())
    registry.register(SaveNoteTool(memory_manager))
    registry.register(SetReminderTool())

    return registry


async def post_init(application) -> None:
    """Set bot commands after initialization."""
    commands = [
        BotCommand("journal", "Process diary entry with journal formatting"),
        BotCommand("chat", "Start a general chat conversation"),
        BotCommand("done", "Finalize conversation and close topic"),
        BotCommand("delete", "Delete current topic"),
        BotCommand("model", "Switch AI model/provider"),
        BotCommand("mode", "Switch chat mode"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands registered with Telegram")


def main():
    # 1. Load Configuration
    try:
        config = Config.from_env()
        logger.info("Configuration loaded successfully")
        logger.info(f"Active provider: {config.active_provider.value}")
        logger.info(f"Streaming: {'enabled' if config.streaming.enabled else 'disabled'}")
        logger.info(f"Tools: {'enabled' if config.tools.enabled else 'disabled'}")
    except ValueError as e:
        logger.error(f"Configuration Error: {e}")
        sys.exit(1)

    # 2. Initialize Services
    memory_manager = MemoryManager(mongodb_uri=config.mongodb_uri)

    # 3. Setup Tools (if enabled)
    tool_registry = None
    if config.tools.enabled:
        tool_registry = setup_tools(memory_manager)
        logger.info(f"Registered {len(tool_registry)} tools")

    # 4. Initialize AI Service with tools
    ai_service = AIService(config, tool_registry)

    # 5. Initialize Bot Handlers
    handlers = TelegramBotHandlers(ai_service, memory_manager, config)

    # 6. Build Application
    application = (
        Application.builder()
        .token(config.telegram_bot_token)
        .post_init(post_init)
        .build()
    )

    # 7. Register Handlers
    # Core commands
    application.add_handler(CommandHandler("journal", handlers.journal_command))
    application.add_handler(CommandHandler("chat", handlers.chat_command))

    # Topic management
    application.add_handler(CommandHandler("done", handlers.done_command))
    application.add_handler(CommandHandler("delete", handlers.delete_topic))

    # Configuration commands
    application.add_handler(CommandHandler("model", handlers.model_command))
    application.add_handler(CommandHandler("mode", handlers.mode_command))

    # Conversation flow (replies in topics)
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS,
            handlers.handle_conversation_flow,
        )
    )

    # 8. Start Bot
    logger.info("Facto AI Bot starting...")
    logger.info("Commands: /journal, /chat, /done, /delete, /model, /mode")

    application.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
