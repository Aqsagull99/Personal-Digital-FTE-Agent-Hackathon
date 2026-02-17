"""
Facebook Poster - Posts content to Facebook
Gold Tier Requirement: Facebook integration
Uses Playwright for browser automation with Human-in-the-Loop approval
"""
import sys
import json
import os
from pathlib import Path
from datetime import datetime

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


class FacebookPoster:
    """
    Posts content to Facebook with approval workflow.

    Usage:
        poster = FacebookPoster(vault_path)
        poster.post("Content here")

    Or from command line:
        python facebook_poster.py "Post content"
        python facebook_poster.py --post-direct "Post without approval"
        python facebook_poster.py --approve   # Publish approved posts
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
        self.done_path = self.vault_path / 'Done'
        self.done_path.mkdir(exist_ok=True)
        self.dry_run = os.getenv('DRY_RUN', 'false').lower() == 'true'

        # Session path
        self.fb_session = Path(__file__).parent.parent / '.facebook_session'

        self.browser = None
        self.context = None
        self.page = None

    def _init_browser(self):
        """Initialize browser with persistent session using user data dir"""
        self._playwright = sync_playwright().start()
        self.fb_session.mkdir(exist_ok=True)

        user_data_dir = str(self.fb_session / 'browser_profile')
        self.context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            viewport={'width': 1280, 'height': 800},
            args=['--disable-blink-features=AutomationControlled'],
        )
        self.browser = None  # persistent context manages its own browser
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()

    def _save_session(self):
        """Save session backup - persistent context auto-saves to disk"""
        if self.context:
            try:
                self.fb_session.mkdir(exist_ok=True)
                self.context.storage_state(path=str(self.fb_session / 'state.json'))
            except Exception:
                pass  # Non-fatal: persistent context already saved to disk

    def create_approval_request(self, content: str, image_path: str = None) -> Path:
        """Create approval request for Facebook post"""
        timestamp = datetime.now()
        filename = f"FACEBOOK_POST_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"

        approval_content = f'''---
type: facebook_post_approval
action: post_to_facebook
created: {timestamp.isoformat()}
has_image: {bool(image_path)}
image_path: {image_path or 'None'}
status: pending
---

## Facebook Post Request

### Content to Post:
{content}

'''
        if image_path:
            approval_content += f'''### Image:
{image_path}

'''

        approval_content += f'''### Post Details
- **Platform:** Facebook
- **Created:** {timestamp.strftime('%Y-%m-%d %H:%M')}

### To Approve
Move this file to /Approved folder.

### To Reject
Move this file to /Done folder (or delete).

---
*This post requires human approval before publishing.*
'''

        approval_path = self.pending_approval / filename
        approval_path.write_text(approval_content)
        return approval_path

    def post(self, content: str, image_path: str = None, require_approval: bool = True) -> dict:
        """Post to Facebook

        Uses Playwright text/role locators and keyboard.type() for the
        contenteditable composer, matching the approach proven in debug scripts.
        """
        if require_approval:
            approval_file = self.create_approval_request(content, image_path)
            return {
                'status': 'pending_approval',
                'message': 'Facebook post requires approval',
                'approval_file': str(approval_file)
            }

        if self.dry_run:
            fake_post_id = f"dryrun_fb_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            self._log_action('facebook_post', {
                'status': 'dry_run_success',
                'post_id': fake_post_id,
                'content': content[:100]
            })
            return {
                'status': 'success',
                'message': f'DRY_RUN enabled: simulated Facebook post {fake_post_id}',
                'post_id': fake_post_id
            }

        try:
            self._init_browser()
            self.page.goto('https://www.facebook.com/')
            self.page.wait_for_timeout(5000)

            # Check login - look for login form or title
            is_login = False
            if self.page.query_selector('input[name="email"]'):
                try:
                    title = self.page.title()
                    if 'log in' in title.lower() or 'sign up' in title.lower():
                        is_login = True
                except Exception:
                    is_login = True
            if is_login:
                return {'status': 'error', 'message': 'Facebook login required. Run fb_login.py first.'}

            # Wait for feed to load
            self.page.wait_for_timeout(3000)

            # Open post composer - try multiple methods
            clicked = False

            # Method 1: Playwright text locator for "What's on your mind"
            if not clicked:
                try:
                    mind_el = self.page.get_by_text("What's on your mind")
                    if mind_el.count() > 0:
                        mind_el.first.click()
                        clicked = True
                except Exception:
                    pass

            # Method 2: aria-label selector
            if not clicked:
                for label_text in ["on your mind", "Create a post", "Create post"]:
                    try:
                        el = self.page.query_selector(f'[aria-label*="{label_text}"]')
                        if el:
                            el.click()
                            clicked = True
                            break
                    except Exception:
                        pass

            # Method 3: JS search for relevant elements
            if not clicked:
                try:
                    result = self.page.evaluate('''() => {
                        var allEls = document.querySelectorAll('[role="button"], [role="textbox"], span, div');
                        for (var i = 0; i < allEls.length; i++) {
                            var text = (allEls[i].innerText || '').trim();
                            var ariaLabel = allEls[i].getAttribute('aria-label') || '';
                            if (text.indexOf('on your mind') >= 0 || ariaLabel.indexOf('on your mind') >= 0 ||
                                text === 'Create post' || ariaLabel === 'Create a post') {
                                var rect = allEls[i].getBoundingClientRect();
                                return {found: true, x: rect.x + rect.width/2, y: rect.y + rect.height/2};
                            }
                        }
                        return {found: false};
                    }''')
                    if result.get('found'):
                        self.page.mouse.click(result['x'], result['y'])
                        clicked = True
                except Exception:
                    pass

            if not clicked:
                return {'status': 'error', 'message': 'Could not find post composer'}

            self.page.wait_for_timeout(3000)

            # Type content using role-based textbox + keyboard.type
            text_entered = False
            try:
                tb = self.page.get_by_role("textbox")
                if tb.count() > 0:
                    for idx in range(tb.count()):
                        try:
                            box = tb.nth(idx)
                            if box.is_visible():
                                box.click()
                                self.page.wait_for_timeout(500)
                                self.page.keyboard.type(content, delay=20)
                                text_entered = True
                                break
                        except Exception:
                            continue
            except Exception:
                pass

            if not text_entered:
                return {'status': 'error', 'message': 'Could not enter text in composer'}

            self.page.wait_for_timeout(2000)

            # Click post action button using multiple fallbacks because
            # Facebook labels differ by UI variant (Post/Publish/Share).
            posted = False

            # Method 1: aria-label exact match variants via JS dispatchEvent
            try:
                result = self.page.evaluate('''() => {
                    var labels = ['Post', 'Publish', 'Share'];
                    for (var j = 0; j < labels.length; j++) {
                        var selector = '[aria-label="' + labels[j] + '"]';
                        var postBtns = document.querySelectorAll(selector);
                        for (var i = 0; i < postBtns.length; i++) {
                            var el = postBtns[i];
                            var rect = el.getBoundingClientRect();
                            var disabled = el.getAttribute('aria-disabled');
                            if (rect.width > 0 && rect.height > 0 && disabled !== 'true') {
                                el.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
                                return {clicked: true, label: labels[j]};
                            }
                        }
                    }
                    return {clicked: false};
                }''')
                if result.get('clicked'):
                    posted = True
            except Exception:
                pass

            # Method 2: role="button" with exact text variants
            if not posted:
                try:
                    result = self.page.evaluate('''() => {
                        var words = ['Post', 'Publish', 'Share'];
                        var allBtns = document.querySelectorAll('[role="button"]');
                        for (var i = 0; i < allBtns.length; i++) {
                            var el = allBtns[i];
                            var text = (el.innerText || '').trim();
                            var ariaLabel = el.getAttribute('aria-label') || '';
                            var rect = el.getBoundingClientRect();
                            var matches = words.indexOf(text) >= 0 || words.indexOf(ariaLabel) >= 0;
                            if (matches &&
                                ariaLabel !== 'Add to your post' &&
                                rect.width > 0 && rect.height > 0) {
                                el.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
                                return {clicked: true};
                            }
                        }
                        return {clicked: false};
                    }''')
                    if result.get('clicked'):
                        posted = True
                except Exception:
                    pass

            # Method 3: Try keyboard Enter on focused primary action button
            if not posted:
                try:
                    focused = self.page.evaluate('''() => {
                        var el = document.activeElement;
                        if (!el) return null;
                        return {
                            text: (el.innerText || '').trim(),
                            ariaLabel: (el.getAttribute('aria-label') || '').trim()
                        };
                    }''')
                    if focused and focused.get('ariaLabel') in ('Post', 'Publish', 'Share'):
                        self.page.keyboard.press('Enter')
                        posted = True
                except Exception:
                    pass

            # Method 4: Tab to action button and press Enter
            if not posted:
                try:
                    for _ in range(15):
                        self.page.keyboard.press('Tab')
                        self.page.wait_for_timeout(200)
                        focused = self.page.evaluate('''() => {
                            var el = document.activeElement;
                            if (!el) return null;
                            return {
                                text: (el.innerText || '').trim(),
                                ariaLabel: (el.getAttribute('aria-label') || '').trim()
                            };
                        }''')
                        if focused and (
                            focused.get('ariaLabel') in ('Post', 'Publish', 'Share') or
                            focused.get('text') in ('Post', 'Publish', 'Share')
                        ):
                            self.page.keyboard.press('Enter')
                            posted = True
                            break
                except Exception:
                    pass

            if not posted:
                return {'status': 'error', 'message': 'Could not click Post/Publish/Share button'}

            self.page.wait_for_timeout(10000)

            self._log_action('facebook_post', {'status': 'success', 'content': content[:100]})
            self._save_session()

            return {'status': 'success', 'message': 'Posted to Facebook'}

        except Exception as e:
            return {'status': 'error', 'message': str(e)}
        finally:
            self.close()

    def process_approved_posts(self):
        """Process approved Facebook posts from /Approved folder"""
        approved_files = list(self.approved_path.glob('FACEBOOK_POST_*.md')) + \
                         list(self.approved_path.glob('*FACEBOOK_POST_APPROVAL_*.md'))

        if not approved_files:
            print('No approved Facebook posts found.')
            return []

        results = []
        for file_path in approved_files:
            print(f"Processing approved post: {file_path.name}")

            content = file_path.read_text()
            content_lines = content.split('\n')
            post_content = ""
            image_path = None

            for i, line in enumerate(content_lines):
                if line.strip() == '### Content to Post:':
                    if i + 1 < len(content_lines):
                        post_content = content_lines[i + 1].strip()
                elif line.strip() == '### Image:':
                    if i + 1 < len(content_lines):
                        image_path = content_lines[i + 1].strip()

            result = self.post(post_content, image_path, require_approval=False)

            results.append({
                'file': str(file_path),
                'platform': 'facebook',
                'content': post_content,
                'result': result
            })

            if result.get('status') == 'success':
                done_path = self.done_path / file_path.name
                if done_path.exists():
                    done_path = self.done_path / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_path.name}"
                file_path.rename(done_path)

        return results

    def generate_summary(self, days: int = 7) -> dict:
        """Generate summary of Facebook posting activity"""
        summary = {
            'platform': 'facebook',
            'period_days': days,
            'posts_created': 0,
            'posts_pending': 0,
            'notifications_processed': 0
        }

        for log_file in self.logs_path.glob('*.json'):
            try:
                with open(log_file, 'r') as f:
                    logs = json.load(f)
                    for entry in logs:
                        if 'facebook' in entry.get('action_type', ''):
                            if 'post' in entry.get('action_type', ''):
                                summary['posts_created'] += 1
                            else:
                                summary['notifications_processed'] += 1
            except:
                pass

        for f in self.pending_approval.glob('FACEBOOK_POST_*.md'):
            summary['posts_pending'] += 1

        return summary

    def _log_action(self, action_type: str, details: dict):
        """Log action"""
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.logs_path / f'{today}.json'

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action_type': action_type,
            **details
        }

        logs = []
        if log_file.exists():
            with open(log_file, 'r') as f:
                try:
                    logs = json.load(f)
                    if not isinstance(logs, list):
                        logs = []
                except json.JSONDecodeError:
                    logs = []

        logs.append(log_entry)

        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)

    def close(self):
        """Clean up"""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if hasattr(self, '_playwright') and self._playwright:
            self._playwright.stop()


def main():
    if len(sys.argv) < 2:
        print('''
Facebook Poster
===============

Usage:
    python facebook_poster.py "Post content"
    python facebook_poster.py --post-direct "Post without approval"
    python facebook_poster.py --approve

Examples:
    python facebook_poster.py "Check out our new product!"
    python facebook_poster.py --post-direct "Urgent announcement"
    python facebook_poster.py --approve
''')
        sys.exit(1)

    poster = FacebookPoster()
    command = sys.argv[1]

    if command == '--approve':
        results = poster.process_approved_posts()
        print(json.dumps(results, indent=2))

    elif command == '--post-direct':
        content = sys.argv[2]
        image = sys.argv[3] if len(sys.argv) > 3 else None
        result = poster.post(content, image, require_approval=False)
        print(json.dumps(result, indent=2))

    elif command == '--summary':
        summary = poster.generate_summary()
        print(json.dumps(summary, indent=2))

    else:
        # Default: create with approval
        content = command
        image = sys.argv[2] if len(sys.argv) > 2 else None
        result = poster.post(content, image)
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
