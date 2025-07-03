"""
Configuration settings for the Telegram Expense Bot.
Centralizes all configuration values and environment variables.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    # Bot Configuration
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    
    # Database Configuration
    DATABASE_URL = os.getenv("DATABASE_URL")
    DATABASE_PUBLIC_URL = os.getenv("DATABASE_PUBLIC_URL")
    
    # Google Sheets Configuration
    GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
    SERVICE_ACCOUNT_JSON_B64 = os.getenv("SERVICE_ACCOUNT_JSON_B64")
    
    # Server Configuration
    PORT = int(os.environ.get("PORT", 8000))
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "bot.log")
    
    @classmethod
    def validate(cls):
        """Validate that all required settings are present."""
        required_settings = [
            ("TELEGRAM_BOT_TOKEN", cls.TELEGRAM_BOT_TOKEN),
            ("DATABASE_URL", cls.DATABASE_URL),
        ]
        
        missing_settings = []
        for name, value in required_settings:
            if not value:
                missing_settings.append(name)
        
        if missing_settings:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_settings)}")
        
        return True


# Global settings instance
settings = Settings() 