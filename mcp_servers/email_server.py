"""
Email MCP Server - Sends emails via Gmail API
Silver Tier Requirement: One working MCP server for external action

This MCP server provides email sending capabilities to Claude Code.
Supports Human-in-the-Loop approval for sensitive actions.
"""
import os
import sys
import json
import base64
import asyncio
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# MCP Protocol imports
try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("MCP package not installed. Running in standalone mode.")


# Gmail API scopes for sending and creating drafts
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose'
]

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
VAULT_PATH = PROJECT_ROOT / 'AI_Employee_Vault'
if VAULT_PATH.is_symlink():
    VAULT_PATH = VAULT_PATH.resolve()


class EmailMCPServer:
    """
    MCP Server for sending emails via Gmail API.

    Features:
    - Send plain text and HTML emails
    - Human-in-the-loop approval for unknown recipients
    - Audit logging
    - Draft creation
    """

    def __init__(self):
        # Point to credentials.json in the root project folder
        self.credentials_path = PROJECT_ROOT / 'credentials.json'
        self.token_path = PROJECT_ROOT / 'token_send.json'  # Separate token for send/compose scopes
        self.service = None

        # Paths
        self.logs_path = VAULT_PATH / 'Logs'
        self.pending_approval = VAULT_PATH / 'Pending_Approval'
        self.approved_path = VAULT_PATH / 'Approved'

        # Known contacts (auto-approve)
        self.known_contacts_file = VAULT_PATH / 'known_contacts.json'
        self.known_contacts = self._load_known_contacts()

        # Ensure directories exist
        self.logs_path.mkdir(exist_ok=True)
        self.pending_approval.mkdir(exist_ok=True)
        self.approved_path.mkdir(exist_ok=True)

    def _load_known_contacts(self) -> set:
        """Load list of known/approved contacts"""
        if self.known_contacts_file.exists():
            with open(self.known_contacts_file, 'r') as f:
                return set(json.load(f))
        return set()

    def _save_known_contacts(self):
        """Save known contacts list"""
        with open(self.known_contacts_file, 'w') as f:
            json.dump(list(self.known_contacts), f, indent=2)

    def _get_gmail_service(self):
        """Authenticate and return Gmail API service with send scope"""
        if self.service:
            return self.service

        creds = None

        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"credentials.json not found at {self.credentials_path}"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                creds = flow.run_local_server(port=9091, authorization_prompt_handler=None)

            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())

        self.service = build('gmail', 'v1', credentials=creds)
        return self.service

    def _log_action(self, action_type: str, details: dict):
        """Log email action"""
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.logs_path / f'{today}.json'

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action_type': action_type,
            'server': 'email_mcp',
            **details
        }

        if log_file.exists():
            with open(log_file, 'r') as f:
                logs = json.load(f)
        else:
            logs = []

        logs.append(log_entry)

        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)

    def _is_known_contact(self, email: str) -> bool:
        """Check if email is a known/approved contact"""
        return email.lower() in [c.lower() for c in self.known_contacts]

    def _create_approval_request(self, to: str, subject: str, body: str) -> Path:
        """Create approval request for email to unknown recipient"""
        timestamp = datetime.now()
        filename = f"EMAIL_SEND_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"

        content = f'''---
type: email_send_approval
action: send_email
to: {to}
subject: {subject}
created: {timestamp.isoformat()}
status: pending
---

## Email Send Request

### Recipient
**To:** {to}

### Subject
{subject}

### Body
{body}

---

## To Approve
Move this file to `/Approved` folder.

## To Reject
Delete this file or move to `/Done`.

## To Add Contact as Known
After approving, the recipient will be asked to be added to known contacts.

---
*This email requires human approval because the recipient is not in your known contacts list.*
'''

        approval_path = self.pending_approval / filename
        approval_path.write_text(content)

        self._log_action('email_approval_requested', {
            'to': to,
            'subject': subject,
            'approval_file': filename
        })

        return approval_path

    def create_message(self, to: str, subject: str, body: str, html: bool = False) -> dict:
        """Create email message"""
        if html:
            message = MIMEMultipart('alternative')
            message.attach(MIMEText(body, 'html'))
        else:
            message = MIMEText(body)

        message['to'] = to
        message['subject'] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return {'raw': raw}

    def send_email(self, to: str, subject: str, body: str,
                   require_approval: bool = True, html: bool = False) -> dict:
        """
        Send an email via Gmail API.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text or HTML)
            require_approval: If True, unknown contacts need approval
            html: If True, body is treated as HTML

        Returns:
            dict with status and details
        """
        # Check if approval needed
        if require_approval and not self._is_known_contact(to):
            approval_file = self._create_approval_request(to, subject, body)
            return {
                'status': 'pending_approval',
                'message': f'Email to unknown contact requires approval',
                'approval_file': str(approval_file),
                'to': to,
                'subject': subject
            }

        try:
            service = self._get_gmail_service()
            message = self.create_message(to, subject, body, html)

            result = service.users().messages().send(
                userId='me',
                body=message
            ).execute()

            self._log_action('email_sent', {
                'to': to,
                'subject': subject,
                'message_id': result.get('id'),
                'status': 'success'
            })

            return {
                'status': 'success',
                'message': f'Email sent successfully to {to}',
                'message_id': result.get('id'),
                'to': to,
                'subject': subject
            }

        except Exception as e:
            self._log_action('email_failed', {
                'to': to,
                'subject': subject,
                'error': str(e)
            })
            return {
                'status': 'error',
                'message': f'Failed to send email: {str(e)}',
                'to': to,
                'subject': subject
            }

    def create_draft(self, to: str, subject: str, body: str, html: bool = False) -> dict:
        """Create email draft (no approval needed)"""
        try:
            service = self._get_gmail_service()
            message = self.create_message(to, subject, body, html)

            draft = service.users().drafts().create(
                userId='me',
                body={'message': message}
            ).execute()

            self._log_action('draft_created', {
                'to': to,
                'subject': subject,
                'draft_id': draft.get('id')
            })

            return {
                'status': 'success',
                'message': f'Draft created for {to}',
                'draft_id': draft.get('id'),
                'to': to,
                'subject': subject
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to create draft: {str(e)}'
            }

    def add_known_contact(self, email: str) -> dict:
        """Add email to known contacts list"""
        self.known_contacts.add(email.lower())
        self._save_known_contacts()

        self._log_action('contact_added', {'email': email})

        return {
            'status': 'success',
            'message': f'{email} added to known contacts'
        }

    def process_approved_emails(self) -> list:
        """Process emails that have been approved"""
        results = []

        for approval_file in self.approved_path.glob('EMAIL_SEND_*.md'):
            try:
                content = approval_file.read_text()

                # Parse the approval file
                lines = content.split('\n')
                to = subject = body = ''
                in_body = False
                body_lines = []

                for line in lines:
                    if line.startswith('to:'):
                        to = line.split(':', 1)[1].strip()
                    elif line.startswith('subject:'):
                        subject = line.split(':', 1)[1].strip()
                    elif '### Body' in line:
                        in_body = True
                        continue
                    elif in_body and line.startswith('---'):
                        in_body = False
                    elif in_body:
                        body_lines.append(line)

                body = '\n'.join(body_lines).strip()

                if to and subject:
                    # Send the email (no approval needed since already approved)
                    result = self.send_email(to, subject, body, require_approval=False)
                    results.append(result)

                    # Move to Done
                    done_path = VAULT_PATH / 'Done' / approval_file.name
                    approval_file.rename(done_path)

            except Exception as e:
                results.append({
                    'status': 'error',
                    'message': f'Error processing {approval_file.name}: {str(e)}'
                })

        return results


# MCP Server setup (if MCP package available)
if MCP_AVAILABLE:
    server = Server("email-mcp")
    email_server = EmailMCPServer()

    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="send_email",
                description="Send an email via Gmail. Requires approval for unknown contacts.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "Recipient email"},
                        "subject": {"type": "string", "description": "Email subject"},
                        "body": {"type": "string", "description": "Email body"},
                        "html": {"type": "boolean", "description": "Is body HTML?", "default": False}
                    },
                    "required": ["to", "subject", "body"]
                }
            ),
            Tool(
                name="create_draft",
                description="Create an email draft without sending",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to": {"type": "string"},
                        "subject": {"type": "string"},
                        "body": {"type": "string"}
                    },
                    "required": ["to", "subject", "body"]
                }
            ),
            Tool(
                name="add_known_contact",
                description="Add email to known contacts (auto-approve list)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email": {"type": "string"}
                    },
                    "required": ["email"]
                }
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name == "send_email":
            result = email_server.send_email(
                arguments["to"],
                arguments["subject"],
                arguments["body"],
                html=arguments.get("html", False)
            )
        elif name == "create_draft":
            result = email_server.create_draft(
                arguments["to"],
                arguments["subject"],
                arguments["body"]
            )
        elif name == "add_known_contact":
            result = email_server.add_known_contact(arguments["email"])
        else:
            result = {"status": "error", "message": f"Unknown tool: {name}"}

        return [TextContent(type="text", text=json.dumps(result, indent=2))]


def main():
    """Command line interface / standalone mode"""
    if len(sys.argv) < 2:
        print('''
Email MCP Server
================

Usage:
    python email_server.py send <to> <subject> <body>
    python email_server.py draft <to> <subject> <body>
    python email_server.py add-contact <email>
    python email_server.py process-approved
    python email_server.py serve  (start MCP server)

Examples:
    python email_server.py send "user@example.com" "Hello" "Test message"
    python email_server.py draft "user@example.com" "Draft" "Draft content"
    python email_server.py add-contact "trusted@example.com"
''')
        sys.exit(1)

    server = EmailMCPServer()
    command = sys.argv[1]

    if command == 'send' and len(sys.argv) >= 5:
        result = server.send_email(sys.argv[2], sys.argv[3], sys.argv[4])
        print(json.dumps(result, indent=2))

    elif command == 'draft' and len(sys.argv) >= 5:
        result = server.create_draft(sys.argv[2], sys.argv[3], sys.argv[4])
        print(json.dumps(result, indent=2))

    elif command == 'add-contact' and len(sys.argv) >= 3:
        result = server.add_known_contact(sys.argv[2])
        print(json.dumps(result, indent=2))

    elif command == 'process-approved':
        results = server.process_approved_emails()
        for r in results:
            print(json.dumps(r, indent=2))

    elif command == 'serve':
        if MCP_AVAILABLE:
            print("Starting Email MCP Server...")
            asyncio.run(server.run())
        else:
            print("MCP package not installed. Install with: pip install mcp")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
