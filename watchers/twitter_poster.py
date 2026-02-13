"""
Twitter (X) Poster - Posts tweets using official API
Gold Tier Requirement: Twitter (X) integration
Uses Twitter API v2 for posting
"""
import sys
import json
import os
from pathlib import Path
from datetime import datetime
import tweepy
from dotenv import load_dotenv


class TwitterPoster:
    """
    Posts tweets to Twitter (X) using official API with human-in-the-loop approval.

    Usage:
        poster = TwitterPoster(vault_path)
        poster.post_tweet("Tweet content")
    """

    def __init__(self, vault_path: str = None):
        # Load environment variables
        load_dotenv()
        
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

        # Initialize Twitter API client
        self.twitter_client = self._init_twitter_api()

    def _init_twitter_api(self):
        """Initialize Twitter API v2 client using environment variables"""
        consumer_key = os.getenv('TWITTER_CONSUMER_KEY')
        consumer_secret = os.getenv('TWITTER_CONSUMER_SECRET')
        access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        bearer_token = os.getenv('TWITTER_BEARER_TOKEN')

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
            
            print(f"Missing required Twitter environment variables: {', '.join(missing_vars)}")
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
            print("Twitter API client initialized successfully for posting")
            return client
        except Exception as e:
            print(f"Failed to initialize Twitter API client: {e}")
            return None

    def post_tweet(self, content: str, requires_approval: bool = True) -> bool:
        """
        Post a tweet with optional approval workflow
        
        Args:
            content: The tweet content to post
            requires_approval: Whether to create approval file first
            
        Returns:
            bool: True if tweet was posted successfully
        """
        if not self.twitter_client:
            print("Twitter client not initialized - cannot post")
            return False

        if requires_approval:
            # Create approval file first
            approval_file = self._create_approval_file(content)
            print(f"Approval required: {approval_file}")
            return False  # Return False to indicate approval needed
        
        # Post directly without approval
        try:
            response = self.twitter_client.create_tweet(text=content)
            if response.data and 'id' in response.data:
                tweet_id = response.data['id']
                print(f"Successfully posted tweet: https://twitter.com/user/status/{tweet_id}")
                
                # Log the action
                self._log_action('twitter_post', {
                    'tweet_id': tweet_id,
                    'content': content,
                    'timestamp': datetime.now().isoformat()
                })
                return True
            else:
                print("Failed to post tweet - no response data")
                return False
        except Exception as e:
            print(f"Error posting tweet: {e}")
            return False

    def _create_approval_file(self, content: str) -> Path:
        """Create approval file for human-in-the-loop workflow"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"TWITTER_POST_APPROVAL_{timestamp}.md"
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
            **details
        }

        # Read existing logs or create new
        if log_file.exists():
            with open(log_file, 'r') as f:
                logs = json.load(f)
        else:
            logs = []

        logs.append(log_entry)

        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)

    def process_approved_posts(self):
        """Process approved Twitter posts"""
        approved_files = list(self.approved_path.glob('TWITTER_POST_APPROVAL_*.md'))
        
        for file_path in approved_files:
            # Read the content from the approval file
            content = file_path.read_text()
            
            # Extract the tweet content (this is a simple approach)
            lines = content.split('\n')
            tweet_content = ""
            capturing = False
            
            for line in lines:
                if "**Content to post:**" in line:
                    capturing = True
                    continue
                elif capturing and line.startswith('##'):
                    break
                elif capturing:
                    tweet_content += line.strip() + " "
            
            tweet_content = tweet_content.strip()
            
            if tweet_content:
                # Post the tweet
                try:
                    response = self.twitter_client.create_tweet(text=tweet_content)
                    if response.data and 'id' in response.data:
                        tweet_id = response.data['id']
                        print(f"Successfully posted approved tweet: https://twitter.com/user/status/{tweet_id}")
                        
                        # Log the action
                        self._log_action('twitter_post_approved', {
                            'tweet_id': tweet_id,
                            'content': tweet_content,
                            'timestamp': datetime.now().isoformat()
                        })
                        
                        # Move the file to indicate completion
                        completed_path = self.approved_path / f"COMPLETED_{file_path.name}"
                        file_path.rename(completed_path)
                    else:
                        print(f"Failed to post approved tweet from {file_path.name}")
                except Exception as e:
                    print(f"Error posting approved tweet from {file_path.name}: {e}")


def main():
    """Main function for testing"""
    default_vault = Path(__file__).parent.parent / 'AI_Employee_Vault'
    if default_vault.is_symlink():
        default_vault = default_vault.resolve()

    poster = TwitterPoster(str(default_vault))
    
    print("Twitter Poster initialized")
    print(f"Twitter client: {'✅ CONNECTED' if poster.twitter_client else '❌ DISCONNECTED'}")
    
    # Example usage:
    # poster.post_tweet("Hello from AI Employee! #AI #Automation", requires_approval=True)


if __name__ == '__main__':
    main()