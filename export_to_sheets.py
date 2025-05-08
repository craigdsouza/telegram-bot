import os, json, base64
from dotenv import load_dotenv  # load local .env
import psycopg2
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import WorksheetNotFound  # for tab creation

load_dotenv()

# 1) Connect to Postgres
dsn = os.getenv("DATABASE_PUBLIC_URL")  # public proxy
conn = psycopg2.connect(dsn)
cur = conn.cursor()

# 2) Auth to Google Sheets
scopes = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
# Load service account JSON from base64 env
creds_b64 = os.getenv("SERVICE_ACCOUNT_JSON_B64")
if not creds_b64:
    raise ValueError("Missing SERVICE_ACCOUNT_JSON_B64 environment variable")
creds_json = base64.b64decode(creds_b64).decode('utf-8')
creds_dict = json.loads(creds_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scopes)
client = gspread.authorize(creds)

# 2) Open your spreadsheet
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
TAB_NAME = "test-daily-expenses"   # ← whatever tab you want
sh = client.open_by_key(SHEET_ID)

# 3) Select or create that tab
try:
    ws = sh.worksheet(TAB_NAME)
except WorksheetNotFound:
    ws = sh.add_worksheet(
        title=TAB_NAME,
        rows="1000",
        cols="5"
    )

# 4) Read existing IDs from sheet
existing = ws.get_all_values()
if not existing:
    # Write header if sheet is empty
    ws.append_row(["ID", "Date", "Amount", "Category", "Description"])
    existing_ids = set()
else:
    # Skip header row, collect existing IDs
    existing_ids = set()
    for row in existing[1:]:
        try:
            existing_ids.add(int(row[0]))
        except:
            continue

# 5) Remove records deleted from Postgres
cur.execute("SELECT id FROM expenses")
db_ids = {row[0] for row in cur.fetchall()}
deleted_ids = existing_ids - db_ids
if deleted_ids:
    # Delete sheet rows for removed IDs (reverse order)
    rows_to_delete = []
    for idx, row in enumerate(existing[1:], start=2):
        if int(row[0]) in deleted_ids:
            rows_to_delete.append(idx)
    for row_idx in sorted(rows_to_delete, reverse=True):
        ws.delete_rows(row_idx)
    existing_ids &= db_ids

# 6) Query only new rows
if existing_ids:
    last_id = max(existing_ids)
    cur.execute(
        "SELECT id, date, amount, category, description FROM expenses WHERE id > %s ORDER BY id",
        (last_id,)
    )
else:
    cur.execute(
        "SELECT id, date, amount, category, description FROM expenses ORDER BY id"
    )
new_rows = cur.fetchall()
cur.close()
conn.close()

# 7) Append only new rows
for id_val, date_val, amount_val, category, description in new_rows:
    ws.append_row([
        id_val,
        date_val.isoformat(),
        float(amount_val),
        category,
        description
    ])