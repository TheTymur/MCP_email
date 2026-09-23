# Gmail MCP Server

This repository contains an implementation of a Model Context Protocol (MCP) server for Gmail, built using `fastmcp`.

## Features
This server currently exposes the following Gmail functionality to your AI agents:
- `read_recent_emails`: Fetches the most recent emails from your inbox.
- `list_labels`: Lists all labels in your Gmail account.
- `create_label`: Creates a new label in your Gmail account.

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

3. **Connect to an MCP Client (e.g. Claude Desktop):**
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
