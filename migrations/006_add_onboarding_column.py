"""
Migration script to add onboarding column to users table.
This script will:
1. Add an onboarding column to track if user has completed onboarding
2. Set default value to 0 (onboarding not completed initially)
3. Use INTEGER type where 0 = not completed, 1 = completed
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

def add_onboarding_column():
    """Add onboarding column to users table."""
    conn = None
    try:
        conn = get_db_connection()
        conn.autocommit = False  # Use transaction
        
        with conn.cursor() as cur:
            # Check if onboarding column already exists
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'onboarding';
            """)
            
            if cur.fetchone():
                print("Onboarding column already exists in users table")
                return
            
            # Add onboarding column to users table
            # Using INTEGER where 0 = not completed, 1 = completed
            cur.execute("""
                ALTER TABLE users 
                ADD COLUMN onboarding INTEGER DEFAULT 0;
            """)
            
            print("Successfully added onboarding column to users table")
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
    print("Starting migration to add onboarding column...")
    add_onboarding_column()
    print("Migration completed!") 