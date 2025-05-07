import logging
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

# Define conversation states
AMOUNT, CATEGORY = range(2) 

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
    await query.answer()
    category = query.data
    amount = context.user_data['amount']

    # 1) Record to Postgres
    today = date.today()
    try:
        db.add_expense(today, amount, category)
        logger.info("Inserted expense in Postgres: %s, %s, %s", today, amount, category)
    except Exception as e:
        logger.error("Failed to insert expense in Postgres: %s", e)
        await query.edit_message_text("❌ Failed to save expense in Postgres. Try again later.")
        return ConversationHandler.END

    current_year = today.year
    current_month = today.month


    try:
        rows = db.get_monthly_summary(current_year, current_month)
        table_lines = [header_title,  "─" * len(header_title), f"{'Category':<30}{'Total':>10}", "─" * len(header_title)]
        for cat, total in rows:
            emoji = category_emojis.get(cat, "")
            display_cat = f"{emoji} {cat}".strip()
            table_lines.append(f"{display_cat:<30}{total:>10.2f}")
        table_text = "\n".join(table_lines)
        response_text = f"Expense recorded: {amount} units in {category} category.\n\n{table_text}"
        await query.edit_message_text(response_text)
    except Exception as e:
        logger.error("Failed to get monthly summary: %s", e)
        await query.edit_message_text("❌ Failed to get monthly summary. Try again later.")
        return ConversationHandler.END

    # # 2) (later) load summary via SQL rather than reading CSV
    # # Get today's date as string and determine current month and year
    # today = datetime.date.today()
    # today_str = today.strftime('%Y-%m-%d')
    

    # # Define the file path for the CSV
    # csv_file = "expenses.csv"
    
    # # Check if file exists to decide if header should be written.
    # write_header = not os.path.isfile(csv_file) or os.path.getsize(csv_file) == 0
    
    # # Append the new expense to the CSV file
    # with open(csv_file, mode='a', newline='') as file:
    #     writer = csv.writer(file)
    #     if write_header:
    #         writer.writerow(["Date", "Amount", "Category"])
    #     writer.writerow([today_str, amount, category])
    
    # # Read the CSV file and compute category wise totals for the current month
    # summary = defaultdict(float)
    # with open(csv_file, mode='r', newline='') as file:
    #     reader = csv.DictReader(file)
    #     for row in reader:
    #         try:
    #             row_date = datetime.datetime.strptime(row["Date"], "%Y-%m-%d").date()
    #         except ValueError:
    #             continue
    #         if row_date.year == current_year and row_date.month == current_month:
    #             try:
    #                 summary[row["Category"]] += float(row["Amount"])
    #             except ValueError:
    #                 continue

    # # Build a simple text-based table for the summary
    # table_lines = []
    # header_title = f"Expense Summary for {current_year}/{current_month:02}"
    # table_lines.append(header_title)
    # table_lines.append("-" * 2 * len(header_title))
    # table_lines.append(f"{'Category':<30}{'Total':>10}")
    # table_lines.append("-" * 2 * len(header_title))

    # for cat, total in summary.items():
    #     emoji = category_emojis.get(cat, "")
    #     display_cat = f"{emoji} {cat}".strip()
    #     table_lines.append(f"{display_cat:<30}{total:>10.2f}")
    # table_text = "\n".join(table_lines)
    
    # response_text = f"Expense recorded: {amount} units in {category} category.\n\n{table_text}"
    # await query.edit_message_text(response_text)
    return ConversationHandler.END

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

def main():
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

    # Set up the conversation handler with the states AMOUNT and CATEGORY
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add', add_expense_start)],
        states={
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_amount)],
            CATEGORY: [CallbackQueryHandler(receive_category)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_chat=True
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('dbtest', db_test))
    # group=0 runs before your ConversationHandler
    application.add_handler(MessageHandler(filters.ALL, debug_all), group=0)

    logger.info("Bot is running. Waiting for commands...")
    # Drop pending updates on startup to ignore old messages
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
