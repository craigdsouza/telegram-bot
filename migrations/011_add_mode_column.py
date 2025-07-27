#!/usr/bin/env python3
"""
Migration 011: Add mode column to expenses table

This migration adds a 'mode' column to the expenses table to track
the payment method used for each expense (UPI, CASH, DEBIT CARD, CREDIT CARD).
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# Add the parent directory to the path so we can import from data
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.db import get_connection

def migrate():
    """Add mode column to expenses table"""
    print("🔄 Starting migration 011: Add mode column to expenses table")
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Check if mode column already exists
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'expenses' AND column_name = 'mode'
            """)
            
            if cur.fetchone():
                print("✅ Mode column already exists, skipping migration")
                return
            
            # Add mode column with default value
            print("📝 Adding mode column to expenses table...")
            cur.execute("""
                ALTER TABLE expenses 
                ADD COLUMN mode TEXT DEFAULT 'CASH'
            """)
            
            # Add a check constraint to ensure valid modes
            print("🔒 Adding check constraint for valid modes...")
            cur.execute("""
                ALTER TABLE expenses 
                ADD CONSTRAINT check_valid_mode 
                CHECK (mode IN ('UPI', 'CASH', 'DEBIT CARD', 'CREDIT CARD'))
            """)
            
            conn.commit()
            print("✅ Successfully added mode column to expenses table")
            
    except Exception as e:
        conn.rollback()
        print(f"❌ Error during migration: {e}")
        raise
    finally:
        conn.close()

def rollback():
    """Rollback the migration by removing the mode column"""
    print("🔄 Rolling back migration 011: Remove mode column from expenses table")
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Remove the check constraint first
            print("🔓 Removing check constraint...")
            cur.execute("""
                ALTER TABLE expenses 
                DROP CONSTRAINT IF EXISTS check_valid_mode
            """)
            
            # Remove the mode column
            print("📝 Removing mode column from expenses table...")
            cur.execute("""
                ALTER TABLE expenses 
                DROP COLUMN IF EXISTS mode
            """)
            
            conn.commit()
            print("✅ Successfully removed mode column from expenses table")
            
    except Exception as e:
        conn.rollback()
        print(f"❌ Error during rollback: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    load_dotenv()
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback()
    else:
        migrate() 