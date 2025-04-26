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
import csv
import datetime

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

    # Build an inline keyboard for category selection.
    keyboard = [
        [InlineKeyboardButton("Food", callback_data='Food'),
         InlineKeyboardButton("Transport", callback_data='Transport')],
        [InlineKeyboardButton("Entertainment", callback_data='Entertainment'),
         InlineKeyboardButton("Other", callback_data='Other')]
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

    # Get today's date
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    
    # Define the file path for the CSV
    csv_file = "expenses.csv"
    
    # Check if file exists to decide if header should be written.
    write_header = not os.path.isfile(csv_file) or os.path.getsize(csv_file) == 0
    
    with open(csv_file, mode='a', newline='') as file:
        writer = csv.writer(file)
        if write_header:
            writer.writerow(["Date", "Amount", "Category"])
        writer.writerow([today_str, amount, category])

    response_text = f"Expense recorded: {amount} units in {category} category."
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
