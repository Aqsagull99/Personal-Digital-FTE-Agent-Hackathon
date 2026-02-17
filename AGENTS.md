# Personal AI Employee - Agent Architecture

## What This Is

A local-first, autonomous Digital FTE (Full-Time Equivalent) that manages personal and business affairs 24/7. Instead of waiting for commands, it **proactively** monitors Gmail, WhatsApp, LinkedIn, Twitter, Facebook, and Instagram — then reasons about what needs doing, plans actions, and executes them with human approval for sensitive operations.

The system uses **Claude Code** as its brain, **Obsidian** as its memory/dashboard, and **file-based communication** as the coordination protocol between all components.

## Core Architecture: Perception → Reasoning → Action

```
External World          Watchers (Python)         Obsidian Vault           Claude Code            MCP Servers
─────────────          ─────────────────         ──────────────           ───────────            ───────────
Gmail API        ───►  gmail_watcher.py    ───►  /Needs_Action/*.md ───► Read + Reason    ───►  email_server.py
WhatsApp Web     ───►  whatsapp_watcher.py ───►  /Needs_Action/*.md ───► Create Plan.md   ───►  odoo_server.py
LinkedIn         ───►  linkedin_watcher.py ───►  /Needs_Action/*.md ───► Request Approval
Twitter API      ───►  twitter_watcher.py  ───►  /Needs_Action/*.md ───► Execute via MCP
Facebook Web     ───►  facebook_watcher.py ───►  /Needs_Action/*.md ───► Move to /Done
Instagram Web    ───►  instagram_watcher.py───►  /Needs_Action/*.md
Local Files      ───►  filesystem_watcher.py──►  /Needs_Action/*.md
```

## The Three Layers

### 1. Perception Layer (Watchers)

Lightweight Python scripts that run continuously, polling external sources for new data. When something relevant arrives, they write a structured markdown file into `/Needs_Action/` in the Obsidian vault.

All watchers inherit from `BaseWatcher` (`watchers/base_watcher.py`) which provides:
- Configurable polling intervals
- Structured logging
- Vault directory management
- Error handling with retry

| Watcher | Source | Method | Check Interval | Status |
|---------|--------|--------|----------------|--------|
| `gmail_watcher.py` | Gmail API | OAuth2 REST API | 120s | **Working** - tested with real emails |
| `twitter_watcher.py` | Twitter/X | Tweepy v2 API | 60s | **Working** - API integrated |
| `filesystem_watcher.py` | Local folders | watchdog library | Real-time | **Working** - file drop detection |
| `whatsapp_watcher.py` | WhatsApp Web | Playwright browser | 30s | **Scaffolded** - needs QR login |
| `linkedin_watcher.py` | LinkedIn | API + linkedin-api | 120s | **Partial** - API path works, message stubs |
| `facebook_watcher.py` | Facebook | Playwright browser | 120s | **Scaffolded** - needs browser session |
| `instagram_watcher.py` | Instagram | Playwright browser | 120s | **Scaffolded** - needs browser session |

**Watcher output format** — each watcher creates markdown files with YAML frontmatter:
```markdown
---
type: email
from: sender@example.com
subject: Invoice Request
received: 2026-02-13T10:30:00Z
priority: high
status: pending
---

## Email Content
Client asking for January invoice...

## Suggested Actions
- [ ] Reply to sender
- [ ] Generate invoice
```

### 2. Reasoning Layer (Claude Code + Skills)

Claude Code is the brain. It reads the vault, understands context from `Company_Handbook.md` and `Business_Goals.md`, and decides what to do. All AI capabilities are packaged as **Agent Skills** (`.claude/skills/*/SKILL.md`).

**Skill categories:**

| Category | Skills | What They Do |
|----------|--------|-------------|
| **Monitoring** | check-gmail, check-linkedin, check-whatsapp, check-facebook, check-instagram, check-twitter | Invoke watchers and process results |
| **Posting** | post-linkedin, post-twitter, post-facebook, post-instagram | Create content with approval workflow |
| **Actions** | send-email, complete-task, process-inbox, scan-inbox | Execute tasks via MCP servers |
| **Planning** | create-plan, ceo-briefing, manage-schedule | Generate plans, reports, schedules |
| **Operations** | check-status, update-dashboard, odoo-accounting | System health, vault updates, ERP |

**Reasoning flow:**
1. Skill triggers Claude to read `/Needs_Action/` files
2. Claude consults `Company_Handbook.md` for rules (e.g., "flag payments over $500")
3. Claude creates a `Plan.md` with checkboxes for multi-step tasks
4. For sensitive actions → writes approval request to `/Pending_Approval/`
5. For safe actions → executes directly via MCP, moves to `/Done/`

### 3. Action Layer (MCP Servers)

MCP (Model Context Protocol) servers are Claude's hands for interacting with external systems.

| Server | File | Capabilities | Status |
|--------|------|-------------|--------|
| **Email MCP** | `mcp_servers/email_server.py` | send_email, create_draft, add_known_contact, process_approved | **Working** - Gmail API with OAuth |
| **Odoo MCP** | `mcp_servers/odoo_server.py` | create_invoice, record_payment, manage_customers, weekly_audit, financial_summary | **Working** - connected to Odoo 19 cloud |

**Social media actions** use Playwright-based poster scripts instead of MCP:
- `watchers/linkedin_poster.py` — Post to LinkedIn
- `watchers/twitter_poster.py` — Post tweets via Tweepy
- `watchers/social_poster.py` — Post to Facebook/Instagram

## Human-in-the-Loop (HITL) Approval

The safety mechanism. Any sensitive action creates an approval file instead of executing directly.

```
Claude detects action needed
        │
        ▼
Is it sensitive? ──── No ──── Execute directly
        │
       Yes
        │
        ▼
Write to /Pending_Approval/
        │
        ▼
Human reviews in Obsidian
        │
   ┌────┴────┐
   ▼         ▼
/Approved  /Rejected
   │
   ▼
MCP executes action
   │
   ▼
Move to /Done + Log
```

**Auto-approve thresholds** (from Company_Handbook.md):
| Action | Auto-Approve | Needs Approval |
|--------|-------------|----------------|
| Email replies | Known contacts | New contacts, bulk sends |
| Payments | < $50 recurring | New payees, > $100 |
| Social posts | Scheduled posts | Replies, DMs |
| File operations | Create, read | Delete, move outside vault |

## Persistence: The Ralph Wiggum Loop

For multi-step tasks that Claude needs to complete autonomously, the Ralph Wiggum pattern (`utils/ralph_wiggum.py`) keeps Claude working until done.

**How it works:**
1. Orchestrator creates a state file with the task prompt
2. Claude processes the task
3. When Claude tries to exit, the Stop hook checks completion
4. If not done → re-inject prompt, Claude continues
5. If done (promise string found or task file in `/Done/`) → allow exit

**Two completion strategies:**
- **Promise-based**: Claude outputs `<promise>TASK_COMPLETE</promise>`
- **File movement**: Stop hook detects task file moved to `/Done/`

## Orchestration & Scheduling

`scheduler/scheduler.py` manages recurring tasks via system cron:

| Task | Script | Schedule | Purpose |
|------|--------|----------|---------|
| Morning Briefing | `scheduler/tasks/morning_briefing.py` | Daily 8 AM | Summarize vault state |
| CEO Briefing | `scheduler/tasks/ceo_briefing.py` | Sunday 8 PM | Weekly business audit |
| Dashboard Update | `scheduler/tasks/update_dashboard.py` | Every 30 min | Refresh Dashboard.md |
| Weekly Report | `scheduler/tasks/weekly_report.py` | Friday 5 PM | Week summary |

## Reliability

### Error Recovery (`utils/error_recovery.py`)
- `@with_retry` — Exponential backoff for transient failures (API timeouts, rate limits)
- `@graceful` — Graceful degradation decorator that queues failed actions for later
- `OfflineQueue` — Stores actions when services are down, replays when restored
- `ServiceHealthMonitor` — Tracks service health status

### Audit Logging (`utils/audit_logger.py`)
Every action logged to `/Vault/Logs/YYYY-MM-DD.json`:
```json
{
  "timestamp": "2026-02-13T10:30:00Z",
  "action_type": "email_send",
  "actor": "claude_code",
  "target": "client@example.com",
  "approval_status": "approved",
  "result": "success"
}
```
Logs retained for 90 days minimum.

## Vault Structure (Obsidian)

```
AI_Employee_Vault/
├── Inbox/                  # Drop zone — files land here first
├── Needs_Action/           # Watchers write here, Claude reads here
├── In_Progress/            # Tasks currently being worked on
├── Pending_Approval/       # HITL — awaiting human review
├── Approved/               # Human approved — ready for execution
├── Rejected/               # Human rejected
├── Done/                   # Completed tasks (archive)
├── Plans/                  # Claude's multi-step plans
├── Briefings/              # CEO and morning briefings
├── Reports/                # Generated reports
├── Logs/                   # JSON audit logs
├── State/                  # Ralph Wiggum loop state files
├── Offline_Queue/          # Queued actions for degraded mode
├── Dashboard.md            # Real-time status overview
├── Company_Handbook.md     # Rules and thresholds
├── Business_Goals.md       # KPIs and targets
└── known_contacts.json     # Auto-approve contact list
```

## File Flow

A typical task moves through folders like this:

```
External event → Watcher → /Inbox or /Needs_Action
                                    │
                           Claude reads + plans
                                    │
                    ┌───────────────┼────────────────┐
                    ▼               ▼                 ▼
              /Plans/*.md    /Pending_Approval/   Direct action
                                    │
                              Human decision
                              ┌─────┴─────┐
                              ▼           ▼
                         /Approved    /Rejected
                              │
                         MCP executes
                              │
                         /Done/*.md + /Logs/*.json
```

## Tech Stack

| Component | Technology | Role |
|-----------|-----------|------|
| Brain | Claude Code (Sonnet/Opus) | Reasoning, planning, decision-making |
| Memory/GUI | Obsidian (local markdown) | Dashboard, knowledge base, file-based workflow |
| Watchers | Python 3.13 + watchdog/Playwright/APIs | Monitor external sources |
| MCP Servers | Python (Gmail API, Odoo JSON-RPC) | Execute external actions |
| Browser Automation | Playwright | WhatsApp, LinkedIn, Facebook, Instagram |
| Scheduling | python-crontab + system cron | Recurring tasks |
| Process Management | PM2 (recommended) | Keep watchers alive 24/7 |
| Version Control | Git | Vault and code versioning |
| ERP | Odoo 19 Community (cloud) | Accounting, invoices, payments |
