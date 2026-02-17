"""
LinkedIn Watcher - Monitors LinkedIn profile and manages posting
Silver Tier Requirement: Additional Watcher script
Uses LinkedIn Official API v2 (OAuth 2.0 access token)

Working features:
  - Read profile (userinfo endpoint)
  - Create posts (v2/ugcPosts endpoint)
  - HITL approval workflow for posts

Requires LINKEDIN_ACCESS_TOKEN in .env with w_member_social scope.
Reading messages/notifications requires r_member_social scope (not available
on most developer apps). If added later, extend _check_messages().
"""
import sys
import json
import os
from pathlib import Path
from datetime import datetime

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from base_watcher import BaseWatcher


class LinkedInWatcher(BaseWatcher):
    """
    Watches LinkedIn and manages posting via official API.

    Usage:
        python linkedin_watcher.py [vault_path]

    Requires LINKEDIN_ACCESS_TOKEN in .env file.
    """

    def __init__(self, vault_path: str):
        super().__init__(vault_path, check_interval=300)  # Check every 5 minutes

        self.important_keywords = [
            'job', 'opportunity', 'offer', 'interview',
            'project', 'collaboration', 'partnership',
            'urgent', 'asap', 'important'
        ]

        self.access_token = os.getenv('LINKEDIN_ACCESS_TOKEN')
        self.api_base_url = 'https://api.linkedin.com'
        self.profile = None
        self.person_urn = None
        self.processed_items = set()

        # Validate token and load profile
        if self.access_token:
            self.profile = self._get_profile()
            if self.profile:
                self.person_urn = f"urn:li:person:{self.profile.get('sub', '')}"
                self.logger.info(
                    f"LinkedIn authenticated as: {self.profile.get('name', 'Unknown')}"
                )
            else:
                self.logger.error("LinkedIn access token invalid or expired")
        else:
            self.logger.error("LINKEDIN_ACCESS_TOKEN not set in .env")

    def _get_headers(self):
        """Get API request headers"""
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        }

    def _get_profile(self) -> dict | None:
        """Get authenticated user's profile via userinfo endpoint"""
        try:
            r = requests.get(
                f'{self.api_base_url}/v2/userinfo',
                headers={'Authorization': f'Bearer {self.access_token}'},
                timeout=10
            )
            if r.status_code == 200:
                return r.json()
            else:
                self.logger.error(f"Profile fetch failed: {r.status_code} {r.text[:200]}")
                return None
        except Exception as e:
            self.logger.error(f"Profile fetch error: {e}")
            return None

    def check_for_updates(self) -> list:
        """Check LinkedIn for actionable items.

        Currently checks:
          - Approved posts waiting to be published
          - Profile status (token validity)

        When r_member_social scope is available, add:
          - Messages, notifications, feed items
        """
        updates = []

        if not self.access_token or not self.profile:
            self.logger.warning("No valid LinkedIn credentials - skipping check")
            return updates

        # Check for approved posts that need publishing
        approved_posts = self._check_approved_posts()
        updates.extend(approved_posts)

        return updates

    def _check_approved_posts(self) -> list:
        """Check /Approved folder for LinkedIn posts waiting to be published"""
        approved_dir = self.vault_path / 'Approved'
        if not approved_dir.exists():
            return []

        posts = []
        for f in approved_dir.glob('LINKEDIN_POST_*.md'):
            item_id = f.stem
            if item_id in self.processed_items:
                continue

            content = self._extract_post_content(f)
            if content:
                posts.append({
                    'type': 'linkedin_approved_post',
                    'content': content,
                    'file_path': str(f),
                    'timestamp': datetime.now().isoformat(),
                    'id': item_id
                })
                self.processed_items.add(item_id)

        if posts:
            self.logger.info(f"Found {len(posts)} approved LinkedIn posts to publish")
        return posts

    def _extract_post_content(self, file_path: Path) -> str:
        """Extract post content from an approval markdown file"""
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

    def post_to_linkedin(self, content: str) -> dict:
        """Post content to LinkedIn using official v2/ugcPosts API.

        Returns:
            dict with 'success' bool, 'post_id' or 'error'
        """
        if not self.person_urn:
            return {'success': False, 'error': 'Not authenticated'}

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
                self.logger.info(f"Posted to LinkedIn: {post_id}")
                return {'success': True, 'post_id': post_id}
            else:
                error = r.text[:300]
                self.logger.error(f"LinkedIn post failed ({r.status_code}): {error}")
                return {'success': False, 'error': f"{r.status_code}: {error}"}

        except Exception as e:
            self.logger.error(f"LinkedIn post error: {e}")
            return {'success': False, 'error': str(e)}

    def create_approval_request(self, content: str) -> Path:
        """Create HITL approval file for a LinkedIn post"""
        timestamp = datetime.now()
        filename = f"LINKEDIN_POST_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"
        pending_dir = self.vault_path / 'Pending_Approval'
        pending_dir.mkdir(exist_ok=True)

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

        approval_path = pending_dir / filename
        approval_path.write_text(approval_content)
        self.logger.info(f"Created LinkedIn post approval request: {filename}")
        return approval_path

    def determine_priority(self, item: dict) -> str:
        """Determine priority based on content"""
        content = item.get('content', '').lower()

        if any(kw in content for kw in ['urgent', 'asap', 'offer', 'interview']):
            return 'P1'
        elif any(kw in content for kw in ['opportunity', 'project', 'collaboration']):
            return 'P2'
        return 'P3'

    def create_action_file(self, item: dict) -> Path:
        """Process an approved post: publish it and move files"""
        if item['type'] == 'linkedin_approved_post':
            # Publish the approved post
            result = self.post_to_linkedin(item['content'])

            timestamp = datetime.now()
            priority = self.determine_priority(item)

            if result['success']:
                status_text = f"Published successfully: {result['post_id']}"
                status = 'completed'
            else:
                status_text = f"Failed to publish: {result['error']}"
                status = 'failed'

            content = f'''---
type: linkedin_post_result
source: linkedin_watcher
priority: {priority}
created: {timestamp.isoformat()}
status: {status}
post_id: {result.get('post_id', 'none')}
---

## LinkedIn Post Result

**Status:** {status_text}

**Content Posted:**
{item['content']}

## Result
{'Post was published to LinkedIn.' if result['success'] else f'Post failed: {result["error"]}'}
'''

            filename = f"LINKEDIN_post_{timestamp.strftime('%H%M%S')}.md"
            action_path = self.needs_action / filename
            action_path.write_text(content)

            # Move the approved file to Done if successful
            if result['success']:
                source = Path(item['file_path'])
                if source.exists():
                    done_dir = self.vault_path / 'Done'
                    done_dir.mkdir(exist_ok=True)
                    source.rename(done_dir / source.name)
                    self.logger.info(f"Moved {source.name} to Done")

            self.log_action('linkedin_post_processed', {
                'type': item['type'],
                'priority': priority,
                'success': result['success'],
                'action_file': filename
            })

            return action_path

        # Default action file for other types (future: messages, notifications)
        priority = self.determine_priority(item)
        timestamp = datetime.now()

        content = f'''---
type: {item['type']}
source: linkedin_watcher
priority: {priority}
created: {timestamp.isoformat()}
status: pending
---

## LinkedIn Update

{item.get('content', 'No content')}

## Suggested Actions
- [ ] Review on LinkedIn
- [ ] Take action if needed
'''

        filename = f"LINKEDIN_update_{timestamp.strftime('%H%M%S')}.md"
        action_path = self.needs_action / filename
        action_path.write_text(content)

        self.log_action('linkedin_processed', {
            'type': item['type'],
            'priority': priority,
            'action_file': filename
        })

        return action_path

    def run(self):
        """Run with status banner"""
        if self.profile:
            status = "ACTIVE"
            user = self.profile.get('name', 'Unknown')
        elif self.access_token:
            status = "TOKEN INVALID/EXPIRED"
            user = "N/A"
        else:
            status = "NO TOKEN"
            user = "N/A"

        print(f'''
╔══════════════════════════════════════════════════════════════╗
║             AI Employee - LinkedIn Watcher                   ║
║                     Silver Tier                              ║
╠══════════════════════════════════════════════════════════════╣
║  User:       {user:<46}║
║  Monitoring: Approved posts queue                            ║
║  Capabilities: Post (API) + Profile                          ║
║  Interval:   {self.check_interval} seconds                             ║
║  Status:     {status:<46}║
╚══════════════════════════════════════════════════════════════╝
''')

        if not self.profile:
            print("LinkedIn watcher cannot start without valid credentials.")
            if not self.access_token:
                print("Set LINKEDIN_ACCESS_TOKEN in .env with w_member_social scope.")
            else:
                print("Access token may be expired. Generate a new one from LinkedIn Developer Portal.")
            return

        super().run()


def main():
    """Main entry point"""
    default_vault = Path(__file__).parent.parent / 'AI_Employee_Vault'

    if default_vault.is_symlink():
        default_vault = default_vault.resolve()

    vault_path = sys.argv[1] if len(sys.argv) > 1 else str(default_vault)
    watcher = LinkedInWatcher(vault_path)

    # If called with --post, create an approval request
    if len(sys.argv) > 2 and sys.argv[1] == '--post':
        content = ' '.join(sys.argv[2:])
        approval = watcher.create_approval_request(content)
        print(f"Approval request created: {approval}")
        return

    # If called with --post-direct, post immediately (skip approval)
    if len(sys.argv) > 2 and sys.argv[1] == '--post-direct':
        content = ' '.join(sys.argv[2:])
        result = watcher.post_to_linkedin(content)
        print(f"Result: {result}")
        return

    watcher.run()


if __name__ == '__main__':
    main()
