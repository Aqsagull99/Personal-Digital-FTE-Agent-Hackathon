---
name: check-gmail
description: Check Gmail for new important/unread emails and create action files. Use when user says "check gmail", "check email", "fetch emails", or "any new emails".
---

# Check Gmail Skill

## Purpose
Manually trigger Gmail check and fetch new important/unread emails into Needs_Action folder.

## Workflow

1. **Load Gmail credentials** from token.json
2. **Query Gmail API** for unread important emails
3. **For each new email**:
   - Extract sender, subject, body
   - Determine priority (P1/P2/P3)
   - Create action file in Needs_Action/
4. **Log activity** in Logs/
5. **Report summary** to user

## Prerequisites
- `credentials.json` must exist in project root
- `token.json` must exist (run gmail_watcher.py once to authenticate)

## Execution

Run the Gmail check:
```bash
uv run python -c "
from watchers.gmail_watcher import GmailWatcher
watcher = GmailWatcher('AI_Employee_Vault')
emails = watcher.check_for_updates()
for email in emails:
    watcher.create_action_file(email)
print(f'Processed {len(emails)} new emails')
"
```

## Output
- New email files in `/Needs_Action/EMAIL_*.md`
- Log entries in `/Logs/[date].json`
- Summary report to user

## Priority Keywords
- **P1 (Critical)**: urgent, asap, payment, invoice, deadline
- **P2 (High)**: request, help, meeting, important
- **P3 (Normal)**: all others
