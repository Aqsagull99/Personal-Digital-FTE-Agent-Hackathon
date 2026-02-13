---
name: check-linkedin
description: Check LinkedIn for new messages and notifications. Use when user says "check linkedin", "linkedin messages", "any linkedin updates", or "linkedin notifications".
---

# Check LinkedIn Skill

## Purpose
Monitor LinkedIn for new messages and important notifications, create action files for follow-up.

## Prerequisites
- Playwright installed (`uv run playwright install chromium`)
- First run requires manual LinkedIn login (session saved for future)

## Workflow

1. **Launch browser** with saved session
2. **Check messages** for unread conversations
3. **Check notifications** for important updates
4. **Create action files** in Needs_Action/
5. **Log activity**

## Execution

```bash
uv run python watchers/linkedin_watcher.py
```

Or single check:
```bash
uv run python -c "
from watchers.linkedin_watcher import LinkedInWatcher
watcher = LinkedInWatcher('AI_Employee_Vault')
updates = watcher.check_for_updates()
for item in updates:
    watcher.create_action_file(item)
print(f'Processed {len(updates)} LinkedIn updates')
watcher.close()
"
```

## Important Keywords
Messages/notifications with these keywords get higher priority:
- **P1**: urgent, asap, offer, interview
- **P2**: opportunity, project, collaboration, partnership
- **P3**: all others

## Output
- Action files: `/Needs_Action/LINKEDIN_message_*.md` or `/Needs_Action/LINKEDIN_notification_*.md`
- Logs: `/Logs/[date].json`

## Notes
- First run opens browser for manual login
- Session saved to `.linkedin_session/` for future use
- Check interval: 5 minutes (when running continuously)
