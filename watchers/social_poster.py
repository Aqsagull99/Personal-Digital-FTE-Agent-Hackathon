"""
Social Media Poster - Posts to Facebook and Instagram
Gold Tier Requirement: Facebook/Instagram integration
Uses Playwright for browser automation with Human-in-the-Loop approval
"""
import sys
import json
from pathlib import Path
from datetime import datetime

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


class SocialMediaPoster:
    """
    Posts content to Facebook and Instagram with approval workflow.

    Usage:
        poster = SocialMediaPoster(vault_path)
        poster.post_facebook("Content here")
        poster.post_instagram("Content here")
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

        # Session paths
        self.fb_session = Path(__file__).parent.parent / '.facebook_session'
        self.ig_session = Path(__file__).parent.parent / '.instagram_session'

        self.browser = None
        self.context = None
        self.page = None

    def _init_browser(self, session_path: Path):
        """Initialize browser with session"""
        playwright = sync_playwright().start()
        self.browser = playwright.chromium.launch(headless=False)

        state_file = session_path / 'state.json'
        self.context = self.browser.new_context(
            storage_state=str(state_file) if state_file.exists() else None
        )
        self.page = self.context.new_page()

    def _save_session(self, session_path: Path):
        """Save session"""
        if self.context:
            session_path.mkdir(exist_ok=True)
            self.context.storage_state(path=str(session_path / 'state.json'))

    def create_approval_request(self, platform: str, content: str, image_path: str = None) -> Path:
        """Create approval request for social media post"""
        timestamp = datetime.now()
        filename = f"{platform.upper()}_POST_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"

        approval_content = f'''---
type: {platform}_post_approval
action: post_to_{platform}
created: {timestamp.isoformat()}
has_image: {bool(image_path)}
image_path: {image_path or 'None'}
status: pending
---

## {platform.title()} Post Request

### Content to Post:
{content}

'''
        if image_path:
            approval_content += f'''### Image:
{image_path}

'''

        approval_content += f'''### Post Details
- **Platform:** {platform.title()}
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

    def post_facebook(self, content: str, image_path: str = None, require_approval: bool = True) -> dict:
        """Post to Facebook"""
        if require_approval:
            approval_file = self.create_approval_request('facebook', content, image_path)
            return {
                'status': 'pending_approval',
                'message': 'Facebook post requires approval',
                'approval_file': str(approval_file)
            }

        try:
            self._init_browser(self.fb_session)
            self.page.goto('https://www.facebook.com/')
            self.page.wait_for_timeout(2000)

            # Check login
            if self.page.query_selector('input[name="email"]'):
                return {'status': 'error', 'message': 'Facebook login required. Run facebook_watcher.py first.'}

            # Click "What's on your mind?"
            post_box = self.page.query_selector('[aria-label*="on your mind"]')
            if not post_box:
                post_box = self.page.query_selector('[role="button"][tabindex="0"]')

            if post_box:
                post_box.click()
                self.page.wait_for_timeout(1000)

                # Type content
                editor = self.page.query_selector('[role="textbox"][contenteditable="true"]')
                if editor:
                    editor.fill(content)
                    self.page.wait_for_timeout(1000)

                    # Click Post button
                    post_btn = self.page.query_selector('[aria-label="Post"]')
                    if post_btn:
                        post_btn.click()
                        self.page.wait_for_timeout(3000)

                        self._log_action('facebook_post', {'status': 'success', 'content': content[:100]})
                        self._save_session(self.fb_session)

                        return {'status': 'success', 'message': 'Posted to Facebook'}

            return {'status': 'error', 'message': 'Could not find post elements'}

        except Exception as e:
            return {'status': 'error', 'message': str(e)}
        finally:
            self.close()

    def post_instagram(self, content: str, image_path: str = None, require_approval: bool = True) -> dict:
        """Post to Instagram (requires image for feed posts)"""
        if require_approval:
            approval_file = self.create_approval_request('instagram', content, image_path)
            return {
                'status': 'pending_approval',
                'message': 'Instagram post requires approval',
                'approval_file': str(approval_file)
            }

        if not image_path:
            return {'status': 'error', 'message': 'Instagram feed posts require an image'}

        try:
            self._init_browser(self.ig_session)
            self.page.goto('https://www.instagram.com/')
            self.page.wait_for_timeout(2000)

            # Check login
            if self.page.query_selector('input[name="username"]'):
                return {'status': 'error', 'message': 'Instagram login required. Run instagram_watcher.py first.'}

            # Click create button
            create_btn = self.page.query_selector('[aria-label="New post"]')
            if create_btn:
                create_btn.click()
                self.page.wait_for_timeout(1000)

                # Upload image
                file_input = self.page.query_selector('input[type="file"]')
                if file_input and Path(image_path).exists():
                    file_input.set_input_files(image_path)
                    self.page.wait_for_timeout(2000)

                    # Click Next
                    next_btn = self.page.query_selector('button:has-text("Next")')
                    if next_btn:
                        next_btn.click()
                        self.page.wait_for_timeout(1000)
                        next_btn.click()  # Click Next again
                        self.page.wait_for_timeout(1000)

                    # Add caption
                    caption_input = self.page.query_selector('textarea[aria-label*="caption"]')
                    if caption_input:
                        caption_input.fill(content)

                    # Share
                    share_btn = self.page.query_selector('button:has-text("Share")')
                    if share_btn:
                        share_btn.click()
                        self.page.wait_for_timeout(5000)

                        self._log_action('instagram_post', {'status': 'success', 'content': content[:100]})
                        self._save_session(self.ig_session)

                        return {'status': 'success', 'message': 'Posted to Instagram'}

            return {'status': 'error', 'message': 'Could not complete Instagram post'}

        except Exception as e:
            return {'status': 'error', 'message': str(e)}
        finally:
            self.close()

    def generate_summary(self, platform: str, days: int = 7) -> dict:
        """Generate summary of social media activity"""
        summary = {
            'platform': platform,
            'period_days': days,
            'posts_created': 0,
            'posts_pending': 0,
            'notifications_processed': 0
        }

        # Count from logs
        for log_file in self.logs_path.glob('*.json'):
            try:
                with open(log_file, 'r') as f:
                    logs = json.load(f)
                    for entry in logs:
                        if platform in entry.get('action_type', ''):
                            if 'post' in entry.get('action_type', ''):
                                summary['posts_created'] += 1
                            else:
                                summary['notifications_processed'] += 1
            except:
                pass

        # Count pending
        for f in self.pending_approval.glob(f'{platform.upper()}_POST_*.md'):
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
                logs = json.load(f)

        logs.append(log_entry)

        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)

    def close(self):
        """Clean up"""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()


def main():
    if len(sys.argv) < 3:
        print('''
Social Media Poster
===================

Usage:
    python social_poster.py facebook "Post content"
    python social_poster.py instagram "Caption" [image_path]
    python social_poster.py summary facebook
    python social_poster.py summary instagram

Examples:
    python social_poster.py facebook "Check out our new product!"
    python social_poster.py instagram "Beautiful day! #nature" /path/to/image.jpg
''')
        sys.exit(1)

    poster = SocialMediaPoster()
    command = sys.argv[1]

    if command == 'facebook':
        content = sys.argv[2]
        result = poster.post_facebook(content)
        print(json.dumps(result, indent=2))

    elif command == 'instagram':
        content = sys.argv[2]
        image = sys.argv[3] if len(sys.argv) > 3 else None
        result = poster.post_instagram(content, image)
        print(json.dumps(result, indent=2))

    elif command == 'summary':
        platform = sys.argv[2]
        summary = poster.generate_summary(platform)
        print(json.dumps(summary, indent=2))

    else:
        print(f"Unknown command: {command}")


if __name__ == '__main__':
    main()
