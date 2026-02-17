# Platinum Runbook

This runbook defines how to operate the AI Employee at Platinum tier using a Cloud agent and a Local executive agent.

## Goal

Move from local-first Gold operation to an always-on dual-agent model:

- Cloud agent: 24/7 monitoring and draft generation
- Local agent: approval authority and sensitive execution

## 1. Cloud 24/7 Deployment

Run cloud components continuously on a VM (Oracle/AWS/etc.):

- Watchers for non-sensitive channels
- Scheduler tasks
- Health checks and restart policy
- Audit logging to vault-compatible markdown/JSON outputs

Recommended controls:

- process supervisor (`pm2` or `systemd`)
- uptime alerting
- disk and memory monitoring
- daily backup of runtime logs

## 2. Work-Zone Specialization

Cloud owns (draft-only):

- email triage and draft replies
- social draft creation and scheduling suggestions
- non-sensitive classification/planning

Local owns (final authority):

- all approvals
- WhatsApp session operations
- payments/banking actions
- final send/post execution
- dashboard merge/write authority

Rule: Cloud must not directly execute final send/post/payment operations.

## 3. Synced Vault Delegation (Phase 1)

Use a synced vault path layout:

- `/Needs_Action/<domain>/`
- `/Plans/<domain>/`
- `/Pending_Approval/<domain>/`
- `/In_Progress/<agent>/`
- `/Updates/` (Cloud writes status updates)

Mandatory coordination rules:

1. Claim-by-move:
   first agent that moves an item from `/Needs_Action` to `/In_Progress/<agent>/` owns it.
2. Single-writer dashboard:
   only Local writes `Dashboard.md`.
3. Update merge flow:
   Cloud writes to `/Updates/`; Local merges to dashboard.

## 4. Vault Sync Security Boundaries

Only sync markdown/state artifacts required for collaboration.

Never sync:

- `.env`
- OAuth tokens
- browser session folders
- payment/banking credentials
- any private keys

Enforce with `.gitignore` and sync-tool ignore rules.

## 5. Odoo Cloud VM Operations

Platinum expectation includes Odoo on cloud with:

- HTTPS endpoint
- backup policy
- service health monitoring
- Local approval before posting invoices/payments

Cloud agent may prepare accounting drafts, but Local performs final approval/posting actions.

## 6. Optional A2A Upgrade (Phase 2)

After stable file-based delegation, optional direct A2A messaging can replace part of handoffs.  
Vault files remain the source of truth for audit history.

## 7. Platinum Demo Gate (Minimum Passing)

Required scenario:

1. Local agent is offline.
2. New email arrives.
3. Cloud agent triages and creates draft + approval file.
4. Local returns and reviews approval.
5. Local approves and executes send via MCP.
6. Action is logged and task moves to `/Done`.

## 8. Evidence Checklist

Capture for submission:

- cloud uptime proof (service status or screenshots)
- synced vault flow proof (claim-by-move artifact trail)
- approval workflow proof (pending -> approved -> done)
- audit log entries for demo action
- Odoo cloud security/health proof (HTTPS, backups, health checks)
