"""
Logging configuration for the Telegram bot.
Sets up both file and console logging.
"""

import logging

def setup_logging(log_filename='bot.log'):
    """Set up logging configuration with both file and console handlers."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Remove all handlers associated with the root logger object (avoid duplicates)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # File handler
    file_handler = logging.FileHandler(log_filename, mode='a')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger