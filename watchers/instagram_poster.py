"""
Instagram Poster - Posts content to Instagram
Gold Tier Requirement: Instagram integration
Uses Playwright for browser automation with Human-in-the-Loop approval
"""
import sys
import json
import os
from pathlib import Path
from datetime import datetime

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


class InstagramPoster:
    """
    Posts content to Instagram with approval workflow.

    Usage:
        poster = InstagramPoster(vault_path)
        poster.post("Caption here", "/path/to/image.jpg")

    Or from command line:
        python instagram_poster.py "Caption" /path/to/image.jpg
        python instagram_poster.py --post-direct "Caption" /path/to/image.jpg
        python instagram_poster.py --approve
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
        self.ig_session = Path(__file__).parent.parent / '.instagram_session'

        self.browser = None
        self.context = None
        self.page = None

    def _init_browser(self):
        """Initialize browser with persistent session using user data dir"""
        self._playwright = sync_playwright().start()
        self.ig_session.mkdir(exist_ok=True)

        user_data_dir = str(self.ig_session / 'browser_profile')
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
                self.ig_session.mkdir(exist_ok=True)
                self.context.storage_state(path=str(self.ig_session / 'state.json'))
            except Exception:
                pass  # Non-fatal: persistent context already saved to disk

    def create_approval_request(self, content: str, image_path: str = None) -> Path:
        """Create approval request for Instagram post"""
        timestamp = datetime.now()
        filename = f"INSTAGRAM_POST_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"

        approval_content = f'''---
type: instagram_post_approval
action: post_to_instagram
created: {timestamp.isoformat()}
has_image: {bool(image_path)}
image_path: {image_path or 'None'}
status: pending
---

## Instagram Post Request

### Content to Post:
{content}

'''
        if image_path:
            approval_content += f'''### Image:
{image_path}

'''

        approval_content += f'''### Post Details
- **Platform:** Instagram
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
        """Post to Instagram (requires image for feed posts)

        Uses pushState + popstate to trigger Instagram's React router
        to render the create dialog, bypassing persistent overlay issues.
        """
        if require_approval:
            approval_file = self.create_approval_request(content, image_path)
            return {
                'status': 'pending_approval',
                'message': 'Instagram post requires approval',
                'approval_file': str(approval_file)
            }

        if self.dry_run:
            fake_post_id = f"dryrun_ig_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            self._log_action('instagram_post', {
                'status': 'dry_run_success',
                'post_id': fake_post_id,
                'content': content[:100],
                'image_path': image_path
            })
            return {
                'status': 'success',
                'message': f'DRY_RUN enabled: simulated Instagram post {fake_post_id}',
                'post_id': fake_post_id
            }

        if not image_path:
            return {'status': 'error', 'message': 'Instagram feed posts require an image'}

        if not Path(image_path).exists():
            return {'status': 'error', 'message': f'Image not found: {image_path}'}

        try:
            self._init_browser()
            self.page.goto('https://www.instagram.com/')
            self.page.wait_for_timeout(5000)

            # Check login
            if self.page.query_selector('input[name="username"]'):
                return {'status': 'error', 'message': 'Instagram login required. Run instagram_watcher.py first.'}

            # Trigger Create dialog via pushState + popstate
            # This bypasses persistent overlay issues with the sidebar Create button
            nav_result = self.page.evaluate('''() => {
                try {
                    window.history.pushState({}, '', '/create/select/');
                    window.dispatchEvent(new PopStateEvent('popstate'));
                    return 'success';
                } catch(e) {
                    return 'error: ' + e.message;
                }
            }''')
            self.page.wait_for_timeout(5000)

            if nav_result != 'success':
                return {'status': 'error', 'message': f'Failed to open create dialog: {nav_result}'}

            # Upload image via file input
            file_input = self.page.query_selector('input[type="file"]')
            if not file_input:
                return {'status': 'error', 'message': 'Create dialog opened but no file input found'}

            file_input.set_input_files(image_path)
            self.page.wait_for_timeout(5000)

            # Click Next (crop step)
            try:
                next_btn = self.page.get_by_role("button", name="Next")
                if next_btn.count() > 0:
                    next_btn.first.click()
                else:
                    self.page.evaluate('''() => {
                        var btns = document.querySelectorAll('button, [role="button"]');
                        for (var i = 0; i < btns.length; i++) {
                            if ((btns[i].innerText||'').trim() === 'Next') { btns[i].click(); return; }
                        }
                    }''')
            except Exception:
                return {'status': 'error', 'message': 'Could not click Next after crop'}
            self.page.wait_for_timeout(3000)

            # Click Next (filter step)
            try:
                next_btn2 = self.page.get_by_role("button", name="Next")
                if next_btn2.count() > 0:
                    next_btn2.first.click()
                else:
                    self.page.evaluate('''() => {
                        var btns = document.querySelectorAll('button, [role="button"]');
                        for (var i = 0; i < btns.length; i++) {
                            if ((btns[i].innerText||'').trim() === 'Next') { btns[i].click(); return; }
                        }
                    }''')
            except Exception:
                return {'status': 'error', 'message': 'Could not click Next after filter'}
            self.page.wait_for_timeout(3000)

            # Enter caption using role-based textbox locator
            caption_entered = False
            try:
                tb = self.page.get_by_role("textbox")
                if tb.count() > 0:
                    tb.first.click()
                    self.page.wait_for_timeout(300)
                    self.page.keyboard.type(content, delay=30)
                    caption_entered = True
            except Exception:
                pass

            if not caption_entered:
                # Fallback: try contenteditable div or textarea
                for sel in ['div[aria-label="Write a caption..."]', 'div[contenteditable="true"]', 'textarea']:
                    try:
                        el = self.page.query_selector(sel)
                        if el:
                            el.click()
                            self.page.wait_for_timeout(300)
                            self.page.keyboard.type(content, delay=30)
                            caption_entered = True
                            break
                    except Exception:
                        pass

            self.page.wait_for_timeout(1000)

            # Click Share
            try:
                share_btn = self.page.get_by_role("button", name="Share")
                if share_btn.count() > 0:
                    share_btn.first.click()
                else:
                    self.page.evaluate('''() => {
                        var btns = document.querySelectorAll('button, [role="button"]');
                        for (var i = 0; i < btns.length; i++) {
                            if ((btns[i].innerText||'').trim() === 'Share') { btns[i].click(); return; }
                        }
                    }''')
            except Exception:
                return {'status': 'error', 'message': 'Could not click Share button'}

            # Wait for post to process
            self.page.wait_for_timeout(15000)

            self._log_action('instagram_post', {'status': 'success', 'content': content[:100]})
            self._save_session()

            return {'status': 'success', 'message': 'Posted to Instagram'}

        except Exception as e:
            return {'status': 'error', 'message': str(e)}
        finally:
            self.close()

    def process_approved_posts(self):
        """Process approved Instagram posts from /Approved folder"""
        approved_files = list(self.approved_path.glob('INSTAGRAM_POST_*.md')) + \
                         list(self.approved_path.glob('*INSTAGRAM_POST_APPROVAL_*.md'))

        if not approved_files:
            print('No approved Instagram posts found.')
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
                'platform': 'instagram',
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
        """Generate summary of Instagram posting activity"""
        summary = {
            'platform': 'instagram',
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
                        if 'instagram' in entry.get('action_type', ''):
                            if 'post' in entry.get('action_type', ''):
                                summary['posts_created'] += 1
                            else:
                                summary['notifications_processed'] += 1
            except:
                pass

        for f in self.pending_approval.glob('INSTAGRAM_POST_*.md'):
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
Instagram Poster
================

Usage:
    python instagram_poster.py "Caption" /path/to/image.jpg
    python instagram_poster.py --post-direct "Caption" /path/to/image.jpg
    python instagram_poster.py --approve

Examples:
    python instagram_poster.py "Beautiful day! #nature" /path/to/image.jpg
    python instagram_poster.py --post-direct "Check this out!" /path/to/photo.png
    python instagram_poster.py --approve
''')
        sys.exit(1)

    poster = InstagramPoster()
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
