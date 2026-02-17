"""
WhatsApp Watcher - Monitors WhatsApp Web for new messages
Silver Tier Requirement: Additional Watcher script
Uses Playwright for browser automation
"""
import sys
import json
import argparse
import hashlib
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
        self.recent_scan_limit = 12
        self.state_dir = self.vault_path / 'State'
        self.state_dir.mkdir(exist_ok=True)
        self.state_file = self.state_dir / 'whatsapp_state.json'
        self.chat_state = self._load_chat_state()
        self.state_was_empty = not bool(self.chat_state.get('chats'))

    def _load_chat_state(self) -> dict:
        """Load persistent per-chat state for hybrid scan."""
        default_state = {'updated_at': None, 'chats': {}}
        if not self.state_file.exists():
            return default_state
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return default_state
            chats = data.get('chats', {})
            if not isinstance(chats, dict):
                chats = {}
            return {
                'updated_at': data.get('updated_at'),
                'chats': chats
            }
        except Exception as e:
            self.logger.warning(f'Could not read WhatsApp state file, resetting: {e}')
            return default_state

    def _save_chat_state(self):
        """Persist per-chat state for next cycle."""
        self.chat_state['updated_at'] = datetime.now().isoformat()
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.chat_state, f, indent=2, ensure_ascii=False)

    def _stable_message_key(self, chat_name: str, preview: str) -> str:
        raw = f'{chat_name}|{preview}'.encode('utf-8', errors='ignore')
        return hashlib.sha1(raw).hexdigest()[:16]

    def _extract_chat_info(self, chat, rank: int) -> dict | None:
        """Extract normalized chat row info across WhatsApp UI variants."""
        unread_badge = (
            chat.query_selector('[data-testid="icon-unread-count"]') or
            chat.query_selector('[aria-label*="unread"]') or
            chat.query_selector('span[aria-label*=" unread"]')
        )

        name_elem = (
            chat.query_selector('[data-testid="cell-frame-title"]') or
            chat.query_selector('span[title]')
        )
        chat_name = name_elem.inner_text().strip() if name_elem else 'Unknown'
        if chat_name == 'Unknown' or not chat_name:
            return None

        preview_elem = chat.query_selector('[data-testid="last-msg-status"]')
        if not preview_elem:
            preview_elem = chat.query_selector('span[title]')

        preview = preview_elem.inner_text().strip() if preview_elem else ''
        if not preview:
            row_text = (chat.inner_text() or '').strip()
            row_lines = [line.strip() for line in row_text.split('\n') if line.strip()]
            filtered = [
                line for line in row_lines
                if line != chat_name and not line.isdigit() and ':' not in line[:8]
            ]
            preview = filtered[0] if filtered else row_text[:200]

        if not preview:
            return None

        msg_key = self._stable_message_key(chat_name, preview)
        chat_key = chat_name.lower()
        preview_lower = preview.lower()
        keyword_matched = any(kw in preview_lower for kw in self.important_keywords)
        state_entry = self.chat_state.get('chats', {}).get(chat_key, {})
        is_new = state_entry.get('last_message_key') != msg_key

        return {
            'chat_key': chat_key,
            'chat_name': chat_name,
            'preview': preview,
            'message_key': msg_key,
            'is_unread': bool(unread_badge),
            'is_new': bool(is_new),
            'keyword_matched': keyword_matched,
            'rank': rank
        }

    def _collect_chat_rows(self) -> list:
        """Collect visible chat rows from WhatsApp sidebar."""
        rows = self.page.query_selector_all('[data-testid="cell-frame-container"]')
        if not rows:
            rows = self.page.query_selector_all('#pane-side [role="gridcell"]')
        chat_rows = []
        for idx, chat in enumerate(rows[:40]):
            try:
                info = self._extract_chat_info(chat, rank=idx)
                if info:
                    chat_rows.append(info)
            except Exception as e:
                self.logger.debug(f'Error parsing chat row: {e}')
        return chat_rows

    def _select_hybrid_updates(self, chat_rows: list) -> list:
        """Hybrid strategy: always unread + recent changed chats."""
        selected = []
        seen_message_keys = set()

        def add_row(row: dict, source: str):
            if row['message_key'] in seen_message_keys:
                return
            msg_id = f"{row['chat_name']}_{row['message_key']}"
            if msg_id in self.processed_messages:
                return
            selected.append({
                'type': 'whatsapp_message',
                'sender': row['chat_name'],
                'preview': row['preview'],
                'timestamp': datetime.now().isoformat(),
                'msg_id': msg_id,
                'keyword_matched': row['keyword_matched'],
                'scan_source': source
            })
            seen_message_keys.add(row['message_key'])
            self.processed_messages.add(msg_id)

        # Always include unread messages.
        for row in chat_rows:
            if row['is_unread']:
                add_row(row, 'unread')

        # Cold start guard: seed state first to avoid flooding historical chats.
        if self.state_was_empty:
            return selected

        # Add recent changed chats even if not unread.
        recent_rows = chat_rows[:self.recent_scan_limit]
        for row in recent_rows:
            if row['is_unread']:
                continue
            if row['is_new']:
                add_row(row, 'recent')

        return selected

    def _update_chat_state(self, chat_rows: list):
        """Update per-chat state with latest seen message keys."""
        chats = self.chat_state.setdefault('chats', {})
        now = datetime.now().isoformat()
        for row in chat_rows:
            chats[row['chat_key']] = {
                'chat_name': row['chat_name'],
                'last_message_key': row['message_key'],
                'last_preview': row['preview'][:300],
                'last_seen': now
            }

    def _init_browser(self):
        """Initialize browser with persistent session using user data dir"""
        self._playwright = sync_playwright().start()

        # Use persistent context - saves ALL browser data (cookies,
        # localStorage, indexedDB) to disk automatically like a real Chrome profile.
        # No manual state.json saving needed.
        user_data_dir = str(self.session_path / 'browser_profile')
        self.context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,  # Must be visible for QR scan
            viewport={'width': 1280, 'height': 800},
            args=['--disable-blink-features=AutomationControlled'],
        )
        self.browser = None  # persistent context manages its own browser
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()

    def _save_session(self):
        """Save session backup - persistent context auto-saves to disk.
        This is kept for explicit save points (e.g. after login)."""
        if self.context:
            try:
                storage_state = self.context.storage_state()
                state_file = self.session_path / 'state.json'
                with open(state_file, 'w', encoding='utf-8') as f:
                    json.dump(storage_state, f, indent=2, ensure_ascii=False)
                self.logger.info('WhatsApp session saved')
            except Exception as e:
                # Non-fatal: persistent context still has the data on disk
                self.logger.warning(f'Backup state.json save failed (non-fatal): {e}')

    def _wait_for_login(self):
        """Navigate to WhatsApp Web and wait for login"""
        self.page.goto('https://web.whatsapp.com/')
        self.page.wait_for_timeout(3000)

        # Wait for chat list readiness first (covers "messages are downloading" state)
        if self._wait_for_chat_list_ready(timeout_ms=45000):
            self.logger.info('WhatsApp already logged in via persistent session')
            return True

        # If chat list is not ready but QR is visible, prompt user to login
        qr_visible = False
        try:
            qr_visible = self.page.locator('canvas[aria-label*="Scan me"]').count() > 0
        except Exception:
            qr_visible = False

        if not qr_visible and self._is_downloading_state():
            # Still syncing; skip this cycle without false login prompt
            self.logger.warning('WhatsApp is still syncing; login prompt skipped for now')
            return False

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
            self.page.wait_for_selector('#pane-side', timeout=10000)
            return True
        except PlaywrightTimeout:
            return False

    def _is_downloading_state(self) -> bool:
        """Detect initial sync screen where messages are still downloading."""
        try:
            body_text = self.page.locator('body').inner_text(timeout=3000).lower()
            return (
                'messages are downloading' in body_text or
                "don't close this window" in body_text
            )
        except Exception:
            return False

    def _wait_for_chat_list_ready(self, timeout_ms: int = 30000) -> bool:
        """
        Wait until chat list is visible and usable.
        Returns False if page stays in downloading/sync state.
        """
        selectors = ['#pane-side', '[data-testid="chat-list"]', '[data-testid="cell-frame-container"]']
        start = datetime.now()

        while (datetime.now() - start).total_seconds() * 1000 < timeout_ms:
            if self._is_downloading_state():
                self.logger.info('WhatsApp is still syncing/downloading messages...')
                self.page.wait_for_timeout(3000)
                continue

            for selector in selectors:
                try:
                    if self.page.query_selector(selector):
                        return True
                except Exception:
                    continue

            self.page.wait_for_timeout(1000)

        return False

    def check_for_updates(self) -> list:
        """Check WhatsApp for new messages with important keywords"""
        messages = []

        try:
            if not self.page:
                self._init_browser()
                if not self._wait_for_login():
                    return []

            # Make sure we're on WhatsApp
            if 'web.whatsapp.com' not in self.page.url:
                self.page.goto('https://web.whatsapp.com/')
                self.page.wait_for_timeout(3000)

            # Wait for chat list to be ready (avoid false negatives during sync state)
            if not self._wait_for_chat_list_ready(timeout_ms=45000):
                self.logger.warning('WhatsApp chat list not ready yet; skipping this cycle')
                return []

            chat_rows = self._collect_chat_rows()
            messages = self._select_hybrid_updates(chat_rows)
            self._update_chat_state(chat_rows)
            self._save_chat_state()

            if messages:
                unread_count = sum(1 for m in messages if m.get('scan_source') == 'unread')
                recent_count = sum(1 for m in messages if m.get('scan_source') == 'recent')
                self.logger.info(
                    f'Found {len(messages)} WhatsApp updates '
                    f'(unread={unread_count}, recent_changed={recent_count})'
                )

        except PlaywrightTimeout:
            self.logger.warning('WhatsApp page timeout')
        except Exception as e:
            self.logger.error(f'Error checking WhatsApp: {e}')
            # If browser crashed, reset so next cycle re-initializes
            self.page = None
            self.context = None

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
- Keywords detected: {item.get('keyword_matched', False)}
- Detection source: {item.get('scan_source', 'unread')}
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
        if hasattr(self, '_playwright') and self._playwright:
            self._playwright.stop()

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

    def run_once(self):
        """Run a single check cycle and exit (useful for testing)."""
        try:
            items = self.check_for_updates()
            created = []
            for item in items:
                path = self.create_action_file(item)
                created.append(str(path))
            print({
                'status': 'ok',
                'updates_found': len(items),
                'files_created': len(created),
                'sample_files': created[:5]
            })
        finally:
            self.close()

    def login_keepalive(self):
        """Keep WhatsApp session open for manual login/sync stabilization."""
        print('\nWhatsApp keepalive mode: session window will stay open. Press Ctrl+C to exit.\n')
        try:
            self._init_browser()
            self.page.goto('https://web.whatsapp.com/')
            while True:
                self.page.wait_for_timeout(5000)
        except KeyboardInterrupt:
            self.logger.info('Keepalive stopped by user')
        finally:
            self.close()


def main():
    """Main entry point"""
    default_vault = Path(__file__).parent.parent / 'AI_Employee_Vault'

    if default_vault.is_symlink():
        default_vault = default_vault.resolve()

    parser = argparse.ArgumentParser(description='WhatsApp watcher')
    parser.add_argument('vault_path', nargs='?', default=str(default_vault))
    parser.add_argument('--once', action='store_true', help='Run one cycle and exit')
    parser.add_argument('--login-only', action='store_true', help='Open WhatsApp and keep session window alive')
    args = parser.parse_args()

    watcher = WhatsAppWatcher(args.vault_path)
    if args.login_only:
        watcher.login_keepalive()
    elif args.once:
        watcher.run_once()
    else:
        watcher.run()


if __name__ == '__main__':
    main()
