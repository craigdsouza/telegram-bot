from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from data import db
import re

import logging

logger = logging.getLogger(__name__)

REMINDER_TIME = 100

async def reminder_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f"Reminder start command received from user {update.effective_user.id}")
    await update.message.reply_text(
        "What time would you like to receive your daily reminder? (e.g., 21:00 for 9pm)",
        reply_markup=ReplyKeyboardRemove()
    )
    return REMINDER_TIME

async def receive_reminder_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f"Reminder time received from user {update.effective_user.id}")
    user = update.effective_user
    time_str = update.message.text.strip()
    # Validate time format (HH:MM, 24-hour)
    if not re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", time_str):
        logger.error(f"Invalid time format received from user {update.effective_user.id}: {time_str}")
        await update.message.reply_text("Please enter a valid time in HH:MM format (e.g., 21:00 for 9pm).")
        return REMINDER_TIME

    # Store in database
    db_user = db.get_user_by_telegram_id(user.id)
    if not db_user:
        logger.error(f"User {update.effective_user.id} not found in database")
        await update.message.reply_text("You need to /start the bot first.")
        return ConversationHandler.END

    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET reminder_time = %s WHERE id = %s",
                (time_str, db_user['id'])
            )
            conn.commit()
        await update.message.reply_text(f"✅ Reminder set for {time_str} daily!")
        logger.info(f"Reminder set for {time_str} daily for user {update.effective_user.id}")
    finally:
        conn.close()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Reminder setup cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END 