import logging
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
import datetime
from collections import defaultdict
from categories import category_emojis, categories
from db import init_db, add_expense, get_monthly_summary

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Define conversation states
AMOUNT, CATEGORY = range(2) 

# /add command handler initiates the expense addition conversation.
async def add_expense_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Please enter the amount for the expense:"
    )
    return AMOUNT

# Handler for receiving the amount.
async def receive_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
    query = update.callback_query
    await query.answer()  # Acknowledge the callback

    category = query.data
    context.user_data['category'] = category

    amount = context.user_data.get('amount')

    # Get today's date as string and determine current month and year
    today = datetime.date.today()
    today_str = today.strftime('%Y-%m-%d')
    current_year = today.year
    current_month = today.month
    
    # Store expense in PostgreSQL
    add_expense(today, amount, category)
    # Fetch monthly summary from DB
    summary_rows = get_monthly_summary(current_year, current_month)
    # Convert to dict for display
    summary = {row['category']: float(row['total']) for row in summary_rows}
    
    # Build a simple text-based table for the summary
    table_lines = []
    header_title = f"Expense Summary for {current_year}/{current_month:02}"
    table_lines.append(header_title)
    table_lines.append("-" * 2 * len(header_title))
    table_lines.append(f"{'Category':<30}{'Total':>10}")
    table_lines.append("-" * 2 * len(header_title))

    for cat, total in summary.items():
        emoji = category_emojis.get(cat, "")
        display_cat = f"{emoji} {cat}".strip()
        table_lines.append(f"{display_cat:<30}{total:>10.2f}")
    table_text = "\n".join(table_lines)
    
    response_text = f"Expense recorded: {amount} units in {category} category.\n\n{table_text}"
    await query.edit_message_text(response_text)
    return ConversationHandler.END

# Cancellation handler in case the user wishes to abort
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Expense addition canceled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    # Load the bot token from environment variables
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("Bot token not found. Please set TELEGRAM_BOT_TOKEN in your environment variables.")
        return

    # Initialize PostgreSQL tables
    init_db()

    application = ApplicationBuilder().token(token).build()

    # Set up the conversation handler with the states AMOUNT and CATEGORY
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add', add_expense_start)],
        states={
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_amount)],
            CATEGORY: [CallbackQueryHandler(receive_category)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(conv_handler)
    logger.info("Bot is running. Waiting for commands...")
    application.run_polling()

if __name__ == '__main__':
    main()
