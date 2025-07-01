"""
sheets.py

Utility functions to sync Postgres 'expenses' table with a Google Sheet.
"""
import os
import json
import time
import base64
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import WorksheetNotFound
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Connect to Postgres
dsn = os.getenv("DATABASE_PUBLIC_URL")  # public proxy



def authenticate_google_sheets():
    """
    Authenticate via service account and open the target spreadsheet.
    Returns a gspread.Spreadsheet instance.
    """
    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_b64 = os.getenv("SERVICE_ACCOUNT_JSON_B64")
    if not creds_b64:
        raise RuntimeError("Missing SERVICE_ACCOUNT_JSON_B64 environment variable")
    creds_json = base64.b64decode(creds_b64).decode("utf-8")
    creds_dict = json.loads(creds_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scopes)
    client = gspread.authorize(creds)
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        raise RuntimeError("GOOGLE_SHEET_ID not set")
    return client.open_by_key(sheet_id)


def get_or_create_worksheet(spreadsheet, tab_name, rows=1000, cols=5):
    """
    Return existing worksheet by title or create it with given dimensions.
    """
    try:
        return spreadsheet.worksheet(tab_name)
    except WorksheetNotFound:
        return spreadsheet.add_worksheet(title=tab_name, rows=str(rows), cols=str(cols))


def get_existing_sheet_ids(ws):
    """
    Read all rows and collect the integer IDs from the first column.
    """
    values = ws.get_all_values()
    if len(values) < 2:
        return set()
    ids = set()
    for row in values[1:]:
        try:
            ids.add(int(row[0]))
        except:
            continue
    return ids

def get_ids_marked_for_deletion(ws):
    """
    Read all rows and collect the integer IDs from the first column.
    """
    values = ws.get_all_values()
    if len(values) < 2:
        return set()
    ids = set()
    for row in values[1:]:
        if row[8] == 'y':
            ids.add(int(row[0]))
    return ids

def remove_db_records_marked_for_deletion(ids_to_delete):
    """
    Remove rows from the Postgres DB for any ID no longer in the Google Sheet.
    ids_to_delete: set of int IDs to delete
    """
    conn = psycopg2.connect(dsn)
    cur = conn.cursor()
    if not ids_to_delete:
        return
    cur.execute("DELETE FROM expenses WHERE id IN %s", (tuple(ids_to_delete),))
    conn.commit()
    cur.close()
    conn.close()

def remove_gsheet_records_marked_for_deletion(ws):
    """
    Remove rows from the Google Sheet for any ID marked for deletion.
    """
    values = ws.get_all_values()
    for i, row in enumerate(values[1:], start=2): # start from 2nd row
        if row[8] == 'y':
            ws.delete_row(i)

def append_data_to_sheet(ws, rows):
    """
    Append each row as a new row to the worksheet.
    rows can be a list of dictionaries or a list of tuples.
    """
    for row in rows:
        time.sleep(0.2)
        if isinstance(row, dict):
            # Handle dictionary format
            ws.append_row([
                row['id'],
                row['user_id'],
                row['date'].strftime('%d-%B-%y'),
                float(row['amount']),
                row['category'],
                row.get('description', '')
            ])
        else:
            # Handle tuple format (legacy)
            id_val, user_id, date_val, amount_val, category, description = row
            ws.append_row([
                id_val,
                user_id,
                date_val.strftime('%d-%B-%y'),
                float(amount_val),
                category,
                description
            ])


