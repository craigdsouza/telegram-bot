import logging
import sys, signal
import asyncio
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
    console_handler = logging.StreamHandler() # send logs to console
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

_enable_console_logging()

import db # import db after logging is configured

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
    
async def ensure_user_registered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> dict:
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

# /add command handler initiates the expense addition conversation.
async def add_expense_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Initiate the expense addition conversation."""
    user = update.effective_user
    logger.info(f"[ADD_START] User {user.id} starting expense addition")
    
    # Ensure user is registered
    db_user = await ensure_user_registered(update, context)
    if not db_user:
        logger.error(f"[ADD_START] Failed to register user {user.id}")
        return ConversationHandler.END
        
    # Store user_id in context for later use
    context.user_data['user_id'] = db_user['id']
    logger.info(f"[ADD_START] User {user.id} registered with user_id {db_user['id']}")
    
    try:
        await update.message.reply_text(
            "💰 Enter the amount spent:",
            reply_markup=ReplyKeyboardRemove(),
        )
        logger.info(f"[ADD_START] Prompted user {user.id} for amount")
        return AMOUNT
    except Exception as e:
        logger.error(f"[ADD_START] Error in add_expense_start: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")
        return ConversationHandler.END

# Handler for receiving the amount.
async def receive_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user input for amount."""
    user = update.effective_user
    logger.info(f"[AMOUNT] User {user.id} entered amount: {update.message.text}")
    
    try:
        # Ensure user is registered (in case they bypassed /start)
        if 'user_id' not in context.user_data:
            logger.info(f"[AMOUNT] User {user.id} - No user_id in context, ensuring registration")
            db_user = await ensure_user_registered(update, context)
            if not db_user:
                logger.error(f"[AMOUNT] User {user.id} - Failed to register user")
                return ConversationHandler.END
            context.user_data['user_id'] = db_user['id']
            logger.info(f"[AMOUNT] User {user.id} - Registered with user_id: {db_user['id']}")
        
        # Store the amount in context
        amount_str = update.message.text.strip()
        logger.info(f"[AMOUNT] User {user.id} - Processing amount: {amount_str}")
        
        try:
            amount = float(amount_str)
            logger.info(f"[AMOUNT] User {user.id} - Parsed amount: {amount}")
        except ValueError:
            logger.error(f"[AMOUNT] User {user.id} - Invalid amount format: {amount_str}")
            await update.message.reply_text("❌ Please enter a valid number for the amount (e.g., 100 or 50.50):")
            return AMOUNT
        
        if amount <= 0:
            logger.warning(f"[AMOUNT] User {user.id} - Amount not greater than 0: {amount}")
            await update.message.reply_text("❌ Amount must be greater than 0. Please try again:")
            return AMOUNT
            
        context.user_data['amount'] = amount
        logger.info(f"[AMOUNT] User {user.id} - Stored amount in context: {amount}")
        
        # Create inline keyboard for categories (2 columns)
        keyboard = []
        logger.info(f"[AMOUNT] User {user.id} - Creating category keyboard")
        
        for i in range(0, len(categories), 2):
            row = []
            # Add first category in row
            cat1 = categories[i]
            row.append(InlineKeyboardButton(
                f"{category_emojis.get(cat1, '📝')} {cat1}", 
                callback_data=f"cat_{cat1}"  # Ensure this matches the pattern in the handler
            ))
            # Add second category in row if it exists
            if i + 1 < len(categories):
                cat2 = categories[i+1]
                row.append(InlineKeyboardButton(
                    f"{category_emojis.get(cat2, '📝')} {cat2}", 
                    callback_data=f"cat_{cat2}"  # Ensure this matches the pattern in the handler
                ))
            keyboard.append(row)
            
            logger.debug(f"[AMOUNT] Added category row: {[btn.text for btn in row]}")
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        logger.info(f"[AMOUNT] User {user.id} - Sending category selection")
        await update.message.reply_text(
            f"💸 You spent ₹{amount:.2f}. Select a category:",
            reply_markup=reply_markup,
        )
        
        logger.info(f"[AMOUNT] User {user.id} - Transitioning to CATEGORY state")
        return CATEGORY
        
    except Exception as e:
        logger.error(f"[AMOUNT] Error in receive_amount for user {user.id}: {e}", exc_info=True)
        try:
            await update.message.reply_text(
                "❌ An error occurred while processing the amount. Please try again with /add"
            )
        except Exception as send_error:
            logger.error(f"[AMOUNT] Failed to send error message: {send_error}")
        return ConversationHandler.END

# Callback query handler for the inline keyboard.
async def receive_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the selected category."""
    try:
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        
        # Log the full callback data for debugging
        logger.info(f"[CATEGORY] User {user_id} - Raw callback data: {query.data}")
        
        # Extract category from callback data (remove 'cat_' prefix if present)
        if query.data.startswith('cat_'):
            category = query.data[4:]  # Remove 'cat_' prefix
        else:
            category = query.data
            
        logger.info(f"[CATEGORY] User {user_id} selected category: {category}")
        
        # Store the category in user_data
        context.user_data['category'] = category
        logger.info(f"[CATEGORY] Stored in context: {context.user_data}")
        
        # Create keyboard for description (skip or enter)
        keyboard = [
            [InlineKeyboardButton("Skip description", callback_data="NONE_DESC")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send message with selected category and prompt for description
        await query.edit_message_text(
            f"✅ Category: {category}\n\n✏️ Please enter a description or click 'Skip description':",
            reply_markup=reply_markup
        )
        
        logger.info(f"[CATEGORY] User {user_id} - Prompted for description")
        return DESCRIPTION
        
    except Exception as e:
        logger.error(f"[CATEGORY] Error in receive_category: {e}", exc_info=True)
        try:
            await query.edit_message_text("❌ An error occurred. Please try again with /add")
        except:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ An error occurred. Please try again with /add"
                )
            except:
                pass
        return ConversationHandler.END

async def receive_description_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'None' button click for description."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    description = 'None'
    logger.info(f"[STATE] DESCRIPTION - User {user_id} clicked 'None' for description")
    # proceed as in receive_description
    amount = context.user_data['amount']
    category = context.user_data['category']
    today = date.today()
    # Get the user's primary key from context (set in add_expense_start)
    user_id = context.user_data.get('user_id')
    if not user_id:
        logger.error(f"[ERROR] User {update.effective_user.id} - No user_id in context")
        await update.message.reply_text("❌ Error: User not properly registered. Please try /start again.")
        return ConversationHandler.END
        
    try:
        # Pass the user's primary key to add_expense
        db.add_expense(today, amount, category, description, user_id=user_id)
        logger.info(
            "[DB] Inserted expense in Postgres - User ID: %s, Date: %s, Amount: %s, Category: %s, Description: %s",
            user_id, today, amount, category, description
        )
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
    user_id = update.effective_user.id
    description = update.message.text.strip()
    logger.info(f"[STATE] DESCRIPTION - User {user_id} entered description: {description}")
    
    if description.lower() == 'none' or not description:
        description = 'None'
        logger.info(f"[PROCESSING] User {user_id} - Using default 'None' description")
    amount = context.user_data['amount']
    category = context.user_data['category']
    today = date.today()
    # Get the user's primary key from context (set in add_expense_start)
    user_id = context.user_data.get('user_id')
    if not user_id:
        logger.error(f"[ERROR] User {update.effective_user.id} - No user_id in context")
        await update.message.reply_text("❌ Error: User not properly registered. Please try /start again.")
        return ConversationHandler.END
        
    try:
        # Pass the user's primary key to add_expense
        db.add_expense(today, amount, category, description, user_id=user_id)
        logger.info(
            "[DB] Inserted expense in Postgres - User ID: %s, Date: %s, Amount: %s, Category: %s, Description: %s",
            user_id, today, amount, category, description
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
        logger.info(f"[SUCCESS] User {user_id} - Expense recorded successfully")
    except Exception as e:
        logger.exception(f"[ERROR] User {user_id} - Failed to send summary message: {e}")
        await update.message.reply_text("❌ Failed to send summary message. Try again later.")
    finally:
        logger.info(f"[CONV_END] User {user_id} - Conversation completed successfully")
        logger.info(f"[CONTEXT] Final user data: {context.user_data}")
    return ConversationHandler.END

# Helper to format and send monthly summary
def build_summary_message(amount, category, description):
    """Build a formatted summary message for the current month."""
    today = date.today()
    rows = db.get_monthly_summary(today.year, today.month)
    logger.info(f"[SUMMARY] Raw rows from DB: {rows}")

    # Include zero totals for categories without entries
    logger.info("[SUMMARY] Building totals dictionary")
    totals = {cat: 0.0 for cat in categories}
    for cat_name, total in rows:
        logger.info(f"[SUMMARY] Adding total {total} for category {cat_name}")
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
    logger.info(f"[SUMMARY] Grand total: {grand}")
    lines.append(f"{'Grand Total':<{CAT_WIDTH}}{grand:>{AMT_WIDTH}.0f}")
    lines.append("```")
    return "\n".join(lines)

# Cancellation handler in case the user wishes to abort
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    logger.info(f"[CONV_END] User {user_id} - Conversation canceled")
    logger.info(f"[CONTEXT] Final user data: {context.user_data}")
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

        application.add_handler(conv_handler)
        application.add_handler(CommandHandler('dbtest', db_test))
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('help', start))
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
