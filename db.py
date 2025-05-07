import os
import psycopg2

def get_connection():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    # psycopg2 accepts a URL directly
    return psycopg2.connect(url)

def init_db():
    """
    Create the expenses table if it doesn't exist.
    """
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    amount NUMERIC NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT
                );
            """)
    conn.close()

def add_expense(date, amount, category, description=None):
    """
    Inserts a row into expenses(date, amount, category, description).
    """
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO expenses (date, amount, category, description)
                VALUES (%s, %s, %s, %s);
                """,
                (date, amount, category, description)
            )
    conn.close()