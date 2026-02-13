---
name: check-whatsapp
description: Check WhatsApp for new important messages. Use when user says "check whatsapp", "whatsapp messages", "any whatsapp updates", or "new whatsapp".
---

# Check WhatsApp Skill

## Purpose
Monitor WhatsApp Web for new messages containing important keywords and create action files.

## Prerequisites
- Playwright installed
- First run requires QR code scan from phone

## Workflow

1. **Launch browser** with saved session
2. **Check unread chats** for keyword matches
3. **Create action files** for important messages
4. **Log activity**

## Important Keywords (triggers action file)
- **Urgent**: urgent, asap, emergency
- **Business**: payment, invoice, client, order
- **Action needed**: help, meeting, call, deadline

## Execution

### Start continuous watcher:
```bash
uv run python watchers/whatsapp_watcher.py
```

### Single check:
```bash
uv run python -c "
from watchers.whatsapp_watcher import WhatsAppWatcher
watcher = WhatsAppWatcher('AI_Employee_Vault')
updates = watcher.check_for_updates()
for item in updates:
    watcher.create_action_file(item)
print(f'Processed {len(updates)} WhatsApp messages')
watcher.close()
"
```

## First Time Setup

1. Run the watcher
2. WhatsApp Web opens in browser
3. Open WhatsApp on phone
4. Go to Settings > Linked Devices
5. Scan QR code
6. Session saved for future use

## Output
- Action files: `/Needs_Action/WHATSAPP_[sender]_[time].md`
- Logs: `/Logs/[date].json`

## Priority Assignment
- **P1 (Critical)**: urgent, asap, payment, invoice, emergency
- **P2 (High)**: important, deadline, meeting, call, client
- **P3 (Normal)**: other keyword matches

## Notes
- Browser must be visible for first-time QR scan
- Check interval: 30 seconds
- Only processes messages with important keywords
