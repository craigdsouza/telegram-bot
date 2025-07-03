"""
User management handlers for the Telegram bot.
Handles user registration, start command, and basic user operations.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from data import db

logger = logging.getLogger(__name__)


async def ensure_user_registered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ensure the user is registered in our database.
    
    Returns:
        dict: User data if registration was successful, None otherwise
    """
    user = update.effective_user
    logger.info(f"Ensuring user is registered: {user.id} - {user.first_name} {user.last_name}")
    
    try:
        # Get or create the user in the database
        db_user = db.get_or_create_user(
            telegram_user_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        if not db_user:
            logger.error(f"Failed to register user {user.id} in database")
            await update.message.reply_text(
                "❌ Sorry, there was an error setting up your account. Please try again."
            )
            return None
            
        logger.info(f"User registered/retrieved: {db_user}")
        return db_user
        
    except Exception as e:
        logger.error(f"Error in ensure_user_registered: {e}")
        await update.message.reply_text(
            "❌ Sorry, there was an error setting up your account. Please try again."
        )
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the command /start is issued."""
    user = update.effective_user
    logger.info(f"Start command received from user {user.id}")
    
    # Ensure user is registered
    db_user = await ensure_user_registered(update, context)
    if not db_user:
        return
    
    welcome_message = (
        f"👋 Welcome, {user.first_name}!\n\n"
        "I'm your personal expense tracker. Here's what you can do:\n"
        "• /add - Add a new expense\n"
        "• /summary - View monthly summary\n"
        "• /help - Show available commands"
    )
    
    await update.message.reply_text(welcome_message)


async def db_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test database connection."""
    try:
        conn = db.get_connection()
        conn.close()
        await update.message.reply_text("✅ Database connection OK")
    except Exception as e:
        await update.message.reply_text(f"❌ DB connection failed: {e}")


async def debug_all(update, context):
    """Debug handler to log all updates."""
    logger.info("📥 GOT UPDATE: %s", update) 