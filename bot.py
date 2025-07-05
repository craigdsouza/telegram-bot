"""
Telegram Expense Tracker Bot - Main Entry Point

A privacy-focused expense tracking bot that helps users record and categorize their expenses
through a simple Telegram interface with PostgreSQL backend and Google Sheets integration.
"""

import sys
import asyncio
import signal
import os
from dotenv import load_dotenv
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)
import logging

# Import our modular components
from utils.logging_config import setup_logging
from utils.health_server import start_health_server
from handlers.user import start, db_test, debug_all, summary, app
from handlers.conversation import (
    add_expense_start,
    receive_amount,
    receive_category,
    receive_description_button,
    receive_description,
    cancel,
    AMOUNT,
    CATEGORY,
    DESCRIPTION
)
from data import db
from handlers.reminder import reminder_start, receive_reminder_time, cancel as reminder_cancel, REMINDER_TIME

# Set up logging
logger = setup_logging()
logger.info("\n")
logger.info("Logging initialized")
logger.info("\n")

# Load environment variables
load_dotenv()

logging.getLogger("httpx").setLevel(logging.WARNING)

def _handle_sigterm(signum, frame):
    """Handle SIGTERM signal for graceful shutdown."""
    logger.info("SIGTERM received—shutting down")
    sys.exit(0)


def create_add_expense_conversation_handler():
    """Create and configure the conversation handler for expense addition."""
    return ConversationHandler(
        entry_points=[
            CommandHandler('add', add_expense_start),
            # Also allow /add to be used as a text command
            MessageHandler(filters.Regex(r'^/add(?:@\w+)?$'), add_expense_start)
        ],
        states={
            AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_amount)
            ],
            CATEGORY: [
                # Handle category selection (callback_data starts with 'cat_')
                CallbackQueryHandler(receive_category, pattern=r'^cat_'),
                # Handle skip description button
                CallbackQueryHandler(receive_description_button, pattern='^NONE_DESC$')
            ],
            DESCRIPTION: [
                # Handle skip description button (in case user goes back)
                CallbackQueryHandler(receive_description_button, pattern='^NONE_DESC$'),
                # Handle text input for description
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_description)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            # Also handle /cancel as a message
            MessageHandler(filters.Regex(r'^/cancel(?:@\w+)?$'), cancel)
        ],
        # Allow the conversation to continue in different chats
        per_chat=True,
        # Allow the conversation to be continued in a group (in case the bot is added to a group)
        per_user=True,
        # Don't allow overlapping conversations
        per_message=False
    )

def create_reminder_conversation_handler():
    """Create and configure the conversation handler for reminder setup."""
    return ConversationHandler(
        entry_points=[CommandHandler('reminder', reminder_start)],
        states={
            REMINDER_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_reminder_time)],
        },
        fallbacks=[CommandHandler('cancel', reminder_cancel)],
        per_chat=True,
        per_user=True,
        per_message=False,
    )
    

def setup_handlers(application):
    """Set up all bot handlers."""
    # Add conversation handler for expense addition
    add_expense_conv_handler = create_add_expense_conversation_handler()
    application.add_handler(add_expense_conv_handler)
    
    # Add reminder conversation handler
    reminder_conv_handler = create_reminder_conversation_handler()
    application.add_handler(reminder_conv_handler)
    
    # Add basic command handlers
    application.add_handler(CommandHandler('dbtest', db_test))
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', start))
    application.add_handler(CommandHandler('summary', summary))
    application.add_handler(CommandHandler('app', app))
    
    # Log all updates after handlers, for debugging
    application.add_handler(MessageHandler(filters.ALL, debug_all), group=1)


def initialize_database():
    """Initialize the database and handle any setup errors."""
    try:
        logger.info("Initializing database...")
        db.init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Database initialization failed: %s", e)
        raise


def main():
    """Main application entry point."""
    logger.info("Starting bot...")
    try:
        # Start the health check server
        start_health_server()

        # Load and validate bot token
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            logger.error("Bot token not found. Please set TELEGRAM_BOT_TOKEN in your environment variables.")
            return

        # Initialize database
        initialize_database()
        logger.info("Database initialized")

        # Fetch and print bot info before polling
        async def print_bot_info(application):
            bot_info = await application.bot.get_me()
            logger.info(f"Bot is running: {bot_info.first_name} (@{bot_info.username})")
            print(f"Bot is running: {bot_info.first_name} (@{bot_info.username})")

        # Build application
        application = ApplicationBuilder().token(token).post_init(print_bot_info).build()
        logger.info("Application built")

        # Set up handlers
        setup_handlers(application)
        logger.info("Handlers set up")

        logger.info("Bot is running. Waiting for commands...")
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error("An error occurred in main: %s", e)
        sys.exit(1)
    finally:
        # Clean up resources
        try:
            db.close_connection()
            logger.info("Database connection closed.")
        except Exception as e:
            logger.error("Failed to close database connection: %s", e)
        logger.info("Bot shutting down.")


if __name__ == '__main__':
    # Set up signal handlers
    signal.signal(signal.SIGTERM, _handle_sigterm)
    
    # Start the application
    main() 