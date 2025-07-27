"""
Migration script to create user_settings table for per-user settings.
Adds columns: user_id (FK), first_name, month_start, month_end.
Defaults for month_start and month_end are NULL.
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()
import psycopg2

def get_db_connection():
    url = os.getenv("DATABASE_PUBLIC_URL")
    if not url:
        raise RuntimeError("DATABASE_PUBLIC_URL not set in environment variables")
    return psycopg2.connect(url)

def create_user_settings_table():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                    first_name VARCHAR(100),
                    last_name VARCHAR(100),
                    month_start INTEGER NULL CHECK (month_start >= 1 AND month_start <= 28),
                    month_end INTEGER NULL CHECK (month_end >= 1 AND month_end <= 31)
                );
            """)
            conn.commit()
            print("user_settings table created successfully!")
    except Exception as e:
        print(f"Error creating user_settings table: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Starting migration to create user_settings table...")
    create_user_settings_table()
    print("Migration completed!") 