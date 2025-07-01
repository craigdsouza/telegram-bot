import os, json, base64
from dotenv import load_dotenv  # load local .env
import psycopg2
import logging
from sheets import (
    authenticate_google_sheets,
    get_or_create_worksheet,
    get_existing_sheet_ids,
    remove_deleted_records,
    append_data_to_sheet
)
from db import fetch_new_entries
from gspread.exceptions import WorksheetNotFound  # for tab creation

# Enable logging
logging.basicConfig(
    filename='sync_google_sheet.log',
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

load_dotenv()

# Connect to Postgres
dsn = os.getenv("DATABASE_PUBLIC_URL")  # public proxy
conn = psycopg2.connect(dsn)
cur = conn.cursor()

# Auth to Google Sheets
sh = authenticate_google_sheets()

# Select or create that tab
TAB_NAME = "sync-daily-expenses"   # ← whatever tab you want
ws = get_or_create_worksheet(sh, TAB_NAME)

# Read existing IDs from Google Sheet
values = ws.get_all_values()
if not values:
    logger.info("Google Sheet is empty, adding header row")
    ws.append_row(["id","user_id", "date", "amount", "category", "description", "created_at", "mode"])
else:
    logger.info("Google Sheet is not empty")
    logger.info(f"Found this in Google Sheet: {values}")

gsheet_ids = get_existing_sheet_ids(ws)    # Get all IDs from Google Sheet
logger.info(f"Found {len(gsheet_ids)} existing records in Google Sheet")

# Remove records deleted from Google Sheet
cur.execute("SELECT id FROM expenses")        
db_ids = {row[0] for row in cur.fetchall()}   # Get all IDs from Postgres DB
logger.info(f"Found {len(db_ids)} existing records in Postgres DB")

deleted_ids = db_ids - gsheet_ids           # Find IDs that exist in Postgres DB but not in Google Sheet
if deleted_ids:
    logger.info(f"Found {len(deleted_ids)} deleted records in Postgres DB with IDs: {deleted_ids}")
    remove_deleted_records(ws, deleted_ids)
    logger.info(f"Removed {len(deleted_ids)} deleted records from Google Sheet with IDs: {deleted_ids}")

# Query only latest rows in Postgres DB by id
if gsheet_ids:
    last_id = max(gsheet_ids)
    new_rows = fetch_new_entries(conn, last_id)
    logger.info(f"Found {len(new_rows)} new rows after last ID: {last_id}")
else:
    new_rows = fetch_new_entries(conn)
    logger.info(f"Found {len(new_rows)} new rows")
cur.close()
conn.close()

# Append only new rows
if new_rows:
    logger.info(f"Attempting to sync {len(new_rows)} new rows to Google Sheet with IDs: {new_rows}")
    append_data_to_sheet(ws, new_rows)
    logger.info(f"Synced {len(new_rows)} new rows to Google Sheet with IDs: {new_rows}")
