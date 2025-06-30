# Telegram Expense Bot - User Experience Flows

## 1. First-Time Setup Flow

```
👤 User starts bot for the first time
└─ 🤖 "Welcome to Expense Tracker! 🔒"
   └─ "Let's set up your secure passphrase to protect your financial data."
      └─ "Please create a strong passphrase (min 12 characters):"
         └─ *User enters passphrase*
            └─ 🔄 "Please confirm your passphrase:"
               └─ *User re-enters passphrase*
                  └─ 🔑 "Generating your secure keys..."
                     └─ 📝 "IMPORTANT: Save this recovery code in a safe place:"
                        └─ 🏷  "RECOVERY-CODE-HERE-123"
                           └─ "You'll need this if you forget your passphrase!"
                              └─ ✅ "Setup complete! Your data is now protected."
                                 └─ "Type /help to see available commands."
```

## 2. Regular Login Flow

```
👤 User starts bot after session expired
└─ 🔒 "Welcome back! Your session has expired."
   └─ "Please enter your passphrase to continue:"
      └─ *User enters passphrase*
         ├─ ✅ "Authentication successful!"
         │  └─ *Shows main menu*
         └─ ❌ "Incorrect passphrase. Please try again:"
            └─ *User retries or selects 'Forgot passphrase'*
```

## 3. Adding an Expense

```
👤 User types /add
└─ 💰 "How much did you spend? (e.g., 15.50)"
   └─ *User enters amount*
      └─ 🏷 "Select a category:"
         └─ *Shows inline keyboard with categories*
            └─ *User selects category*
               └─ 📝 "Add a description (or /skip):"
                  └─ *User enters description or skips*
                     └─ 💾 "Saving expense..."
                        └─ ✅ "Expense added!"
                           └─ *Shows monthly summary*
```

## 4. Viewing Monthly Summary

```
👤 User types /summary
└─ 📊 "June 2025 Expense Summary"
   └─ "Total Spent: $1,234.56"
      └─ "By Category:"
          ├─ 🍔 Food: $400.00 (32%)
          ├─ 🚌 Transport: $300.00 (24%)
          ├─ 🏠 Rent: $400.00 (32%)
          └─ 🛒 Shopping: $134.56 (11%)
          
          ────────────────
          Total: $1,234.56
          
          "View detailed report: /details"
```

## 5. Passphrase Recovery Flow

```
👤 User selects "Forgot passphrase"
└─ 🔄 "To reset your passphrase, please enter your recovery code:"
   └─ *User enters recovery code*
      ├─ ❌ "Invalid recovery code. Please try again:"
      └─ ✅ "Code verified! Please enter a new passphrase:"
         └─ *User enters new passphrase*
            └─ 🔄 "Please confirm your new passphrase:"
               └─ *User confirms*
                  └─ 🔑 "Generating new keys..."
                     └─ 📝 "Your NEW recovery code (save this!):"
                        └─ 🏷  "NEW-RECOVERY-CODE-456"
                           └─ ✅ "Passphrase updated successfully!"
```

## 6. Session Management

### Automatic Session Expiry
```
👤 User returns after 24h of inactivity
└─ ⏳ "Your session has expired for security."
   └─ "Please enter your passphrase to continue:"
      └─ *Continues to login flow*
```

### Manual Lock
```
👤 User types /lock
└─ 🔒 "Session locked!"
   └─ "Enter your passphrase to continue:"
      └─ *Continues to login flow*
```

## 7. Help Command

```
👤 User types /help
└─ 📚 *Available Commands:*
   ├─ /add - Record a new expense
   ├─ /summary - View monthly summary
   ├─ /details - Detailed expense report
   ├─ /categories - Manage categories
   ├─ /export - Export your data
   ├─ /lock - Lock your session
   ├─ /help - Show this help
   └─ /feedback - Send us your thoughts
```

## Security Notes

- 🔒 All data is encrypted with your passphrase
- 🔑 Passphrase is never stored on our servers
- ⏳ Sessions expire after 24h of inactivity
- 📝 Always save your recovery code in a safe place

---
*Last Updated: June 26, 2025*
