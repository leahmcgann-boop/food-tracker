import json
import os
import anthropic
from googleapiclient.discovery import build
from google.oauth2 import service_account
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- Configuration ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
SHEET_NAME = "Log"

# --- Set up Google Sheets connection ---
def get_sheets_client():
    creds_json = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
    creds = service_account.Credentials.from_service_account_info(
        creds_json,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    service = build("sheets", "v4", credentials=creds)
    return service.spreadsheets()

# --- Ask Claude to parse the meal ---
def parse_meal(entry):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": f"""You are a nutrition tracking assistant. The user will describe what they ate.
Extract the meal type (breakfast/lunch/dinner/snack), a clean description, and estimate
calories, protein (g), carbs (g), fat (g), and fiber (g). Be concise and realistic with estimates.
Return only valid JSON in this exact format with no other text:
{{"meal_type": "", "description": "", "calories": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0, "notes": ""}}

User entry: {entry}"""
            }
        ]
    )
    raw = message.content[0].text
    clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(clean)

# --- Write the row to Google Sheets ---
def log_to_sheet(meal_data):
    sheets = get_sheets_client()
    from datetime import timezone, timedelta
    est = timezone(timedelta(hours=-5))
    timestamp = datetime.now(est).strftime("%Y-%m-%d %H:%M")
    row = [[
        timestamp,
        meal_data["meal_type"],
        meal_data["description"],
        meal_data["calories"],
        meal_data["protein"],
        meal_data["carbs"],
        meal_data["fat"],
        meal_data["fiber"],
        meal_data["notes"]
    ]]
    sheets.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A:I",
        valueInputOption="RAW",
        body={"values": row}
    ).execute()

# --- Web endpoint ---
@app.route("/log", methods=["POST"])
def log_meal():
    try:
        data = request.get_json()
        entry = data.get("entry", "")
        if not entry:
            return jsonify({"error": "No food entry provided"}), 400
        meal_data = parse_meal(entry)
        log_to_sheet(meal_data)
        return jsonify({"message": "Logged successfully!", "meal": meal_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

