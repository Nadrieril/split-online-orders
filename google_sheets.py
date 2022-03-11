#!/usr/bin/env python3
import sys, os, io, math, re, json, csv

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import googleapiclient.discovery

# If modifying these scopes, delete the token file.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
TOKEN_FILE = '.google-token.json'
CREDENTIALS_FILE = '.google-credentials.json'
SPREADSHEET_DATA_FILE = '.google-spreadsheet-data.json'

def login_to_google_api():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is created automatically
    # when the authorization flow completes for the first time.
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return googleapiclient.discovery.build('sheets', 'v4', credentials=creds)

with open(SPREADSHEET_DATA_FILE) as f:
    data = json.load(f)
    SPREADSHEET_ID = data['id']

# This assumes a specific spreadsheet template.
INPUT_RANGE = "Input!A1:C"
CHECKBOX_RANGE = "Boxes!D6:R"
CHECKBOX_RANGEOBJ = {
    "sheetId": 0,
    "startRowIndex": 5,
    "startColumnIndex": 3,
    "endColumnIndex": 18,
}
def setup_new_input_data(service, data, spreadsheet_id=SPREADSHEET_ID):
    service.spreadsheets().values().clear(spreadsheetId=spreadsheet_id, range=CHECKBOX_RANGE).execute()
    body = {
        "requests": [{
            "setDataValidation": {
                "range": CHECKBOX_RANGEOBJ,
                "rule": {
                    "condition": {
                        "type": "BOOLEAN",
                    },
                    "strict": False,
                    "showCustomUi": True,
                },
            }
        }]
    }
    result = service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

    service.spreadsheets().values().clear(spreadsheetId=spreadsheet_id, range=INPUT_RANGE).execute()
    body = {'values': data}
    service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range=INPUT_RANGE,
            valueInputOption="RAW", body=body).execute()

if __name__ == '__main__':
    service = login_to_google_api()

    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID,
                                                 range=INPUT_RANGE).execute()
    data = result.get('values', [])

    if not data:
        raise Exception('No data found')

    writer = csv.writer(sys.stdout, delimiter=',')
    for row in data:
        writer.writerow(row)
