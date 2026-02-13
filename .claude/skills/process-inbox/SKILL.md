---
name: process-inbox
description: Process items in AI_Employee_Vault/Inbox folder. Use when user says "process inbox", "check inbox", or "handle new items". Reads new files, categorizes them, creates action items in Needs_Action folder.
---

# Process Inbox Skill

## Purpose
Scan the Inbox folder for new items and process them according to Company_Handbook.md rules.

## Workflow

1. **Read Company Handbook** first to understand processing rules
2. **Scan Inbox folder** for any files
3. **For each file**:
   - Determine type (email, task, document, etc.)
   - Assign priority (P1-P4) based on content
   - Create action file in `/Needs_Action/` with proper metadata
   - Move original to appropriate location or delete if processed
4. **Update Dashboard.md** with new counts

## File Processing Rules

### Email files (EMAIL_*.md)
- Check sender against known contacts
- Flag urgent keywords: "urgent", "asap", "payment", "invoice"
- Create reply draft if needed

### Task files (TASK_*.md)
- Extract due date if present
- Assign priority based on deadline
- Link to relevant projects

### Document files (DOC_*.md, FILE_*)
- Categorize by content type
- Move to appropriate project folder if identifiable

## Output Format

Create files in Needs_Action with this structure:

```markdown
---
type: [email|task|document]
source: inbox
priority: [P1|P2|P3|P4]
created: [ISO timestamp]
original_file: [filename]
status: pending
---

## Summary
[Brief description of the item]

## Suggested Actions
- [ ] Action item 1
- [ ] Action item 2

## Context
[Any relevant context from Company_Handbook.md]
```

## After Processing

- Update Dashboard.md counts
- Log action in /Logs/[date].json
- Report summary to user
