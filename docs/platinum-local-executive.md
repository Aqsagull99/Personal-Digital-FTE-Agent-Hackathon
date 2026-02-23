# Platinum Local Executive Agent

This local agent is the final authority in Platinum mode.

## Responsibilities Implemented

1. Monitor synced vault queues:
   - `AI_Employee_Vault/Pending_Approval/`
   - `AI_Employee_Vault/Needs_Action/cloud/`
2. Enforce single-writer dashboard:
   - lock file: `AI_Employee_Vault/State/dashboard_writer.lock`
   - merge updates from `AI_Employee_Vault/Updates/`
   - write master `Dashboard.md` locally
3. Local ownership of sensitive execution:
   - WhatsApp session actions (`WHATSAPP_REPLY_*.md`)
   - final approved actions via orchestrator (`main.process_approved`)
4. Approval workflow execution:
   - after files are moved to `/Approved/`, local agent executes corresponding actions

## Files Added

- `scripts/local/local_executive_agent.py`
- `scripts/local/ecosystem.local.cjs`
- `scripts/local/start_local_executive.sh`
- `scripts/local/stop_local_executive.sh`

## Start

```bash
npm install -g pm2
bash scripts/local/start_local_executive.sh
pm2 status
```

## Stop

```bash
bash scripts/local/stop_local_executive.sh
```

## WhatsApp Approval File Format

To execute a WhatsApp final reply, place a file in `/Approved/` named like:

`WHATSAPP_REPLY_<anything>.md`

Frontmatter example:

```markdown
---
type: whatsapp_reply_approval
phone: +923001234567
message: Thanks, approved from Local Executive.
status: approved
---
```

The local agent uses local `.whatsapp_session` to send and then moves file to `/Done/` on success.
