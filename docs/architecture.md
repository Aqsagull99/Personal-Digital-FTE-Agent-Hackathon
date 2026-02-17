# Architecture Documentation

This project follows a local-first agent architecture with three layers:

1. Perception (watchers)
2. Reasoning (Claude Code + skills)
3. Action (MCP servers + automation scripts)

## System Flow

External sources (Gmail, WhatsApp, LinkedIn, Twitter/X, Facebook, Instagram, local files) are monitored by watcher scripts.  
Watchers write structured markdown tasks into the Obsidian vault, primarily in `/Needs_Action/`.

Claude Code reads those files, applies business rules from the vault (`Company_Handbook.md`, `Business_Goals.md`), and decides next actions:

- Execute directly for low-risk operations
- Create approval requests in `/Pending_Approval/` for sensitive operations

Approved tasks are executed through MCP servers or platform-specific posters, then archived to `/Done/` with audit logs.

## Layers

## 1) Perception Layer

Primary watcher location: `watchers/`

- `gmail_watcher.py`: Gmail polling via OAuth APIs
- `twitter_watcher.py`: Twitter/X monitoring
- `filesystem_watcher.py`: Local file-triggered tasks
- `whatsapp_watcher.py`, `linkedin_watcher.py`, `facebook_watcher.py`, `instagram_watcher.py`: Browser/API-based monitoring

Output format is markdown with YAML frontmatter, enabling consistent downstream processing.

## 2) Reasoning Layer

Claude Code + skills in `.claude/skills/` provide:

- Inbox processing
- Task planning
- Approval file generation
- Briefing/report generation
- Operational checks and workflows

Key pattern: Claude reasons over files in the vault instead of direct DB state, making the workflow transparent and auditable.

## 3) Action Layer

MCP servers:

- `mcp_servers/email_server.py`: email actions (draft/send/contact workflows)
- `mcp_servers/odoo_server.py`: Odoo accounting operations

Social posting actions also use Playwright/Tweepy poster scripts in `watchers/` when MCP is not used for that channel.

## Human-in-the-Loop Safety

Sensitive actions are routed through:

`/Pending_Approval/` -> `/Approved/` or `/Rejected/` -> execution -> `/Done/`

This avoids unsafe autonomous execution for high-risk operations such as financial updates and outbound communications.

## Persistence and Reliability

- Retry/degradation helpers: `utils/error_recovery.py`
- Audit logs: `utils/audit_logger.py` and vault log files
- Long-running completion loop: `utils/ralph_wiggum.py`
- Scheduled operations: `scheduler/` tasks (briefings, dashboard refresh, weekly reports)

## Vault-Centric Design

Obsidian vault folders provide operational state:

- `/Needs_Action/`
- `/In_Progress/`
- `/Pending_Approval/`
- `/Approved/`
- `/Rejected/`
- `/Done/`
- `/Plans/`, `/Briefings/`, `/Reports/`, `/Logs/`

This design keeps state human-readable and easy to inspect during development and demos.
