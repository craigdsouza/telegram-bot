"""
Migration script to update database schema for encrypted storage.
This script will:
1. Create a new expenses_encrypted table
2. Encrypt all existing data
3. Replace the old expenses table with the new one
"""
import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime

# Add parent directory to path to import crypto_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from crypto_utils import ExpenseEncryptor

# Default passphrase - in production, this should be provided by the user
DEFAULT_PASSPHRASE = "temporary-default-passphrase"

def get_db_connection():
    """Get a database connection."""
    url = os.getenv("DATABASE_PUBLIC_URL")
    if not url:
        raise ValueError("DATABASE_PUBLIC_URL environment variable not set")
    return psycopg2.connect(url)

def migrate_data(conn, passphrase):
    """Migrate data from expenses to expenses_encrypted."""
    with conn.cursor() as cur:
        # Create the new table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses_encrypted (
            id SERIAL PRIMARY KEY,
            date_encrypted BYTEA NOT NULL,
            amount_encrypted BYTEA NOT NULL,
            category_encrypted BYTEA NOT NULL,
            description_encrypted BYTEA,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            salt_hex TEXT NOT NULL
        );
        """)
        
        # Get all existing data
        cur.execute("SELECT * FROM expenses")
        expenses = cur.fetchall()
        
        if not expenses:
            print("No expenses found to migrate")
            return 0
            
        # Encrypt and migrate each expense
        migrated_count = 0
        for expense in expenses:
            expense_id, date_val, amount, category, description = expense
            
            # Create encryptor with new salt for each user (in a real app, you'd have one per user)
            encryptor = ExpenseEncryptor(passphrase)
            
            # Encrypt the data
            encrypted_data = encryptor.encrypt_expense({
                'date': date_val.isoformat(),
                'amount': amount,
                'category': category,
                'description': description or ''
            })
            
            # Insert into new table
            cur.execute("""
                INSERT INTO expenses_encrypted 
                (date_encrypted, amount_encrypted, category_encrypted, 
                 description_encrypted, salt_hex)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                encrypted_data['date'].encode(),
                encrypted_data['amount'].encode(),
                encrypted_data['category'].encode(),
                encrypted_data['description'].encode() if encrypted_data['description'] else None,
                encryptor.salt_hex
            ))
            
            migrated_count += 1
            if migrated_count % 10 == 0:
                print(f"Migrated {migrated_count} expenses...")
        
        return migrated_count

def verify_migration(conn, passphrase, expected_count):
    """Verify that the migration was successful."""
    with conn.cursor(cursor_factory=DictCursor) as cur:
        # Count records in both tables
        cur.execute("SELECT COUNT(*) FROM expenses_encrypted")
        encrypted_count = cur.fetchone()['count']
        
        if encrypted_count != expected_count:
            print(f"Warning: Expected {expected_count} records, found {encrypted_count}")
            return False
        
        # Verify we can decrypt a sample of records
        cur.execute("""
            SELECT * FROM expenses_encrypted 
            ORDER BY RANDOM() 
            LIMIT 5
        """)
        
        for row in cur.fetchall():
            try:
                encryptor = ExpenseEncryptor.from_salt_hex(passphrase, row['salt_hex'])
                decrypted = encryptor.decrypt_expense({
                    'date': bytes(row['date_encrypted']).decode('utf-8'),
                    'amount': bytes(row['amount_encrypted']).decode('utf-8'),
                    'category': bytes(row['category_encrypted']).decode('utf-8'),
                    'description': bytes(row['description_encrypted']).decode('utf-8') if row['description_encrypted'] else ''
                })
                print(f"Verified: {decrypted['date']} - {decrypted['amount']} {decrypted['category']}")
            except Exception as e:
                print(f"Verification failed: {e}")
                return False
        
        return True

def main():
    """Run the migration."""
    load_dotenv()
    
    # Get passphrase from user or use default for testing
    passphrase = os.getenv("ENCRYPTION_PASSPHRASE", DEFAULT_PASSPHRASE)
    if passphrase == DEFAULT_PASSPHRASE:
        print("WARNING: Using default encryption passphrase. This is not secure for production!")
    
    print("Starting database migration...")
    
    try:
        conn = get_db_connection()
        conn.autocommit = False  # Use transaction
        
        # Count existing expenses
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM expenses")
            count = cur.fetchone()[0]
            
        if count == 0:
            print("No expenses found to migrate")
            return
            
        print(f"Found {count} expenses to migrate")
        
        # Migrate the data
        migrated_count = migrate_data(conn, passphrase)
        
        if migrated_count == 0:
            print("No data was migrated")
            return
            
        # Verify the migration
        print("Verifying migration...")
        if verify_migration(conn, passphrase, migrated_count):
            print("Migration verified successfully!")
            
            # Ask for confirmation before proceeding with the final steps
            if input("\nMigration verified. Proceed with replacing tables? (y/n): ").lower() == 'y':
                # Replace the tables
                with conn.cursor() as cur:
                    # Rename old table
                    cur.execute("ALTER TABLE expenses RENAME TO expenses_old")
                    # Rename new table
                    cur.execute("ALTER TABLE expenses_encrypted RENAME TO expenses")
                    # Drop the old table
                    cur.execute("DROP TABLE expenses_old")
                    print("Migration completed successfully!")
                    conn.commit()
            else:
                print("Migration aborted by user")
                conn.rollback()
        else:
            print("Migration verification failed. Rolling back changes.")
            conn.rollback()
            
    except Exception as e:
        print(f"Error during migration: {e}")
        if 'conn' in locals():
            conn.rollback()
        raise
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
