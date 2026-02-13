---
name: check-facebook
description: Check Facebook for notifications and messages. Use when user says "check facebook", "facebook messages", "facebook notifications", or "any facebook updates".
---

# Check Facebook Skill

## Purpose
Monitor Facebook for new notifications and Messenger messages.

## Execution

### Start continuous watcher:
```bash
uv run python watchers/facebook_watcher.py
```

### First Time Setup
1. Run watcher
2. Login to Facebook in browser
3. Press Enter to continue
4. Session saved for future use

## What It Monitors
- Facebook notifications (mentions, comments, tags)
- Messenger messages

## Priority Keywords
- **P1**: urgent, payment, order, business
- **P2**: message, inquiry, question
- **P3**: Other notifications

## Output
- `/Needs_Action/FACEBOOK_notification_*.md`
- `/Needs_Action/FACEBOOK_message_*.md`
