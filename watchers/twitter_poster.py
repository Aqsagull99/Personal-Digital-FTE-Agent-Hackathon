"""
Twitter (X) Poster - Posts tweets using Playwright automation
Gold Tier Requirement: Twitter (X) integration
Uses browser session flow to avoid paid API dependency
"""
import argparse
import json
from pathlib import Path
from datetime import datetime

from playwright.sync_api import sync_playwright


class TwitterPoster:
    """
    Posts tweets to Twitter (X) with human-in-the-loop approval.

    Usage:
        poster = TwitterPoster(vault_path)
        poster.post_tweet("Tweet content")
    """

    def __init__(self, vault_path: str = None):
        if vault_path is None:
            vault_path = Path(__file__).parent.parent / 'AI_Employee_Vault'
        self.vault_path = Path(vault_path)

        if self.vault_path.is_symlink():
            self.vault_path = self.vault_path.resolve()

        self.logs_path = self.vault_path / 'Logs'
        self.pending_approval = self.vault_path / 'Pending_Approval'
        self.approved_path = self.vault_path / 'Approved'

        self.logs_path.mkdir(exist_ok=True)
        self.pending_approval.mkdir(exist_ok=True)
        self.approved_path.mkdir(exist_ok=True)

        self.session_path = Path(__file__).parent.parent / '.twitter_session'
        self.session_path.mkdir(exist_ok=True)

        self.playwright = None
        self.context = None
        self.page = None

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

    def close(self):
        """Clean up browser context"""
        try:
            if self.context:
                self.context.close()
        finally:
            self.context = None
            self.page = None
            if self.playwright:
                self.playwright.stop()
                self.playwright = None

    def _save_session(self):
        """Save session backup - persistent context auto-saves to disk"""
        if not self.context:
            return
        try:
            self.context.storage_state(path=str(self.session_path / 'state.json'))
        except Exception:
            pass

    def _needs_login(self) -> bool:
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

    def _wait_for_login_if_needed(self) -> bool:
        """Ensure active authenticated session; return True when ready"""
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

            if self._needs_login():
                print('Login still not detected. Post cancelled.')
                return False

            self._save_session()

        return True

    def _post_direct(self, content: str) -> bool:
        """Post tweet directly through web composer"""
        self._init_browser()

        if not self._wait_for_login_if_needed():
            return False

        self.page.goto('https://x.com/compose/post', wait_until='domcontentloaded')

        textarea = None
        for selector in ['[data-testid="tweetTextarea_0"][contenteditable="true"]', '[data-testid="tweetTextarea_0"]', 'div[role="textbox"][contenteditable="true"]']:
            try:
                self.page.wait_for_selector(selector, timeout=15000)
                candidates = self.page.query_selector_all(selector)
                for candidate in candidates:
                    try:
                        if candidate.is_visible():
                            textarea = candidate
                            break
                    except Exception:
                        continue
                if textarea:
                    break
            except Exception:
                continue

        if not textarea:
            print('Could not find tweet composer textbox.')
            return False

        textarea.click()
        self.page.wait_for_timeout(300)
        payload = content[:280]
        self.page.keyboard.type(payload, delay=20)
        self.page.wait_for_timeout(700)

        # Verify text really landed in the active editor; if not, force inject.
        try:
            current_text = (textarea.inner_text() or '').strip()
        except Exception:
            current_text = ''
        if not current_text:
            try:
                textarea.evaluate(
                    """(el, value) => {
                        el.focus();
                        el.textContent = value;
                        el.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertText', data: value}));
                    }""",
                    payload,
                )
                self.page.wait_for_timeout(800)
            except Exception:
                pass

        tweet_btn = None
        for selector in ['[data-testid="tweetButton"]', '[data-testid="tweetButtonInline"]']:
            try:
                self.page.wait_for_selector(selector, timeout=10000)
                buttons = self.page.query_selector_all(selector)
                for button in buttons:
                    try:
                        if not button.is_visible():
                            continue
                    except Exception:
                        continue

                    disabled = None
                    try:
                        disabled = button.get_attribute('aria-disabled')
                    except Exception:
                        pass
                    if disabled == 'true':
                        continue

                    tweet_btn = button
                    break
                if tweet_btn:
                    break
            except Exception:
                continue

        if not tweet_btn:
            print('Could not find Tweet/Post button.')
            return False

        clicked = False
        try:
            tweet_btn.click()
            clicked = True
        except Exception:
            try:
                tweet_btn.evaluate("(el) => el.click()")
                clicked = True
            except Exception:
                clicked = False

        if not clicked:
            print('Could not click Tweet/Post button.')
            return False
        self.page.wait_for_timeout(4000)
        self._save_session()
        return True

    def post_tweet(self, content: str, requires_approval: bool = True) -> bool:
        """
        Post a tweet with optional approval workflow.

        Args:
            content: The tweet content to post
            requires_approval: Whether to create approval file first

        Returns:
            bool: True if tweet was posted successfully
        """
        if requires_approval:
            approval_file = self._create_approval_file(content)
            print(f'Approval required: {approval_file}')
            return False

        try:
            success = self._post_direct(content)
            if success:
                print('Successfully posted tweet via Playwright session')
                self._log_action('twitter_post', {
                    'content': content,
                    'timestamp': datetime.now().isoformat(),
                    'mode': 'playwright',
                })
                return True

            print('Failed to post tweet via Playwright')
            return False
        except Exception as e:
            print(f'Error posting tweet: {e}')
            return False
        finally:
            self.close()

    def _create_approval_file(self, content: str) -> Path:
        """Create approval file for human-in-the-loop workflow"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'TWITTER_POST_APPROVAL_{timestamp}.md'
        approval_path = self.pending_approval / filename

        approval_content = f"""---
type: twitter_post_approval
source: twitter_poster
created: {datetime.now().isoformat()}
status: pending
---

## Twitter Post Approval Request

**Content to post:**
{content}

## To Approve
Move this file to the `/Approved` folder to post to Twitter.

## To Reject
Move this file to the `/Rejected` folder.

## Tweet Preview
{content[:280]}  <!-- Twitter character limit -->
"""

        approval_path.write_text(approval_content)
        return approval_path

    def _log_action(self, action_type: str, details: dict):
        """Log action to daily log file"""
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.logs_path / f'{today}.json'

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action_type': action_type,
            'poster': 'TwitterPoster',
            **details,
        }

        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        else:
            logs = []

        logs.append(log_entry)

        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2)

    def process_approved_posts(self):
        """Process approved Twitter posts"""
        approved_files = list(self.approved_path.glob('TWITTER_POST_APPROVAL_*.md'))

        for file_path in approved_files:
            content = file_path.read_text(encoding='utf-8')

            lines = content.split('\n')
            tweet_content = ''
            capturing = False

            for line in lines:
                if '**Content to post:**' in line:
                    capturing = True
                    continue
                if capturing and line.startswith('##'):
                    break
                if capturing:
                    tweet_content += line.strip() + ' '

            tweet_content = tweet_content.strip()
            if not tweet_content:
                print(f'Skipping {file_path.name}: no tweet content found')
                continue

            try:
                posted = self.post_tweet(tweet_content, requires_approval=False)
                if posted:
                    self._log_action('twitter_post_approved', {
                        'content': tweet_content,
                        'timestamp': datetime.now().isoformat(),
                        'mode': 'playwright',
                    })
                    completed_path = self.approved_path / f'COMPLETED_{file_path.name}'
                    file_path.rename(completed_path)
                    print(f'Processed approved tweet: {file_path.name}')
                else:
                    print(f'Failed to post approved tweet from {file_path.name}')
            except Exception as e:
                print(f'Error posting approved tweet from {file_path.name}: {e}')


def main():
    """CLI entrypoint"""
    default_vault = Path(__file__).parent.parent / 'AI_Employee_Vault'
    if default_vault.is_symlink():
        default_vault = default_vault.resolve()

    parser = argparse.ArgumentParser(description='Twitter/X poster using Playwright')
    parser.add_argument('content', nargs='?', help='Tweet content')
    parser.add_argument('--vault-path', default=str(default_vault), help='Path to AI_Employee_Vault')
    parser.add_argument('--post-direct', help='Post this content immediately without approval')
    parser.add_argument('--approve', action='store_true', help='Process approved Twitter post files')
    args = parser.parse_args()

    poster = TwitterPoster(args.vault_path)

    if args.approve:
        print('Processing approved Twitter posts...')
        poster.process_approved_posts()
        return

    if args.post_direct:
        ok = poster.post_tweet(args.post_direct, requires_approval=False)
        print(f'POST_OK={ok}')
        return

    if args.content:
        ok = poster.post_tweet(args.content, requires_approval=True)
        print(f'PENDING_APPROVAL={not ok}')
        return

    print('Twitter Poster initialized')
    print('Mode: Playwright browser session')
    print('Usage examples:')
    print('  python twitter_poster.py "Draft tweet for approval"')
    print('  python twitter_poster.py --post-direct "Post now"')
    print('  python twitter_poster.py --approve')


if __name__ == '__main__':
    main()
