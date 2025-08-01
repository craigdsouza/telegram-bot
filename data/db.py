import os
import psycopg2
import logging
from datetime import datetime
from datetime import date
from typing import List, Tuple, Dict, Any, Optional
from psycopg2.extras import DictCursor
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def get_connection():
    url = os.getenv("DATABASE_PUBLIC_URL")
    if not url:
        raise RuntimeError("DATABASE_PUBLIC_URL not set")
    # psycopg2 accepts a URL directly
    return psycopg2.connect(url)

def init_db():
    """
    Create the expenses table if it doesn't exist.
    """
    conn = get_connection()
    logger.info("Creating expenses table if it doesn't exist...")
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL,
                    amount NUMERIC NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT,
                    user_id INTEGER,
                    mode TEXT
                );
            """)
    conn.close()

def add_expense(date, amount, category, description=None, user_id=None, mode=None):
    """
    Inserts a row into expenses(date, amount, category, description, user_id, mode).
    
    Args:
        date: The date of the expense
        amount: The amount of the expense
        category: The category of the expense
        description: Optional description of the expense
        user_id: The ID of the user who made the expense
        mode: The payment mode (UPI, CASH, DEBIT CARD, CREDIT CARD) - optional for bot
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO expenses (date, amount, category, description, user_id, mode)
                VALUES (%s, %s, %s, %s, %s, %s);
                """,
                (date, amount, category, description, user_id, mode)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error in add_expense: {e}")
        raise
    finally:
        if conn and not conn.closed:
            conn.close()

def get_monthly_summary(year: int, month: int, user_id: int) -> List[Tuple[str, float]]:
    """
    Returns a list of (category, total_amount) for the given year/month, filtered by user.
    Supports custom month start dates from user settings.
    """
    
    sql = """
        SELECT category, SUM(amount) AS total
        FROM expenses
        WHERE date >= %s AND date < %s AND user_id = %s
        GROUP BY category
        ORDER BY category;
    """
    
    # Get user settings to check for custom month start
    user_settings = get_user_settings(user_id)
    
    if user_settings and user_settings.get('month_start') is not None:
        # Custom month period (e.g., 15th to 14th)
        month_start = user_settings['month_start']
        from datetime import datetime
        
        # Calculate start of current period
        today = datetime.now()
        if month_start <= today.day:
            # Current period started this month
            start = date(year, month, month_start)
        else:
            # Current period started last month
            if month == 1:
                start = date(year - 1, 12, month_start)
            else:
                start = date(year, month - 1, month_start)
        
        # Calculate end of current period
        if month == 12:
            end = date(year + 1, 1, month_start)
        else:
            end = date(year, month + 1, month_start)
        
        logger.info(f"[SUMMARY] Custom period for user {user_id}: {start} to {end}")
    else:
        # Standard calendar month (1st to last day)
        start = date(year, month, 1)
        # advance one month safely
        if month == 12:
            end = date(year+1, 1, 1)
        else:
            end = date(year, month+1, 1)
        logger.info(f"[SUMMARY] Standard period for user {user_id}: {start} to {end}")
    
    conn = get_connection()
    with conn, conn.cursor() as cur:
        cur.execute(sql, (start, end, user_id))
        return cur.fetchall()  # list of (category, total)

def fetch_new_entries(conn, last_id=None):
    """
    Query Postgres for entries with id > last_id, or all if last_id is None.
    Returns a list of tuples (id, date, amount, category, description).
    """
    cur = conn.cursor()
    if last_id:
        cur.execute(
            "SELECT id, user_id, date, amount, category, description"
            " FROM expenses WHERE id > %s ORDER BY id",
            (last_id,)
        )
    else:
        cur.execute(
            "SELECT id, user_id, date, amount, category, description"
            " FROM expenses ORDER BY id"
        )
    rows = cur.fetchall()
    cur.close()
    return rows


def close_connection(conn=None):
    """Close a database connection if it's open."""
    if conn and not conn.closed:
        conn.close()

def get_or_create_user(telegram_user_id: int, first_name: str = None, last_name: str = None) -> dict:
    """
    Get a user by Telegram ID, or create a new user if they don't exist.
    Returns a dictionary with user data.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # Try to get existing user
            cur.execute(
                """
                SELECT * FROM users 
                WHERE telegram_user_id = %s
                """,
                (telegram_user_id,)
            )
            user = cur.fetchone()
            
            if user:
                # Update last_active timestamp for existing user
                cur.execute(
                    """
                    UPDATE users 
                    SET last_active = CURRENT_TIMESTAMP,
                        first_name = COALESCE(%s, first_name),
                        last_name = COALESCE(%s, last_name)
                    WHERE telegram_user_id = %s
                    RETURNING *
                    """,
                    (first_name, last_name, telegram_user_id)
                )
                updated_user = cur.fetchone()
                conn.commit()
                logger.info(f"Updated existing user: {updated_user}")
                return dict(updated_user) if updated_user else None
            else:
                # Create new user
                cur.execute(
                    """
                    INSERT INTO users (telegram_user_id, first_name, last_name)
                    VALUES (%s, %s, %s)
                    RETURNING *
                    """,
                    (telegram_user_id, first_name, last_name)
                )
                new_user = cur.fetchone()
                # Auto-create user_settings row for new user
                if new_user:
                    cur.execute(
                        """
                        INSERT INTO user_settings (user_id, first_name, last_name)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (user_id) DO NOTHING
                        """,
                        (new_user['id'], new_user['first_name'], new_user['last_name'])
                    )
                conn.commit()
                logger.info(f"Created new user: {new_user}")
                return dict(new_user) if new_user else None
    except Exception as e:
        logger.error(f"Error in get_or_create_user: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn and not conn.closed:
            conn.close()

def get_user_by_telegram_id(telegram_user_id: int) -> dict:
    """
    Get a user by their Telegram user ID.
    Returns a dictionary with user data or None if not found.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM users 
                WHERE telegram_user_id = %s
                """,
                (telegram_user_id,)
            )
            user = cur.fetchone()
            logger.info(f"Found user: {user}")
            return dict(user) if user else None
    except Exception as e:
        logger.error(f"Error in get_user_by_telegram_id: {e}")
        raise
    finally:
        if conn and not conn.closed:
            conn.close()

def get_family_members(user_id: int) -> List[int]:
    """
    Get all family member user IDs for a given user.
    Returns a list of user IDs including the user themselves.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Get the family group for this user
            cur.execute(
                """
                SELECT family FROM users WHERE id = %s
                """,
                (user_id,)
            )
            result = cur.fetchone()
            
            if not result or not result[0]:
                # No family group, return just this user
                return [user_id]
            
            # Parse the family JSON array
            import json
            try:
                family_ids = json.loads(result[0])
                if isinstance(family_ids, list):
                    return family_ids
                else:
                    logger.error(f"Invalid family format for user {user_id}: {result[0]}")
                    return [user_id]
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in family column for user {user_id}: {result[0]}")
                return [user_id]
    except Exception as e:
        logger.error(f"Error in get_family_members: {e}")
        return [user_id]
    finally:
        if conn and not conn.closed:
            conn.close()

def get_family_budget(family_member_ids: List[int]) -> float:
    """
    Get the budget set by any family member.
    Returns the first non-null budget found, or None if no budget is set.
    """
    if not family_member_ids:
        return None
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Get the first non-null budget from any family member
            cur.execute(
                """
                SELECT budget FROM users 
                WHERE id = ANY(%s) AND budget IS NOT NULL AND budget > 0
                ORDER BY id
                LIMIT 1
                """,
                (family_member_ids,)
            )
            result = cur.fetchone()
            return float(result[0]) if result else None
    except Exception as e:
        logger.error(f"Error in get_family_budget: {e}")
        return None
    finally:
        if conn and not conn.closed:
            conn.close()

def get_user_settings(user_id: int) -> dict:
    """
    Get user settings including month_start and month_end.
    Returns a dictionary with user settings or None if not found.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT user_id, first_name, last_name, month_start, month_end
                FROM user_settings
                WHERE user_id = %s
                """,
                (user_id,)
            )
            result = cur.fetchone()
            return dict(result) if result else None
    except Exception as e:
        logger.error(f"Error in get_user_settings: {e}")
        return None
    finally:
        if conn and not conn.closed:
            conn.close()


def get_family_monthly_summary(year: int, month: int, family_member_ids: List[int]) -> List[Tuple[str, float]]:
    """
    Get monthly summary for all family members combined.
    Returns a list of (category, total_amount) for the given year/month.
    Supports custom month start dates from the first family member's settings.
    """
    if not family_member_ids:
        return []
    
    sql = """
        SELECT category, SUM(amount) AS total
        FROM expenses
        WHERE date >= %s AND date < %s AND user_id = ANY(%s)
        GROUP BY category
        ORDER BY category;
    """
    
    # Get settings from the first family member to determine custom period
    first_member_settings = get_user_settings(family_member_ids[0])
    
    if first_member_settings and first_member_settings.get('month_start') is not None:
        # Custom month period (e.g., 15th to 14th)
        month_start = first_member_settings['month_start']
        from datetime import datetime
        
        # Calculate start of current period
        today = datetime.now()
        if month_start <= today.day:
            # Current period started this month
            start = date(year, month, month_start)
        else:
            # Current period started last month
            if month == 1:
                start = date(year - 1, 12, month_start)
            else:
                start = date(year, month - 1, month_start)
        
        # Calculate end of current period
        if month == 12:
            end = date(year + 1, 1, month_start)
        else:
            end = date(year, month + 1, month_start)
        
        logger.info(f"[SUMMARY] Family custom period: {start} to {end}")
    else:
        # Standard calendar month (1st to last day)
        start = date(year, month, 1)
        # advance one month safely
        if month == 12:
            end = date(year+1, 1, 1)
        else:
            end = date(year, month+1, 1)
        logger.info(f"[SUMMARY] Family standard period: {start} to {end}")
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (start, end, family_member_ids))
            return cur.fetchall()  # list of (category, total)
    except Exception as e:
        logger.error(f"Error in get_family_monthly_summary: {e}")
        return []
    finally:
        if conn and not conn.closed:
            conn.close()