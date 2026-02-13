---
name: check-instagram
description: Check Instagram for notifications and DMs. Use when user says "check instagram", "instagram messages", "instagram dms", or "any instagram updates".
---

# Check Instagram Skill

## Purpose
Monitor Instagram for new notifications and direct messages.

## Execution

### Start continuous watcher:
```bash
uv run python watchers/instagram_watcher.py
```

### First Time Setup
1. Run watcher
2. Login to Instagram in browser
3. Press Enter to continue
4. Session saved for future use

## What It Monitors
- Instagram notifications (likes, comments, mentions)
- Direct Messages (DMs)

## Priority Keywords
- **P1**: business, order, sponsor, partnership
- **P2**: collab, inquiry, dm
- **P3**: Other notifications

## Output
- `/Needs_Action/INSTAGRAM_notification_*.md`
- `/Needs_Action/INSTAGRAM_dm_*.md`
