import os
import socket
import ipaddress
import re
import requests
import base64
from urllib.parse import urlparse, unquote, parse_qs
from email.message import EmailMessage
from bs4 import BeautifulSoup
from fastmcp import FastMCP
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://mail.google.com/',
    'https://www.googleapis.com/auth/gmail.settings.basic'
]

mcp = FastMCP("Gmail Server")

def get_gmail_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
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
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

service = get_gmail_service()

# --- Helper Functions ---
def _extract_body(part):
    found_text = ""
    found_html = ""
    if part.get('mimeType') == 'text/plain' and 'data' in part.get('body', {}):
        found_text = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
    elif part.get('mimeType') == 'text/html' and 'data' in part.get('body', {}):
        found_html = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
    
    if 'parts' in part:
        for subpart in part['parts']:
            sub_text, sub_html = _extract_body(subpart)
            if sub_text: found_text += sub_text
            if sub_html: found_html += sub_html
            
    return found_text, found_html

def _parse_email(msg_data):
    """Helper to parse headers and body from Gmail API response."""
    payload = msg_data.get("payload", {})
    headers = payload.get("headers", [])
    
    sender, recipient, subject, date, message_id = "Unknown", "Unknown", "No Subject", "Unknown", None
    in_reply_to, references, cc, reply_to = "None", "None", "", "Unknown"
    
    for header in headers:
        name = header['name'].lower()
        if name == 'from': sender = header['value']
        elif name == 'to': recipient = header['value']
        elif name == 'cc': cc = header['value']
        elif name == 'subject': subject = header['value']
        elif name == 'reply-to': reply_to = header['value']
        elif name == 'date': date = header['value']
        elif name == 'message-id': message_id = header['value']
        elif name == 'in-reply-to': in_reply_to = header['value']
        elif name == 'references': references = header['value']

    plain_text, html_text = _extract_body(payload)
    
    body = "No Body available"
    if html_text:
        soup = BeautifulSoup(html_text, "html.parser")
        body = soup.get_text(separator="\n", strip=True)
    elif plain_text:
        body = plain_text
    else:
        body = msg_data.get("snippet", "No Body available")
        
    return {
        "sender": sender, "recipient": recipient, "cc": cc, 
        "subject": subject, "date": date, "message_id": message_id,
        "in_reply_to": in_reply_to, "references": references,
        "reply_to": reply_to, "body": body
    }

def _is_safe_url(url: str):
    """Only allow https URLs that resolve to public IPs. Anti Server-Side Request Forgery (SSRF)."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    try:
        for info in socket.getaddrinfo(parsed.hostname, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
    except (socket.gaierror, ValueError):
        return False
    return True

# --- Email Reading/Searching Tools ---
@mcp.tool()
def read_recent_emails(limit: int = 5) -> str:
    """Reads the most recent emails from the user's Gmail inbox. 
    IMPORTANT: This returns a list of emails. Each email has an 'ID' field. You MUST save and use this exact 'ID' if you need to read the full content, reply, forward, or delete the email later."""
    if not service:
        return "Error: Gmail service is not authenticated."
    try:
        results = service.users().messages().list(userId="me", labelIds=["INBOX"], maxResults=limit).execute()
        messages = results.get("messages", [])

        if not messages:
            return "No new emails found."
    
        email_data = []
        for msg in messages:
            txt = service.users().messages().get(userId="me", id=msg["id"]).execute()
            parsed = _parse_email(txt)

            snippet = txt.get("snippet", "No preview available")
            email_data.append(f"- ID: {msg['id']} | Message-ID: {parsed['message_id']} | Date: {parsed['date']} | From: {parsed['sender']} | To: {parsed['recipient']} | Subject: {parsed['subject']} | Snippet: {snippet}")
    
        return "\n".join(email_data)

    except Exception as error:
        return f"An error occurred connecting to Gmail: {error}"

@mcp.tool()
def search_emails(query: str) -> str:
    """
    Searches for emails in the user's Gmail account based on a query. 
    IMPORTANT: This returns a list of emails. Each email has an 'ID' field. You MUST save and use this exact 'ID' if you need to read the full content, reply, forward, or delete the email later.
    """
    if not service:
        return "Error: Gmail service is not authenticated."
    try:
        results = service.users().messages().list(userId="me", q=query, maxResults=5).execute()
        messages = results.get("messages", [])

        if not messages:
            return "No emails found matching that query."
    
        email_data = []
        for msg in messages:
            txt = service.users().messages().get(userId="me", id=msg["id"]).execute()
            parsed = _parse_email(txt)

            snippet = txt.get("snippet", "No preview available")
            email_data.append(f"- ID: {msg['id']} | Message-ID: {parsed['message_id']} | Date: {parsed['date']} | From: {parsed['sender']} | To: {parsed['recipient']} | Subject: {parsed['subject']} | Snippet: {snippet}")
    
        return "\n".join(email_data)

    except Exception as error:
        return f"An error occurred searching for emails: {error}"

@mcp.tool()
def read_email_content(email_id: str) -> str:
    """Reads the full content of a specific email in the user's Gmail account.
    You MUST provide the 'email_id' parameter. You can find the email_id by first calling the 'read_recent_emails' or 'search_emails' tools and looking for the 'ID:' field in the results."""
    if not service:
        return "Error: Gmail service is not authenticated."
    try:
        txt = service.users().messages().get(userId="me", id=email_id).execute()
        parsed = _parse_email(txt)
        
        body = parsed['body']
        if len(body) > 2000:
            body = body[:2000] + "\n\n...[EMAIL BODY TRUNCATED TO SAVE TOKENS]..."
            
        cc_string = f" | Cc: {parsed['cc']}" if parsed['cc'] else ""
        return f"- ID: {email_id} | Message-ID: {parsed['message_id']} | Date: {parsed['date']} | From: {parsed['sender']} | To: {parsed['recipient']}{cc_string} | Reply-to: {parsed['reply_to']} | In-Reply-To: {parsed['in_reply_to']} | References: {parsed['references']} | Subject: {parsed['subject']} | Body:\n{body}"
        
    except Exception as error:
        return f"An error occurred reading the email content: {error}"

# --- Label Management Tools ---
@mcp.tool()
def create_label(label_name: str) -> str:
    """Creates a new label in the user's Gmail account."""
    if not service:
        return "Error: Gmail service is not authenticated."
    try:
        label = service.users().labels().create(userId="me", body={
            "name": label_name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show"
        }).execute()
        return f"Label '{label_name}' created successfully and its ID is {label['id']}."
    except Exception as error:
        return f"An error occurred creating the label: {error}"

@mcp.tool()
def list_labels() -> str:
    """Lists all labels in the user's Gmail account."""
    if not service:
        return "Error: Gmail service is not authenticated."
    try:
        results = service.users().labels().list(userId="me").execute()
        labels = results.get("labels", [])

        if not labels:
            return "No labels found."
    
        label_data = []
        for label in labels:
            label_data.append(f"- ID: {label['id']} | Name: {label['name']}")
    
        return "\n".join(label_data)
    except Exception as error:
        return f"An error occurred listing the labels: {error}"

@mcp.tool()
def apply_label(email_id: str, label_id: str) -> str:
    """Applies a label to a message in the user's Gmail account."""
    if not service:
        return "Error: Gmail service is not authenticated."
    try:
        service.users().messages().modify(userId="me", id=email_id, body={
            "addLabelIds": [label_id]
        }).execute()
        return f"Label '{label_id}' applied to message '{email_id}' successfully."
    except Exception as error:
        return f"An error occurred applying the label: {error}" 

@mcp.tool()
def remove_label(email_id: str, label_id: str) -> str:
    """Removes a label from a message in the user's Gmail account.
    Also you can use this tool to mark email as read by setting the label_id to "UNREAD".
    """
    if not service:
        return "Error: Gmail service is not authenticated."
    try:
        service.users().messages().modify(userId="me", id=email_id, body={
            "removeLabelIds": [label_id]
        }).execute()
        return f"Label '{label_id}' removed from message '{email_id}' successfully."
    except Exception as error:
        return f"An error occurred removing the label: {error}" 

@mcp.tool()
def delete_label(label_id: str) -> str:
    """Deletes a label from the user's Gmail account. """
    if not service:
        return "Error: Gmail service is not authenticated."
    try:
        service.users().labels().delete(userId="me", id=label_id).execute()
        return f"Label '{label_id}' deleted successfully."
    except Exception as error:
        return f"An error occurred deleting the label: {error}"

@mcp.tool()
def count_messages_in_label(label_id: str) -> str:
    """Counts the number of messages in a specific label in the user's Gmail account."""
    if not service:
        return "Error: Gmail service is not authenticated."
    try:
        results = service.users().messages().list(userId="me", labelIds=[label_id]).execute()
        message_count = results.get("resultSizeEstimate", 0)
        return f"The label '{label_id}' has {message_count} message(s)."
    except Exception as error:
        return f"An error occurred counting messages in label '{label_id}': {error}"

# --- Email Management Tools ---
@mcp.tool()
def delete_message(email_id: str) -> str:
    """
    Deletes an email or moves it to the trash. 
    If the user asks to 'trash', 'remove', or 'delete' an email, use this tool. 
    You MUST provide the 'email_id'. Look in the previous tool responses for the exact ID of the email you are trying to delete.
    CRITICAL: NEVER guess or hallucinate the ID. If you don't know the exact ID, you MUST call 'read_recent_emails' or 'search_emails' FIRST and wait for the results. Do NOT call this tool and a search tool in the same turn.
    Note: To undo a deletion, use the `untrash_message` tool.
    """
    if not service:
        return "Error: Gmail service is not authenticated."
    try:
        msg = service.users().messages().get(userId="me", id=email_id, format="metadata").execute()
        if 'TRASH' in msg.get('labelIds', []):
            service.users().messages().delete(userId="me", id=email_id).execute()
            return f"Message '{email_id}' permanently deleted from trash successfully."
        else:
            service.users().messages().trash(userId="me", id=email_id).execute()
            return f"Message '{email_id}' moved to trash successfully."
    except Exception as error:
        return f"An error occurred deleting the message: {error}"

@mcp.tool()
def untrash_message(email_id: str) -> str:
    """
    Removes an email from the trash and restores it to the inbox.
    Use this tool if the user asks to undo a deletion, restore a deleted email, or move an email out of the trash.
    """
    if not service:
        return "Error: Gmail service is not authenticated."
    try:
        service.users().messages().untrash(userId="me", id=email_id).execute()
        return f"Message '{email_id}' restored from trash successfully."
    except Exception as error:
        return f"An error occurred untrashing the message: {error}"

# --- Draft Management Tools ---
@mcp.tool()
def delete_draft(draft_id: str) -> str:
    """Deletes a draft from the user's Gmail account."""
    if not service:
        return "Error: Gmail service is not authenticated."
    try:
        service.users().drafts().delete(userId="me", id=draft_id).execute()
        return f"Draft '{draft_id}' deleted successfully."
    except Exception as error:
        return f"An error occurred deleting the draft: {error}"

@mcp.tool()
def list_drafts() -> str:
    """Lists all drafts and its details (To, Subject, Body) in the user's Gmail account."""
    if not service:
        return "Error: Gmail service is not authenticated."
    try:
        results = service.users().drafts().list(userId="me").execute()
        drafts = results.get("drafts", [])

        if not drafts:
            return "No drafts found."
    
        draft_data = []
        for draft in drafts:
            txt = service.users().drafts().get(userId="me", id=draft["id"]).execute()
            message = txt.get("message", {})
            payload = message.get("payload", {})
            headers = payload.get("headers", [])
            
            to = "No To available"
            subject = "No Subject available"
            date = "Unknown"
            
            for header in headers:
                name = header['name'].lower()
                if name == 'to': to = header['value']
                elif name == 'subject': subject = header['value']
                elif name == 'date': date = header['value']
            
            snippet = message.get("snippet", "No Body available")
            draft_data.append(f"- ID: {draft['id']} | Date: {date} | To: {to} | Subject: {subject} | Body: {snippet}")
    
        return "\n".join(draft_data)

    except Exception as error:
        return f"An error occurred listing the drafts: {error}"

@mcp.tool()
def create_draft(to: str, subject: str, message: str) -> str:
    """Creates a draft with To, Subject and Message in the user's Gmail account."""
    if not service:
        return "Error: Gmail service is not authenticated."
    try:
        email_msg = EmailMessage()
        email_msg.set_content(message)
        email_msg['To'] = to
        email_msg['Subject'] = subject

        encoded_message = base64.urlsafe_b64encode(email_msg.as_bytes()).decode()

        draft = {
            'message': {
                'raw': encoded_message
            }
        }
        draft = service.users().drafts().create(userId="me", body=draft).execute()
        return f"Draft '{draft['id']}' created successfully."
    except Exception as error:
        return f"An error occurred creating the draft: {error}"

@mcp.tool()
def modify_draft(draft_id: str, to: str, subject: str, message: str) -> str:
    """Modifies a draft in the user's Gmail account."""
    if not service:
        return "Error: Gmail service is not authenticated."
    try:
        existing_draft = service.users().drafts().get(userId="me", id=draft_id, format="metadata").execute()
        existing_message = existing_draft.get('message', {})
        thread_id = existing_message.get('threadId')
        
        headers = existing_message.get('payload', {}).get('headers', [])
        in_reply_to = ""
        references = ""
        
        for header in headers:
            if header['name'].lower() == 'in-reply-to':
                in_reply_to = header['value']
            if header['name'].lower() == 'references':
                references = header['value']

        email_msg = EmailMessage()
        email_msg.set_content(message)
        email_msg['To'] = to
        email_msg['Subject'] = subject
        if in_reply_to:
            email_msg['In-Reply-To'] = in_reply_to
        if references:
            email_msg['References'] = references

        encoded_message = base64.urlsafe_b64encode(email_msg.as_bytes()).decode()

        draft = {
            'message': {
                'raw': encoded_message
            }
        }
        if thread_id:
            draft['message']['threadId'] = thread_id

        draft = service.users().drafts().update(userId="me", id=draft_id, body=draft).execute()
        return f"Draft '{draft['id']}' modified successfully."
    except Exception as error:
        return f"An error occurred modifying the draft: {error}"

@mcp.tool()
def send_draft(draft_id: str) -> str:
    """Sends an existing draft email. 
    CRITICAL: MUST ONLY BE USED AFTER EXPLICIT USER APPROVAL of the draft content.
    CRITICAL: You MUST NOT call this tool in the same turn as 'create_draft', 'create_response_draft', or 'forward_email'. You must create the draft first, show it to the user, and wait for their approval in the next turn before sending.
    """
    if not service:
        return "Error: Gmail service is not authenticated."
    try:
        draft_body = {'id': draft_id}
        draft = service.users().drafts().send(userId="me", body=draft_body).execute()
        return f"Draft '{draft['id']}' sent successfully."
    except Exception as error:
        return f"An error occurred sending the draft: {error}"

@mcp.tool()
def create_response_draft(to: str, subject: str, message: str, in_reply_to: str) -> str:
    """Creates a draft reply to an email using the in_reply_to field to thread it correctly. Use if user wants to reply to an email. Not to confuse with create_draft function.
    
    Args:
        to (str): The recipient of the email.
        subject (str): The subject of the email.
        message (str): The body of the email.
        in_reply_to (str): The ID of the email to reply to.
    """
    if not service:
        return "Error: Gmail service is not authenticated."
    try:
        original_msg = service.users().messages().get(userId="me", id=in_reply_to, format="metadata").execute()
        thread_id = original_msg.get('threadId')
        
        headers = original_msg.get('payload', {}).get('headers', [])
        message_id = ""
        references = ""
        
        for header in headers:
            if header['name'].lower() == 'message-id':
                message_id = header['value']
            if header['name'].lower() == 'references':
                references = header['value']
        
        email_msg = EmailMessage()
        email_msg.set_content(message)
        email_msg['To'] = to
        
        if not subject.lower().startswith('re:'):
            subject = 'Re: ' + subject
        email_msg['Subject'] = subject
        
        if message_id:
            email_msg['In-Reply-To'] = message_id
            email_msg['References'] = (references + " " + message_id).strip() if references else message_id

        encoded_message = base64.urlsafe_b64encode(email_msg.as_bytes()).decode()

        draft = {
            'message': {
                'raw': encoded_message,
                'threadId': thread_id
            }
        }
        draft = service.users().drafts().create(userId="me", body=draft).execute()
        return f"Draft '{draft['id']}' created successfully."
    except Exception as error:
        return f"An error occurred creating the draft: {error}"


@mcp.tool()
def forward_email(to: str, subject: str, message: str, in_reply_to: str) -> str:
    """Forwards an email using the in_reply_to field to thread it correctly. Use if user wants to forward an email.
    
    Args:
        to (str): The recipient of the email.
        subject (str): The subject of the email.
        message (str): The body of the email.
        in_reply_to (str): The ID of the email to forward.
    """
    if not service:
        return "Error: Gmail service is not authenticated."
    try:
        original_msg = service.users().messages().get(userId="me", id=in_reply_to, format="full").execute()
        thread_id = original_msg.get('threadId')
        
        headers = original_msg.get('payload', {}).get('headers', [])
        message_id = ""
        references = ""
        payload = original_msg.get('payload', {}) 
        original_body = ""

        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    data = part["body"].get("data")
                    if data:
                        original_body = base64.urlsafe_b64decode(data).decode()
                        break
        elif "body" in payload and "data" in payload["body"]:
            original_body = base64.urlsafe_b64decode(payload["body"]["data"]).decode()
        
        combined_message = message + "\n\n" + "Original message:\n" + original_body

        for header in headers:
            if header['name'].lower() == 'message-id':
                message_id = header['value']
            if header['name'].lower() == 'references':
                references = header['value']
        
        email_msg = EmailMessage()
        email_msg.set_content(combined_message)
        email_msg['To'] = to
        
        if not subject.lower().startswith('fwd:'):
            subject = 'Fwd: ' + subject
        email_msg['Subject'] = subject
        
        if message_id:
            email_msg['In-Reply-To'] = message_id
            email_msg['References'] = (references + " " + message_id).strip() if references else message_id

        encoded_message = base64.urlsafe_b64encode(email_msg.as_bytes()).decode()

        draft = {
            'message': {
                'raw': encoded_message,
                'threadId': thread_id
            }
        }
        draft = service.users().drafts().create(userId="me", body=draft).execute()
        return f"Draft '{draft['id']}' created successfully."
    except Exception as error:
        return f"An error occurred creating the draft: {error}"

# --- Misc Tools ---
@mcp.tool()
def unsubscribe_from_email(email_id: str) -> str:
    """Unsubscribes the user from a mailing list using the email's List-Unsubscribe header.
    This sends an email or a web request on the user's behalf, so ONLY call it after the user
    explicitly asks to unsubscribe from that sender.
    You MUST provide the Gmail 'email_id' (the 'ID:' field from read_recent_emails or search_emails).
    """
    if not service:
        return "Error: Gmail service is not authenticated."
    sender = "Unknown"
    try:
        msg = service.users().messages().get(
            userId="me",
            id=email_id,
            format="metadata",
            metadataHeaders=["List-Unsubscribe", "List-Unsubscribe-Post", "From"],
        ).execute()

        headers = {
            h["name"].lower(): h["value"]
            for h in msg.get("payload", {}).get("headers", [])
        }
        sender = headers.get("from", "Unknown")
        unsub_header = headers.get("list-unsubscribe")
        one_click = "one-click" in headers.get("list-unsubscribe-post", "").lower()

        if not unsub_header:
            return "No unsubscribe option found in this email."

        mailto_match = re.search(r"<(mailto:[^>]+)>", unsub_header, re.I)
        http_match = re.search(r"<(https?://[^>]+)>", unsub_header, re.I)
        http_url = http_match.group(1) if http_match else None

        if http_url and one_click and _is_safe_url(http_url):
            try:
                res = requests.post(
                    http_url,
                    data={"List-Unsubscribe": "One-Click"},
                    timeout=10,
                    allow_redirects=False,
                )
                if 200 <= res.status_code < 300:
                    return f"Sent a one-click unsubscribe request to {sender} (HTTP {res.status_code})."
            except requests.RequestException:
                pass 

        if mailto_match:
            parsed = urlparse(mailto_match.group(1))
            to_email = unquote(parsed.path)
            params = parse_qs(parsed.query)

            email_msg = EmailMessage()
            email_msg.set_content(params.get("body", ["Unsubscribe"])[0])
            email_msg["To"] = to_email
            email_msg["Subject"] = params.get("subject", ["Unsubscribe"])[0]

            encoded_message = base64.urlsafe_b64encode(email_msg.as_bytes()).decode()
            service.users().messages().send(
                userId="me", body={"raw": encoded_message}
            ).execute()
            return f"Sent an unsubscribe email to {to_email} for {sender}."

        if http_url:
            return (
                f"{sender} has no one-click unsubscribe. "
                f"Open this link to finish unsubscribing: {http_url}"
            )

        return "Found an unsubscribe header, but it was not in a usable format."

    except Exception as e:
        return f"An error occurred unsubscribing from {sender}: {e}"

@mcp.tool()
def block_sender(sender: str):
    """Blocks an email sender by creating a filter to move all their emails to the trash.

    Args:
        sender (str): The email address to block.
    """
    if not service:
        return "Error: Gmail service is not authenticated."
    filter_config = {
        "criteria": {
            "from": sender
        },
        "action": {
            "addLabelIds": ["TRASH"],
            "removeLabelIds": ["INBOX"]
        }
    }

    try:
        service.users().settings().filters().create(userId="me", body=filter_config).execute()
        return f"Successfully blocked {sender}."
    except Exception as e:
        return f"An error occurred blocking {sender}: {e}"

@mcp.tool()
def unblock_sender(sender: str) -> str:
    """Unblocks an email sender by finding and removing their specific filter.

    Args:
        sender (str): The email address to unblock.
    """
    if not service:
        return "Error: Gmail service is not authenticated."
    try:
        results = service.users().settings().filters().list(userId="me").execute()
        filters = results.get('filter', [])
        
        if not filters:
            return "No block filters found in your account."
            
        filters_deleted = 0
        
        for f in filters:
            criteria = f.get('criteria', {})
            from_email = criteria.get('from', '')
            
            if sender.lower() in from_email.lower():
                filter_id = f['id']
                
                service.users().settings().filters().delete(userId="me", id=filter_id).execute()
                filters_deleted += 1
                
        if filters_deleted > 0:
            return f"Successfully unblocked {sender} by removing {filters_deleted} filter(s)."
        else:
            return f"Could not find any active block filter for {sender}."
            
    except Exception as e:
        return f"An error occurred unblocking {sender}: {e}"

@mcp.tool()
def list_blocked_senders() -> list[str] | str:
    """Lists all blocked senders in the user's Gmail account."""
    if not service:
        return "Error: Gmail service is not authenticated."
    try:
        results = service.users().settings().filters().list(userId="me").execute()
        filters = results.get('filter', [])
        
        if not filters:
            return "No block filters found in your account."
                
        blocked_senders = []
            
        for f in filters:
            criteria = f.get('criteria', {})
            from_email = criteria.get('from', '')
            
            if from_email:
                blocked_senders.append(from_email)
        
        return blocked_senders
    except Exception as e:
        return f"An error occurred listing blocked senders: {e}"

if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
