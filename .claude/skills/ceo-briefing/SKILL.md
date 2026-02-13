---
name: ceo-briefing
description: Generate comprehensive CEO/business briefing with financial and operational metrics. Use when user says "ceo briefing", "business report", "weekly summary", "how's business", or "executive summary".
---

# CEO Briefing Skill

## Purpose
Generate comprehensive weekly business briefing combining:
- Financial metrics (from Odoo)
- Task completion stats
- Communication metrics
- Bottleneck identification
- Proactive suggestions

## The "Monday Morning CEO Briefing"
Transforms AI from chatbot to proactive business partner.

## Execution

### Generate Briefing
```bash
uv run python scheduler/tasks/ceo_briefing.py
```

### Scheduled (Recommended)
Add to cron for Sunday evening:
```bash
uv run python scheduler/scheduler.py add ceo_briefing scheduler/tasks/ceo_briefing.py "0 20 * * 0"
```

## Report Contents

### 1. Executive Summary
- Tasks completed this week
- Overall completion rate

### 2. Financial Overview (if Odoo connected)
- Revenue invoiced
- Cash received
- Net cash flow
- Outstanding balance
- Overdue invoices

### 3. Task Performance
- Completed vs pending
- By priority (P1/P2/P3)
- By type (Email, Social, etc.)

### 4. Communication Stats
- Emails processed/sent
- Social media posts
- Messages handled
- Activity by platform

### 5. Bottlenecks Identified
- Critical task backlog
- Stale tasks
- Low completion rate
- High pending count

### 6. Proactive Suggestions
- Payment reminders needed
- Social media schedule
- Prioritization advice
- Process improvements

### 7. Recommended Actions
- Follow up on overdue invoices
- Address critical tasks
- Review pending items
- Schedule content

## Output
- Briefing: `/Briefings/CEO_BRIEFING_[date].md`
- Copy in: `/Inbox/WEEKLY_CEO_BRIEFING_[date].md`
- Logged in: `/Logs/[date].json`

## Example Output

```markdown
# CEO Briefing
## Week of February 4 - February 11, 2026

## Executive Summary
Your AI Employee processed 45 tasks with 78% completion rate.

## Financial Overview
| Metric | Amount |
|--------|--------|
| Revenue | $12,500 |
| Cash Received | $8,200 |
| Outstanding | $15,300 |

## Bottlenecks
- 🔴 5 critical tasks pending
- ⏰ 8 tasks older than 3 days

## Suggestions
1. Send payment reminders for $3,500 overdue
2. Prioritize 5 critical tasks today
```

## Integration

Works with:
- Odoo (accounting metrics)
- All watchers (task metrics)
- Scheduler (automated generation)
- Dashboard (summary sync)
