# Gmail MCP Server

This repository contains an implementation of a Model Context Protocol (MCP) server for Gmail, built using `fastmcp`. This server provides a comprehensive suite of AI-accessible tools to interact seamlessly with your Gmail account. 

## Features

This server currently exposes the following 19 Gmail functions to your AI agents:

**Email Reading & Searching:**
- `read_recent_emails`: Fetches the most recent emails from your inbox.
- `search_emails`: Searches your entire inbox based on custom queries.
- `read_email_content`: Fetches the full content and metadata of a specific email.

**Drafts Management:**
- `list_drafts`: Lists all current drafts.
- `create_draft`: Creates a new email draft.
- `create_response_draft`: Creates a draft threaded as a reply to a specific email.
- `modify_draft`: Updates an existing draft's recipients, subject, or content.
- `send_draft`: Sends an existing draft.

**Email Actions:**
- `delete_message`: Moves an email to the trash (or permanently deletes it if already in trash).
- `untrash_message`: Restores an email from the trash to the inbox.
- `forward_email`: Forwards a specific email to a new recipient.
- `unsubscribe_from_email`: Uses the `List-Unsubscribe` headers to unsubscribe you from mailing lists automatically.
- `block_sender`: Automatically creates a filter to move all future emails from a specific sender to the trash.
- `unblock_sender`: Removes a blocking filter for a sender.
- `list_blocked_senders`: Returns a list of all senders currently blocked via filters.

**Label Management:**
- `list_labels`: Lists all labels in your Gmail account.
- `create_label`: Creates a new custom label.
- `apply_label`: Applies a specific label to an email.
- `remove_label`: Removes a label from an email (can also be used to mark emails as read).
- `count_messages_in_label`: Counts how many messages exist under a specific label.
- `delete_label`: Deletes a custom label.

## Setup

1. **Create Virtual Environment & Install:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Google Cloud Credentials (Required):**
   To securely use this server, you need your own Google Cloud credentials.
   - Go to the [Google Cloud Console](https://console.cloud.google.com/).
   - Create a new Project and search for/enable the **Gmail API**.
   - Go to **APIs & Services > Credentials** on the left menu.
   - Click **Create Credentials > OAuth client ID**.
   - If prompted to configure the OAuth consent screen, set it to "Desktop app".
   - Download the resulting JSON file and rename it to `credentials.json`.
   - Place `credentials.json` directly inside this project folder. *(Note: This file is ignored by Git, so it won't be uploaded!)*
   - **First Run**: When you run the server for the first time, it will automatically open a browser window asking you to log into your Google Account. It will then generate a `token.json` file for future access.

3. **Running the FastMCP Dev Inspector (Recommended for Testing):**
   ```bash
   fastmcp dev inspector -m mcp_server
   ```
   This will run the server in dev mode with a UI that you can interact with from your browser!

4. **Connect to an MCP Client (e.g. Claude Desktop):**
   Add this to your MCP client configuration file:
   ```json
   {
     "mcpServers": {
       "gmail": {
         "command": "/absolute/path/to/venv/bin/python",
         "args": ["/absolute/path/to/mcp_server.py"]
       }
     }
   }
   ```
