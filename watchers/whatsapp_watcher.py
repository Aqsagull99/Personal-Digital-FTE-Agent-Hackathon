"""
WhatsApp Watcher - Monitors WhatsApp Web for new messages
Silver Tier Requirement: Additional Watcher script
Uses Playwright for browser automation
"""
import sys
import json
from pathlib import Path
from datetime import datetime

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from base_watcher import BaseWatcher


class WhatsAppWatcher(BaseWatcher):
    """
    Watches WhatsApp Web for new messages containing important keywords.

    Usage:
        python whatsapp_watcher.py [vault_path]

    First run will show QR code for WhatsApp Web login.
    Session is saved for future use.
    """

    def __init__(self, vault_path: str, session_path: str = None):
        super().__init__(vault_path, check_interval=30)  # Check every 30 seconds

        # Session storage for persistent login
        if session_path is None:
            session_path = Path(__file__).parent.parent / '.whatsapp_session'
        self.session_path = Path(session_path)
        self.session_path.mkdir(exist_ok=True)

        # Keywords that indicate important messages (from docs)
        self.important_keywords = [
            'urgent', 'asap', 'invoice', 'payment', 'help',
            'important', 'deadline', 'meeting', 'call',
            'project', 'client', 'order', 'delivery'
        ]

        self.browser = None
        self.context = None
        self.page = None
        self.processed_messages = set()

    def _init_browser(self):
        """Initialize browser with persistent session"""
        playwright = sync_playwright().start()
        self.browser = playwright.chromium.launch(headless=False)  # Must be visible for QR scan

        state_file = self.session_path / 'state.json'
        self.context = self.browser.new_context(
            storage_state=str(state_file) if state_file.exists() else None,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        self.page = self.context.new_page()

    def _save_session(self):
        """Save browser session for future use"""
        if self.context:
            self.context.storage_state(path=str(self.session_path / 'state.json'))
            self.logger.info('WhatsApp session saved')

    def _wait_for_login(self):
        """Navigate to WhatsApp Web and wait for login"""
        self.page.goto('https://web.whatsapp.com/')

        print('\n' + '='*60)
        print('WhatsApp Web Login')
        print('='*60)
        print('1. Open WhatsApp on your phone')
        print('2. Go to Settings > Linked Devices')
        print('3. Tap "Link a Device"')
        print('4. Scan the QR code in the browser')
        print('='*60 + '\n')

        try:
            # Wait for chat list to appear (multiple selectors for compatibility)
            self.page.wait_for_selector('div[role="listitem"], [data-testid="chat-list"], #pane-side', timeout=120000)
            self.logger.info('WhatsApp logged in successfully')
            self._save_session()
            return True
        except PlaywrightTimeout:
            self.logger.error('WhatsApp login timeout')
            return False

    def _is_logged_in(self) -> bool:
        """Check if already logged into WhatsApp"""
        try:
            self.page.wait_for_selector('div[role="listitem"], [data-testid="chat-list"], #pane-side', timeout=10000)
            return True
        except PlaywrightTimeout:
            return False

    def check_for_updates(self) -> list:
        """Check WhatsApp for new messages with important keywords"""
        messages = []

        try:
            if not self.page:
                self._init_browser()
                self.page.goto('https://web.whatsapp.com/')

                if not self._is_logged_in():
                    if not self._wait_for_login():
                        return []

            # Find unread chats
            unread_chats = self.page.query_selector_all('[data-testid="cell-frame-container"]')

            for chat in unread_chats:
                try:
                    # Check for unread indicator
                    unread_badge = chat.query_selector('[data-testid="icon-unread-count"]')
                    if not unread_badge:
                        continue

                    # Get chat name
                    name_elem = chat.query_selector('[data-testid="cell-frame-title"]')
                    chat_name = name_elem.inner_text().strip() if name_elem else 'Unknown'

                    # Get last message preview
                    preview_elem = chat.query_selector('[data-testid="last-msg-status"]')
                    if not preview_elem:
                        preview_elem = chat.query_selector('span[title]')

                    preview = preview_elem.inner_text().strip() if preview_elem else ''

                    # Create unique identifier
                    msg_id = f"{chat_name}_{hash(preview)}"

                    if msg_id in self.processed_messages:
                        continue

                    # Check if message contains important keywords
                    preview_lower = preview.lower()
                    if any(kw in preview_lower for kw in self.important_keywords):
                        messages.append({
                            'type': 'whatsapp_message',
                            'sender': chat_name,
                            'preview': preview,
                            'timestamp': datetime.now().isoformat(),
                            'msg_id': msg_id
                        })
                        self.processed_messages.add(msg_id)

                except Exception as e:
                    self.logger.debug(f'Error parsing chat: {e}')

            if messages:
                self.logger.info(f'Found {len(messages)} important WhatsApp messages')

        except PlaywrightTimeout:
            self.logger.warning('WhatsApp page timeout')
        except Exception as e:
            self.logger.error(f'Error checking WhatsApp: {e}')

        return messages

    def determine_priority(self, item: dict) -> str:
        """Determine priority based on message content"""
        content = f"{item.get('sender', '')} {item.get('preview', '')}".lower()

        urgent_keywords = ['urgent', 'asap', 'payment', 'invoice', 'emergency']
        high_keywords = ['important', 'deadline', 'meeting', 'call', 'client']

        if any(kw in content for kw in urgent_keywords):
            return 'P1'
        elif any(kw in content for kw in high_keywords):
            return 'P2'
        return 'P3'

    def create_action_file(self, item: dict) -> Path:
        """Create action file from WhatsApp message"""
        priority = self.determine_priority(item)
        timestamp = datetime.now()

        content = f'''---
type: whatsapp_message
source: whatsapp_watcher
priority: {priority}
created: {timestamp.isoformat()}
sender: {item.get('sender', 'Unknown')}
status: pending
---

## WhatsApp Message

**From:** {item.get('sender', 'Unknown')}

**Preview:**
{item.get('preview', 'No preview available')}

## Suggested Actions
- [ ] Open WhatsApp and read full message
- [ ] Reply if needed
- [ ] Mark as handled when complete

## Notes
- Priority: {priority}
- Keywords detected in message
'''

        # Create unique filename
        safe_sender = "".join(c for c in item.get('sender', 'unknown')[:20] if c.isalnum() or c in ' -_').strip()
        safe_sender = safe_sender.replace(' ', '_')
        filename = f"WHATSAPP_{safe_sender}_{timestamp.strftime('%H%M%S')}.md"

        action_path = self.needs_action / filename
        action_path.write_text(content)

        # Mark as processed
        if 'msg_id' in item:
            self.processed_messages.add(item['msg_id'])

        # Log the action
        self.log_action('whatsapp_processed', {
            'sender': item.get('sender', 'Unknown'),
            'priority': priority,
            'action_file': filename
        })

        return action_path

    def close(self):
        """Clean up browser resources"""
        if self.context:
            self._save_session()
            self.context.close()
        if self.browser:
            self.browser.close()

    def run(self):
        """Override run with cleanup and banner"""
        print(f'''
╔══════════════════════════════════════════════════════════════╗
║             AI Employee - WhatsApp Watcher                   ║
║                     Silver Tier                              ║
╠══════════════════════════════════════════════════════════════╣
║  Monitoring: WhatsApp Web for important messages             ║
║  Keywords:   urgent, payment, invoice, help, meeting...      ║
║  Interval:   {self.check_interval} seconds                                    ║
║  Actions:    {self.needs_action}
╚══════════════════════════════════════════════════════════════╝
''')
        try:
            super().run()
        finally:
            self.close()


def main():
    """Main entry point"""
    default_vault = Path(__file__).parent.parent / 'AI_Employee_Vault'

    if default_vault.is_symlink():
        default_vault = default_vault.resolve()

    if len(sys.argv) > 1:
        vault_path = sys.argv[1]
    else:
        vault_path = str(default_vault)

    watcher = WhatsAppWatcher(vault_path)
    watcher.run()


if __name__ == '__main__':
    main()
