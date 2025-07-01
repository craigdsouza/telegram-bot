"""
Migration script to add users table for user management.
This script will:
1. Create a new users table with telegram_user_id, first_name, last_name, and created_at fields
2. Add a foreign key reference to users in the expenses table
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime

# Add parent directory to path to import db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import psycopg2

def get_db_connection():
    """Get a database connection using DATABASE_PUBLIC_URL."""
    url = os.getenv("DATABASE_PUBLIC_URL")
    if not url:
        raise RuntimeError("DATABASE_PUBLIC_URL not set in environment variables")
    return psycopg2.connect(url)

def add_users_table():
    """Add users table and update expenses table with user_id foreign key."""
    conn = None
    try:
        conn = get_db_connection()
        conn.autocommit = False  # Use transaction
        
        with conn.cursor() as cur:
            # Create users table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    telegram_user_id BIGINT NOT NULL UNIQUE,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Add index on telegram_user_id for faster lookups
                CREATE INDEX IF NOT EXISTS idx_users_telegram_user_id ON users(telegram_user_id);
                
            """)
            
            print("Successfully created users table and updated expenses table")
            conn.commit()
            
    except Exception as e:
        print(f"Error during migration: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Starting migration to add users table...")
    add_users_table()
    print("Migration completed!")
