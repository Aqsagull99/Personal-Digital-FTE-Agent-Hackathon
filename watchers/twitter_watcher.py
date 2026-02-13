"""
Twitter (X) Watcher - Monitors Twitter for notifications and DMs
Gold Tier Requirement: Twitter (X) integration
Uses Twitter API v2 for better reliability
"""
import sys
import json
import os
from pathlib import Path
from datetime import datetime

import tweepy
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))
from base_watcher import BaseWatcher


class TwitterWatcher(BaseWatcher):
    """
    Watches Twitter (X) for new notifications and direct messages using API.

    Usage:
        python twitter_watcher.py [vault_path]

    Requires Twitter API credentials in .env file.
    """

    def __init__(self, vault_path: str):
        super().__init__(vault_path, check_interval=300)  # Every 5 minutes

        self.important_keywords = [
            'mention', 'reply', 'dm', 'message', 'quote',
            'business', 'collab', 'partnership', 'opportunity',
            'urgent', 'help', 'inquiry'
        ]

        # Initialize Twitter API client using environment variables
        self.twitter_client = self._init_twitter_api()
        self.processed_items = set()

    def _init_twitter_api(self):
        """Initialize Twitter API v2 client using environment variables"""
        consumer_key = os.getenv('TWITTER_CONSUMER_KEY')
        consumer_secret = os.getenv('TWITTER_CONSUMER_SECRET')
        access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        bearer_token = os.getenv('TWITTER_BEARER_TOKEN')  # Optional for certain endpoints

        if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
            missing_vars = []
            for var_name, var_value in [
                ('TWITTER_CONSUMER_KEY', consumer_key),
                ('TWITTER_CONSUMER_SECRET', consumer_secret),
                ('TWITTER_ACCESS_TOKEN', access_token),
                ('TWITTER_ACCESS_TOKEN_SECRET', access_token_secret)
            ]:
                if not var_value:
                    missing_vars.append(var_name)
            
            self.logger.error(f"Missing required Twitter environment variables: {', '.join(missing_vars)}")
            return None

        try:
            # Initialize Tweepy client with API v2 using OAuth 1.0a User Context
            client = tweepy.Client(
                consumer_key=consumer_key,
                consumer_secret=consumer_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
                bearer_token=bearer_token,  # Use if available
                wait_on_rate_limit=True
            )
            self.logger.info("Twitter API client initialized successfully with OAuth 1.0a")
            return client
        except Exception as e:
            self.logger.error(f"Failed to initialize Twitter API client: {e}")
            return None

    def check_for_updates(self) -> list:
        """Check Twitter for new notifications and DMs using API"""
        updates = []

        if not self.twitter_client:
            self.logger.error("Twitter client not initialized - skipping check")
            return updates

        try:
            # Check mentions
            mentions = self._check_mentions()
            updates.extend(mentions)

            # Check home timeline for relevant content
            timeline_posts = self._check_home_timeline()
            updates.extend(timeline_posts)

        except Exception as e:
            self.logger.error(f'Error checking Twitter: {e}')

        return updates

    def _check_mentions(self) -> list:
        """Check Twitter mentions using API"""
        mentions = []

        if not self.twitter_client:
            return mentions

        try:
            # Get recent mentions
            # Note: The free Twitter API tier has limited access to mentions
            # For full access, you may need to upgrade to a paid tier
            mentions_response = self.twitter_client.get_users_mentions(
                id=self.twitter_client.get_me().data.id,
                max_results=10,
                tweet_fields=['created_at', 'author_id', 'public_metrics', 'context_annotations', 'entities']
            )

            if mentions_response.data:
                for tweet in mentions_response.data:
                    # Extract hashtags and mentions from entities
                    hashtags = []
                    mentioned_users = []
                    
                    if hasattr(tweet, 'entities') and tweet.entities:
                        if 'hashtags' in tweet.entities:
                            hashtags = [tag['tag'] for tag in tweet.entities['hashtags']]
                        if 'mentions' in tweet.entities:
                            mentioned_users = [mention['username'] for mention in tweet.entities['mentions']]
                    
                    # Get author info
                    author_info = self._get_user_by_id(tweet.author_id) if tweet.author_id else {'username': 'unknown'}
                    
                    item_id = tweet.id
                    if item_id in self.processed_items:
                        continue

                    mentions.append({
                        'type': 'twitter_mention',
                        'sender': author_info.get('username', 'unknown'),
                        'content': tweet.text[:400],
                        'timestamp': tweet.created_at.isoformat() if tweet.created_at else datetime.now().isoformat(),
                        'item_id': item_id,
                        'hashtags': hashtags,
                        'mentioned_users': mentioned_users
                    })
                    self.processed_items.add(item_id)

            self.logger.info(f'Found {len(mentions)} Twitter mentions')

        except Exception as e:
            self.logger.warning(f'Error checking mentions: {e}')

        return mentions

    def _check_home_timeline(self) -> list:
        """Check home timeline for relevant content using API"""
        timeline_posts = []

        if not self.twitter_client:
            return timeline_posts

        try:
            # Get recent home timeline tweets
            timeline_response = self.twitter_client.get_home_timeline(
                max_results=20,
                tweet_fields=['created_at', 'author_id', 'public_metrics', 'context_annotations', 'entities']
            )

            if timeline_response.data:
                for tweet in timeline_response.data:
                    # Check if the tweet contains important keywords
                    if any(keyword in tweet.text.lower() for keyword in self.important_keywords):
                        # Extract hashtags and mentions from entities
                        hashtags = []
                        mentioned_users = []
                        
                        if hasattr(tweet, 'entities') and tweet.entities:
                            if 'hashtags' in tweet.entities:
                                hashtags = [tag['tag'] for tag in tweet.entities['hashtags']]
                            if 'mentions' in tweet.entities:
                                mentioned_users = [mention['username'] for mention in tweet.entities['mentions']]
                        
                        # Get author info
                        author_info = self._get_user_by_id(tweet.author_id) if tweet.author_id else {'username': 'unknown'}
                        
                        item_id = tweet.id
                        if item_id in self.processed_items:
                            continue

                        timeline_posts.append({
                            'type': 'twitter_timeline_post',
                            'sender': author_info.get('username', 'unknown'),
                            'content': tweet.text[:400],
                            'timestamp': tweet.created_at.isoformat() if tweet.created_at else datetime.now().isoformat(),
                            'item_id': item_id,
                            'hashtags': hashtags,
                            'mentioned_users': mentioned_users
                        })
                        self.processed_items.add(item_id)

            self.logger.info(f'Found {len(timeline_posts)} relevant posts in timeline')

        except Exception as e:
            self.logger.warning(f'Error checking home timeline: {e}')

        return timeline_posts

    def _get_user_by_id(self, user_id: str):
        """Get user information by ID"""
        try:
            user_response = self.twitter_client.get_user(id=user_id, user_fields=['username', 'name'])
            if user_response.data:
                return user_response.data
        except Exception:
            pass
        return {'username': 'unknown', 'name': 'Unknown User'}

    def determine_priority(self, item: dict) -> str:
        """Determine priority based on content"""
        content = f"{item.get('content', '')} {item.get('preview', '')}".lower()

        if any(kw in content for kw in ['urgent', 'business', 'opportunity', 'partnership']):
            return 'P1'
        elif any(kw in content for kw in ['collab', 'inquiry', 'help', 'dm']):
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
            # Default for other types
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
            'action_file': filename
        })

        return action_path

    def run(self):
        """Run with banner"""
        print(f'''
╔══════════════════════════════════════════════════════════════╗
║             AI Employee - Twitter (X) Watcher                ║
║                      Gold Tier                               ║
╠══════════════════════════════════════════════════════════════╣
║  Monitoring: Mentions & Timeline Posts                        ║
║  Interval:   {self.check_interval} seconds                             ║
║  Status:     {'ACTIVE' if self.twitter_client else 'INACTIVE (missing credentials)'}           ║
╚══════════════════════════════════════════════════════════════╝
''')
        if not self.twitter_client:
            print("⚠️  Twitter API client not initialized. Please check your environment variables.")
            return
        
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
