---
name: scan-inbox
description: Scan Inbox folder for new files and process them into Needs_Action. Use when user says "scan inbox", "check inbox folder", "process new files", or "any new files".
---

# Scan Inbox Skill

## Purpose
Manually scan the Inbox folder and process any new files into Needs_Action folder.

## Workflow

1. **List files** in AI_Employee_Vault/Inbox/
2. **For each file**:
   - Determine type (email, task, document)
   - Determine priority based on content
   - Create action file in Needs_Action/
3. **Log activity** in Logs/
4. **Report summary** to user

## Execution

Scan and process inbox files:
```bash
uv run python -c "
from watchers.filesystem_watcher import FileSystemWatcher
watcher = FileSystemWatcher('AI_Employee_Vault')
files = watcher.check_for_updates()
for f in files:
    watcher.create_action_file(f)
print(f'Processed {len(files)} files from Inbox')
"
```

## File Type Detection
- `EMAIL_*.md` → type: email
- `TASK_*.md` → type: task
- `DOC_*.md`, `FILE_*` → type: document
- Others → type: general

## Priority Detection
- **P1**: Contains "urgent", "asap", "invoice", "payment", "critical"
- **P2**: Contains "request", "help", "needed", "deadline"
- **P3**: All others

## Output
- Action files in `/Needs_Action/ACTION_*.md`
- Log entries in `/Logs/[date].json`
- Summary count to user
