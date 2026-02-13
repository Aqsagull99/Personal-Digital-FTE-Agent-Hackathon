---
name: manage-schedule
description: Manage scheduled tasks and cron jobs for AI Employee. Use when user says "setup schedule", "schedule task", "list scheduled jobs", "manage cron", or "automate".
---

# Manage Schedule Skill

## Purpose
Set up and manage automated scheduled tasks using cron.

## Available Commands

### Setup Default Schedule
```bash
uv run python scheduler/scheduler.py setup
```

Sets up:
- Gmail check every 5 minutes
- Inbox scan every 2 minutes
- Dashboard update every 15 minutes
- Morning briefing at 8:00 AM
- Weekly report on Sunday 8:00 PM

### List Scheduled Jobs
```bash
uv run python scheduler/scheduler.py list
```

### Add Custom Job
```bash
uv run python scheduler/scheduler.py add <name> <script> "<schedule>"
```

### Remove Job
```bash
uv run python scheduler/scheduler.py remove <name>
```

### Clear All Jobs
```bash
uv run python scheduler/scheduler.py clear
```

## Cron Schedule Format

```
*    *    *    *    *
│    │    │    │    │
│    │    │    │    └── Day of week (0-7, Sun=0 or 7)
│    │    │    └─────── Month (1-12)
│    │    └──────────── Day of month (1-31)
│    └───────────────── Hour (0-23)
└────────────────────── Minute (0-59)
```

### Common Schedules

| Schedule | Meaning |
|----------|---------|
| `*/5 * * * *` | Every 5 minutes |
| `*/15 * * * *` | Every 15 minutes |
| `0 * * * *` | Every hour |
| `0 8 * * *` | Daily at 8:00 AM |
| `0 9 * * 1-5` | Weekdays at 9:00 AM |
| `0 20 * * 0` | Sunday at 8:00 PM |
| `0 0 1 * *` | First of every month |

## Default Scheduled Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| gmail_check | Every 5 min | Check Gmail for new emails |
| inbox_scan | Every 2 min | Scan Inbox folder |
| dashboard_update | Every 15 min | Update Dashboard.md |
| morning_briefing | 8:00 AM daily | Create daily briefing |
| weekly_report | Sun 8:00 PM | Create weekly summary |

## Output Files

- **Morning Briefing**: `/Briefings/BRIEFING_[date].md` + copy in Inbox
- **Weekly Report**: `/Reports/WEEKLY_REPORT_[date].md`
- **Logs**: `/Logs/cron_[task].log`

## Notes

- Cron runs in background, even when terminal closed
- Check logs for errors: `tail -f AI_Employee_Vault/Logs/cron_*.log`
- Jobs persist across reboots (system crontab)
