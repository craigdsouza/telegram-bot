"""
User management handlers for the Telegram bot.
Handles user registration, start command, and basic user operations.
"""

import logging
import os
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes
from data import db
from handlers.conversation import build_summary_message
from datetime import date

logger = logging.getLogger(__name__)


async def ensure_user_registered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ensure the user is registered in our database.
    
    Returns:
        dict: User data if registration was successful, None otherwise
    """
    user = update.effective_user
    user_str = f"User {user.id} ({user.first_name} {user.last_name})"
    logger.info(f"[REGISTER] {user_str} - Ensuring user is registered")
    
    try:
        # Get or create the user in the database
        db_user = db.get_or_create_user(
            telegram_user_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        if not db_user:
            logger.error(f"[REGISTER] {user_str} - Failed to register in database")
            await update.message.reply_text(
                "❌ Sorry, there was an error setting up your account. Please try again."
            )
            return None
            
        logger.info(f"[REGISTER] {user_str} - Registered/retrieved: {db_user}")
        return db_user
        
    except Exception as e:
        logger.error(f"[REGISTER] {user_str} - Error: {e}")
        await update.message.reply_text(
            "❌ Sorry, there was an error setting up your account. Please try again."
        )
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the command /start is issued."""
    user = update.effective_user
    user_str = f"User {user.id} ({user.first_name} {user.last_name})"
    logger.info(f"[START] {user_str} - Start command received")
    
    # Ensure user is registered
    db_user = await ensure_user_registered(update, context)
    if not db_user:
        return
    
    welcome_message = (
        f"👋 Welcome, {user.first_name}!\n\n"
        "I'm your personal expense tracker. Here's what you can do:\n"
        "• /add - Add a new expense\n"
        "• /summary - View summary of current month’s expenses and budget status\n"
        "• /budget - Set monthly budget\n"
        "• /reminder - set a time for daily reminder, (e.g. 21:00 for 9p.m.)\n"
        "• /cancel - exit current conversation"
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
    user = update.effective_user
    user_str = f"User {user.id} ({user.first_name} {user.last_name})"
    logger.info(f"[DEBUG_ALL] {user_str} - Update: %s", update)


async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the monthly summary to the user."""
    today = date.today()
    user = update.effective_user
    user_str = f"User {user.id} ({user.first_name} {user.last_name})"
    # Try to get the user's database ID
    db_user = db.get_user_by_telegram_id(user.id)  # pass telegram_user_id to get local user_id
    if not db_user:
        # Register the user if not found
        from handlers.user import ensure_user_registered
        db_user = await ensure_user_registered(update, context)
        if not db_user:
            # Registration failed, abort
            logger.error(f"[SUMMARY] {user_str} - Failed to register in database")
            return
    user_id = db_user['id']
    logger.info(f"[SUMMARY] {user_str} - Generating summary for internal user_id {user_id}")
    msg = build_summary_message(amount=0, category='', description='', user_id=user_id)
    if hasattr(update, "message") and update.message:
        await update.message.reply_text(msg)
    elif hasattr(update, "callback_query") and update.callback_query:
        await update.callback_query.edit_message_text(msg)


async def app(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a button to open the Telegram Mini App."""
    user = update.effective_user
    user_str = f"User {user.id} ({user.first_name} {user.last_name})"
    logger.info(f"[APP] {user_str} - /app command received")
    mini_app_url = os.environ.get("MINI_APP_URL", "https://telegram-mini-app-production-8aae.up.railway.app/")

    # Create a keyboard with a Web App button
    keyboard = [
        [KeyboardButton(text="Open Expense Mini App", web_app=WebAppInfo(url=mini_app_url))]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text(
        "Click the button below to open the Expense Mini App:",
        reply_markup=reply_markup
    ) 