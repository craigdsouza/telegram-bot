"""
Migration script to add reminder columns to users table.
This script will:
1. Add reminder_time column to store the time for daily reminders
2. Add reminder_timezone column to store the user's timezone
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file
import psycopg2
from psycopg2.extras import DictCursor

# Add parent directory to path to import db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import psycopg2

def get_db_connection():
    """Get a database connection using DATABASE_PUBLIC_URL."""
    url = os.getenv("DATABASE_PUBLIC_URL")
    if not url:
        raise RuntimeError("DATABASE_PUBLIC_URL not set in environment variables")
    return psycopg2.connect(url)

def add_reminder_columns():
    """Add reminder_time and reminder_timezone columns to users table."""
    conn = None
    try:
        conn = get_db_connection()
        conn.autocommit = False  # Use transaction
        
        with conn.cursor() as cur:
            # Check if reminder_time column already exists
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'reminder_time';
            """)
            
            if not cur.fetchone():
                # Add reminder_time column to users table
                cur.execute("""
                    ALTER TABLE users 
                    ADD COLUMN reminder_time TIME DEFAULT NULL;
                """)
                print("Successfully added reminder_time column to users table")
            else:
                print("reminder_time column already exists in users table")
            
            # Check if reminder_timezone column already exists
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'reminder_timezone';
            """)
            
            if not cur.fetchone():
                # Add reminder_timezone column to users table
                cur.execute("""
                    ALTER TABLE users 
                    ADD COLUMN reminder_timezone TEXT DEFAULT NULL;
                """)
                print("Successfully added reminder_timezone column to users table")
            else:
                print("reminder_timezone column already exists in users table")
            
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
    print("Starting migration to add reminder columns...")
    add_reminder_columns()
    print("Migration completed!") 