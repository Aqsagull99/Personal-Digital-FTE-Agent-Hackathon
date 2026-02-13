---
name: complete-task
description: Mark a task as complete and move to Done folder. Use when user says "complete task", "mark done", "finish task", or when a task is finished processing.
---

# Complete Task Skill

## Purpose
Move completed tasks from Needs_Action to Done folder with proper logging.

## Workflow

1. **Identify the task** to complete (by filename or description)
2. **Update task file** metadata:
   - Set `status: completed`
   - Add `completed_at: [timestamp]`
3. **Move file** from `/Needs_Action/` to `/Done/`
4. **Log completion** in `/Logs/[date].json`
5. **Update Dashboard.md** via update-dashboard skill

## Task Completion Format

Update the task file before moving:

```markdown
---
type: [original type]
source: [original source]
priority: [original priority]
created: [original timestamp]
status: completed
completed_at: [ISO timestamp]
---

## Summary
[Original summary]

## Completed Actions
- [x] Action item 1
- [x] Action item 2

## Completion Notes
[Any notes about how task was completed]
```

## Log Entry Format

Add to `/Logs/[YYYY-MM-DD].json`:

```json
{
  "timestamp": "[ISO timestamp]",
  "action_type": "task_complete",
  "task_file": "[filename]",
  "task_type": "[type]",
  "priority": "[priority]",
  "result": "success"
}
```

## After Completion
- Confirm to user task is done
- Update dashboard counts
- Suggest next priority task if any
