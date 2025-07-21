"""
Conversation handlers for expense tracking.
Handles the /add command flow: amount -> category -> description.
"""

import logging
from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from data.categories import category_emojis, categories
from data import db

logger = logging.getLogger(__name__)

# Define conversation states
AMOUNT, CATEGORY, DESCRIPTION = range(3)


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
        
        # Create category selection keyboard
        keyboard = create_category_keyboard()
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
    
    return await _save_expense_and_show_summary(update, context, description)


async def receive_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle user input for description."""
    user_id = update.effective_user.id
    description = update.message.text.strip()
    logger.info(f"[STATE] DESCRIPTION - User {user_id} entered description: {description}")
    
    if description.lower() == 'none' or not description:
        description = 'None'
        logger.info(f"[PROCESSING] User {user_id} - Using default 'None' description")
    
    return await _save_expense_and_show_summary(update, context, description)


async def _save_expense_and_show_summary(update: Update, context: ContextTypes.DEFAULT_TYPE, description: str) -> int:
    """Common logic for saving expense and showing confirmation only."""
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
    # Send simple confirmation only
    try:
        msg = f"Expense recorded: {amount} units in {category}."
        if hasattr(update, "message") and update.message:
            await update.message.reply_text(msg)
        elif hasattr(update, "callback_query") and update.callback_query:
            await update.callback_query.edit_message_text(msg)
        logger.info(f"[SUCCESS] User {user_id} - Expense recorded successfully")
    except Exception as e:
        logger.exception(f"[ERROR] User {user_id} - Failed to send confirmation message: {e}")
        if hasattr(update, "message") and update.message:
            await update.message.reply_text("❌ Failed to send confirmation message. Try again later.")
        elif hasattr(update, "callback_query") and update.callback_query:
            await update.callback_query.edit_message_text("❌ Failed to send confirmation message. Try again later.")
    finally:
        logger.info(f"[CONV_END] User {user_id} - Conversation completed successfully")
        logger.info(f"[CONTEXT] Final user data: {context.user_data}")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancellation handler in case the user wishes to abort."""
    user_id = update.effective_user.id
    logger.info(f"[CONV_END] User {user_id} - Conversation canceled")
    logger.info(f"[CONTEXT] Final user data: {context.user_data}")
    await update.message.reply_text("Expense addition canceled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def create_category_keyboard():
    """Create inline keyboard for category selection (2 columns)."""
    keyboard = []
    logger.info("Creating category keyboard")
    
    for i in range(0, len(categories), 2):
        row = []
        # Add first category in row
        cat1 = categories[i]
        row.append(InlineKeyboardButton(
            f"{category_emojis.get(cat1, '📝')} {cat1}", 
            callback_data=f"cat_{cat1}"
        ))
        # Add second category in row if it exists
        if i + 1 < len(categories):
            cat2 = categories[i+1]
            row.append(InlineKeyboardButton(
                f"{category_emojis.get(cat2, '📝')} {cat2}", 
                callback_data=f"cat_{cat2}"
            ))
        keyboard.append(row)
        logger.debug(f"Added category row: {[btn.text for btn in row]}")
    
    return keyboard


def build_summary_message(amount, category, description, user_id):
    """Build a formatted summary message for the current month for a specific user."""
    today = date.today()
    rows = db.get_monthly_summary(today.year, today.month, user_id=user_id)
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

    lines = ["```", sep_line, f"{'Category':<{CAT_WIDTH}}{'Total':>{AMT_WIDTH}}", sep_line]

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
    
    # Add budget information if user has set a budget
    try:
        # Get user budget from database using internal user_id
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT budget FROM users WHERE id = %s", (user_id,))
            result = cur.fetchone()
            if result and result[0]:
                budget = float(result[0])
                remaining = budget - grand
                budget_percentage = (grand / budget) * 100
                
                # Add budget section
                lines.append("")  # Empty line for spacing
                lines.append("💰 **Budget Status**")
                lines.append(f"Monthly Budget: ₹{budget:,.2f}")
                lines.append(f"Spent: ₹{grand:,.2f}")
                lines.append(f"Remaining: ₹{remaining:,.2f}")
                
                # Add status indicator
                if budget_percentage > 100:
                    lines.append(f"⚠️ Over budget by ₹{abs(remaining):,.2f} ({budget_percentage:.1f}%)")
                elif budget_percentage > 80:
                    lines.append(f"🟡 {budget_percentage:.1f}% of budget used")
                else:
                    lines.append(f"✅ {budget_percentage:.1f}% of budget used")
        conn.close()
    except Exception as e:
        logger.error(f"[SUMMARY] Error getting budget info: {e}")
        # Continue without budget info if there's an error
    
    return "\n".join(lines)


# Import this function from handlers.user to avoid circular imports
async def ensure_user_registered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ensure the user is registered in our database."""
    from handlers.user import ensure_user_registered as _ensure_user_registered
    return await _ensure_user_registered(update, context) 