"""
Migration script to add budget column to users table.
This script will:
1. Add a budget column to the existing users table
2. Set default value to NULL (no budget set initially)
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

def add_budget_column():
    """Add budget column to users table."""
    conn = None
    try:
        conn = get_db_connection()
        conn.autocommit = False  # Use transaction
        
        with conn.cursor() as cur:
            # Check if budget column already exists
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'budget';
            """)
            
            if cur.fetchone():
                print("Budget column already exists in users table")
                return
            
            # Add budget column to users table
            cur.execute("""
                ALTER TABLE users 
                ADD COLUMN budget DECIMAL(10,2) DEFAULT NULL;
            """)
            
            print("Successfully added budget column to users table")
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
    print("Starting migration to add budget column...")
    add_budget_column()
    print("Migration completed!") 