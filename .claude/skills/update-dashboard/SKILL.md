---
name: update-dashboard
description: Update AI_Employee_Vault/Dashboard.md with current status. Use when user says "update dashboard", "refresh status", or after completing any vault operation.
---

# Update Dashboard Skill

## Purpose
Keep Dashboard.md accurate and up-to-date with real-time vault status.

## Workflow

1. **Count files** in each folder:
   - `/Inbox/` - new items
   - `/Needs_Action/` - pending tasks
   - `/Done/` - completed today
   - `/Pending_Approval/` - awaiting human approval

2. **Read recent activity** from `/Logs/` folder

3. **Update Dashboard.md** with:
   - Current counts
   - Recent activity log
   - Today's priorities
   - Any alerts

## Dashboard Structure

```markdown
---
last_updated: [ISO timestamp]
status: active
---

# AI Employee Dashboard

## Quick Status
| Category | Count | Status |
|----------|-------|--------|
| Inbox | [count] | [Clear/Needs Attention] |
| Needs Action | [count] | [Clear/Needs Attention] |
| Done Today | [count] | - |
| Pending Approval | [count] | [Clear/Action Required] |

## Recent Activity
- [timestamp] Activity description
- [timestamp] Activity description

## Today's Priorities
1. [Priority item based on P1/P2 tasks]
2. [Next priority]

## Alerts
- [Any urgent items or issues]

---
*Last processed by AI Employee: [timestamp]*
```

## Status Logic

- **Clear**: 0 items
- **Needs Attention**: 1-5 items
- **Action Required**: >5 items or P1 priority items present

## After Update
- Log the update action
- Report changes to user if significant
