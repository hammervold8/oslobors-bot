import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from datetime import datetime

def log_to_sheet(job, decision, raw):
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "service_account.json", scope
    )
    client = gspread.authorize(creds)
    sheet = client.open("OsloBotLogs").sheet1
    sheet.append_row([datetime.now().isoformat(), job, decision, raw])
