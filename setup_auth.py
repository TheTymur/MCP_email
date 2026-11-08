import os
import argparse
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SCOPES = [
    'https://mail.google.com/',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.settings.basic'
]

def authenticate_account(account: str = "personal"):
    """Authenticates a specific account and saves its token file."""
    token_file = f"token_{account}.json"
    legacy_file = "token.json" if account in ("personal", "default") else None

    target_file = token_file
    if legacy_file and os.path.exists(legacy_file) and not os.path.exists(token_file):
        target_file = legacy_file

    creds = None
    if os.path.exists(target_file):
        creds = Credentials.from_authorized_user_file(target_file, SCOPES)
    elif legacy_file and os.path.exists(legacy_file):
        creds = Credentials.from_authorized_user_file(legacy_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print(f"Refreshing credentials for account '{account}'...")
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("ERROR: credentials.json not found! You must download it from Google Cloud Console.")
                return False
            print(f"Starting authentication flow for account '{account}'. A browser window should open...")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_file, 'w') as token:
            token.write(creds.to_json())
        print(f"Successfully saved {token_file}!")

        if account in ("personal", "default"):
            with open("token.json", 'w') as token:
                token.write(creds.to_json())
            print("Successfully updated token.json!")
    else:
        print(f"Credentials for account '{account}' are already valid ({target_file}).")
        if not os.path.exists(token_file):
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
            print(f"Created {token_file} from existing valid credentials.")
    return True

def main():
    parser = argparse.ArgumentParser(description="Authenticate Gmail accounts for the MCP Gmail Server.")
    parser.add_argument(
        "account",
        nargs="?",
        default="personal",
        help="Account identifier to authenticate (e.g. 'personal', 'work'). Defaults to 'personal'."
    )
    args = parser.parse_args()
    authenticate_account(args.account)

if __name__ == '__main__':
    main()
