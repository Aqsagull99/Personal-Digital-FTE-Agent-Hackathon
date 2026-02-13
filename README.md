# Personal AI Employee - Gold Tier Implementation

A fully autonomous Digital FTE (Full-Time Equivalent) that manages personal and business affairs 24/7 using Claude Code as the reasoning engine and Obsidian as the management dashboard.

**Hackathon:** Personal AI Employee Hackathon 0
**Tier:** Gold (Autonomous Employee)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    PERSONAL AI EMPLOYEE                         │
│                      SYSTEM ARCHITECTURE                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      EXTERNAL SOURCES                           │
├─────────────────┬─────────────────┬─────────────────────────────┤
│     Gmail       │    WhatsApp     │   Social Media   │  Odoo    │
└────────┬────────┴────────┬────────┴─────────┬────────┴────┬─────┘
         │                 │                  │             │
         ▼                 ▼                  ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PERCEPTION LAYER (Watchers)                  │
│  Gmail │ WhatsApp │ LinkedIn │ Twitter │ Facebook │ Instagram   │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OBSIDIAN VAULT (Local)                       │
│  /Inbox │ /Needs_Action │ /Done │ /Logs │ /Pending_Approval     │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    REASONING LAYER (Claude Code)                │
│   Read → Think → Plan → Write → Request Approval                │
└────────────────────────────────┬────────────────────────────────┘
                                 │
              ┌──────────────────┴───────────────────┐
              ▼                                      ▼
┌────────────────────────────┐    ┌────────────────────────────────┐
│    HUMAN-IN-THE-LOOP       │    │         MCP SERVERS            │
│   Approval Workflow        │    │   Email │ Odoo │ Browser       │
└────────────────────────────┘    └────────────────────────────────┘
```

## Gold Tier Requirements Checklist

| # | Requirement | Status | Implementation |
|---|-------------|--------|----------------|
| 1 | All Silver requirements | ✅ | Complete |
| 2 | Full cross-domain integration | ✅ | Personal + Business |
| 3 | Odoo accounting via MCP | ✅ | `mcp_servers/odoo_server.py` |
| 4 | Facebook + Instagram | ✅ | `watchers/facebook_watcher.py`, `instagram_watcher.py` |
| 5 | Twitter (X) integration | ✅ | `watchers/twitter_watcher.py`, `twitter_poster.py` |
| 6 | Multiple MCP servers | ✅ | Email, Odoo |
| 7 | CEO Briefing + Audit | ✅ | `scheduler/tasks/ceo_briefing.py` |
| 8 | Error recovery | ✅ | `utils/error_recovery.py` |
| 9 | Audit logging | ✅ | `utils/audit_logger.py` |
| 10 | Ralph Wiggum loop | ✅ | `utils/ralph_wiggum.py` |
| 11 | Documentation | ✅ | This README |
| 12 | Agent Skills | ✅ | `.claude/skills/` |

## Quick Start

### Prerequisites
- Python 3.13+
- Node.js v24+ LTS
- Claude Code (Pro subscription)
- Obsidian v1.10.6+

### Setup

```bash
# Clone and setup
git clone <repo-url>
cd hackhathon_AI_Employee

# Install dependencies
uv sync

# Create Obsidian vault symlink
ln -s /path/to/AI_Employee_Vault ./AI_Employee_Vault

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Environment Variables

```bash
# Gmail API
GMAIL_CREDENTIALS_PATH=/path/to/credentials.json
GMAIL_TOKEN_PATH=/path/to/token.json

# Odoo
ODOO_URL=http://localhost:8069
ODOO_DB=odoo_db
ODOO_USERNAME=admin
ODOO_PASSWORD=admin

# Social Media (Playwright sessions)
WHATSAPP_SESSION_PATH=/path/to/whatsapp_session
LINKEDIN_SESSION_PATH=/path/to/linkedin_session
TWITTER_SESSION_PATH=/path/to/twitter_session
FACEBOOK_SESSION_PATH=/path/to/facebook_session
INSTAGRAM_SESSION_PATH=/path/to/instagram_session

# AI Employee
VAULT_PATH=/path/to/AI_Employee_Vault
DRY_RUN=true  # Set to false for production
```

## Project Structure

```
hackhathon_AI_Employee/
├── .claude/
│   └── skills/                 # Claude Agent Skills
│       ├── check-gmail/
│       ├── check-linkedin/
│       ├── check-whatsapp/
│       ├── check-facebook/
│       ├── check-instagram/
│       ├── check-twitter/
│       ├── post-linkedin/
│       ├── post-twitter/
│       ├── post-social/
│       ├── send-email/
│       ├── odoo-accounting/
│       ├── ceo-briefing/
│       ├── process-inbox/
│       ├── scan-inbox/
│       ├── complete-task/
│       ├── create-plan/
│       ├── manage-schedule/
│       ├── check-status/
│       └── update-dashboard/
├── watchers/                   # Perception Layer
│   ├── base_watcher.py
│   ├── gmail_watcher.py
│   ├── whatsapp_watcher.py
│   ├── linkedin_watcher.py
│   ├── linkedin_poster.py
│   ├── twitter_watcher.py
│   ├── twitter_poster.py
│   ├── facebook_watcher.py
│   ├── instagram_watcher.py
│   ├── social_poster.py
│   └── filesystem_watcher.py
├── mcp_servers/                # Action Layer
│   ├── email_server.py
│   └── odoo_server.py
├── scheduler/                  # Orchestration
│   ├── scheduler.py
│   └── tasks/
│       ├── morning_briefing.py
│       ├── weekly_report.py
│       ├── ceo_briefing.py
│       └── update_dashboard.py
├── utils/                      # Gold Tier Utilities
│   ├── audit_logger.py        # Comprehensive logging
│   ├── error_recovery.py      # Graceful degradation
│   └── ralph_wiggum.py        # Autonomous loops
├── AI_Employee_Vault -> symlink
├── main.py
├── pyproject.toml
└── README.md
```

## Vault Structure

```
AI_Employee_Vault/
├── Inbox/                      # Drop zone for new items
├── Needs_Action/               # Tasks awaiting processing
├── In_Progress/                # Currently being worked on
├── Done/                       # Completed tasks
├── Pending_Approval/           # HITL approval queue
├── Approved/                   # User-approved actions
├── Rejected/                   # User-rejected actions
├── Plans/                      # Claude's task plans
├── Briefings/                  # CEO briefings
├── Reports/                    # Generated reports
├── Logs/                       # Audit logs (JSON)
├── State/                      # Ralph Wiggum state
├── Offline_Queue/              # Queued offline actions
├── Dashboard.md                # Real-time status
├── Company_Handbook.md         # Rules of engagement
└── Business_Goals.md           # KPIs and targets
```

## Key Features

### 1. Watchers (Perception Layer)
Lightweight Python scripts that monitor external sources:
- **Gmail Watcher**: Monitors important/unread emails
- **WhatsApp Watcher**: Detects urgent keywords
- **LinkedIn Watcher**: Tracks messages and notifications
- **Twitter Watcher**: Monitors mentions and DMs
- **Facebook/Instagram Watchers**: Check notifications

### 2. MCP Servers (Action Layer)
- **Email MCP**: Send/draft emails via Gmail API
- **Odoo MCP**: Accounting operations (invoices, payments)

### 3. Skills (Claude's Capabilities)
All AI functionality implemented as Agent Skills for:
- Checking each platform
- Posting to social media
- Processing inbox items
- Generating CEO briefings
- Managing schedules

### 4. Gold Tier Utilities

#### Audit Logger
```python
from utils import get_logger, ActionCategory

logger = get_logger()
logger.log_email_sent("client@example.com", "Invoice", ApprovalStatus.APPROVED)
logger.generate_audit_report(days=7)
```

#### Error Recovery
```python
from utils import with_retry, graceful, TransientError

@with_retry(max_attempts=3, base_delay=1.0)
def flaky_api_call():
    ...

@graceful(service="gmail", queue_on_failure=True)
def send_email(to, subject, body):
    ...
```

#### Ralph Wiggum Loop
```bash
# Keep Claude working until task complete
python utils/ralph_wiggum.py \
    --task "Process all files in /Needs_Action and move to /Done" \
    --completion-promise "TASK_COMPLETE" \
    --max-iterations 10
```

### 5. CEO Briefing
Weekly business audit with:
- Financial overview (Odoo)
- Task performance metrics
- Communication stats
- Bottleneck identification
- Proactive suggestions

```bash
# Generate CEO briefing
uv run python scheduler/tasks/ceo_briefing.py

# Schedule for Sunday evenings
uv run python scheduler/scheduler.py add ceo_briefing \
    scheduler/tasks/ceo_briefing.py "0 20 * * 0"
```

## Human-in-the-Loop (HITL)

Sensitive actions require approval:
1. Claude creates file in `/Pending_Approval/`
2. User reviews and moves to `/Approved/` or `/Rejected/`
3. Orchestrator executes approved actions

```markdown
# /Pending_Approval/EMAIL_invoice_client.md
---
action: send_email
to: client@example.com
subject: Invoice #123
amount: $500
---

Move to /Approved to proceed.
```

## Running the System

### Start Individual Watchers
```bash
uv run python watchers/gmail_watcher.py
uv run python watchers/linkedin_watcher.py
```

### Start Scheduler
```bash
uv run python scheduler/scheduler.py start
```

### Use with PM2 (Recommended)
```bash
npm install -g pm2

pm2 start watchers/gmail_watcher.py --interpreter python3
pm2 start watchers/linkedin_watcher.py --interpreter python3
pm2 start scheduler/scheduler.py --interpreter python3 -- start

pm2 save
pm2 startup
```

## Security

- All credentials in `.env` (never committed)
- HITL approval for sensitive actions
- Audit logging for all actions
- 90-day log retention
- Dry run mode for testing

## Lessons Learned

1. **File-based communication** is robust and debuggable
2. **HITL is essential** for payments and new contacts
3. **Graceful degradation** prevents cascade failures
4. **Ralph Wiggum pattern** enables autonomous multi-step tasks
5. **Skills make Claude reusable** across contexts

## Demo Video

[Link to demo video]

## Author

Built for Personal AI Employee Hackathon 0

---

*This AI Employee works 8,760 hours/year vs a human's 2,000, with 85-90% cost savings.*
