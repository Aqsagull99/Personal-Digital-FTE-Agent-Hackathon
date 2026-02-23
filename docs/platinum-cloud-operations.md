# Platinum Cloud Operations

This setup configures cloud-side behavior for Platinum tier:

1. Run Gmail + Social watchers 24/7 on VM
2. Enforce draft-only output in `/Needs_Action/cloud/`
3. Enforce claim-by-move to `/In_Progress/cloud/`
4. Guard against blocked sensitive data on cloud
5. Sync vault state with local machine via Git
6. Run Odoo Community on cloud with HTTPS + health checks
7. Enforce cloud Odoo draft-only finance behavior

## Components Added

- `scripts/cloud/ecosystem.cloud.cjs`: PM2 app definitions
- `scripts/cloud/cloud_draft_worker.py`: draft-only + claim-by-move worker
- `scripts/cloud/cloud_security_guard.sh`: sensitive-data policy guard
- `scripts/cloud/cloud_git_sync.sh`: Git sync loop for vault paths
- `scripts/cloud/odoo_mcp_cloud_service.py`: cloud Odoo MCP draft worker + health loop
- `scripts/cloud/watchdog_watchers.sh`: watcher watchdog auto-restart
- `scripts/cloud/docker-compose.odoo-cloud.yml`: Odoo+Postgres+Caddy HTTPS stack
- `scripts/cloud/setup_odoo_cloud.sh`: one-command Odoo cloud deployment bootstrap
- `scripts/cloud/odoo_health_monitor.sh`: periodic Odoo HTTP health monitor
- `scripts/cloud/start_cloud_stack.sh`: one-command start
- `scripts/cloud/stop_cloud_stack.sh`: one-command stop

## Runbook

## 1) Preflight

Install PM2 if missing:

```bash
npm install -g pm2
```

Ensure repository remote is configured and authenticated:

```bash
git remote -v
```

## 2) Security Gate

Run:

```bash
bash scripts/cloud/cloud_security_guard.sh
```

This fails if blocked artifacts exist (for example `.whatsapp_session`).

## 3) Start 24/7 Cloud Stack

```bash
bash scripts/cloud/start_cloud_stack.sh
pm2 status
```

Apps started:

- cloud-gmail-watcher
- cloud-twitter-watcher
- cloud-facebook-watcher
- cloud-instagram-watcher
- cloud-draft-worker
- cloud-odoo-mcp
- cloud-odoo-health
- cloud-git-sync
- cloud-watchdog

## 4) Draft-Only Rule

`cloud_draft_worker.py` behavior:

- Reads `AI_Employee_Vault/Needs_Action/*.md`
- Claims by move to `AI_Employee_Vault/In_Progress/cloud/`
- Creates draft file in `AI_Employee_Vault/Needs_Action/cloud/`

No direct send/post actions are executed by this worker.

## 5) Odoo Cloud Deployment (HTTPS + Health)

Set environment variables and run setup:

```bash
export POSTGRES_PASSWORD='change_this_strong_password'
export ODOO_DOMAIN='odoo.yourdomain.com'
export ODOO_EMAIL='you@example.com'
bash scripts/cloud/setup_odoo_cloud.sh
```

This deploys:

- `odoo:19`
- `postgres:15`
- `caddy:2` with automatic TLS
- container healthcheck for Odoo

## 6) Odoo MCP Draft-Only Rule (Cloud)

Cloud processes only `ODOO_DRAFT_INVOICE_*.md` tasks from `/Needs_Action/cloud/`.

- Cloud can create **draft invoices only**
- Cloud cannot directly post invoices
- Cloud cannot directly process payments

Runtime enforcement:

- `AGENT_ROLE=cloud`
- `CLOUD_DRAFT_ONLY=true`

## 7) Local Approval for Posting/Payments

Posting invoices and processing payments are Local Executive responsibilities.
For posting, use approval files:

- `ODOO_POST_INVOICE_*.md` -> move to `/Approved/` -> Local executes

Payment approvals remain:

- `ODOO_PAYMENT_*.md` -> move to `/Approved/` -> Local executes

## 5) Git Vault Sync

`cloud_git_sync.sh` syncs only vault state paths and pushes to `origin/main`.
Local machine should periodically pull:

```bash
git pull --rebase origin main
```

## 8) Git Vault Sync

`cloud_git_sync.sh` syncs only vault state paths and pushes to `origin/main`.
Local machine should periodically pull:

```bash
git pull --rebase origin main
```

## 9) Stop Stack

```bash
bash scripts/cloud/stop_cloud_stack.sh
```
