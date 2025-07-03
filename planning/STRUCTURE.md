# Telegram Expense Bot - Code Structure

## Overview

This document describes the improved code structure and organization for the Telegram Expense Bot.

## Folder Structure

```
telegram-bot/
├── bot.py                          # Original monolithic bot file (to be replaced)
├── bot_refactored.py               # New modular main entry point
├── requirements.txt                # Python dependencies
├── Procfile                        # Railway deployment configuration
├── README.md                       # Project overview
├── STRUCTURE.md                    # This file - code structure documentation
│
├── config/                         # Configuration management
│   ├── __init__.py
│   └── settings.py                 # Centralized settings and environment variables
│
├── handlers/                       # Bot command and conversation handlers
│   ├── __init__.py
│   ├── user.py                     # User registration and basic commands
│   └── conversation.py             # Expense addition conversation flow
│
├── utils/                          # Utility functions and helpers
│   ├── __init__.py
│   ├── health_server.py            # Health check server for deployment
│   └── logging_config.py           # Logging setup and configuration
│
├── data/                           # Data management and database
│   ├── db.py                       # Database operations (existing)
│   ├── db_encrypted.py             # Encrypted database operations (existing)
│   └── categories.py               # Expense categories (existing)
│
├── integrations/                   # External service integrations
│   ├── sheets.py                   # Google Sheets integration (existing)
│   ├── sync_google_sheet.py        # Google Sheets sync (existing)
│   └── dashboard.py                # Web dashboard (existing)
│
├── migrations/                     # Database migrations (existing)
│   ├── 001_encrypt_existing_data.py
│   └── 002_add_users_table.py
│
├── planning/                       # Project planning and documentation (existing)
│   ├── USER_EXPERIENCE_FLOWS.md
│   ├── ENHANCEMENT_PLAN.md
│   ├── USER_CONVERSATIONS.md
│   ├── TODAYS_PLAN.md
│   └── LOCAL_TESTING.md
│
├── scripts/                        # Utility scripts and tools
│   ├── import_from_csv.py          # CSV import tool (existing)
│   ├── check_csv_categories.py     # Category validation (existing)
│   ├── test_crypto.py              # Crypto testing (existing)
│   └── scheduler.py                # Scheduled tasks (existing)
│
└── backups/                        # Backup files (existing)
```

## Code Organization Principles

### 1. **Separation of Concerns**
- **Handlers**: Handle user interactions and bot commands
- **Utils**: Reusable utility functions
- **Config**: Centralized configuration management
- **Data**: Database operations and data models
- **Integrations**: External service connections

### 2. **Modular Design**
- Each module has a single responsibility
- Clear interfaces between modules
- Easy to test individual components
- Simple to extend with new features

### 3. **Configuration Management**
- All environment variables centralized in `config/settings.py`
- Validation of required settings on startup
- Easy to manage different environments (dev, staging, prod)

### 4. **Error Handling**
- Consistent error handling patterns
- Proper logging at all levels
- Graceful degradation when services are unavailable

## Key Improvements

### **Before (bot.py - 516 lines)**
- Monolithic file with mixed responsibilities
- Hard to navigate and maintain
- Difficult to test individual components
- Configuration scattered throughout code

### **After (Modular Structure)**
- **bot_refactored.py** (120 lines): Clean main entry point
- **handlers/conversation.py**: Dedicated conversation flow
- **handlers/user.py**: User management functions
- **utils/health_server.py**: Health check functionality
- **config/settings.py**: Centralized configuration

## Migration Guide

### **Step 1: Test the New Structure**
```bash
# Test the refactored bot
python bot_refactored.py
```

### **Step 2: Update Imports**
Update any existing imports to use the new structure:
```python
# Old
from bot import some_function

# New
from handlers.user import some_function
```

### **Step 3: Replace bot.py**
Once tested, replace the original `bot.py` with `bot_refactored.py`:
```bash
mv bot.py bot_old.py
mv bot_refactored.py bot.py
```

## Benefits of New Structure

1. **Maintainability**: Easier to find and modify specific functionality
2. **Testability**: Individual components can be tested in isolation
3. **Scalability**: New features can be added without cluttering main file
4. **Readability**: Clear separation of concerns makes code easier to understand
5. **Configuration**: Centralized settings management
6. **Documentation**: Better organized with clear module purposes

## Next Steps

1. **Move existing files** to appropriate folders
2. **Update import statements** throughout the codebase
3. **Add unit tests** for individual modules
4. **Create deployment scripts** for the new structure
5. **Update documentation** to reflect new organization

## File Movement Plan

```bash
# Move data-related files
mv db.py data/
mv db_encrypted.py data/
mv categories.py data/

# Move integration files
mv sheets.py integrations/
mv sync_google_sheet.py integrations/
mv dashboard.py integrations/

# Move utility scripts
mv import_from_csv.py scripts/
mv check_csv_categories.py scripts/
mv test_crypto.py scripts/
mv scheduler.py scripts/
```

This structure makes the codebase much more maintainable and follows Python best practices for project organization. 