"""
Twitter (X) Watcher - Monitors Twitter notifications and mentions
Gold Tier Requirement: Twitter (X) integration
Uses Playwright for browser automation (no paid API required)
"""
import re
import sys
from pathlib import Path
from datetime import datetime

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

sys.path.insert(0, str(Path(__file__).parent))
from base_watcher import BaseWatcher


class TwitterWatcher(BaseWatcher):
    """
    Watches Twitter (X) for new mentions and relevant notifications.

    Usage:
        python twitter_watcher.py [vault_path]

    First run requires manual login in browser window.
    """

    def __init__(self, vault_path: str, session_path: str = None):
        super().__init__(vault_path, check_interval=300)  # Every 5 minutes

        if session_path is None:
            session_path = Path(__file__).parent.parent / '.twitter_session'
        self.session_path = Path(session_path)
        self.session_path.mkdir(exist_ok=True)

        self.important_keywords = [
            'mention', 'reply', 'dm', 'message', 'quote',
            'business', 'collab', 'partnership', 'opportunity',
            'urgent', 'help', 'inquiry'
        ]

        self.playwright = None
        self.context = None
        self.page = None
        self.processed_items = set()

    def _init_browser(self):
        """Initialize browser with persistent session"""
        if self.page:
            return

        self.playwright = sync_playwright().start()
        user_data_dir = str(self.session_path / 'browser_profile')

        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            viewport={'width': 1280, 'height': 900},
            args=['--disable-blink-features=AutomationControlled'],
        )
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()

    def _save_session(self):
        """Save session backup - persistent context auto-saves to disk"""
        if not self.context:
            return
        try:
            self.context.storage_state(path=str(self.session_path / 'state.json'))
            self.logger.info('Twitter session saved')
        except Exception as e:
            self.logger.warning(f'Could not save Twitter state backup: {e}')

    def _needs_login(self) -> bool:
        """Best-effort login detection"""
        url = self.page.url.lower()
        if '/login' in url or '/i/flow/login' in url:
            return True

        login_inputs = [
            'input[name="text"]',
            'input[autocomplete="username"]',
            'input[name="password"]',
        ]
        for selector in login_inputs:
            if self.page.query_selector(selector):
                return True
        return False

    def _wait_for_login(self):
        """Navigate to X and wait for manual login when needed"""
        self.page.goto('https://x.com/home', wait_until='domcontentloaded')
        self.page.wait_for_timeout(3000)

        if self._needs_login():
            print('\n' + '=' * 64)
            print('Twitter/X Login Required')
            print('Please login in the opened browser window.')
            print('After login completes, press Enter here to continue...')
            print('=' * 64 + '\n')
            input()
            self.page.goto('https://x.com/home', wait_until='domcontentloaded')
            self.page.wait_for_timeout(3000)
            self._save_session()

        self.logger.info('Twitter/X session ready')

    def _extract_entities(self, text: str) -> tuple[list, list]:
        hashtags = re.findall(r'#([A-Za-z0-9_]+)', text or '')
        mentions = re.findall(r'@([A-Za-z0-9_]+)', text or '')
        return hashtags, mentions

    def check_for_updates(self) -> list:
        """Check Twitter for new mentions and relevant notifications"""
        updates = []

        try:
            if not self.page:
                self._init_browser()
                self._wait_for_login()

            mentions = self._check_mentions()
            updates.extend(mentions)

            notifications = self._check_notifications()
            updates.extend(notifications)

            self._save_session()

        except PlaywrightTimeout:
            self.logger.warning('Twitter page timeout')
        except Exception as e:
            self.logger.error(f'Error checking Twitter: {e}')
            self.page = None
            self.context = None

        return updates

    def _check_mentions(self) -> list:
        """Check the mentions tab"""
        mentions = []

        try:
            self.page.goto('https://x.com/notifications/mentions', wait_until='domcontentloaded')
            self.page.wait_for_timeout(3500)

            tweets = self.page.query_selector_all('[data-testid="tweet"]')[:15]
            for tweet in tweets:
                try:
                    text_el = tweet.query_selector('[data-testid="tweetText"]')
                    text = text_el.inner_text().strip() if text_el else ''
                    if not text:
                        continue

                    user_el = tweet.query_selector('[data-testid="User-Name"]')
                    sender = 'unknown'
                    if user_el:
                        lines = [line.strip() for line in user_el.inner_text().split('\n') if line.strip()]
                        if lines:
                            sender = lines[0]

                    item_id = tweet.get_attribute('data-tweet-id') or str(hash(f'mention:{sender}:{text[:120]}'))
                    if item_id in self.processed_items:
                        continue

                    hashtags, mentioned_users = self._extract_entities(text)
                    mentions.append({
                        'type': 'twitter_mention',
                        'sender': sender,
                        'content': text[:400],
                        'timestamp': datetime.now().isoformat(),
                        'item_id': item_id,
                        'hashtags': hashtags,
                        'mentioned_users': mentioned_users,
                    })
                    self.processed_items.add(item_id)
                except Exception as e:
                    self.logger.debug(f'Error parsing mention tweet: {e}')

            self.logger.info(f'Found {len(mentions)} Twitter mentions')

        except Exception as e:
            self.logger.warning(f'Error checking mentions: {e}')

        return mentions

    def _check_notifications(self) -> list:
        """Check notifications for keyword-relevant tweets"""
        notifications = []

        try:
            self.page.goto('https://x.com/notifications', wait_until='domcontentloaded')
            self.page.wait_for_timeout(3500)

            tweets = self.page.query_selector_all('[data-testid="tweet"]')[:20]
            for tweet in tweets:
                try:
                    text_el = tweet.query_selector('[data-testid="tweetText"]')
                    text = text_el.inner_text().strip() if text_el else ''
                    if not text:
                        continue

                    if not any(keyword in text.lower() for keyword in self.important_keywords):
                        continue

                    user_el = tweet.query_selector('[data-testid="User-Name"]')
                    sender = 'unknown'
                    if user_el:
                        lines = [line.strip() for line in user_el.inner_text().split('\n') if line.strip()]
                        if lines:
                            sender = lines[0]

                    item_id = tweet.get_attribute('data-tweet-id') or str(hash(f'notif:{sender}:{text[:120]}'))
                    if item_id in self.processed_items:
                        continue

                    hashtags, mentioned_users = self._extract_entities(text)
                    notifications.append({
                        'type': 'twitter_timeline_post',
                        'sender': sender,
                        'content': text[:400],
                        'timestamp': datetime.now().isoformat(),
                        'item_id': item_id,
                        'hashtags': hashtags,
                        'mentioned_users': mentioned_users,
                    })
                    self.processed_items.add(item_id)
                except Exception as e:
                    self.logger.debug(f'Error parsing notification tweet: {e}')

            self.logger.info(f'Found {len(notifications)} relevant posts in notifications')

        except Exception as e:
            self.logger.warning(f'Error checking notifications: {e}')

        return notifications

    def determine_priority(self, item: dict) -> str:
        """Determine priority based on content"""
        content = f"{item.get('content', '')} {item.get('preview', '')}".lower()

        if any(kw in content for kw in ['urgent', 'business', 'opportunity', 'partnership']):
            return 'P1'
        if any(kw in content for kw in ['collab', 'inquiry', 'help', 'dm']):
            return 'P2'
        return 'P3'

    def create_action_file(self, item: dict) -> Path:
        """Create action file from Twitter update"""
        priority = self.determine_priority(item)
        timestamp = datetime.now()

        item_type = item['type'].split('_')[1]  # mention or timeline_post

        if item['type'] == 'twitter_mention':
            content = f'''---
type: twitter_mention
source: twitter_watcher
priority: {priority}
created: {timestamp.isoformat()}
sender: {item.get('sender', 'Unknown')}
hashtags: {item.get('hashtags', [])}
mentioned_users: {item.get('mentioned_users', [])}
status: pending
---

## Twitter Mention

**From:** {item.get('sender', 'Unknown')}

**Tweet:**
{item.get('content', 'No content')}

**Hashtags:** {', '.join(item.get('hashtags', [])) or 'None'}
**Mentioned Users:** {', '.join(item.get('mentioned_users', [])) or 'None'}

## Suggested Actions
- [ ] View tweet on Twitter
- [ ] Reply or retweet if appropriate
- [ ] Like to acknowledge
'''
        elif item['type'] == 'twitter_timeline_post':
            content = f'''---
type: twitter_timeline_post
source: twitter_watcher
priority: {priority}
created: {timestamp.isoformat()}
sender: {item.get('sender', 'Unknown')}
hashtags: {item.get('hashtags', [])}
mentioned_users: {item.get('mentioned_users', [])}
status: pending
---

## Twitter Timeline Post

**From:** {item.get('sender', 'Unknown')}

**Tweet:**
{item.get('content', 'No content')}

**Hashtags:** {', '.join(item.get('hashtags', [])) or 'None'}
**Mentioned Users:** {', '.join(item.get('mentioned_users', [])) or 'None'}

## Suggested Actions
- [ ] Review on Twitter
- [ ] Engage if relevant
- [ ] Save for follow-up if important
'''
        else:
            content = f'''---
type: twitter_update
source: twitter_watcher
priority: {priority}
created: {timestamp.isoformat()}
status: pending
---

## Twitter Update

{item.get('content', 'No content')}

## Suggested Actions
- [ ] Review on Twitter
- [ ] Take action if needed
'''

        filename = f"TWITTER_{item_type}_{timestamp.strftime('%H%M%S')}.md"
        action_path = self.needs_action / filename
        action_path.write_text(content)

        self.log_action('twitter_processed', {
            'type': item['type'],
            'priority': priority,
            'action_file': filename,
        })

        return action_path

    def run(self):
        """Run with banner"""
        print(f'''
╔══════════════════════════════════════════════════════════════╗
║             AI Employee - Twitter (X) Watcher                ║
║                      Gold Tier                               ║
╠══════════════════════════════════════════════════════════════╣
║  Monitoring: Mentions & Notifications                        ║
║  Interval:   {self.check_interval} seconds                             ║
║  Mode:       Playwright session (.twitter_session)           ║
╚══════════════════════════════════════════════════════════════╝
''')
        super().run()


def main():
    default_vault = Path(__file__).parent.parent / 'AI_Employee_Vault'
    if default_vault.is_symlink():
        default_vault = default_vault.resolve()

    vault_path = sys.argv[1] if len(sys.argv) > 1 else str(default_vault)
    watcher = TwitterWatcher(vault_path)
    watcher.run()


if __name__ == '__main__':
    main()
