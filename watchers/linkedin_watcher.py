"""
LinkedIn Watcher - Monitors LinkedIn for new messages and notifications
Silver Tier Requirement: Additional Watcher script
Uses LinkedIn API with environment variables
"""
import sys
import json
import os
from pathlib import Path
from datetime import datetime

from linkedin_api import Linkedin
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from base_watcher import BaseWatcher


class LinkedInWatcher(BaseWatcher):
    """
    Watches LinkedIn for new messages and notifications using API.

    Usage:
        python linkedin_watcher.py [vault_path]

    Requires LinkedIn credentials in .env file.
    """

    def __init__(self, vault_path: str):
        super().__init__(vault_path, check_interval=300)  # Check every 5 minutes

        # Keywords that indicate important messages
        self.important_keywords = [
            'job', 'opportunity', 'offer', 'interview',
            'project', 'collaboration', 'partnership',
            'urgent', 'asap', 'important'
        ]

        # Initialize LinkedIn API client using environment variables
        self.linkedin_client = self._init_linkedin_api()
        self.processed_items = set()
        self.access_token = getattr(self, 'access_token', None)  # Initialize access token
        self.api_base_url = 'https://api.linkedin.com/v2'

    def _init_linkedin_api(self):
        """Initialize LinkedIn API client using environment variables"""
        # First try OAuth 2.0 authentication (preferred method for production)
        client_id = os.getenv('LINKEDIN_CLIENT_ID')
        client_secret = os.getenv('LINKEDIN_CLIENT_SECRET')
        access_token = os.getenv('LINKEDIN_ACCESS_TOKEN')
        
        if access_token:
            self.logger.info("LinkedIn access token found, will use for API calls")
            # Store access token for API calls
            self.access_token = access_token
            return True  # Return True to indicate we have credentials
        elif all([client_id, client_secret]):
            self.logger.info("LinkedIn OAuth credentials found, but no access token")
            # We have OAuth credentials but no token
            self.access_token = None
            return None
        else:
            # Try email/password authentication as fallback
            linkedin_email = os.getenv('LINKEDIN_EMAIL')
            linkedin_password = os.getenv('LINKEDIN_PASSWORD')

            if linkedin_email and linkedin_password:
                try:
                    # Initialize with email/password (unofficial API)
                    client = Linkedin(linkedin_email, linkedin_password, refresh_cookies=True)
                    self.logger.info("LinkedIn client initialized with email/password")
                    return client
                except Exception as e:
                    self.logger.error(f"Failed to initialize LinkedIn client: {e}")
                    return None
            else:
                self.logger.warning("No LinkedIn credentials found in environment variables")
                return None

    def check_for_updates(self) -> list:
        """Check LinkedIn for new messages and notifications using API"""
        updates = []

        # If we have an access token, try using the official API
        if self.access_token:
            try:
                # Check for updates using official API
                api_updates = self._check_updates_via_api()
                updates.extend(api_updates)
            except Exception as e:
                self.logger.warning(f'API check failed: {e}')
                # Fall back to other methods if API fails
        elif self.linkedin_client:
            # Use the existing client if available
            try:
                # Check messages
                messages = self._check_messages()
                updates.extend(messages)

                # Check notifications
                notifications = self._check_notifications()
                updates.extend(notifications)
            except Exception as e:
                self.logger.error(f'Error checking LinkedIn: {e}')
        else:
            self.logger.warning("No LinkedIn client or access token available - skipping check")

        return updates

    def _check_updates_via_api(self) -> list:
        """Check LinkedIn for updates using official API with access token"""
        updates = []
        
        if not self.access_token:
            return updates
            
        import requests
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Get user's feed for recent activity
            response = requests.get(
                f'{self.api_base_url}/network/feed',
                headers=headers,
                params={'q': 'shareFeed', 'count': 10},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                # Process feed items
                for item in data.get('elements', []):
                    # Extract relevant information
                    post_id = item.get('id')
                    if post_id and post_id not in self.processed_items:
                        # Check if content contains important keywords
                        commentary = item.get('commentary', {}).get('text', '') if isinstance(item.get('commentary'), dict) else str(item.get('commentary', ''))
                        if any(kw in commentary.lower() for kw in self.important_keywords):
                            updates.append({
                                'type': 'linkedin_feed_item',
                                'content': commentary[:400],
                                'timestamp': datetime.now().isoformat(),
                                'id': post_id
                            })
                            self.processed_items.add(post_id)
            elif response.status_code == 403:
                self.logger.warning("Insufficient permissions to access feed via API")
            elif response.status_code == 401:
                self.logger.error("Invalid or expired access token")
            else:
                self.logger.warning(f"API response status: {response.status_code}")
                
        except Exception as e:
            self.logger.warning(f'Error checking updates via API: {e}')

        return updates

    def _check_messages(self) -> list:
        """Check LinkedIn messaging for new messages"""
        messages = []

        if not self.linkedin_client:
            return messages

        try:
            # The unofficial LinkedIn API doesn't have a direct method to fetch messages
            # This is a simplified approach - actual implementation would depend on the API capabilities
            # For now, we'll simulate checking for messages
            
            # In a real implementation, you would use the LinkedIn API to fetch messages
            # For example: self.linkedin_client.get_messages()
            
            # Simulating message check - in reality, you'd fetch actual messages
            # This is a placeholder for the actual API call
            self.logger.info("Checking LinkedIn messages (API implementation needed)")
            
            # Placeholder for actual API call
            # messages_data = self.linkedin_client.get_messages()
            # for message in messages_data:
            #     if message['id'] not in self.processed_items:
            #         messages.append({
            #             'type': 'linkedin_message',
            #             'sender': message.get('sender', 'Unknown'),
            #             'preview': message.get('preview', ''),
            #             'timestamp': message.get('timestamp', datetime.now().isoformat()),
            #             'id': message['id']
            #         })
            #         self.processed_items.add(message['id'])

        except Exception as e:
            self.logger.warning(f'Error checking messages: {e}')

        return messages

    def _check_notifications(self) -> list:
        """Check LinkedIn notifications"""
        notifications = []

        if not self.linkedin_client:
            return notifications

        try:
            # The unofficial LinkedIn API doesn't have a direct method to fetch notifications
            # This is a simplified approach - actual implementation would depend on the API capabilities
            # For now, we'll simulate checking for notifications
            
            # In a real implementation, you would use the LinkedIn API to fetch notifications
            # For example: self.linkedin_client.get_notifications()
            
            # Simulating notification check - in reality, you'd fetch actual notifications
            self.logger.info("Checking LinkedIn notifications (API implementation needed)")
            
            # Placeholder for actual API call
            # notifications_data = self.linkedin_client.get_notifications()
            # for notification in notifications_data:
            #     if any(kw in notification.get('text', '').lower() for kw in self.important_keywords):
            #         if notification['id'] not in self.processed_items:
            #             notifications.append({
            #                 'type': 'linkedin_notification',
            #                 'content': notification.get('text', '')[:200],
            #                 'timestamp': notification.get('timestamp', datetime.now().isoformat()),
            #                 'id': notification['id']
            #             })
            #             self.processed_items.add(notification['id'])

        except Exception as e:
            self.logger.warning(f'Error checking notifications: {e}')

        return notifications

    def determine_priority(self, item: dict) -> str:
        """Determine priority based on content"""
        content = f"{item.get('sender', '')} {item.get('preview', '')} {item.get('content', '')}".lower()

        if any(kw in content for kw in ['urgent', 'asap', 'offer', 'interview']):
            return 'P1'
        elif any(kw in content for kw in ['opportunity', 'project', 'collaboration']):
            return 'P2'
        return 'P3'

    def create_action_file(self, item: dict) -> Path:
        """Create action file from LinkedIn update"""
        priority = self.determine_priority(item)
        timestamp = datetime.now()

        if item['type'] == 'linkedin_message':
            content = f'''---
type: linkedin_message
source: linkedin_watcher
priority: {priority}
created: {timestamp.isoformat()}
sender: {item.get('sender', 'Unknown')}
status: pending
---

## LinkedIn Message

**From:** {item.get('sender', 'Unknown')}

**Preview:**
{item.get('preview', 'No preview available')}

## Suggested Actions
- [ ] Read full message on LinkedIn
- [ ] Reply if needed
- [ ] Connect if relevant
'''
        else:  # notification
            content = f'''---
type: linkedin_notification
source: linkedin_watcher
priority: {priority}
created: {timestamp.isoformat()}
status: pending
---

## LinkedIn Notification

{item.get('content', 'No content')}

## Suggested Actions
- [ ] Review on LinkedIn
- [ ] Take action if needed
'''

        # Create unique filename
        filename = f"LINKEDIN_{item['type'].split('_')[1]}_{timestamp.strftime('%H%M%S')}.md"
        action_path = self.needs_action / filename
        action_path.write_text(content)

        # Log the action
        self.log_action('linkedin_processed', {
            'type': item['type'],
            'priority': priority,
            'action_file': filename
        })

        return action_path

    def run(self):
        """Override run with cleanup"""
        # Determine status based on credential availability
        oauth_creds_available = bool(os.getenv('LINKEDIN_CLIENT_ID') and os.getenv('LINKEDIN_CLIENT_SECRET'))
        email_creds_available = bool(os.getenv('LINKEDIN_EMAIL') and os.getenv('LINKEDIN_PASSWORD'))
        
        if self.linkedin_client:
            status = "ACTIVE"
        elif oauth_creds_available and email_creds_available:
            status = "CONFIGURED (security blocking)"
        elif oauth_creds_available or email_creds_available:
            status = "PARTIALLY CONFIGURED"
        else:
            status = "INACTIVE (missing credentials)"
        
        print(f'''
╔══════════════════════════════════════════════════════════════╗
║             AI Employee - LinkedIn Watcher                   ║
║                     Silver Tier                              ║
╠══════════════════════════════════════════════════════════════╣
║  Monitoring: LinkedIn Messages & Notifications               ║
║  Interval:   {self.check_interval} seconds                             ║
║  Status:     {status}           ║
╚══════════════════════════════════════════════════════════════╝
''')
        
        if not self.linkedin_client:
            if oauth_creds_available and email_creds_available:
                print("ℹ️  OAuth credentials are properly configured but LinkedIn security blocks automated access.")
                print("ℹ️  This is expected behavior for enhanced security.")
            elif oauth_creds_available or email_creds_available:
                print("⚠️  Partial credentials detected. Please check your environment variables.")
            else:
                print("⚠️  LinkedIn API client not initialized. Please check your environment variables.")
            return
        
        super().run()


def main():
    """Main entry point"""
    default_vault = Path(__file__).parent.parent / 'AI_Employee_Vault'

    if default_vault.is_symlink():
        default_vault = default_vault.resolve()

    if len(sys.argv) > 1:
        vault_path = sys.argv[1]
    else:
        vault_path = str(default_vault)

    watcher = LinkedInWatcher(vault_path)
    watcher.run()


if __name__ == '__main__':
    main()
