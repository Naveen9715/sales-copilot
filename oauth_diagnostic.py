
import json
from urllib.parse import urlparse, parse_qs

from google_auth_oauthlib.flow import InstalledAppFlow

CREDENTIALS_FILE = "credentials.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
]


def main():
    print("=" * 55)
    print("SALES COPILOT V6 - OAUTH DIAGNOSTIC")
    print("=" * 55)

    try:
        with open(CREDENTIALS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        client_type = "installed" if "installed" in data else (
            "web" if "web" in data else "unknown"
        )
        client = data.get(client_type, {})

        print("Credential type:", client_type)
        print("Authorization endpoint:", client.get("auth_uri", "MISSING"))
        print(
            "Token endpoint host:",
            urlparse(client.get("token_uri", "")).netloc or "MISSING",
        )

        client_id = client.get("client_id", "")
        print(
            "Client ID format:",
            "ends with .apps.googleusercontent.com"
            if client_id.endswith(".apps.googleusercontent.com")
            else "UNEXPECTED FORMAT",
        )

        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE,
            SCOPES,
        )

        original_authorization_url = flow.authorization_url

        def diagnostic_authorization_url(*args, **kwargs):
            url, state = original_authorization_url(*args, **kwargs)
            parsed = urlparse(url)
            params = parse_qs(parsed.query)

            print("\n--- Generated authorization request ---")
            print("Authorization host:", parsed.netloc)
            print("Authorization path:", parsed.path)
            print("Response type:", params.get("response_type", ["MISSING"])[0])
            print("Redirect URI:", params.get("redirect_uri", ["MISSING"])[0])
            print("Requested scopes:", params.get("scope", ["MISSING"])[0])
            print(
                "PKCE method:",
                params.get("code_challenge_method", ["not present"])[0],
            )
            print("Client ID present:", bool(params.get("client_id")))
            print("Full authorization URL hidden for safety.")
            print("\nOpening Google's authorization page now...")

            return url, state

        flow.authorization_url = diagnostic_authorization_url

        flow.run_local_server(port=0)

        print("\nAuthorization succeeded.")
        print("The diagnostic did not save or replace token.json.")

    except KeyboardInterrupt:
        print("\nDiagnostic stopped by user.")
    except Exception as error:
        print("\nDiagnostic error type:", type(error).__name__)
        print("Diagnostic error:", str(error))


if __name__ == "__main__":
    main()
