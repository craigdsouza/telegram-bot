"""
Script to fix existing reminders by setting timezone for users who have reminder_time but no reminder_timezone.
This will set all existing reminders to Asia/Kolkata timezone.
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file
import psycopg2
from psycopg2.extras import DictCursor

def get_db_connection():
    """Get a database connection using DATABASE_PUBLIC_URL."""
    url = os.getenv("DATABASE_PUBLIC_URL")
    if not url:
        raise RuntimeError("DATABASE_PUBLIC_URL not set in environment variables")
    return psycopg2.connect(url)

def fix_existing_reminders():
    """Update existing users who have reminder_time but no reminder_timezone."""
    conn = None
    try:
        conn = get_db_connection()
        conn.autocommit = False  # Use transaction
        
        with conn.cursor() as cur:
            # Find users with reminder_time but no reminder_timezone
            cur.execute("""
                SELECT id, telegram_user_id, reminder_time 
                FROM users 
                WHERE reminder_time IS NOT NULL AND reminder_timezone IS NULL
            """)
            
            users_to_fix = cur.fetchall()
            print(f"Found {len(users_to_fix)} users with reminders but no timezone")
            
            if users_to_fix:
                # Update these users to have Asia/Kolkata timezone
                cur.execute("""
                    UPDATE users 
                    SET reminder_timezone = '+05:30' 
                    WHERE reminder_time IS NOT NULL AND reminder_timezone IS NULL
                """)
                
                updated_count = cur.rowcount
                print(f"Updated {updated_count} users to have Asia/Kolkata timezone")
                
                # Show the users that were updated
                for user_id, telegram_user_id, reminder_time in users_to_fix:
                    print(f"  - User {telegram_user_id}: reminder at {reminder_time} (IST)")
                
                conn.commit()
            else:
                print("No users found with reminders but no timezone")
            
    except Exception as e:
        print(f"Error during fix: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Starting fix for existing reminders...")
    fix_existing_reminders()
    print("Fix completed!") 