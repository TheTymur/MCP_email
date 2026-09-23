import os
from fastmcp import FastMCP
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Define the scopes for Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    """Authenticates and returns the Gmail service."""
    creds = None
    # token.json stores the user's access and refresh tokens
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no valid credentials, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("WARNING: credentials.json not found! You must download it from Google Cloud Console.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

# 1. Create the server
mcp = FastMCP("Gmail Server")

# 2. Initialize the Gmail service globally so tools can use it
service = get_gmail_service()

# 3. Define the tool
@mcp.tool()
def read_recent_emails(limit: int = 5) -> str:
    """Reads the most recent emails from the user's Gmail inbox. 
    IMPORTANT: This returns a list of emails. Each email has an 'ID' field. You MUST save and use this exact 'ID' if you need to read the full content, reply, forward, or delete the email later."""
    if not service:
        return "Error: Gmail service is not authenticated. Missing credentials.json or token.json."
        
    try:
        results = service.users().messages().list(userId="me", labelIds=["INBOX"], maxResults=limit).execute()
        messages = results.get("messages", [])

        if not messages:
            return "No new emails found."
        
        email_data = []
        for msg in messages:
            # Fetch the full message to get headers and snippet
            txt = service.users().messages().get(userId="me", id=msg["id"]).execute()
            snippet = txt.get("snippet", "No preview available")
            
            # Extract headers (like Subject, From, To) from the payload
            headers = txt.get("payload", {}).get("headers", [])
            subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "No Subject")
            sender = next((h["value"] for h in headers if h["name"].lower() == "from"), "Unknown Sender")
            recipient = next((h["value"] for h in headers if h["name"].lower() == "to"), "Unknown Recipient")
            date = next((h["value"] for h in headers if h["name"].lower() == "date"), "Unknown Date")
            msg_id = next((h["value"] for h in headers if h["name"].lower() == "message-id"), "No Message-ID")

            email_data.append(f"- ID: {msg['id']} | Message-ID: {msg_id} | Date: {date} | From: {sender} | To: {recipient} | Subject: {subject} | Snippet: {snippet}")
        
        return "\n".join(email_data)

    except Exception as error:
        return f"An error occurred connecting to Gmail: {error}"


if __name__ == "__main__":
    # 4. Run the server
    mcp.run()
