from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from data import db
import re

import logging

logger = logging.getLogger(__name__)

BUDGET_AMOUNT = 200

async def budget_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the budget setting conversation."""
    user = update.effective_user
    user_str = f"User {user.id} ({user.first_name} {user.last_name})"
    logger.info(f"[BUDGET_START] {user_str} - Budget start command received")
    
    # Get current budget if set
    user_db = db.get_user_by_telegram_id(user.id)
    if not user_db:
        await update.message.reply_text("You need to /start the bot first.")
        logger.error(f"[BUDGET_START] {user_str} - Not found in DB")
        return ConversationHandler.END
    
    # Check if user is part of a family
    family_member_ids = db.get_family_members(user_db['id'])
    family_budget = db.get_family_budget(family_member_ids)
    logger.info(f"[BUDGET_START] {user_str} - Family members: {family_member_ids}, Family budget: {family_budget}")
    
    if len(family_member_ids) > 1:
        # Family budget
        if family_budget:
            await update.message.reply_text(
                f"Your family's current monthly budget is ₹{family_budget:,.2f}\n\n"
                "Enter your new family monthly budget amount (e.g., 10000):",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            await update.message.reply_text(
                f"Set your family's monthly budget! ({len(family_member_ids)} members)\n\n"
                "Enter your family monthly budget amount (e.g., 10000):",
                reply_markup=ReplyKeyboardRemove()
            )
    else:
        # Individual budget
        current_budget = user_db.get('budget')
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
    user = update.effective_user
    user_str = f"User {user.id} ({user.first_name} {user.last_name})"
    logger.info(f"[BUDGET_AMOUNT] {user_str} - Budget amount received: {update.message.text}")
    
    amount_str = update.message.text.strip()
    
    # Validate amount format (positive number)
    if not re.match(r"^\d+(\.\d{1,2})?$", amount_str):
        logger.error(f"[BUDGET_AMOUNT] {user_str} - Invalid budget amount format received: {amount_str}")
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
        logger.error(f"[BUDGET_AMOUNT] {user_str} - User not found in database")
        await update.message.reply_text("You need to /start the bot first.")
        return ConversationHandler.END

    # Check if user is part of a family
    family_member_ids = db.get_family_members(db_user['id'])
    
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            if len(family_member_ids) > 1:
                # Set budget for all family members
                cur.execute(
                    "UPDATE users SET budget = %s WHERE id = ANY(%s)",
                    (budget_amount, family_member_ids)
                )
                conn.commit()
                
                await update.message.reply_text(
                    f"✅ Family monthly budget set to ₹{budget_amount:,.2f}!\n\n"
                    f"This budget applies to all {len(family_member_ids)} family members. "
                    "Use /summary to see your family's combined expenses."
                )
                logger.info(f"[BUDGET_AMOUNT] {user_str} - Family budget set to ₹{budget_amount:,.2f} for {len(family_member_ids)} members")
            else:
                # Set individual budget
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
                logger.info(f"[BUDGET_AMOUNT] {user_str} - Budget set to ₹{budget_amount:,.2f} for user {update.effective_user.id}")
    finally:
        conn.close()
    
    return ConversationHandler.END

async def budget_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the budget setting conversation."""
    user = update.effective_user
    user_str = f"User {user.id} ({user.first_name} {user.last_name})"
    logger.info(f"[BUDGET_CANCEL] {user_str} - Budget conversation cancelled")
    await update.message.reply_text(
        "Budget setting cancelled. Your current budget remains unchanged.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def budget_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current budget information."""
    user = update.effective_user
    user_str = f"User {user.id} ({user.first_name} {user.last_name})"
    logger.info(f"[BUDGET_INFO] {user_str} - Budget info requested")
    
    user_db = db.get_user_by_telegram_id(user.id)
    if not user_db:
        await update.message.reply_text("You need to /start the bot first.")
        return
    
    # Get family information
    family_member_ids = db.get_family_members(user_db['id'])
    family_budget = db.get_family_budget(family_member_ids)
    
    if not family_budget:
        if len(family_member_ids) > 1:
            await update.message.reply_text(
                "Your family hasn't set a monthly budget yet.\n\n"
                "Use /budget to set your family's monthly spending limit!"
            )
        else:
            await update.message.reply_text(
                "You haven't set a monthly budget yet.\n\n"
                "Use /budget to set your monthly spending limit!"
            )
        return
    
    # Get current month's expenses
    from datetime import date
    today = date.today()
    
    if len(family_member_ids) > 1:
        # Family expenses
        monthly_expenses = db.get_family_monthly_summary(today.year, today.month, family_member_ids)
        total_spent = sum(amount for category, amount in monthly_expenses if category != 'Transfers')
        
        message = (
            f"💰 **Family Monthly Budget Status**\n\n"
            f"Family Members: {len(family_member_ids)}\n"
            f"Budget: ₹{family_budget:,.2f}\n"
            f"Spent this month: ₹{total_spent:,.2f}\n"
        )
    else:
        # Individual expenses
        monthly_expenses = db.get_monthly_summary(today.year, today.month, user_db['id'])
        total_spent = sum(amount for category, amount in monthly_expenses if category != 'Transfers')
        
        message = (
            f"💰 **Monthly Budget Status**\n\n"
            f"Budget: ₹{family_budget:,.2f}\n"
            f"Spent this month: ₹{total_spent:,.2f}\n"
        )
    
    # Calculate budget status
    budget_percentage = (total_spent / family_budget) * 100
    remaining = family_budget - total_spent
    
    status_emoji = "🟢" if budget_percentage <= 80 else "🟡" if budget_percentage <= 100 else "🔴"
    
    message += (
        f"Remaining: ₹{remaining:,.2f}\n\n"
        f"{status_emoji} {budget_percentage:.1f}% of budget used\n\n"
    )
    
    if budget_percentage > 100:
        message += f"⚠️ Over budget by ₹{abs(remaining):,.2f}"
    elif budget_percentage > 80:
        message += "⚠️ Approaching budget limit"
    else:
        message += "✅ Within budget"
    
    await update.message.reply_text(message) 