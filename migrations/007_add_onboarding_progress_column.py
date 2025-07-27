"""
Migration script to add onboarding_progress column to users table.
This script will:
1. Add an onboarding_progress JSONB column to track detailed onboarding progress
2. Migrate existing onboarding data to the new format
3. Drop the old onboarding column
4. Set default value with initial progress structure for single-step onboarding
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

def add_onboarding_progress_column():
    """Add onboarding_progress column and migrate existing data."""
    conn = None
    try:
        conn = get_db_connection()
        conn.autocommit = False  # Use transaction
        
        with conn.cursor() as cur:
            # Check if onboarding_progress column already exists
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'onboarding_progress';
            """)
            
            if cur.fetchone():
                print("Onboarding progress column already exists in users table")
                return
            
            # Add onboarding_progress column to users table
            # Default to single-step onboarding (welcome step only)
            cur.execute("""
                ALTER TABLE users 
                ADD COLUMN onboarding_progress JSONB DEFAULT '{"current_step": 0, "completed_steps": [], "total_steps": 1, "step_data": {}}';
            """)
            
            print("Successfully added onboarding_progress column to users table")
            
            # Check if old onboarding column exists and migrate data
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'onboarding';
            """)
            
            if cur.fetchone():
                print("Migrating existing onboarding data...")
                
                # Get all users with existing onboarding data
                cur.execute("""
                    SELECT id, onboarding FROM users WHERE onboarding IS NOT NULL;
                """)
                
                users = cur.fetchall()
                print(f"Found {len(users)} users with existing onboarding data")
                
                for user in users:
                    user_id, old_onboarding = user
                    
                    # Convert old onboarding value to new format
                    if old_onboarding == 1:
                        # User completed onboarding, mark welcome step as completed
                        new_progress = {
                            "current_step": 1,
                            "completed_steps": [0],
                            "total_steps": 1,
                            "step_data": {
                                "step_0": {
                                    "completed_at": "2024-01-01T00:00:00Z"
                                }
                            }
                        }
                    else:
                        # User hasn't completed onboarding
                        new_progress = {
                            "current_step": 0,
                            "completed_steps": [],
                            "total_steps": 1,
                            "step_data": {}
                        }
                    
                    # Update user with new progress format
                    cur.execute("""
                        UPDATE users 
                        SET onboarding_progress = %s 
                        WHERE id = %s;
                    """, (json.dumps(new_progress), user_id))
                
                print(f"Migrated onboarding data for {len(users)} users")
                
                # Drop the old onboarding column
                cur.execute("""
                    ALTER TABLE users DROP COLUMN onboarding;
                """)
                
                print("Dropped old onboarding column")
            
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
    print("Starting migration to add onboarding progress column...")
    add_onboarding_progress_column()
    print("Migration completed!") 