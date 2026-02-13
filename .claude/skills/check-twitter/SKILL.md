---
name: check-twitter
description: Check Twitter (X) for notifications, mentions and DMs. Use when user says "check twitter", "twitter notifications", "twitter mentions", "twitter dms", or "any tweets".
---

# Check Twitter Skill

## Purpose
Monitor Twitter (X) for new notifications, mentions, and direct messages.

## Execution

### Start continuous watcher:
```bash
uv run python watchers/twitter_watcher.py
```

### First Time Setup
1. Run watcher
2. Login to Twitter in browser
3. Press Enter to continue
4. Session saved for future use

## What It Monitors

| Type | Description |
|------|-------------|
| Notifications | Likes, retweets, follows |
| Mentions | @mentions in tweets |
| DMs | Direct messages |

## Priority Keywords
- **P1**: urgent, business, opportunity, partnership
- **P2**: collab, inquiry, help, dm
- **P3**: Other interactions

## Output Files
- `/Needs_Action/TWITTER_notification_*.md`
- `/Needs_Action/TWITTER_mention_*.md`
- `/Needs_Action/TWITTER_dm_*.md`
