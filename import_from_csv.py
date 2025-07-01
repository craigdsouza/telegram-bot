"""
import_from_csv.py

One-time script to clear and bulk import expenses from a CSV file into Postgres.
Usage: python import_from_csv.py path/to/file.csv
"""
import os
import sys
import csv
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import argparse

def main():
    """
    One-time script to clear and bulk import expenses from a CSV file into Postgres.
    Usage: python import_from_csv.py path/to/file.csv

    Args:
        csv_path: Path to CSV file
        clear: Clear table before import
    
    Requires:
        DATABASE_PUBLIC_URL or DATABASE_URL environment variable
        CSV file with columns in this order: sno, user_id, date, amount, category, description, mode
        sno is not used directly but it can be integers
        user_id must be an integer, cannot be null
        date must be in format dd-Mon-yy
        amount must be a float
        category must be one of the categories in categories.py
        description can be empty
        mode can be empty
    """
    parser = argparse.ArgumentParser(
        description="Import expenses from CSV. Append by default, use --clear to truncate first."
    )
    parser.add_argument('csv_path', help='Path to CSV file')
    parser.add_argument('--clear', action='store_true', help='Clear table before import')
    args = parser.parse_args()
    load_dotenv()
    # Use public proxy URL or DATABASE_URL
    url = os.getenv("DATABASE_PUBLIC_URL") or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_PUBLIC_URL or DATABASE_URL not set")
    conn = psycopg2.connect(url)
    try:
        with conn:
            with conn.cursor() as cur:
                # Clear existing data if requested
                if args.clear:
                    cur.execute("TRUNCATE TABLE expenses RESTART IDENTITY CASCADE;")
                    print("Cleared expenses table.")
                else:
                    print("Append mode: existing data preserved.")

                csv_path = args.csv_path

                # Read and prepare rows
                rows = []
                with open(csv_path, newline='') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        # Parse fields
                        user_id = row.get("user_id", "")
                        date_val = datetime.strptime(row.get("date", ""), "%d-%b-%y").date()
                        amount = float(row.get("amount", 0))
                        category = row.get("category", "").strip()
                        description = row.get("description", "").strip() or None
                        mode = row.get("mode", "").strip() or None
                        rows.append((user_id, date_val, amount, category, description, mode))
                        print(f"Prepared row: {user_id}, {date_val}, {amount}, {category}, {description}, {mode}")
                # Bulk insert
                sql = (
                    "INSERT INTO expenses (user_id, date, amount, category, description, mode) VALUES %s"
                )
                execute_values(cur, sql, rows)
                print(f"Inserted {len(rows)} rows into expenses.")
    finally:
        conn.close()

if __name__ == '__main__':
    main()
