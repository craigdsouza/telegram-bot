import logging
import sys, signal
import db
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from dotenv import load_dotenv
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import csv
import datetime
from collections import defaultdict
from categories import category_emojis, categories
from datetime import date

# Enable logging
logging.basicConfig(
    filename='bot.log',
    filemode='a',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Send logs to console as well, so hosted platforms like Railway can capture them
def _enable_console_logging():
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

_enable_console_logging()

# Load environment variables from .env file
load_dotenv()

# start a simple HTTP server for health checks
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Always respond 200 OK
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

def run_health_server():
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    # This will block forever handling health-check requests
    server.serve_forever()

# Define conversation states
AMOUNT, CATEGORY, DESCRIPTION = range(3) 

async def debug_all(update, context):
    logger.info("📥 GOT UPDATE: %s", update)
    
# /add command handler initiates the expense addition conversation.
async def add_expense_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("add_expense_start invoked for chat %s", update.effective_chat.id)
    await update.message.reply_text(
        "Please enter the amount for the expense:"
    )
    return AMOUNT

# Handler for receiving the amount.
async def receive_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user input for amount."""
    text = update.message.text
    try:
        amount = float(text)
    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a numeric value:")
        return AMOUNT
    
    context.user_data['amount'] = amount  # Store the amount temporarily

    keyboard = [
        [InlineKeyboardButton(f"{category_emojis.get(cat, '')} {cat}", callback_data=cat) for cat in categories[i:i+3]]
        for i in range(0, len(categories), 3)
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Select a category for your expense:",
        reply_markup=reply_markup
    )
    return CATEGORY

# Callback query handler for the inline keyboard.
async def receive_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the selected category."""
    query = update.callback_query
    await query.answer()
    category = query.data
    context.user_data['category'] = category
    # Prompt for description or allow skipping via button
    keyboard = [[InlineKeyboardButton("None", callback_data="NONE_DESC")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"Category selected: {category}.\nPlease enter a description or click 'None' to skip.",
        reply_markup=reply_markup
    )
    return DESCRIPTION

async def receive_description_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'None' button click for description."""
    query = update.callback_query
    await query.answer()
    description = 'None'
    # proceed as in receive_description
    amount = context.user_data['amount']
    category = context.user_data['category']
    today = date.today()
    try:
        db.add_expense(today, amount, category, description)
        logger.info("Inserted expense with no description: %s, %s, %s", today, amount, category)
    except Exception as e:
        logger.error("Failed to insert expense in Postgres: %s", e)
        await query.edit_message_text("❌ Failed to save expense. Try again later.")
        return ConversationHandler.END
    # Send summary
    try:
        msg = build_summary_message(amount, category, description)
        await query.edit_message_text(msg)
    except Exception as e:
        logger.exception("Failed to send summary message: %s", e)
        await query.edit_message_text("❌ Failed to send summary message. Try again later.")
    return ConversationHandler.END

async def receive_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle user input for description."""
    description = update.message.text.strip()
    if description.lower() == 'none' or not description:
        description = 'None'
    amount = context.user_data['amount']
    category = context.user_data['category']
    today = date.today()
    try:
        db.add_expense(today, amount, category, description)
        logger.info(
            "Inserted expense in Postgres: %s, %s, %s, %s",
            today, amount, category, description
        )
    except Exception as e:
        logger.error("Failed to insert expense in Postgres: %s", e)
        await update.message.reply_text(
            "❌ Failed to save expense in Postgres. Try again later."
        )
        return ConversationHandler.END
    # Send summary
    try:
        msg = build_summary_message(amount, category, description)
        await update.message.reply_text(msg)
    except Exception as e:
        logger.exception("Failed to send summary message: %s", e)
        await query.edit_message_text("❌ Failed to send summary message. Try again later.")
    return ConversationHandler.END

# Helper to format and send monthly summary
def build_summary_message(amount, category, description):
    """Build a formatted summary message for the current month."""
    today = date.today()
    rows = db.get_monthly_summary(today.year, today.month)

    # Include zero totals for categories without entries
    totals = {cat: 0.0 for cat in categories}
    for cat_name, total in rows:
        totals[cat_name] = float(total)

    # Column widths
    CAT_WIDTH   = 18   # 15-char name + emoji + space + padding
    AMT_WIDTH   = 10
    TOTAL_WIDTH = CAT_WIDTH + AMT_WIDTH

    # ASCII separator
    sep_line = "-" * TOTAL_WIDTH

    header = f"Expense recorded: {amount} units in {category} ({description}).\n\nSummary for {today.year}/{today.month:02}"
    
    lines = ["```", header, sep_line, f"{'Category':<{CAT_WIDTH}}{'Total':>{AMT_WIDTH}}", sep_line]

    # Sort categories by descending expense
    sorted_items = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    for cat_name, total in sorted_items:
        emoji = category_emojis.get(cat_name, "")
        display = f"{emoji} {cat_name}".strip()
        lines.append(f"{display:<{CAT_WIDTH}}{total:>{AMT_WIDTH}.0f}")
    
    lines.append(sep_line)
    grand = sum(totals.values())
    lines.append(f"{'Grand Total':<{CAT_WIDTH}}{grand:>{AMT_WIDTH}.0f}")
    lines.append("```")
    return "\n".join(lines)

# Cancellation handler in case the user wishes to abort
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Expense addition canceled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def db_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        conn = db.get_connection()
        conn.close()
        await update.message.reply_text("✅ Database connection OK")
    except Exception as e:
        await update.message.reply_text(f"❌ DB connection failed: {e}")


def _handle_sigterm(signum, frame):
    logger.info("SIGTERM received—shutting down")
    sys.exit(0)

signal.signal(signal.SIGTERM, _handle_sigterm)

def main():
    try:
        # Start the health check server in a separate thread
        threading.Thread(target=run_health_server, daemon=True).start()
        logger.info("Health check server started.")
        
        # Load the bot token from environment variables
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            logger.error("Bot token not found. Please set TELEGRAM_BOT_TOKEN in your environment variables.")
            return

        # Build application
        application = ApplicationBuilder()\
            .token(token)\
            .build()

        # Initialize your table on startup
        try:
            db.init_db()
            logger.info("Database initialized")
        except Exception as e:
            logger.error("DB init failed: %s", e)

        # Set up the conversation handler with the states AMOUNT, CATEGORY, DESCRIPTION
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('add', add_expense_start)],
            states={
                AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_amount)],
                CATEGORY: [CallbackQueryHandler(receive_category)],
                DESCRIPTION: [
                    CallbackQueryHandler(receive_description_button, pattern="^NONE_DESC$"),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, receive_description)
                ]
            },
            fallbacks=[CommandHandler('cancel', cancel)],
            per_chat=True
        )

        application.add_handler(conv_handler)
        application.add_handler(CommandHandler('dbtest', db_test))
        # Log all updates after handlers, for debugging
        application.add_handler(MessageHandler(filters.ALL, debug_all), group=1)

        logger.info("Bot is running. Waiting for commands...")
        application.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.error("An error occurred in main: %s", e)
        sys.exit(1)
    finally:
        # Close the database connection if it was opened
        try:
            db.close_connection()
            logger.info("Database connection closed.")
        except Exception as e:
            logger.error("Failed to close database connection: %s", e)
        logger.info("Bot shutting down.")

if __name__ == '__main__':
    main()
