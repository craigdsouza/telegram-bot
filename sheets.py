"""
sheets.py

Utility functions to sync Postgres 'expenses' table with a Google Sheet.
"""
import os
import json
import base64
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import WorksheetNotFound

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


def remove_deleted_records(ws, ids_to_delete):
    """
    Remove rows from the sheet for any ID no longer in the database.
    ids_to_delete: set of int IDs to delete
    """
    if not ids_to_delete:
        return
    values = ws.get_all_values()
    rows_to_delete = []
    for idx, row in enumerate(values[1:], start=2):
        try:
            if int(row[0]) in ids_to_delete:
                rows_to_delete.append(idx)
        except:
            continue
    for row_idx in sorted(rows_to_delete, reverse=True):
        ws.delete_rows(row_idx)


def append_data_to_sheet(ws, rows):
    """
    Append each tuple (id, date, amount, category, description) as a new row.
    """
    for id_val, date_val, amount_val, category, description in rows:
        ws.append_row([
            id_val,
            date_val.isoformat(),
            float(amount_val),
            category,
            description
        ])
