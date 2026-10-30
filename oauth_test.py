from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send"
]

flow = InstalledAppFlow.from_client_secrets_file(
    "credentials.json",
    SCOPES
)

print("Starting Google OAuth...")

creds = flow.run_local_server(
    host="localhost",
    bind_addr="127.0.0.1",
    port=0,
    open_browser=True
)

print("\nSUCCESS!")
print("Google OAuth authorization completed.")

with open("token.json", "w") as token:
    token.write(creds.to_json())

print("token.json created successfully!")