---
name: check-status
description: Check overall AI Employee status and vault health. Use when user says "status", "check status", "how are things", or "what's pending".
---

# Check Status Skill

## Purpose
Provide quick overview of AI Employee vault status and pending work.

## Workflow

1. **Count items** in each folder
2. **Identify priority items** (P1, P2)
3. **Check for stale items** (>24 hours old)
4. **Report summary** to user

## Status Check Process

### Folder Counts
```
/Inbox/           → New items awaiting processing
/Needs_Action/    → Tasks requiring attention
/Pending_Approval/→ Awaiting human approval
/Done/            → Completed (today's count)
```

### Priority Analysis
- List any P1 (Critical) items
- List any P2 (High) items older than 4 hours
- Flag overdue items

### Health Checks
- Dashboard.md last updated time
- Any errors in recent logs
- Stale items (>24h without action)

## Output Format

```
## AI Employee Status

📊 **Counts**
- Inbox: X items
- Needs Action: X items
- Pending Approval: X items
- Done Today: X items

⚠️ **Alerts**
- [Any P1/P2 items or issues]

✅ **Health**
- Last updated: [timestamp]
- System: Operational

📋 **Next Actions**
1. [Suggested next action]
```

## After Status Check
- Offer to process inbox if items present
- Offer to handle priority items
- Update dashboard if counts changed
