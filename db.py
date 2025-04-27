import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL')

# Get a new database connection
def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

# Initialize the expenses table
def init_db():
    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                CREATE TABLE IF NOT EXISTS expenses (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    amount NUMERIC NOT NULL,
                    category TEXT NOT NULL
                )
                '''
            )
    conn.close()

# Add a new expense record
def add_expense(date, amount, category):
    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO expenses (date, amount, category) VALUES (%s, %s, %s)",
                (date, amount, category)
            )
    conn.close()

# Get summary totals for a given month and year
def get_monthly_summary(year, month):
    conn = get_conn()
    with conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                '''
                SELECT category, SUM(amount) AS total
                FROM expenses
                WHERE EXTRACT(YEAR FROM date) = %s
                  AND EXTRACT(MONTH FROM date) = %s
                GROUP BY category
                ORDER BY category
                ''',
                (year, month)
            )
            rows = cur.fetchall()
    conn.close()
    return rows

# Fetch all expenses
def get_all_expenses():
    conn = get_conn()
    with conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT date AS Date, amount AS Amount, category AS Category FROM expenses ORDER BY date"
            )
            rows = cur.fetchall()
    conn.close()
    return rows
