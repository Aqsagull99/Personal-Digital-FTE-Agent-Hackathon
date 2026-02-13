"""
LinkedIn Auto Poster - Posts content to LinkedIn
Silver Tier Requirement: Automatically Post on LinkedIn about business
Uses Playwright for browser automation
"""
import sys
import json
from pathlib import Path
from datetime import datetime

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


class LinkedInPoster:
    """
    Posts content to LinkedIn automatically.

    Usage:
        from linkedin_poster import LinkedInPoster
        poster = LinkedInPoster(vault_path)
        poster.post("Your post content here")

    Or from command line:
        python linkedin_poster.py "Your post content"
    """

    def __init__(self, vault_path: str = None, session_path: str = None):
        if vault_path is None:
            vault_path = Path(__file__).parent.parent / 'AI_Employee_Vault'
        self.vault_path = Path(vault_path)

        if self.vault_path.is_symlink():
            self.vault_path = self.vault_path.resolve()

        # Session storage
        if session_path is None:
            session_path = Path(__file__).parent.parent / '.linkedin_session'
        self.session_path = Path(session_path)
        self.session_path.mkdir(exist_ok=True)

        # Logs and approval
        self.logs_path = self.vault_path / 'Logs'
        self.pending_approval = self.vault_path / 'Pending_Approval'
        self.logs_path.mkdir(exist_ok=True)
        self.pending_approval.mkdir(exist_ok=True)

        self.browser = None
        self.context = None
        self.page = None

    def _init_browser(self, headless: bool = False):
        """Initialize browser with persistent session"""
        playwright = sync_playwright().start()
        self.browser = playwright.chromium.launch(headless=headless)

        state_file = self.session_path / 'state.json'
        self.context = self.browser.new_context(
            storage_state=str(state_file) if state_file.exists() else None
        )
        self.page = self.context.new_page()

    def _save_session(self):
        """Save browser session"""
        if self.context:
            self.context.storage_state(path=str(self.session_path / 'state.json'))

    def _login_if_needed(self):
        """Check if login is required"""
        self.page.goto('https://www.linkedin.com/feed/')

        if 'login' in self.page.url or 'checkpoint' in self.page.url:
            print('\n' + '='*60)
            print('LinkedIn Login Required!')
            print('Please login in the browser window.')
            print('After login, press Enter here to continue...')
            print('='*60 + '\n')
            input()
            self._save_session()

    def create_approval_request(self, content: str, post_type: str = 'text') -> Path:
        """Create approval request file for human review"""
        timestamp = datetime.now()
        filename = f"LINKEDIN_POST_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"

        approval_content = f'''---
type: linkedin_post_approval
action: post_to_linkedin
post_type: {post_type}
created: {timestamp.isoformat()}
expires: {timestamp.strftime('%Y-%m-%d')}T23:59:59
status: pending
---

## LinkedIn Post Request

### Content to Post:
{content}

### Post Details
- **Type:** {post_type}
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

    def post(self, content: str, require_approval: bool = True) -> dict:
        """
        Post content to LinkedIn.

        Args:
            content: The text to post
            require_approval: If True, creates approval file first

        Returns:
            dict with status and details
        """
        if require_approval:
            approval_file = self.create_approval_request(content)
            return {
                'status': 'pending_approval',
                'message': f'Approval required. Review: {approval_file.name}',
                'approval_file': str(approval_file)
            }

        try:
            self._init_browser(headless=False)
            self._login_if_needed()

            # Navigate to feed
            self.page.goto('https://www.linkedin.com/feed/')
            self.page.wait_for_load_state('networkidle')

            # Click "Start a post" button
            start_post_btn = self.page.wait_for_selector(
                'button.share-box-feed-entry__trigger',
                timeout=10000
            )
            start_post_btn.click()

            # Wait for post modal
            self.page.wait_for_selector('.share-creation-state__text-editor', timeout=5000)

            # Type content
            editor = self.page.query_selector('.ql-editor[data-placeholder="What do you want to talk about?"]')
            if editor:
                editor.fill(content)
            else:
                # Fallback: try different selector
                self.page.keyboard.type(content)

            # Small delay for content to register
            self.page.wait_for_timeout(1000)

            # Click Post button
            post_btn = self.page.query_selector('button.share-actions__primary-action')
            if post_btn:
                post_btn.click()
                self.page.wait_for_timeout(3000)

                self._log_post(content, 'success')
                self._save_session()

                return {
                    'status': 'success',
                    'message': 'Posted to LinkedIn successfully',
                    'content': content[:100] + '...' if len(content) > 100 else content
                }
            else:
                return {
                    'status': 'error',
                    'message': 'Could not find Post button'
                }

        except PlaywrightTimeout as e:
            return {
                'status': 'error',
                'message': f'Timeout error: {str(e)}'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error: {str(e)}'
            }
        finally:
            self.close()

    def _log_post(self, content: str, status: str):
        """Log the post action"""
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.logs_path / f'{today}.json'

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action_type': 'linkedin_post',
            'status': status,
            'content_preview': content[:100]
        }

        if log_file.exists():
            with open(log_file, 'r') as f:
                logs = json.load(f)
        else:
            logs = []

        logs.append(log_entry)

        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)

    def close(self):
        """Clean up browser resources"""
        if self.context:
            self._save_session()
            self.context.close()
        if self.browser:
            self.browser.close()


def main():
    """Command line interface"""
    if len(sys.argv) < 2:
        print('''
LinkedIn Auto Poster
====================

Usage:
    python linkedin_poster.py "Your post content"
    python linkedin_poster.py --approve  # Post approved content

Options:
    --approve    Post content from /Approved folder
    --no-approval    Post directly without approval (use carefully!)
''')
        sys.exit(1)

    poster = LinkedInPoster()

    if sys.argv[1] == '--approve':
        # Check approved folder for posts
        approved = poster.vault_path / 'Approved'
        posts = list(approved.glob('LINKEDIN_POST_*.md'))

        if not posts:
            print('No approved LinkedIn posts found.')
            sys.exit(0)

        for post_file in posts:
            content = post_file.read_text()
            # Extract actual content from markdown
            lines = content.split('\n')
            in_content = False
            post_content = []

            for line in lines:
                if '### Content to Post:' in line:
                    in_content = True
                    continue
                if in_content and line.startswith('###'):
                    break
                if in_content:
                    post_content.append(line)

            actual_content = '\n'.join(post_content).strip()

            if actual_content:
                print(f'Posting: {actual_content[:50]}...')
                result = poster.post(actual_content, require_approval=False)
                print(f'Result: {result["status"]}')

                # Move to Done
                done_path = poster.vault_path / 'Done' / post_file.name
                post_file.rename(done_path)

    else:
        content = sys.argv[1]
        no_approval = '--no-approval' in sys.argv

        result = poster.post(content, require_approval=not no_approval)
        print(f'Status: {result["status"]}')
        print(f'Message: {result["message"]}')


if __name__ == '__main__':
    main()
