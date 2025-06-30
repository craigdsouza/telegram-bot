import os
import psycopg2
import logging
from datetime import datetime
from datetime import date
from typing import List, Tuple, Dict, Any, Optional
from psycopg2.extras import DictCursor
from dotenv import load_dotenv

# Set up module-level logger
logger = logging.getLogger(__name__)
from crypto_utils import ExpenseEncryptor

# Load environment variables
load_dotenv()

def get_connection():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    # psycopg2 accepts a URL directly
    return psycopg2.connect(url)

def get_encryption_key() -> str:
    """
    Get the encryption key from the environment variables.
    """
    key = os.getenv("ENCRYPTION_PASSPHRASE")
    if not key:
        raise RuntimeError("ENCRYPTION_PASSPHRASE not set")
    return key

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
                    date_encrypted BYTEA NOT NULL,
                    amount_encrypted BYTEA NOT NULL,
                    category_encrypted BYTEA NOT NULL,
                    description_encrypted BYTEA,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    salt_hex TEXT NOT NULL
                );
            """)
    conn.close()

def add_expense(date_val: str, amount: float, category: str, description: Optional[str] = None) -> None:
    """
    Insert a new expense with encrypted data.
    """
    # Initialize encryptor (generates new salt)
    encryptor = ExpenseEncryptor(get_encryption_key())
    
    # Encrypt the data
    encrypted_data = encryptor.encrypt_expense({
        'date': date_val.isoformat() if hasattr(date_val, 'isoformat') else str(date_val),
        'amount': str(amount),
        'category': category,
        'description': description or ''
    })
    
    # Store the encrypted data
    conn = get_connection()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO expenses (
                    date_encrypted, 
                    amount_encrypted, 
                    category_encrypted, 
                    description_encrypted,
                    salt_hex
                ) VALUES (%s, %s, %s, %s, %s);
            """, (
                encrypted_data['date'].encode(),
                encrypted_data['amount'].encode(),
                encrypted_data['category'].encode(),
                encrypted_data['description'].encode() if encrypted_data['description'] else None,
                encryptor.salt_hex
            ))
    finally:
        conn.close()

def _decrypt_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to decrypt a database row."""
    encryptor = ExpenseEncryptor.from_salt_hex(
        get_encryption_key(),
        row['salt_hex']
    )
    
    decrypted = encryptor.decrypt_expense({
        'date': bytes(row['date_encrypted']).decode('utf-8'),
        'amount': bytes(row['amount_encrypted']).decode('utf-8'),
        'category': bytes(row['category_encrypted']).decode('utf-8'),
        'description': bytes(row['description_encrypted']).decode('utf-8') if row['description_encrypted'] else ''
    })

    # convert date string to date object
    decrypted['date'] = datetime.strptime(decrypted['date'], '%Y-%m-%d').date()
    decrypted['amount'] = float(decrypted['amount'])
    return decrypted

def get_monthly_summary(year: int, month: int) -> List[Tuple[str, float]]:
    """
    Get monthly summary with decrypted data.
    Returns a list of (category, total_amount) for the given year/month.
    """
    start = date(year, month, 1)
    logger.info(f"[SUMMARY] Fetching expenses from {start} for year={year} month={month}")
    end = date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)
    
    conn = get_connection()
    try:
        with conn, conn.cursor(cursor_factory=DictCursor) as cur:
            # Get all expenses for the month
            cur.execute("""
                SELECT * FROM expenses
                WHERE created_at >= %s AND created_at < %s
            """, (start, end))
            
            # Decrypt and aggregate
            logger.info("[SUMMARY] Decrypting expense rows for aggregation")
            category_totals = {}
            fetched_rows = cur.fetchall()
            logger.info(f"[SUMMARY] Fetched {len(fetched_rows)} rows for month {month}")
            for row in fetched_rows:
                decrypted = _decrypt_row(row)
                category = decrypted['category']
                logger.info(f"[SUMMARY] Row id={row.get('id')} category={category} amount={decrypted['amount']}")
                amount = float(decrypted['amount'])
                category_totals[category] = category_totals.get(category, 0) + amount
            logger.info(f"[SUMMARY] Aggregated totals: {category_totals}")
            return list(category_totals.items())
    finally:
        conn.close()

def fetch_new_entries(conn, last_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Fetch new entries with decrypted data.
    Returns a list of dictionaries with decrypted expense data.
    """
    cur = conn.cursor(cursor_factory=DictCursor)
    try:
        if last_id:
            cur.execute(
                "SELECT * FROM expenses WHERE id > %s ORDER BY id",
                (last_id,)
            )
        else:
            cur.execute("SELECT * FROM expenses ORDER BY id")
        
        # Decrypt each row
        decrypted_rows = []
        for row in cur.fetchall():
            decrypted = _decrypt_row(row)
            decrypted['id'] = row['id']  # Keep the original ID
            decrypted_rows.append(decrypted)
            
        return decrypted_rows
    finally:
        cur.close()

def test_decryption():
    """Test function to verify decryption works with the database."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:  # Use DictCursor for named columns
            cur.execute("SELECT * FROM expenses LIMIT 1")
            row = cur.fetchone()
            if row:
                print("\n=== Encrypted Row ===")
                print(f"ID: {row['id']}")
                print(f"Salt hex: {row['salt_hex']}")
                print("Encrypted fields (hex):")
                for field in ['date_encrypted', 'amount_encrypted', 'category_encrypted', 'description_encrypted']:
                    print(f"  {field}: {bytes(row[field]).hex() if row[field] else 'NULL'}")
                
                print("\n=== Decrypted Data ===")
                try:
                    decrypted = _decrypt_row(row)
                    for key, value in decrypted.items():
                        print(f"{key}: {value!r} (type: {type(value).__name__})")
                except Exception as e:
                    print(f"Error during decryption: {e}")
                    raise
    finally:
        conn.close()


def close_connection(conn=None):
    """Close a database connection if it's open."""
    if conn and not conn.closed:
        conn.close()

if __name__ == "__main__":
    test_decryption()