# Platinum Odoo Cloud Integration

This document covers the Odoo-specific Platinum requirements.

## Requirement Mapping

1. Deploy Odoo Community on Cloud VM with HTTPS and health monitoring  
2. Use MCP server integration via Odoo JSON-RPC/JSON-2 APIs  
3. Cloud agent is draft-only for accounting actions  
4. Local approval required for posting invoices and processing payments  
5. Watchdog restarts crashed watchers/services

## 1) Deploy Odoo + HTTPS

Files:

- `scripts/cloud/docker-compose.odoo-cloud.yml`
- `scripts/cloud/Caddyfile.odoo`
- `scripts/cloud/setup_odoo_cloud.sh`

Run:

```bash
export POSTGRES_PASSWORD='change_this_strong_password'
export ODOO_DOMAIN='odoo.yourdomain.com'
export ODOO_EMAIL='you@example.com'
bash scripts/cloud/setup_odoo_cloud.sh
```

Result:

- Odoo 19 container
- PostgreSQL container
- Caddy reverse proxy with automatic TLS certificates
- Built-in Odoo healthcheck

## 2) MCP on Cloud

Files:

- `mcp_servers/odoo_server.py`
- `scripts/cloud/odoo_mcp_cloud_service.py`

Cloud PM2 app: `cloud-odoo-mcp`

It continuously checks Odoo connectivity and processes only cloud draft invoice tasks.

## 3) Draft-Only Enforcement

Enforced in `mcp_servers/odoo_server.py` via environment role:

- `AGENT_ROLE=cloud`
- `CLOUD_DRAFT_ONLY=true`

Behavior:

- `create_invoice(..., require_approval=False)` creates draft invoice only
- `record_payment(..., require_approval=False)` blocked on cloud
- `post_invoice(..., require_approval=False)` blocked on cloud

## 4) Local Approval and Final Execution

Posting invoice flow:

1. Create `ODOO_POST_INVOICE_*.md` approval request
2. Human/Local moves file to `/Approved/`
3. Local executor runs `main.py process-approved` and posts invoice

Payment flow:

1. Create `ODOO_PAYMENT_*.md` approval request
2. Move to `/Approved/`
3. Local executor processes payment

## 5) Watchdog + Auto-Restart

File: `scripts/cloud/watchdog_watchers.sh`

PM2 app: `cloud-watchdog`

Monitors and restarts:

- cloud-gmail-watcher
- cloud-twitter-watcher
- cloud-facebook-watcher
- cloud-instagram-watcher
- cloud-draft-worker
- cloud-odoo-mcp
- cloud-git-sync

Also logs Odoo HTTP health warnings.
