import os
import base64

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText


# Permission required to send Gmail
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def gmail_login():

    creds = None

    # Check if we already have a login token
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file(
            "token.json",
            SCOPES
        )

    # If login is not valid, login again
    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES
            )

            creds = flow.run_local_server(port=0)

        # Save login information
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds


def send_email(to, subject, message):

    creds = gmail_login()

    service = build(
        "gmail",
        "v1",
        credentials=creds
    )

    email = MIMEText(message)

    email["to"] = to
    email["subject"] = subject

    encoded_message = base64.urlsafe_b64encode(
        email.as_bytes()
    ).decode()

    body = {
        "raw": encoded_message
    }

    result = service.users().messages().send(
        userId="me",
        body=body
    ).execute()

    print("Email sent successfully!")
    print("Message ID:", result["id"])


# ==========================================
# TEST
# ==========================================

to = input("Enter recipient Gmail address: ")

send_email(
    to,
    "Sales Copilot Test",
    "Hello! This is a test email sent using my Sales Copilot Gmail Agent."
)