
import os

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

# Exact two scopes from sales_agent_unified_v6.py
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
]


def main():
    print("=" * 55)
    print("SALES COPILOT VERSION 6 - AUTHORIZATION TEST")
    print("=" * 55)

    if not os.path.isfile(CREDENTIALS_FILE):
        print(f"ERROR: {CREDENTIALS_FILE} was not found.")
        print("Make sure it is inside D:\\project\\sales-copilot.")
        return

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE,
            SCOPES,
        )

        # Match the original Version 6 authorization flow.
        credentials = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w", encoding="utf-8") as file:
            file.write(credentials.to_json())

        print("\nGoogle authorization succeeded.")

        # Check that the Google API clients can be initialized.
        gmail = build(
            "gmail",
            "v1",
            credentials=credentials,
            cache_discovery=False,
        )

        calendar = build(
            "calendar",
            "v3",
            credentials=credentials,
            cache_discovery=False,
        )

        print("Gmail API client initialized.")

        # Read a small number of events to verify Calendar access.
        result = calendar.events().list(
            calendarId="primary",
            maxResults=1,
        ).execute()

        print("Google Calendar API access succeeded.")
        print(
            "Calendar access verified. Events returned:",
            len(result.get("items", [])),
        )
        print("\nSUCCESS: Version 6 authorization test passed.")
        print("You can now close this test and run your Sales Agent.")

    except Exception as error:
        print("\nTEST FAILED")
        print("Error type:", type(error).__name__)
        print("Error details:", str(error))


if __name__ == "__main__":
    main()
