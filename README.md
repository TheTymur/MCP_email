# Gmail Unified MCP Server

This repository contains an enhanced Model Context Protocol (MCP) server for Gmail, built using `fastmcp`. This server provides a comprehensive suite of 28 AI-accessible tools to interact seamlessly with your Gmail account(s), featuring multi-account support, attachment downloading, automated filter management, and robust HTML email parsing.

## Key Features

### 1. Multi-Account Support
- All tools accept an optional `account` parameter (e.g. `personal`, `work`, or any custom name).
- Dynamic token management (`token_personal.json`, `token_work.json`) with backwards compatibility for single-account `token.json`.

### 2. Attachment Handling
- Multi-part emails are parsed to extract all attachment metadata (`filename`, `attachmentId`).
- `download_attachment`: Downloads attachment bytes directly via the Gmail API, decodes them safely, and saves them to the user's `~/Downloads` folder.

### 3. Advanced HTML Email Parsing & Security
- Strips `<script>` and `<style>` tags, properly transforms `<br>` and block elements (`<p>`, `<div>`, headings, `<li>`, `<tr>`) to clean readable text, and collapses redundant whitespace.
- Prompt injection protection: Encloses subjects and body content in XML tags (`<email_subject>`, `<email_body>`, `<email_snippet>`).
- Anti-SSRF validation on unsubscribe URLs (`is_safe_url`) ensuring requests only resolve to public HTTPS endpoints.

---

## Complete Tools Catalog (28 Tools)

### Email Reading & Searching:
- `read_recent_emails`: Fetches the latest emails with unread status, snippet preview, and saveable IDs.
- `search_emails`: Searches Gmail with full query syntax (`after:YYYY/MM/DD`, `from:`, `has:attachment`, `filename:pdf`, `-term`) and configurable limit (up to 100).
- `read_email_content`: Fetches full email body (up to 4000 chars), extracts attachment metadata, and auto-marks email as read.

### Attachments:
- `download_attachment`: Downloads an attachment by email ID and attachment ID and saves it to `~/Downloads`.

### Drafts Management:
- `list_drafts`: Lists all current drafts with recipients, subject, and snippet preview.
- `create_draft`: Creates a new email draft.
- `create_response_draft`: Creates a draft threaded as a reply to a specific email (sets `In-Reply-To`, `References`, and `threadId`).
- `modify_draft`: Updates an existing draft's recipients, subject, or content while preserving headers and thread context.
- `send_draft`: Sends an existing draft (requires explicit user confirmation).
- `delete_draft`: Permanently deletes an unwanted draft.

### Email Actions & Filtering:
- `delete_message`: Moves an email to trash or permanently deletes it if already in trash.
- `untrash_message`: Restores an email from trash back to the inbox.
- `forward_email`: Forwards an email threaded properly with previous header information and body content.
- `mark_email_as_read`: Marks an email as read by removing the `UNREAD` label.
- `unsubscribe_from_email`: Safely handles mailing list unsubscription via one-click HTTP POST or mailto.
- `block_sender`: Automatically creates a filter to route all incoming emails from a sender to TRASH.
- `unblock_sender`: Finds and removes the specific block/trash filter for a sender.
- `list_blocked_senders`: Lists all senders currently blocked via TRASH filters.
- `create_filter`: Creates automated Gmail filters with criteria (`from`, `to`, `subject`, `query`) and actions (`add_label_ids`, `remove_label_ids`).
- `list_filters`: Lists all automated filters in the account with criteria and actions.
- `delete_filter`: Deletes a filter by ID.

### Label Management:
- `list_labels`: Lists all labels in your Gmail account.
- `create_label`: Creates a new custom label with visibility options.
- `apply_label`: Applies a specific label to an email.
- `remove_label`: Removes a label from an email.
- `update_label`: Updates label name, list visibility, message visibility, text color, and background color.
- `count_messages_in_label`: Counts how many messages exist under a label.
- `delete_label`: Permanently deletes a custom label.

---

## Setup & Authentication

### 1. Install Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Google Cloud Credentials
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a Project and enable the **Gmail API**.
3. Under **APIs & Services > Credentials**, create an **OAuth 2.0 Client ID** (Application type: "Desktop app").
4. Download the client secret JSON file and save it as `credentials.json` in this directory.

### 3. Authenticate Account(s)
Run the setup script:

- **Single / Default Account (`personal`):**
  ```bash
  python setup_auth.py
  ```
  *(Creates `token_personal.json` and `token.json`)*

- **Additional Account (e.g., `work`):**
  ```bash
  python setup_auth.py work
  ```
  *(Creates `token_work.json`)*

---

## Testing

### Option 1: FastMCP Dev Inspector (Interactive Browser UI)
FastMCP comes with a built-in dev inspector that runs a local web UI where you can inspect and invoke all 28 tools interactively:
```bash
fastmcp dev inspector -m mcp_server
```

### Option 2: Automated Unit Tests
You can run automated test suites covering tool definitions, HTML parsing, SSRF URL validation, and email structure:
```bash
python -m unittest discover -s tests
```

---

## Connect to an MCP Client (e.g. Claude Desktop, Antigravity, Cursor)
Add the server configuration to your MCP settings:

```json
{
  "mcpServers": {
    "gmail": {
      "command": "/absolute/path/to/MCP_email/venv/bin/python",
      "args": ["/absolute/path/to/MCP_email/mcp_server.py"]
    }
  }
}
```
