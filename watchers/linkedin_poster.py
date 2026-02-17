"""
LinkedIn Auto Poster - Posts content to LinkedIn via official API
Silver Tier Requirement: Automatically Post on LinkedIn about business
Uses LinkedIn v2/ugcPosts API (OAuth 2.0 access token)

Requires LINKEDIN_ACCESS_TOKEN in .env with w_member_social scope.
"""
import sys
import json
import os
from pathlib import Path
from datetime import datetime

import requests
from dotenv import load_dotenv


class LinkedInPoster:
    """
    Posts content to LinkedIn using official API with human-in-the-loop approval.

    Usage:
        poster = LinkedInPoster(vault_path)
        poster.post("Your post content here")

    Or from command line:
        python linkedin_poster.py "Your post content"
        python linkedin_poster.py --post-direct "Post without approval"
        python linkedin_poster.py --approve   # Publish approved posts
    """

    def __init__(self, vault_path: str = None):
        load_dotenv()

        if vault_path is None:
            vault_path = Path(__file__).parent.parent / 'AI_Employee_Vault'
        self.vault_path = Path(vault_path)

        if self.vault_path.is_symlink():
            self.vault_path = self.vault_path.resolve()

        self.logs_path = self.vault_path / 'Logs'
        self.pending_approval = self.vault_path / 'Pending_Approval'
        self.approved_path = self.vault_path / 'Approved'
        self.done_path = self.vault_path / 'Done'

        self.logs_path.mkdir(exist_ok=True)
        self.pending_approval.mkdir(exist_ok=True)
        self.approved_path.mkdir(exist_ok=True)
        self.done_path.mkdir(exist_ok=True)

        self.access_token = os.getenv('LINKEDIN_ACCESS_TOKEN')
        self.dry_run = os.getenv('DRY_RUN', 'false').lower() == 'true'
        self.api_base_url = 'https://api.linkedin.com'
        self.profile = None
        self.person_urn = None

        if self.access_token:
            self.profile = self._get_profile()
            if self.profile:
                self.person_urn = f"urn:li:person:{self.profile.get('sub', '')}"

    def _get_profile(self) -> dict | None:
        """Get authenticated user's profile"""
        try:
            r = requests.get(
                f'{self.api_base_url}/v2/userinfo',
                headers={'Authorization': f'Bearer {self.access_token}'},
                timeout=10
            )
            if r.status_code == 200:
                return r.json()
            return None
        except Exception:
            return None

    def _get_headers(self):
        """Get API request headers"""
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        }

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
            approval_file = self._create_approval_file(content)
            return {
                'status': 'pending_approval',
                'message': f'Approval required. Review: {approval_file.name}',
                'approval_file': str(approval_file)
            }

        if self.dry_run:
            fake_post_id = f"dryrun_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            self._log_post(content, 'dry_run_success', fake_post_id)
            return {
                'status': 'success',
                'message': f'DRY_RUN enabled: simulated LinkedIn post {fake_post_id}',
                'post_id': fake_post_id,
                'content': content[:100] + '...' if len(content) > 100 else content
            }

        if not self.person_urn:
            return {
                'status': 'error',
                'message': 'LinkedIn not authenticated. Check LINKEDIN_ACCESS_TOKEN in .env'
            }

        # Post directly via API
        post_data = {
            'author': self.person_urn,
            'lifecycleState': 'PUBLISHED',
            'specificContent': {
                'com.linkedin.ugc.ShareContent': {
                    'shareCommentary': {
                        'text': content
                    },
                    'shareMediaCategory': 'NONE'
                }
            },
            'visibility': {
                'com.linkedin.ugc.MemberNetworkVisibility': 'PUBLIC'
            }
        }

        try:
            r = requests.post(
                f'{self.api_base_url}/v2/ugcPosts',
                headers=self._get_headers(),
                json=post_data,
                timeout=15
            )

            if r.status_code == 201:
                post_id = r.json().get('id', 'unknown')
                print(f"Posted to LinkedIn: {post_id}")
                self._log_post(content, 'success', post_id)
                return {
                    'status': 'success',
                    'message': f'Posted to LinkedIn: {post_id}',
                    'post_id': post_id,
                    'content': content[:100] + '...' if len(content) > 100 else content
                }
            else:
                error = r.text[:300]
                print(f"LinkedIn post failed ({r.status_code}): {error}")
                self._log_post(content, 'failed')
                return {
                    'status': 'error',
                    'message': f'API error {r.status_code}: {error}'
                }

        except Exception as e:
            print(f"Error posting: {e}")
            self._log_post(content, 'error')
            return {
                'status': 'error',
                'message': str(e)
            }

    def _create_approval_file(self, content: str) -> Path:
        """Create approval file for human-in-the-loop workflow"""
        timestamp = datetime.now()
        filename = f"LINKEDIN_POST_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"
        author_name = self.profile.get('name', 'Unknown') if self.profile else 'Unknown'

        approval_content = f'''---
type: linkedin_post_approval
action: post_to_linkedin
created: {timestamp.isoformat()}
author: {author_name}
status: pending
---

## LinkedIn Post Request

### Content to Post:
{content}

### Post Details
- **Author:** {author_name}
- **Visibility:** Public
- **Created:** {timestamp.strftime('%Y-%m-%d %H:%M')}

### To Approve
Move this file to /Approved folder.

### To Reject
Move this file to /Rejected folder.

---
*This post requires human approval before publishing.*
'''

        approval_path = self.pending_approval / filename
        approval_path.write_text(approval_content)
        return approval_path

    def _log_post(self, content: str, status: str, post_id: str = None):
        """Log the post action"""
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.logs_path / f'{today}.json'

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action_type': 'linkedin_post',
            'status': status,
            'content_preview': content[:100],
            'post_id': post_id
        }

        if log_file.exists():
            with open(log_file, 'r') as f:
                logs = json.load(f)
        else:
            logs = []

        logs.append(log_entry)

        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)

    def process_approved_posts(self):
        """Process approved LinkedIn posts from /Approved folder"""
        approved_files = list(self.approved_path.glob('LINKEDIN_POST_*.md'))

        if not approved_files:
            print('No approved LinkedIn posts found.')
            return

        for file_path in approved_files:
            content = self._extract_post_content(file_path)

            if content:
                print(f'Publishing: {content[:60]}...')
                result = self.post(content, require_approval=False)
                print(f'Result: {result["status"]} - {result["message"]}')

                if result['status'] == 'success':
                    # Move to Done
                    file_path.rename(self.done_path / file_path.name)
                    print(f'Moved {file_path.name} to Done')
            else:
                print(f'Could not extract content from {file_path.name}')

    def _extract_post_content(self, file_path: Path) -> str:
        """Extract post content from approval markdown file"""
        text = file_path.read_text()
        lines = text.split('\n')
        capturing = False
        content_lines = []

        for line in lines:
            if '### Content to Post:' in line or '**Content to post:**' in line:
                capturing = True
                continue
            if capturing and (line.startswith('###') or line.startswith('## ')):
                break
            if capturing:
                content_lines.append(line)

        return '\n'.join(content_lines).strip()


def main():
    """Command line interface"""
    if len(sys.argv) < 2:
        print('''
LinkedIn Auto Poster (API)
==========================

Usage:
    python linkedin_poster.py "Your post content"
    python linkedin_poster.py --post-direct "Post without approval"
    python linkedin_poster.py --approve    # Publish approved posts
    python linkedin_poster.py --status     # Check connection status
    DRY_RUN=true python linkedin_poster.py --approve  # Simulate publish
''')
        sys.exit(1)

    poster = LinkedInPoster()

    if sys.argv[1] == '--status':
        if poster.profile:
            print(f"Connected as: {poster.profile.get('name', 'Unknown')}")
            print(f"Email: {poster.profile.get('email', 'Unknown')}")
            print(f"Person URN: {poster.person_urn}")
        else:
            print("Not connected. Check LINKEDIN_ACCESS_TOKEN in .env")
        print(f"Dry Run: {poster.dry_run}")
        return

    if sys.argv[1] == '--approve':
        poster.process_approved_posts()
        return

    if sys.argv[1] == '--post-direct':
        content = ' '.join(sys.argv[2:])
        result = poster.post(content, require_approval=False)
        print(f'Status: {result["status"]}')
        print(f'Message: {result["message"]}')
        return

    # Default: post with approval
    content = ' '.join(sys.argv[1:])
    result = poster.post(content, require_approval=True)
    print(f'Status: {result["status"]}')
    print(f'Message: {result["message"]}')


if __name__ == '__main__':
    main()
