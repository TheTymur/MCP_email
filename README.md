# Gmail MCP Server

This repository contains an implementation of a Model Context Protocol (MCP) server for Gmail, built using `fastmcp`.

## Overview
This server exposes Gmail functionality (like fetching unread emails, sending emails, and searching) as standardized tools that can be used by MCP clients such as Claude Desktop or custom AI agents.

## Setup

1. **Create Virtual Environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Connect to an MCP Client:**
   Configure your MCP client to run this script as an MCP server. For example, in Claude Desktop config:
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
