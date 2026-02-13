"""
Instagram Watcher - Monitors Instagram for notifications and DMs
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


class InstagramWatcher(BaseWatcher):
    """
    Watches Instagram for new notifications and direct messages.

    Usage:
        python instagram_watcher.py [vault_path]

    First run requires manual Instagram login.
    """

    def __init__(self, vault_path: str, session_path: str = None):
        super().__init__(vault_path, check_interval=300)  # Every 5 minutes

        if session_path is None:
            session_path = Path(__file__).parent.parent / '.instagram_session'
        self.session_path = Path(session_path)
        self.session_path.mkdir(exist_ok=True)

        self.important_keywords = [
            'dm', 'message', 'comment', 'mention', 'collab',
            'business', 'inquiry', 'order', 'partnership', 'sponsor'
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
            self.logger.info('Instagram session saved')

    def _wait_for_login(self):
        """Navigate to Instagram and wait for login"""
        self.page.goto('https://www.instagram.com/')
        self.page.wait_for_timeout(2000)

        # Check if login needed
        if self.page.query_selector('input[name="username"]'):
            print('\n' + '='*60)
            print('Instagram Login Required!')
            print('Please login in the browser window.')
            print('After login, press Enter here to continue...')
            print('='*60 + '\n')
            input()
            self._save_session()

        self.logger.info('Instagram logged in successfully')

    def check_for_updates(self) -> list:
        """Check Instagram for new notifications and DMs"""
        updates = []

        try:
            if not self.page:
                self._init_browser()
                self._wait_for_login()

            # Check notifications
            notifications = self._check_notifications()
            updates.extend(notifications)

            # Check DMs
            dms = self._check_direct_messages()
            updates.extend(dms)

        except PlaywrightTimeout:
            self.logger.warning('Instagram page timeout')
        except Exception as e:
            self.logger.error(f'Error checking Instagram: {e}')

        return updates

    def _check_notifications(self) -> list:
        """Check Instagram notifications"""
        notifications = []

        try:
            self.page.goto('https://www.instagram.com/')
            self.page.wait_for_timeout(2000)

            # Click notifications icon
            notif_btn = self.page.query_selector('[aria-label="Notifications"]')
            if notif_btn:
                notif_btn.click()
                self.page.wait_for_timeout(2000)

                # Find notification items
                notif_items = self.page.query_selector_all('[role="dialog"] [role="button"]')[:10]

                for item in notif_items:
                    try:
                        text = item.inner_text().strip()
                        item_id = hash(text[:100])

                        if item_id in self.processed_items:
                            continue

                        if any(kw in text.lower() for kw in self.important_keywords):
                            notifications.append({
                                'type': 'instagram_notification',
                                'content': text[:300],
                                'timestamp': datetime.now().isoformat(),
                                'item_id': item_id
                            })
                            self.processed_items.add(item_id)

                    except Exception as e:
                        self.logger.debug(f'Error parsing notification: {e}')

            self.logger.info(f'Found {len(notifications)} important Instagram notifications')

        except Exception as e:
            self.logger.warning(f'Error checking notifications: {e}')

        return notifications

    def _check_direct_messages(self) -> list:
        """Check Instagram Direct Messages"""
        messages = []

        try:
            self.page.goto('https://www.instagram.com/direct/inbox/')
            self.page.wait_for_timeout(3000)

            # Find unread conversations (usually have a blue dot)
            conversations = self.page.query_selector_all('[role="listitem"]')[:10]

            for conv in conversations:
                try:
                    # Check for unread indicator
                    has_unread = conv.query_selector('[aria-label*="unread"]') or \
                                 conv.query_selector('.x1ey2m1c')  # Blue dot class

                    if not has_unread:
                        continue

                    text = conv.inner_text().strip()
                    item_id = hash(text[:50])

                    if item_id in self.processed_items:
                        continue

                    lines = text.split('\n')
                    sender = lines[0] if lines else 'Unknown'
                    preview = lines[-1] if len(lines) > 1 else ''

                    messages.append({
                        'type': 'instagram_dm',
                        'sender': sender,
                        'preview': preview[:200],
                        'timestamp': datetime.now().isoformat(),
                        'item_id': item_id
                    })
                    self.processed_items.add(item_id)

                except Exception as e:
                    self.logger.debug(f'Error parsing DM: {e}')

            self.logger.info(f'Found {len(messages)} unread Instagram DMs')

        except Exception as e:
            self.logger.warning(f'Error checking DMs: {e}')

        return messages

    def determine_priority(self, item: dict) -> str:
        """Determine priority based on content"""
        content = f"{item.get('content', '')} {item.get('preview', '')}".lower()

        if any(kw in content for kw in ['business', 'order', 'sponsor', 'partnership']):
            return 'P1'
        elif any(kw in content for kw in ['collab', 'inquiry', 'dm']):
            return 'P2'
        return 'P3'

    def create_action_file(self, item: dict) -> Path:
        """Create action file from Instagram update"""
        priority = self.determine_priority(item)
        timestamp = datetime.now()

        if item['type'] == 'instagram_dm':
            content = f'''---
type: instagram_dm
source: instagram_watcher
priority: {priority}
created: {timestamp.isoformat()}
sender: {item.get('sender', 'Unknown')}
status: pending
---

## Instagram Direct Message

**From:** {item.get('sender', 'Unknown')}

**Preview:**
{item.get('preview', 'No preview')}

## Suggested Actions
- [ ] Open Instagram DMs
- [ ] Read full message
- [ ] Reply if needed
'''
        else:
            content = f'''---
type: instagram_notification
source: instagram_watcher
priority: {priority}
created: {timestamp.isoformat()}
status: pending
---

## Instagram Notification

{item.get('content', 'No content')}

## Suggested Actions
- [ ] Review on Instagram
- [ ] Take action if needed
'''

        filename = f"INSTAGRAM_{item['type'].split('_')[1]}_{timestamp.strftime('%H%M%S')}.md"
        action_path = self.needs_action / filename
        action_path.write_text(content)

        self.log_action('instagram_processed', {
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
║             AI Employee - Instagram Watcher                  ║
║                      Gold Tier                               ║
╠══════════════════════════════════════════════════════════════╣
║  Monitoring: Instagram Notifications & DMs                   ║
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
    watcher = InstagramWatcher(vault_path)
    watcher.run()


if __name__ == '__main__':
    main()
