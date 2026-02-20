Here's the complete file exactly as it should be:
pythonimport os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from googleapiclient.discovery import build
from google.oauth2 import service_account
from datetime import datetime, timedelta

# --- Configuration ---
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
RECIPIENT_EMAIL = "leahmcgann@gmail.com"
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")

# --- Get yesterday's date ---
def get_yesterday():
    yesterday = datetime.now() - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d")

# --- Read daily totals from Google Sheets ---
def get_daily_totals(date):
    creds_json = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
    creds = service_account.Credentials.from_service_account_info(
        creds_json,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    service = build("sheets", "v4", credentials=creds)
    sheets = service.spreadsheets()
    result = sheets.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range="Daily Totals!A2:I1000"
    ).execute()
    rows = result.get("values", [])
    for row in rows:
        if row and row[0] == date:
            return {
                "date": row[0],
                "calories": row[1] if len(row) > 1 else "N/A",
                "protein": row[2] if len(row) > 2 else "N/A",
                "protein_pct": row[3] if len(row) > 3 else "N/A",
                "carbs": row[4] if len(row) > 4 else "N/A",
                "carbs_pct": row[5] if len(row) > 5 else "N/A",
                "fat": row[6] if len(row) > 6 else "N/A",
                "fat_pct": row[7] if len(row) > 7 else "N/A",
                "fiber": row[8] if len(row) > 8 else "N/A",
            }
    return None

# --- Send the email ---
def send_email(totals):
    subject = f"Your Nutrition Summary for {totals['date']}"
    body = f"""
Good morning! Here's your nutrition summary for {totals['date']}:

Calories:  {totals['calories']} kcal

Protein:   {totals['protein']}g ({totals['protein_pct']})
Carbs:     {totals['carbs']}g ({totals['carbs_pct']})
Fat:       {totals['fat']}g ({totals['fat_pct']})

Fiber:     {totals['fiber']}g

Have a great day!
"""
    msg = MIMEMultipart()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = RECIPIENT_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, RECIPIENT_EMAIL, msg.as_string())
    print("Email sent successfully!")

# --- Main ---
if __name__ == "__main__":
    yesterday = get_yesterday()
    print(f"Looking up totals for {yesterday}...")
    totals = get_daily_totals(yesterday)
    if totals:
        send_email(totals)
    else:
        print(f"No data found for {yesterday}")