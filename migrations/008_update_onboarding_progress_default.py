"""
Migration script to update onboarding_progress column default value.
This script will:
1. Update the default value of onboarding_progress to reflect 2-step onboarding
2. Update existing users who have the old default (total_steps: 1) to the new format
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file
import psycopg2
from psycopg2.extras import DictCursor
import json

# Add parent directory to path to import db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import psycopg2

def get_db_connection():
    """Get a database connection using DATABASE_PUBLIC_URL."""
    url = os.getenv("DATABASE_PUBLIC_URL")
    if not url:
        raise RuntimeError("DATABASE_PUBLIC_URL not set in environment variables")
    return psycopg2.connect(url)

def update_onboarding_progress_default():
    """Update onboarding_progress column default value and existing data."""
    conn = None
    try:
        conn = get_db_connection()
        conn.autocommit = False  # Use transaction
        
        with conn.cursor() as cur:
            # Check if onboarding_progress column exists
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'onboarding_progress';
            """)
            
            if not cur.fetchone():
                print("Onboarding progress column does not exist in users table")
                return
            
            # Update existing users who have total_steps: 1 to total_steps: 2
            print("Updating existing users with old onboarding format...")
            
            # Find users with total_steps: 1
            cur.execute("""
                SELECT id, onboarding_progress 
                FROM users 
                WHERE onboarding_progress->>'total_steps' = '1';
            """)
            
            users = cur.fetchall()
            print(f"Found {len(users)} users with old onboarding format")
            
            for user in users:
                user_id, current_progress = user
                
                # Update to new format with 2 steps
                updated_progress = {
                    "current_step": current_progress.get("current_step", 0),
                    "completed_steps": current_progress.get("completed_steps", []),
                    "total_steps": 2,  # Updated to 2 steps
                    "step_data": current_progress.get("step_data", {})
                }
                
                # Update user with new progress format
                cur.execute("""
                    UPDATE users 
                    SET onboarding_progress = %s 
                    WHERE id = %s;
                """, (json.dumps(updated_progress), user_id))
            
            print(f"Updated onboarding data for {len(users)} users")
            
            # Update the default value for new users
            print("Updating default value for new users...")
            
            # First, drop the existing default
            cur.execute("""
                ALTER TABLE users 
                ALTER COLUMN onboarding_progress DROP DEFAULT;
            """)
            
            # Then set the new default
            cur.execute("""
                ALTER TABLE users 
                ALTER COLUMN onboarding_progress 
                SET DEFAULT '{"current_step": 0, "completed_steps": [], "total_steps": 2, "step_data": {}}';
            """)
            
            print("Successfully updated default value for onboarding_progress column")
            
            conn.commit()
            print("Migration completed successfully!")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Starting migration to update onboarding progress default...")
    update_onboarding_progress_default()
    print("Migration completed!") 