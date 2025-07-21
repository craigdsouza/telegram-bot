from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from data import db
import re

import logging

logger = logging.getLogger(__name__)

BUDGET_AMOUNT = 200

async def budget_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the budget setting conversation."""
    logger.info(f"Budget start command received from user {update.effective_user.id}")
    
    # Get current budget if set
    user = db.get_user_by_telegram_id(update.effective_user.id)
    if not user:
        await update.message.reply_text("You need to /start the bot first.")
        return ConversationHandler.END
    
    current_budget = user.get('budget')
    if current_budget:
        await update.message.reply_text(
            f"Your current monthly budget is ₹{current_budget:,.2f}\n\n"
            "Enter your new monthly budget amount (e.g., 5000):",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await update.message.reply_text(
            "Set your monthly budget to track your spending!\n\n"
            "Enter your monthly budget amount (e.g., 5000):",
            reply_markup=ReplyKeyboardRemove()
        )
    
    return BUDGET_AMOUNT

async def receive_budget_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive and validate the budget amount."""
    logger.info(f"Budget amount received from user {update.effective_user.id}")
    
    user = update.effective_user
    amount_str = update.message.text.strip()
    
    # Validate amount format (positive number)
    if not re.match(r"^\d+(\.\d{1,2})?$", amount_str):
        logger.error(f"Invalid budget amount format received from user {update.effective_user.id}: {amount_str}")
        await update.message.reply_text(
            "Please enter a valid amount (e.g., 5000 or 5000.50).\n"
            "Only positive numbers are allowed."
        )
        return BUDGET_AMOUNT
    
    try:
        budget_amount = float(amount_str)
        if budget_amount <= 0:
            await update.message.reply_text("Please enter a positive amount greater than 0.")
            return BUDGET_AMOUNT
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return BUDGET_AMOUNT
    
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
                "UPDATE users SET budget = %s WHERE id = %s",
                (budget_amount, db_user['id'])
            )
            conn.commit()
        
        await update.message.reply_text(
            f"✅ Monthly budget set to ₹{budget_amount:,.2f}!\n\n"
            "You can now track your spending against this budget. "
            "Use /summary to see your current month's expenses."
        )
        logger.info(f"Budget set to ₹{budget_amount:,.2f} for user {update.effective_user.id}")
    finally:
        conn.close()
    
    return ConversationHandler.END

async def budget_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the budget setting conversation."""
    logger.info(f"Budget conversation cancelled by user {update.effective_user.id}")
    await update.message.reply_text(
        "Budget setting cancelled. Your current budget remains unchanged.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def budget_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current budget information."""
    logger.info(f"Budget info requested by user {update.effective_user.id}")
    
    user = db.get_user_by_telegram_id(update.effective_user.id)
    if not user:
        await update.message.reply_text("You need to /start the bot first.")
        return
    
    current_budget = user.get('budget')
    if not current_budget:
        await update.message.reply_text(
            "You haven't set a monthly budget yet.\n\n"
            "Use /budget to set your monthly spending limit!"
        )
        return
    
    # Get current month's expenses
    from datetime import date
    today = date.today()
    monthly_expenses = db.get_monthly_summary(today.year, today.month, user['id'])
    total_spent = sum(amount for _, amount in monthly_expenses)
    
    # Calculate budget status
    budget_percentage = (total_spent / current_budget) * 100
    remaining = current_budget - total_spent
    
    status_emoji = "🟢" if budget_percentage <= 80 else "🟡" if budget_percentage <= 100 else "🔴"
    
    message = (
        f"💰 **Monthly Budget Status**\n\n"
        f"Budget: ₹{current_budget:,.2f}\n"
        f"Spent this month: ₹{total_spent:,.2f}\n"
        f"Remaining: ₹{remaining:,.2f}\n\n"
        f"{status_emoji} {budget_percentage:.1f}% of budget used\n\n"
    )
    
    if budget_percentage > 100:
        message += f"⚠️ You're over budget by ₹{abs(remaining):,.2f}"
    elif budget_percentage > 80:
        message += "⚠️ You're approaching your budget limit"
    else:
        message += "✅ You're within your budget"
    
    await update.message.reply_text(message) 