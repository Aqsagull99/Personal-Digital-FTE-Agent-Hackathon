#!/usr/bin/env bash
set -euo pipefail

pm2 delete cloud-gmail-watcher 2>/dev/null || true
pm2 delete cloud-twitter-watcher 2>/dev/null || true
pm2 delete cloud-facebook-watcher 2>/dev/null || true
pm2 delete cloud-instagram-watcher 2>/dev/null || true
pm2 delete cloud-draft-worker 2>/dev/null || true
pm2 delete cloud-odoo-mcp 2>/dev/null || true
pm2 delete cloud-odoo-health 2>/dev/null || true
pm2 delete cloud-git-sync 2>/dev/null || true
pm2 delete cloud-watchdog 2>/dev/null || true

echo "[cloud] Cloud stack stopped."
