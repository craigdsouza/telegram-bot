import os, json, base64
from dotenv import load_dotenv  # load local .env
import psycopg2
from sheets import (
    authenticate_google_sheets,
    get_or_create_worksheet,
    get_existing_sheet_ids,
    remove_deleted_records,
    append_data_to_sheet
)
from db import fetch_new_entries
from gspread.exceptions import WorksheetNotFound  # for tab creation

load_dotenv()

# 1) Connect to Postgres
dsn = os.getenv("DATABASE_PUBLIC_URL")  # public proxy
conn = psycopg2.connect(dsn)
cur = conn.cursor()

# 2) Auth to Google Sheets
sh = authenticate_google_sheets()

# 3) Select or create that tab
TAB_NAME = "test-daily-expenses"   # ← whatever tab you want
ws = get_or_create_worksheet(sh, TAB_NAME)

# 4) Read existing IDs from sheet
values = ws.get_all_values()
if not values:
    ws.append_row(["ID", "Date", "Amount", "Category", "Description"])
existing_ids = get_existing_sheet_ids(ws)

# 5) Remove records deleted from Postgres
cur.execute("SELECT id FROM expenses")
db_ids = {row[0] for row in cur.fetchall()}
deleted_ids = existing_ids - db_ids            # Compare existing IDs with DB IDs
if deleted_ids:
    remove_deleted_records(ws, deleted_ids)

# 6) Query only new rows
if existing_ids:
    last_id = max(existing_ids)
    new_rows = fetch_new_entries(conn, last_id)
    print(f"found {len(new_rows)} new rows")
else:
    new_rows = fetch_new_entries(conn)
    print(f"found {len(new_rows)} new rows")
cur.close()
conn.close()

# 7) Append only new rows
print("attempting to sync new rows:",new_rows)
append_data_to_sheet(ws, new_rows)
