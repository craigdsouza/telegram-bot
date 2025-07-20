#!/usr/bin/env python3
"""
Debug script to check for multiple bot instances and identify the source of conflicts.
"""
import os
import sys
import psutil
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_running_instances():
    """Check for running Python processes that might be bot instances."""
    logger.info("Checking for running Python processes...")
    
    bot_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] == 'python' and proc.info['cmdline']:
                cmdline = ' '.join(proc.info['cmdline'])
                if 'bot.py' in cmdline or 'scheduler.py' in cmdline:
                    bot_processes.append({
                        'pid': proc.info['pid'],
                        'cmdline': cmdline
                    })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    logger.info(f"Found {len(bot_processes)} potential bot processes:")
    for proc in bot_processes:
        logger.info(f"  PID {proc['pid']}: {proc['cmdline']}")
    
    return bot_processes

def check_environment():
    """Check environment variables and Railway-specific settings."""
    logger.info("Checking environment...")
    
    # Check Railway-specific environment variables
    railway_vars = [k for k in os.environ.keys() if 'RAILWAY' in k.upper()]
    logger.info(f"Railway environment variables: {railway_vars}")
    
    # Check if we're in a Railway environment
    if 'RAILWAY_ENVIRONMENT' in os.environ:
        logger.info(f"Railway environment: {os.environ['RAILWAY_ENVIRONMENT']}")
    
    # Check current working directory
    logger.info(f"Current working directory: {os.getcwd()}")
    
    # Check if Procfile exists
    procfile_path = os.path.join(os.getcwd(), 'Procfile')
    if os.path.exists(procfile_path):
        with open(procfile_path, 'r') as f:
            procfile_content = f.read()
        logger.info(f"Procfile content:\n{procfile_content}")
    else:
        logger.warning("Procfile not found")

if __name__ == "__main__":
    logger.info("=== Bot Instance Debug Report ===")
    check_environment()
    check_running_instances()
    logger.info("=== End Debug Report ===") 