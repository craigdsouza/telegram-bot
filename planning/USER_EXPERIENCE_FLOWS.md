# Telegram Expense Bot - User Experience Flows

## Current Implementation (as of 3rd July, 2025)

### 1. First-Time User Flow

```
👤 User starts bot for the first time
└─ 🤖 "👋 Welcome, [Name]!"
   └─ "I'm your personal expense tracker. Here's what you can do:"
      └─ "• /add - Add a new expense"
         └─ "• /summary - View monthly summary"
            └─ "• /help - Show available commands"
               └─ *User is automatically registered in database*
```

### 2. Adding an Expense Flow

```
👤 User types /add
└─ 💰 "Enter the amount spent:"
   └─ *User enters amount (e.g., "50.25")*
      └─ 💸 "You spent ₹50.25. Select a category:"
         └─ *Shows inline keyboard with 23 categories*
            └─ *User selects category (e.g., "🍱 Ordering in")*
               └─ ✅ "Category: Ordering in"
                  └─ "✏️ Please enter a description or click 'Skip description':"
                     └─ *User enters description or clicks skip*
                        └─ 💾 *Saves to PostgreSQL database*
                           └─ ✅ *Shows monthly summary with all categories*
```

### 3. Monthly Summary Display

```
📊 *After adding expense, shows:*
└─ "Expense recorded: 50.25 units in Ordering in (Lunch)."

   └─ "Summary for 2025/01"
      └─ "────────────────────────────────"
         └─ "Category              Total"
            └─ "────────────────────────────────"
               └─ "🍱 Ordering in        50"
                  └─ "🛒 Groceries        200"
                  └─ "🚌 Transport        150"
                  └─ "💡 Utilities        100"
                  └─ "❓ Other              0"
                  └─ "────────────────────────────────"
                     └─ "Grand Total        500"
```

### 4. Available Commands

```
👤 User types /help
└─ 📚 *Available Commands:*
   ├─ /add - Add a new expense
   ├─ /summary - View monthly summary (not implemented yet)
   ├─ /help - Show this help
   ├─ /start - Welcome message
   ├─ /cancel - Cancel current conversation
   └─ /dbtest - Test database connection
```

### 5. Category Selection

The bot offers 23 predefined categories with emojis:
- 🛒 Groceries
- 🍱 Ordering in
- 🍴 Eating out
- 🚌 Transport
- 🏠 Household items
- 💡 Utilities
- 💊 Health
- 🏗️ Capex
- 🎁 Gifts
- 👗 Clothes
- 🛁 Self care
- 🎬 Entertainment
- ✈️ Trips
- 💍 Wedding
- 📚 Learning
- ❓ Other
- 🏆 Memberships
- 💳 Card fees
- 🔄 Transfers
- 🧪 Test
- 🏠 Rent
- 💼 Work
- 💰 Investments

### 6. Error Handling

```
❌ *Common error scenarios:*
├─ Invalid amount format
│  └─ "Please enter a valid number for the amount (e.g., 100 or 50.50):"
├─ Amount <= 0
│  └─ "Amount must be greater than 0. Please try again:"
├─ Database connection issues
│  └─ "❌ Failed to save expense. Try again later."
└─ User registration issues
   └─ "❌ Sorry, there was an error setting up your account. Please try again."
```

## Technical Implementation Details

### Database Schema
- **expenses table**: id, date, amount, category, description, user_id
- **users table**: id, telegram_user_id, first_name, last_name, created_at, last_active

### Data Flow
1. User sends `/add` command
2. Bot prompts for amount
3. User enters amount
4. Bot shows category selection keyboard
5. User selects category
6. Bot prompts for description
7. User enters description or skips
8. Data saved to PostgreSQL
9. Monthly summary displayed

### Integration Features
- **Google Sheets Sync**: Bidirectional sync with Google Sheets
- **Web Dashboard**: Simple Flask web interface for viewing expenses
- **Multi-user Support**: Each user has their own expense records

## Planned Features (Not Yet Implemented)

Based on ENHANCEMENT_PLAN.md, future features include:
- Voice input support
- Receipt processing with OCR
- Smart category suggestions
- Budget tracking
- Multi-currency support
- Enhanced reporting
- Quick-add buttons
- Inline expense editing

## Security Notes

- 🔒 User data is stored in PostgreSQL database
- 👤 Each user has their own expense records
- 📊 Data can be exported to Google Sheets
- 🌐 Simple web dashboard available for viewing

---