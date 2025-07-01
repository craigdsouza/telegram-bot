import os
import psycopg2
import logging
from datetime import datetime
from datetime import date
from typing import List, Tuple, Dict, Any, Optional
from psycopg2.extras import DictCursor
from dotenv import load_dotenv
from crypto_utils import ExpenseEncryptor

# Enable logging
logging.basicConfig(
    filename='db_encrypted.log',
    filemode='a',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Send logs to console as well
def _enable_console_logging():
    console_handler = logging.StreamHandler() # send logs to console
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

_enable_console_logging()

# Load environment variables
load_dotenv()

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

def get_monthly_summary(year: int, month: int) -> List[Tuple[str, float]]:
    """
    Returns a list of (category, total_amount) for the given year/month.
    """
    sql = """
      SELECT category, SUM(amount) AS total
      FROM expenses
      WHERE date >= %s AND date < %s
      GROUP BY category
      ORDER BY category;
    """
    start = date(year, month, 1)
    # advance one month safely
    if month == 12:
        end = date(year+1, 1, 1)
    else:
        end = date(year, month+1, 1)
    conn = get_connection()
    with conn, conn.cursor() as cur:
        cur.execute(sql, (start, end))
        return cur.fetchall()  # list of (category, total)

def fetch_new_entries(conn, last_id=None):
    """
    Query Postgres for entries with id > last_id, or all if last_id is None.
    Returns a list of tuples (id, date, amount, category, description).
    """
    cur = conn.cursor()
    if last_id:
        cur.execute(
            "SELECT id, date, amount, category, description"
            " FROM expenses WHERE id > %s ORDER BY id",
            (last_id,)
        )
    else:
        cur.execute(
            "SELECT id, date, amount, category, description"
            " FROM expenses ORDER BY id"
        )
    rows = cur.fetchall()
    cur.close()
    return rows


def close_connection(conn=None):
    """Close a database connection if it's open."""
    if conn and not conn.closed:
        conn.close()