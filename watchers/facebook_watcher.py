"""
Facebook Watcher - Monitors Facebook for notifications and messages
Gold Tier Requirement: Facebook/Instagram integration
Uses Playwright for browser automation
"""
import sys
import json
from pathlib import Path
from datetime import datetime

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

sys.path.insert(0, str(Path(__file__).parent))
from base_watcher import BaseWatcher


class FacebookWatcher(BaseWatcher):
    """
    Watches Facebook for new notifications and messages.

    Usage:
        python facebook_watcher.py [vault_path]

    First run requires manual Facebook login.
    """

    def __init__(self, vault_path: str, session_path: str = None):
        super().__init__(vault_path, check_interval=300)  # Every 5 minutes

        if session_path is None:
            session_path = Path(__file__).parent.parent / '.facebook_session'
        self.session_path = Path(session_path)
        self.session_path.mkdir(exist_ok=True)

        self.important_keywords = [
            'message', 'comment', 'mention', 'tag', 'reply',
            'business', 'order', 'payment', 'inquiry', 'urgent'
        ]

        self.browser = None
        self.context = None
        self.page = None
        self.processed_items = set()

    def _init_browser(self):
        """Initialize browser with persistent session"""
        playwright = sync_playwright().start()
        self.browser = playwright.chromium.launch(headless=False)

        state_file = self.session_path / 'state.json'
        self.context = self.browser.new_context(
            storage_state=str(state_file) if state_file.exists() else None,
            viewport={'width': 1280, 'height': 800}
        )
        self.page = self.context.new_page()

    def _save_session(self):
        """Save browser session"""
        if self.context:
            self.context.storage_state(path=str(self.session_path / 'state.json'))
            self.logger.info('Facebook session saved')

    def _wait_for_login(self):
        """Navigate to Facebook and wait for login"""
        self.page.goto('https://www.facebook.com/')

        # Check if login needed
        if 'login' in self.page.url.lower() or self.page.query_selector('input[name="email"]'):
            print('\n' + '='*60)
            print('Facebook Login Required!')
            print('Please login in the browser window.')
            print('After login, press Enter here to continue...')
            print('='*60 + '\n')
            input()
            self._save_session()

        self.logger.info('Facebook logged in successfully')

    def check_for_updates(self) -> list:
        """Check Facebook for new notifications and messages"""
        updates = []

        try:
            if not self.page:
                self._init_browser()
                self._wait_for_login()

            # Check notifications
            notifications = self._check_notifications()
            updates.extend(notifications)

            # Check messages
            messages = self._check_messages()
            updates.extend(messages)

        except PlaywrightTimeout:
            self.logger.warning('Facebook page timeout')
        except Exception as e:
            self.logger.error(f'Error checking Facebook: {e}')

        return updates

    def _check_notifications(self) -> list:
        """Check Facebook notifications"""
        notifications = []

        try:
            self.page.goto('https://www.facebook.com/notifications')
            self.page.wait_for_timeout(3000)

            # Find notification items
            notif_items = self.page.query_selector_all('[role="listitem"]')[:10]

            for item in notif_items:
                try:
                    text = item.inner_text().strip()
                    item_id = hash(text[:100])

                    if item_id in self.processed_items:
                        continue

                    # Check for important keywords
                    if any(kw in text.lower() for kw in self.important_keywords):
                        notifications.append({
                            'type': 'facebook_notification',
                            'content': text[:300],
                            'timestamp': datetime.now().isoformat(),
                            'item_id': item_id
                        })
                        self.processed_items.add(item_id)

                except Exception as e:
                    self.logger.debug(f'Error parsing notification: {e}')

            self.logger.info(f'Found {len(notifications)} important Facebook notifications')

        except Exception as e:
            self.logger.warning(f'Error checking notifications: {e}')

        return notifications

    def _check_messages(self) -> list:
        """Check Facebook Messenger"""
        messages = []

        try:
            self.page.goto('https://www.facebook.com/messages/t/')
            self.page.wait_for_timeout(3000)

            # Find unread conversations
            unread = self.page.query_selector_all('[aria-label*="unread"]')[:5]

            for conv in unread:
                try:
                    text = conv.inner_text().strip()
                    item_id = hash(text[:50])

                    if item_id in self.processed_items:
                        continue

                    # Extract sender and preview
                    lines = text.split('\n')
                    sender = lines[0] if lines else 'Unknown'
                    preview = lines[1] if len(lines) > 1 else ''

                    messages.append({
                        'type': 'facebook_message',
                        'sender': sender,
                        'preview': preview[:200],
                        'timestamp': datetime.now().isoformat(),
                        'item_id': item_id
                    })
                    self.processed_items.add(item_id)

                except Exception as e:
                    self.logger.debug(f'Error parsing message: {e}')

            self.logger.info(f'Found {len(messages)} unread Facebook messages')

        except Exception as e:
            self.logger.warning(f'Error checking messages: {e}')

        return messages

    def determine_priority(self, item: dict) -> str:
        """Determine priority based on content"""
        content = f"{item.get('content', '')} {item.get('preview', '')}".lower()

        if any(kw in content for kw in ['urgent', 'payment', 'order', 'business']):
            return 'P1'
        elif any(kw in content for kw in ['message', 'inquiry', 'question']):
            return 'P2'
        return 'P3'

    def create_action_file(self, item: dict) -> Path:
        """Create action file from Facebook update"""
        priority = self.determine_priority(item)
        timestamp = datetime.now()

        if item['type'] == 'facebook_message':
            content = f'''---
type: facebook_message
source: facebook_watcher
priority: {priority}
created: {timestamp.isoformat()}
sender: {item.get('sender', 'Unknown')}
status: pending
---

## Facebook Message

**From:** {item.get('sender', 'Unknown')}

**Preview:**
{item.get('preview', 'No preview')}

## Suggested Actions
- [ ] Open Facebook Messenger
- [ ] Read full message
- [ ] Reply if needed
'''
        else:
            content = f'''---
type: facebook_notification
source: facebook_watcher
priority: {priority}
created: {timestamp.isoformat()}
status: pending
---

## Facebook Notification

{item.get('content', 'No content')}

## Suggested Actions
- [ ] Review on Facebook
- [ ] Take action if needed
'''

        filename = f"FACEBOOK_{item['type'].split('_')[1]}_{timestamp.strftime('%H%M%S')}.md"
        action_path = self.needs_action / filename
        action_path.write_text(content)

        self.log_action('facebook_processed', {
            'type': item['type'],
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
        """Run with banner"""
        print(f'''
╔══════════════════════════════════════════════════════════════╗
║             AI Employee - Facebook Watcher                   ║
║                      Gold Tier                               ║
╠══════════════════════════════════════════════════════════════╣
║  Monitoring: Facebook Notifications & Messages               ║
║  Interval:   {self.check_interval} seconds                             ║
╚══════════════════════════════════════════════════════════════╝
''')
        try:
            super().run()
        finally:
            self.close()


def main():
    default_vault = Path(__file__).parent.parent / 'AI_Employee_Vault'
    if default_vault.is_symlink():
        default_vault = default_vault.resolve()

    vault_path = sys.argv[1] if len(sys.argv) > 1 else str(default_vault)
    watcher = FacebookWatcher(vault_path)
    watcher.run()


if __name__ == '__main__':
    main()
