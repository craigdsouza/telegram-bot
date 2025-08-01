from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from data import db
import re

import logging

logger = logging.getLogger(__name__)

REMINDER_TIME = 100

async def reminder_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f"[REMINDER_SETUP] User {update.effective_user.id} - Starting reminder setup")
    await update.message.reply_text(
        "What time would you like to receive your daily reminder? (e.g., 21:00 for 9pm)",
        reply_markup=ReplyKeyboardRemove()
    )
    return REMINDER_TIME

async def receive_reminder_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f"[REMINDER_SETUP] User {update.effective_user.id} - Received time input")
    user = update.effective_user
    time_str = update.message.text.strip()
    # Validate time format (HH:MM, 24-hour)
    if not re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", time_str):
        logger.error(f"[REMINDER_SETUP] User {update.effective_user.id} - Invalid time format: {time_str}")
        await update.message.reply_text("Please enter a valid time in HH:MM format (e.g., 21:00 for 9pm).")
        return REMINDER_TIME

    # Store in database
    db_user = db.get_user_by_telegram_id(user.id)
    if not db_user:
        logger.error(f"[REMINDER_SETUP] User {update.effective_user.id} - User not found in database")
        await update.message.reply_text("You need to /start the bot first.")
        return ConversationHandler.END

    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET reminder_time = %s, reminder_timezone = %s WHERE id = %s",
                (time_str, "+05:30", db_user['id'])
            )
            conn.commit()
        
        # Clear the user from reminder cache so it gets re-scheduled on next hourly check
        try:
            from scripts.reminder_scheduler import cleanup_cache_for_user
            cleanup_cache_for_user(user.id)
            logger.info(f"[REMINDER_SETUP] User {user.id} - Cache cleared for re-scheduling")
        except Exception as e:
            logger.warning(f"[REMINDER_SETUP] User {user.id} - Failed to clear cache: {e}")
        
        await update.message.reply_text(f"✅ Reminder set for {time_str} daily (IST)!")
        logger.info(f"[REMINDER_SETUP] User {update.effective_user.id} - Reminder set for {time_str} daily (Asia/Kolkata)")
    finally:
        conn.close()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f"[REMINDER_SETUP] User {update.effective_user.id} - Setup cancelled")
    await update.message.reply_text("Reminder setup cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END 