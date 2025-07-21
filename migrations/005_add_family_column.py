"""
Migration script to add family column to users table.
This script will:
1. Add a family column to store a list of user IDs for family/couple tracking
2. Set default value to NULL (no family group initially)
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

def add_family_column():
    """Add family column to users table."""
    conn = None
    try:
        conn = get_db_connection()
        conn.autocommit = False  # Use transaction
        
        with conn.cursor() as cur:
            # Check if family column already exists
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'family';
            """)
            
            if cur.fetchone():
                print("Family column already exists in users table")
                return
            
            # Add family column to users table
            # Using TEXT to store JSON array of user IDs
            cur.execute("""
                ALTER TABLE users 
                ADD COLUMN family TEXT DEFAULT NULL;
            """)
            
            print("Successfully added family column to users table")
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
    print("Starting migration to add family column...")
    add_family_column()
    print("Migration completed!") 