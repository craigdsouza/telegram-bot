"""
Migration script to populate user_settings table with existing users.
Copies id and first_name from users table to user_settings table.
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

def populate_user_settings():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Insert users who do not already have a user_settings row
            cur.execute("""
                INSERT INTO user_settings (user_id, first_name, last_name)
                SELECT id, first_name, last_name
                FROM users
                WHERE id NOT IN (SELECT user_id FROM user_settings);
            """)
            conn.commit()
            print("user_settings table populated with existing users!")
    except Exception as e:
        print(f"Error populating user_settings table: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Starting migration to populate user_settings table...")
    populate_user_settings()
    print("Migration completed!") 