# Personal AI Employee

A local-first, autonomous Digital FTE (Full-Time Equivalent) that manages personal and business affairs 24/7. It monitors Gmail, WhatsApp, LinkedIn, Twitter, Facebook, and Instagram — reasons about what needs doing — and executes with human-in-the-loop approval for sensitive operations.

**Hackathon:** Personal AI Employee Hackathon 0
**Target Tier:** Platinum (In Progress)
**Architecture:** [AGENTS.md](./AGENTS.md)

## Hackathon Documentation

- Architecture (submission doc): [docs/architecture.md](./docs/architecture.md)
- Lessons learned (submission doc): [docs/lessons-learned.md](./docs/lessons-learned.md)
- Platinum runbook (cloud + local split): [docs/platinum-runbook.md](./docs/platinum-runbook.md)
- Platinum cloud ops: [docs/platinum-cloud-operations.md](./docs/platinum-cloud-operations.md)
- Platinum Odoo cloud integration: [docs/platinum-odoo-cloud.md](./docs/platinum-odoo-cloud.md)
- Detailed agent architecture reference: [AGENTS.md](./AGENTS.md)

## How It Works

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  External    │    │   Watchers   │    │   Obsidian   │    │  Claude Code │
│  Sources     │───►│   (Python)   │───►│   Vault      │───►│  (Reasoning) │
│  Gmail, X...│    │  Poll & Save │    │  .md files   │    │  Plan & Act  │
└──────────────┘    └──────────────┘    └──────────────┘    └──────┬───────┘
                                                                    │
                                              ┌─────────────────────┤
                                              ▼                     ▼
                                        ┌───────────┐     ┌──────────────┐
                                        │   HITL    │     │ MCP Servers  │
                                        │  Approval │     │ Email, Odoo  │
                                        └───────────┘     └──────────────┘
```

1. **Watchers** monitor Gmail, Twitter, WhatsApp, LinkedIn, Facebook, Instagram, and local file drops
2. New items land as markdown files in the Obsidian vault's `/Needs_Action/` folder
3. **Claude Code** reads the vault, consults `Company_Handbook.md` rules, and decides what to do
4. Sensitive actions go to `/Pending_Approval/` for human review
5. **MCP Servers** execute approved actions (send emails, create Odoo invoices)
6. Everything is logged to `/Logs/` as JSON audit trails

## Current Status

### Working End-to-End
- **Gmail → Obsidian → Odoo pipeline**: Emails fetched via OAuth, triaged by priority, auto-creates Odoo contacts
- **Email MCP Server**: Send emails, create drafts, manage known contacts with approval workflow
- **Odoo MCP Server**: Connected and operational for read/audit paths; some write paths still need API payload fixes
- **Filesystem Watcher**: Detects new files dropped into `/Inbox/`, creates action items
- **Twitter Watcher + Poster**: Tweepy v2 integration for mentions, timeline monitoring, and posting
- **34 Claude Agent Skills**: AI functionality packaged as reusable skills
- **Audit Logging**: 3+ days of structured JSON logs in the vault
- **Scheduler**: Cron-based morning briefings, weekly reports, and dashboard updates
- **Silver Tier Validation**: Reproducible proof pack generated with overall `PASS`

### Scaffolded (Code Complete, Needs Browser Sessions)
- **WhatsApp Watcher**: Playwright-based, requires QR code login to WhatsApp Web
- **LinkedIn Watcher + Poster**: API path works, Playwright posting ready
- **Facebook Watcher + Poster**: Playwright browser automation
- **Instagram Watcher + Poster**: Playwright browser automation

### Planned / Not Yet Exercised
- **Full approval workflow loop**: `/Pending_Approval/` → `/Approved/` → execute → `/Done/`
- **Ralph Wiggum autonomous loop**: Code written, not yet run end-to-end
- **Main orchestrator**: `main.py` is a placeholder; system runs as individual scripts/skills

## Quick Start

### Prerequisites
- Python 3.13+
- Node.js v24+ LTS
- Claude Code (Pro subscription or Claude Code Router)
- Obsidian v1.10.6+

### Setup

```bash
# Clone
git clone <repo-url>
cd hackhathon_AI_Employee

# Install Python dependencies
uv sync

# Create Obsidian vault (or symlink existing one)
# The vault should be an Obsidian-managed folder on your local machine
ln -s /path/to/your/AI_Employee_Vault ./AI_Employee_Vault

# Configure environment
cp .env.example .env
# Edit .env with your actual credentials
```

### Environment Variables

```bash
# Gmail API (OAuth2)
GMAIL_CREDENTIALS_PATH=./credentials.json
GMAIL_TOKEN_PATH=./token.json

# Odoo ERP
ODOO_URL=http://localhost:8069
ODOO_DB=your_odoo_db_here
ODOO_USERNAME=your_odoo_username_here
ODOO_PASSWORD=your_odoo_password_here

# Social Media (Playwright session paths)
WHATSAPP_SESSION_PATH=/path/to/whatsapp_session
LINKEDIN_SESSION_PATH=/path/to/linkedin_session
TWITTER_SESSION_PATH=/path/to/twitter_session
FACEBOOK_SESSION_PATH=/path/to/facebook_session
INSTAGRAM_SESSION_PATH=/path/to/instagram_session

# Twitter API (Tweepy)
TWITTER_BEARER_TOKEN=your_bearer_token
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_SECRET=your_access_secret

# AI Employee
VAULT_PATH=/path/to/AI_Employee_Vault
DRY_RUN=true  # Set to false for production
```

## Project Structure

```
hackhathon_AI_Employee/
├── .claude/skills/             # 34 custom Agent Skills
│   ├── check-gmail/            #   Monitor Gmail
│   ├── check-linkedin/         #   Monitor LinkedIn
│   ├── check-whatsapp/         #   Monitor WhatsApp
│   ├── check-facebook/         #   Monitor Facebook
│   ├── check-instagram/        #   Monitor Instagram
│   ├── check-twitter/          #   Monitor Twitter
│   ├── post-linkedin/          #   Post to LinkedIn
│   ├── post-twitter/           #   Post tweets
│   ├── post-facebook/          #   Post to Facebook
│   ├── post-instagram/         #   Post to Instagram
│   ├── send-email/             #   Send email with approval
│   ├── odoo-accounting/        #   Odoo ERP operations
│   ├── ceo-briefing/           #   Weekly business report
│   ├── process-inbox/          #   Process vault inbox
│   ├── scan-inbox/             #   Scan for new files
│   ├── complete-task/          #   Mark tasks done
│   ├── create-plan/            #   Generate Plan.md
│   ├── manage-schedule/        #   Manage cron jobs
│   ├── check-status/           #   System health
│   └── update-dashboard/       #   Refresh Dashboard.md
├── watchers/                   # Perception Layer
│   ├── base_watcher.py         #   Abstract base class
│   ├── gmail_watcher.py        #   Gmail API (OAuth2)
│   ├── twitter_watcher.py      #   Tweepy v2
│   ├── filesystem_watcher.py   #   watchdog library
│   ├── whatsapp_watcher.py     #   Playwright
│   ├── linkedin_watcher.py     #   API + linkedin-api
│   ├── linkedin_poster.py      #   Playwright posting
│   ├── facebook_watcher.py     #   Playwright
│   ├── instagram_watcher.py    #   Playwright
│   ├── facebook_poster.py      #   Playwright posting
│   ├── instagram_poster.py     #   Playwright posting
│   ├── twitter_poster.py       #   Tweepy posting
│   └── whatsapp_watcher.py     #   Playwright + QR login
├── mcp_servers/                # Action Layer
│   ├── email_server.py         #   Gmail send/draft MCP
│   └── odoo_server.py          #   Odoo 19 JSON-RPC MCP
├── scheduler/                  # Orchestration
│   ├── scheduler.py            #   Cron job management
│   └── tasks/
│       ├── morning_briefing.py #   Daily summary
│       ├── ceo_briefing.py     #   Weekly CEO report
│       ├── weekly_report.py    #   Week summary
│       └── update_dashboard.py #   Dashboard refresh
├── utils/                      # Reliability Layer
│   ├── audit_logger.py         #   JSON action logging
│   ├── error_recovery.py       #   Retry, graceful degradation
│   ├── ralph_wiggum.py         #   Autonomous task loops
│   └── plan_creator.py         #   Plan.md generation
├── AI_Employee_Vault/          # Obsidian vault (symlink)
├── AGENTS.md                   # Detailed architecture docs
├── CLAUDE.MD                   # Claude Code project config
├── pyproject.toml              # Python project config
└── main.py                     # Entry point (placeholder)
```

## Vault Structure

```
AI_Employee_Vault/
├── Inbox/                  # Drop zone for new items
├── Needs_Action/           # Watchers write here, Claude reads here
├── In_Progress/            # Tasks being worked on
├── Pending_Approval/       # HITL approval queue
├── Approved/               # Human-approved actions
├── Rejected/               # Human-rejected actions
├── Done/                   # Completed tasks
├── Plans/                  # Claude's task plans
├── Briefings/              # CEO and morning briefings
├── Reports/                # Generated reports
├── Logs/                   # JSON audit logs (90-day retention)
├── State/                  # Ralph Wiggum loop state
├── Offline_Queue/          # Queued actions during outages
├── Dashboard.md            # Real-time status
├── Company_Handbook.md     # Rules of engagement
└── Business_Goals.md       # KPIs and targets
```

## Key Features

### Agent Skills
All AI functionality is implemented as [Claude Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview). Invoke them directly:
- `/check-gmail` — Fetch and triage new emails
- `/check-status` — See what's pending across all folders
- `/ceo-briefing` — Generate weekly business report
- `/send-email` — Compose and send with approval
- `/odoo-accounting` — Manage invoices, payments, customers

### Human-in-the-Loop
Sensitive actions create approval files in `/Pending_Approval/`. Review in Obsidian, then:
- Move to `/Approved/` to execute
- Move to `/Rejected/` to cancel

Auto-approve thresholds are configured in `Company_Handbook.md`.

### CEO Briefing
Weekly business audit combining:
- Odoo financial data (revenue, invoices, payments)
- Task completion metrics from vault
- Communication stats across platforms
- Bottleneck identification
- Proactive cost-saving suggestions

### Error Recovery
- Exponential backoff retry for transient API failures
- Graceful degradation with offline queuing
- Service health monitoring
- Watchdog process management

## Running

### Individual Components
```bash
# Start a watcher
uv run python watchers/gmail_watcher.py

# Generate a briefing
uv run python scheduler/tasks/ceo_briefing.py

# Start the scheduler
uv run python scheduler/scheduler.py start
```

### Frontend + API Bridge
```bash
# Terminal 1: start FastAPI bridge for frontend
uv run uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: start Next.js frontend
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Frontend expects these API routes on `http://localhost:8000`:
- `GET /healthz`
- `GET /api/executive/summary`
- `GET /api/accounting/summary`
- `GET /api/execution/monitor`
- `GET /api/oversight/queue`
- `GET /api/compliance/panel`
- `GET /api/system/monitor`
- `GET /api/system/health`
- `GET /api/tasks`
- `GET /api/tasks/{task_id}`
- `GET /api/approvals`
- `GET /api/approvals/{approval_id}`
- `GET /api/logs`
- `GET /api/briefings`
- `GET /api/briefings/{briefing_id}`
- `GET /api/watchers`
- `WS /ws/events`
- `POST /api/approvals/{approval_id}/approve`
- `POST /api/approvals/{approval_id}/reject`
- `POST /api/watchers/{watcher_name}/start`
- `POST /api/watchers/{watcher_name}/stop`
- `POST /api/watchers/{watcher_name}/restart`

Useful query params:
- `/api/tasks?limit=50&priority=high&status=pending&type=email`
- `/api/approvals?limit=25&riskLevel=high&min_amount=100`
- `/api/logs?channel=payment&date_from=2026-02-01&date_to=2026-02-22&limit=200`

Frontend polls live API every ~8-12 seconds with no runtime mock fallback.

### With PM2 (Recommended for Always-On)
```bash
npm install -g pm2

pm2 start watchers/gmail_watcher.py --interpreter python3
pm2 start watchers/twitter_watcher.py --interpreter python3
pm2 start scheduler/scheduler.py --interpreter python3 -- start

pm2 save
pm2 startup
```

### Platinum Cloud Stack (VM)
```bash
# Security gate (must pass before cloud start)
bash scripts/cloud/cloud_security_guard.sh

# Start 24/7 cloud watchers + draft worker + git sync
bash scripts/cloud/start_cloud_stack.sh

# Monitor
pm2 status
pm2 logs cloud-draft-worker
```

### Platinum Local Executive Agent
```bash
# Start local final-approval + execution agent
bash scripts/local/start_local_executive.sh

# Monitor
pm2 status
pm2 logs local-executive-agent
```

### Via Claude Code Skills
```bash
# In Claude Code session:
/check-gmail
/check-status
/ceo-briefing
/send-email
```

## Security

- **Credentials**: All secrets in `.env`, never committed (`.gitignore`)
- **HITL**: Payments, new contacts, and bulk operations require human approval
- **Audit Trail**: Every action logged as structured JSON
- **Dry Run**: `DRY_RUN=true` prevents real external actions during development
- **Sandboxing**: Playwright sessions isolated per platform
- **Rotation**: Credentials should be rotated monthly

## Gold Tier Checklist

| # | Requirement | Status |
|---|-------------|--------|
| 1 | All Silver requirements | Done (validated via `final_silver` evidence pack) |
| 2 | Full cross-domain integration (Personal + Business) | Done (validated via `final_gold` evidence pack) |
| 3 | Odoo accounting via MCP (JSON-RPC, Odoo 19+) | Partial (strict self-hosted local Odoo proof pending) |
| 4 | Facebook + Instagram integration | Done (posting + summary workflow validated in DRY_RUN) |
| 5 | Twitter (X) integration | Done (Tweepy v2) |
| 6 | Multiple MCP servers | Done (Email + Odoo) |
| 7 | Weekly CEO Briefing + Business Audit | Done (generator implemented and outputs present) |
| 8 | Error recovery + graceful degradation | Done |
| 9 | Comprehensive audit logging | Done |
| 10 | Ralph Wiggum autonomous loop | Done (hook + file-completion strategy validated) |
| 11 | Documentation | This README + AGENTS.md |
| 12 | All AI as Agent Skills | Done (34 skills) |

## Platinum Tier Checklist

| # | Requirement | Status |
|---|-------------|--------|
| 1 | Run AI Employee on cloud 24/7 | Partial (runbook defined; deployment proof pending) |
| 2 | Work-zone specialization (Cloud draft-only, Local final actions) | Partial (policy documented; enforcement hardening pending) |
| 3 | Synced vault delegation with claim-by-move and single-writer dashboard | Partial (folders exist; distributed-ops proof pending) |
| 4 | Secrets excluded from vault sync | Done (gitignore + policy documented) |
| 5 | Odoo on cloud VM with HTTPS/backups/health monitoring | Partial (runbook defined; production evidence pending) |
| 6 | Optional A2A phase 2 path | Done (documented migration path) |
| 7 | Platinum demo gate (cloud draft while local offline, local approve+execute) | Partial (script scaffold added; live demo evidence pending) |

## Lessons Learned

1. **File-based communication works well** — markdown files in a shared vault are easy to debug, inspect in Obsidian, and version with git
2. **HITL is non-negotiable for money** — never auto-approve payments to new recipients
3. **Playwright-based watchers are fragile** — API-based integrations (Gmail, Twitter) are far more reliable than browser automation (WhatsApp, Facebook)
4. **Skills make Claude reusable** — packaging each capability as a skill with clear instructions made the system modular
5. **Logging early saves debugging time** — structured JSON logs from day 1 made it easy to trace issues

## Submission Evidence

Evidence artifacts for hackathon/demo validation are stored in `evidence_pack/`.

- Command outputs: `evidence_pack/outputs/`
- Workflow logs/artifacts: `evidence_pack/logs/`
- Summary and checklist: `evidence_pack/README.md`

### Notes on Self-Hosted Odoo Proof

- Odoo MCP integration and accounting workflows are evidenced in the output/log files.
- For strict "self-hosted local Odoo" confirmation, include one additional proof in `evidence_pack/screenshots/`:
  - local Odoo service running on port `8069`, and/or
  - Odoo UI screenshot from your local instance showing created invoice/payment records.

### One-Command Gold Finalization

Run the script below to generate a strict Gold evidence pack (including self-hosted checks):

```bash
bash scripts/finalize_gold.sh
```

It creates a timestamped folder at `evidence_pack/final_gold_YYYYMMDD_HHMMSS/` with:
- command outputs
- copied logs/artifacts
- requirement-wise pass/partial summary in `README.md`

### One-Command Platinum Finalization

Run the script below to generate a Platinum readiness evidence pack:

```bash
bash scripts/finalize_platinum.sh
```

It creates a timestamped folder at `evidence_pack/final_platinum_YYYYMMDD_HHMMSS/` with:
- requirement-wise Platinum checks
- cloud/local runbook coverage checks
- demo-gate attempt logs and summary

### One-Command Silver Finalization

Run the script below to generate a strict Silver evidence pack:

```bash
bash scripts/finalize_silver.sh
```

It creates a timestamped folder at `evidence_pack/final_silver_YYYYMMDD_HHMMSS/` with:
- requirement-wise checks
- command outputs
- pass/partial summary in `README.md`

## Author

Built for Personal AI Employee Hackathon 0 by Aqsa Gull.

---

*A Digital FTE works 8,760 hours/year vs a human's 2,000, at 85-90% cost savings.*
