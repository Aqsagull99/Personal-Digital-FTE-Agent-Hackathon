"""
Gmail Watcher - Monitors Gmail for new important/unread emails
Creates action files in AI_Employee_Vault/Needs_Action
Automatically creates contacts in Odoo for new email senders
"""
import sys
import os
import base64
import re
from pathlib import Path
from datetime import datetime
from email.utils import parsedate_to_datetime

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from base_watcher import BaseWatcher

# Import Odoo server - adjust path to go up one level to project root
sys.path.insert(0, str(Path(__file__).parent.parent))
from mcp_servers.odoo_server import OdooMCPServer

# Gmail API scopes - read-only access
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


class GmailWatcher(BaseWatcher):
    """
    Watches Gmail for new unread/important emails.

    Usage:
        python gmail_watcher.py [vault_path]

    First run will open browser for Google OAuth authentication.
    """

    def __init__(self, vault_path: str, credentials_path: str = None):
        super().__init__(vault_path, check_interval=120)  # Check every 2 minutes

        # Set credentials path
        if credentials_path is None:
            credentials_path = Path(__file__).parent.parent / 'credentials.json'
        self.credentials_path = Path(credentials_path)
        self.token_path = self.credentials_path.parent / 'token.json'

        # Track processed email IDs to avoid duplicates
        self.processed_ids = set()

        # Keywords that indicate priority
        self.urgent_keywords = ['urgent', 'asap', 'critical', 'important', 'payment', 'invoice', 'deadline']
        self.high_keywords = ['request', 'help', 'needed', 'question', 'meeting']

        # Initialize Gmail service
        self.service = self._get_gmail_service()

    def _get_gmail_service(self):
        """Authenticate and return Gmail API service"""
        creds = None

        # Load existing token if available
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)

        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"credentials.json not found at {self.credentials_path}\n"
                        "Please download OAuth credentials from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                # Use console-based auth for WSL/headless environments
                print("\n" + "="*60)
                print("Opening browser for Google authentication...")
                print("If browser doesn't open, copy this URL manually:")
                print("="*60)
                creds = flow.run_local_server(
                    port=8080,
                    open_browser=False,
                    authorization_prompt_message='Please visit this URL: {url}',
                    success_message='Authentication successful! You can close this window.'
                )

            # Save credentials for next run
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
            self.logger.info(f'Token saved to {self.token_path}')

        return build('gmail', 'v1', credentials=creds)

    def check_for_updates(self) -> list:
        """Check Gmail for new unread important emails"""
        try:
            # Query for unread important emails
            # You can modify this query as needed
            results = self.service.users().messages().list(
                userId='me',
                q='is:unread is:important',
                maxResults=10
            ).execute()

            messages = results.get('messages', [])

            # Filter out already processed emails
            new_messages = [
                m for m in messages
                if m['id'] not in self.processed_ids
            ]

            if new_messages:
                self.logger.info(f'Found {len(new_messages)} new emails')

            return new_messages

        except Exception as e:
            self.logger.error(f'Error checking Gmail: {e}')
            return []

    def _get_email_content(self, message_id: str) -> dict:
        """Fetch full email content"""
        msg = self.service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()

        # Extract headers
        headers = {}
        for header in msg['payload'].get('headers', []):
            headers[header['name'].lower()] = header['value']

        # Extract body
        body = ''
        payload = msg['payload']

        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
        else:
            data = payload['body'].get('data', '')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8')

        # Use snippet if body is empty
        if not body:
            body = msg.get('snippet', '')

        return {
            'id': message_id,
            'from': headers.get('from', 'Unknown'),
            'to': headers.get('to', ''),
            'subject': headers.get('subject', 'No Subject'),
            'date': headers.get('date', ''),
            'body': body,
            'snippet': msg.get('snippet', ''),
            'labels': msg.get('labelIds', [])
        }

    def determine_priority(self, email_data: dict) -> str:
        """Determine priority based on email content"""
        content = f"{email_data['subject']} {email_data['body']}".lower()

        for keyword in self.urgent_keywords:
            if keyword in content:
                return 'P1'

        for keyword in self.high_keywords:
            if keyword in content:
                return 'P2'

        # Check if from important sender (you can customize this)
        if 'IMPORTANT' in email_data.get('labels', []):
            return 'P2'

        return 'P3'

    def create_action_file(self, message: dict) -> Path:
        """Create action file from Gmail message and create Odoo contact"""
        # Fetch full email content
        email_data = self._get_email_content(message['id'])

        priority = self.determine_priority(email_data)
        timestamp = datetime.now().isoformat()

        # Extract name and email from sender field
        name, email = self.extract_name_and_email(email_data['from'])

        # Clean body for markdown (limit length)
        body_preview = email_data['body'][:1000]
        if len(email_data['body']) > 1000:
            body_preview += '\n\n... [truncated]'

        action_content = f'''---
type: email
source: gmail_watcher
priority: {priority}
created: {timestamp}
email_id: {email_data['id']}
from: {email_data['from']}
subject: {email_data['subject']}
received: {email_data['date']}
status: pending
---

## Email Summary

**From:** {email_data['from']}
**Subject:** {email_data['subject']}
**Date:** {email_data['date']}

## Content

{body_preview}

## Suggested Actions
- [ ] Read full email
- [ ] Reply to sender
- [ ] Forward if needed
- [ ] Archive after processing
'''

        # Create unique filename
        safe_subject = "".join(c for c in email_data['subject'][:30] if c.isalnum() or c in ' -_').strip()
        safe_subject = safe_subject.replace(' ', '_')
        filename = f"EMAIL_{safe_subject}_{message['id'][:8]}.md"

        action_path = self.needs_action / filename
        action_path.write_text(action_content)

        # Mark as processed
        self.processed_ids.add(message['id'])

        # Log the action
        self.log_action('email_processed', {
            'email_id': message['id'],
            'from': email_data['from'],
            'subject': email_data['subject'],
            'priority': priority,
            'action_file': filename
        })

        # Create Odoo contact for the sender
        self.create_odoo_contact(name, email)

        return action_path

    def extract_name_and_email(self, sender_field: str) -> tuple:
        """Extract name and email from sender field"""
        # Extract email address (format: "Name <email@domain.com>" or just email)
        email_pattern = r'<([^>]+)>'
        email_match = re.search(email_pattern, sender_field)
        
        if email_match:
            email = email_match.group(1)
            # Extract name by removing email part
            name = re.sub(email_pattern, '', sender_field).strip().strip('"\'')
        else:
            # If no angle brackets, assume it's just an email address
            email = sender_field.strip()
            name = sender_field.split('@')[0]  # Use part before @ as name
        
        return name, email

    def create_odoo_contact(self, name: str, email: str):
        """Create contact in Odoo for the email sender"""
        try:
            # Initialize Odoo server
            odoo_server = OdooMCPServer()
            
            if not odoo_server.connect():
                self.logger.error("Failed to connect to Odoo for contact creation")
                return
            
            # Check if contact already exists (optional - to prevent duplicates)
            # For now, we'll just create the contact
            result = odoo_server.create_customer(
                name=name,
                email=email
            )
            
            if result['status'] == 'success':
                self.logger.info(f"✅ Contact created in Odoo: {name} <{email}> (ID: {result['partner_id']})")
                print(f"✅ Contact created in Odoo: {name} <{email}> (ID: {result['partner_id']})")
            else:
                self.logger.error(f"❌ Failed to create contact in Odoo: {result['message']}")
                
        except Exception as e:
            self.logger.error(f"❌ Error creating contact in Odoo: {str(e)}")

    def run(self):
        """Override run to include startup message"""
        print(f'''
╔══════════════════════════════════════════════════════════════╗
║              AI Employee - Gmail Watcher                     ║
╠══════════════════════════════════════════════════════════════╣
║  Monitoring: Gmail (unread + important)                      ║
║  Interval:   {self.check_interval} seconds                              ║
║  Actions:    {self.needs_action}
╚══════════════════════════════════════════════════════════════╝
''')
        super().run()


def main():
    """Main entry point"""
    # Default vault path
    default_vault = Path(__file__).parent.parent / 'AI_Employee_Vault'

    # Allow custom vault path via command line
    if len(sys.argv) > 1:
        vault_path = sys.argv[1]
    else:
        vault_path = str(default_vault)

    try:
        watcher = GmailWatcher(vault_path)
        watcher.run()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nSetup instructions:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a project and enable Gmail API")
        print("3. Create OAuth 2.0 credentials")
        print("4. Download credentials.json to project root")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
