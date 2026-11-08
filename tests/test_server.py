import asyncio
import unittest
import base64
from unittest.mock import MagicMock, patch

import mcp_server


class TestMCPServer(unittest.TestCase):
    def setUp(self):
        self.manager = mcp_server.GmailServiceManager()

    def test_tools_registered(self):
        """Verify that all 28 tools are properly registered on the FastMCP instance."""
        tools = asyncio.run(mcp_server.mcp.list_tools())
        tool_names = {t.name for t in tools}
        
        expected_tools = {
            "read_recent_emails",
            "search_emails",
            "read_email_content",
            "download_attachment",
            "create_label",
            "list_labels",
            "apply_label",
            "remove_label",
            "mark_email_as_read",
            "delete_label",
            "count_messages_in_label",
            "update_label",
            "create_filter",
            "list_filters",
            "delete_filter",
            "block_sender",
            "unblock_sender",
            "list_blocked_senders",
            "delete_message",
            "untrash_message",
            "list_drafts",
            "create_draft",
            "modify_draft",
            "send_draft",
            "create_response_draft",
            "forward_email",
            "delete_draft",
            "unsubscribe_from_email"
        }
        
        self.assertEqual(len(tool_names), 28)
        self.assertEqual(tool_names, expected_tools)

    def test_is_safe_url(self):
        """Test SSRF validation logic for unsubscribe URLs."""
        # Non-HTTPS should be rejected
        self.assertFalse(mcp_server.GmailServiceManager.is_safe_url("http://example.com"))
        self.assertFalse(mcp_server.GmailServiceManager.is_safe_url("ftp://example.com"))
        self.assertFalse(mcp_server.GmailServiceManager.is_safe_url("file:///etc/passwd"))
        self.assertFalse(mcp_server.GmailServiceManager.is_safe_url("javascript:alert(1)"))

        with patch("socket.getaddrinfo") as mock_dns:
            # 127.0.0.1 loopback
            mock_dns.return_value = [(None, None, None, None, ("127.0.0.1", 443))]
            self.assertFalse(mcp_server.GmailServiceManager.is_safe_url("https://localhost/unsub"))
            self.assertFalse(mcp_server.GmailServiceManager.is_safe_url("https://127.0.0.1/unsub"))

            # 10.0.0.1 private IP
            mock_dns.return_value = [(None, None, None, None, ("10.0.0.1", 443))]
            self.assertFalse(mcp_server.GmailServiceManager.is_safe_url("https://10.0.0.1/unsub"))

            # 192.168.1.1 private IP
            mock_dns.return_value = [(None, None, None, None, ("192.168.1.1", 443))]
            self.assertFalse(mcp_server.GmailServiceManager.is_safe_url("https://192.168.1.1/unsub"))

            # 142.250.190.46 (public Google IP)
            mock_dns.return_value = [(None, None, None, None, ("142.250.190.46", 443))]
            self.assertTrue(mcp_server.GmailServiceManager.is_safe_url("https://google.com"))

    def test_extract_body_plain_and_attachments(self):
        """Test payload body extraction and attachment metadata parsing."""
        plain_text = "Hello, world!"
        encoded_plain = base64.urlsafe_b64encode(plain_text.encode('utf-8')).decode('utf-8')
        
        payload = {
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": encoded_plain}
                },
                {
                    "filename": "invoice.pdf",
                    "mimeType": "application/pdf",
                    "body": {"attachmentId": "att_12345"}
                }
            ]
        }
        
        text, html, attachments = self.manager.extract_body(payload)
        self.assertEqual(text, plain_text)
        self.assertEqual(html, "")
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0]["filename"], "invoice.pdf")
        self.assertEqual(attachments[0]["attachmentId"], "att_12345")

    def test_parse_email_html_cleaning(self):
        """Test HTML parsing, script stripping, and newline conversion."""
        html_content = """
        <html>
            <head><style>body { color: red; }</style></head>
            <body>
                <script>alert('malicious');</script>
                <h1>Flight Confirmation</h1>
                <p>Your flight to Paris is confirmed.<br>Departure: 10:00 AM</p>
            </body>
        </html>
        """
        encoded_html = base64.urlsafe_b64encode(html_content.encode('utf-8')).decode('utf-8')

        msg_data = {
            "id": "18a123456789",
            "labelIds": ["INBOX", "UNREAD"],
            "payload": {
                "headers": [
                    {"name": "From", "value": "airline@example.com"},
                    {"name": "To", "value": "user@example.com"},
                    {"name": "Subject", "value": "Flight Confirmation"},
                    {"name": "Date", "value": "Thu, 6 Nov 2026 14:00:00 +0100"},
                    {"name": "Message-ID", "value": "<abc123@example.com>"}
                ],
                "parts": [
                    {
                        "mimeType": "text/html",
                        "body": {"data": encoded_html}
                    }
                ]
            }
        }

        parsed = self.manager.parse_email(msg_data)
        
        self.assertEqual(parsed["sender"], "airline@example.com")
        self.assertEqual(parsed["recipient"], "user@example.com")
        self.assertEqual(parsed["subject"], "Flight Confirmation")
        self.assertEqual(parsed["message_id"], "<abc123@example.com>")
        
        self.assertNotIn("alert", parsed["body"])
        self.assertNotIn("color: red", parsed["body"])
        
        self.assertIn("Flight Confirmation", parsed["body"])
        self.assertIn("Your flight to Paris is confirmed.", parsed["body"])
        self.assertIn("Departure: 10:00 AM", parsed["body"])

    def test_account_fallback_to_token_json(self):
        """Test that get_service uses token.json when token_personal.json is not present."""
        with patch("os.path.exists") as mock_exists, \
             patch("mcp_server.Credentials") as mock_creds, \
             patch("mcp_server.build") as mock_build:
            
            # Simulate only token.json exists, but token_personal.json does not
            def exists_side_effect(path):
                return path in ("token.json", "credentials.json")
            
            mock_exists.side_effect = exists_side_effect
            mock_creds.from_authorized_user_file.return_value = MagicMock(valid=True)
            mock_build.return_value = MagicMock()

            manager = mcp_server.GmailServiceManager()
            service = manager.get_service("personal")
            
            mock_creds.from_authorized_user_file.assert_called_with("token.json", mcp_server.SCOPES)
            self.assertIsNotNone(service)


if __name__ == "__main__":
    unittest.main()
