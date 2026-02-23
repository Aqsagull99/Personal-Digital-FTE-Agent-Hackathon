#!/usr/bin/env bash
set -euo pipefail

# Watchdog: monitor watcher/services and restart if down.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

VAULT_PATH="${VAULT_PATH:-$ROOT_DIR/AI_Employee_Vault}"
if [[ -L "$VAULT_PATH" ]]; then
  VAULT_PATH="$(readlink -f "$VAULT_PATH")"
fi
LOG_DIR="$VAULT_PATH/Logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/cloud_watchdog_$(date +%F).log"

WATCH_APPS=(
  "cloud-gmail-watcher"
  "cloud-twitter-watcher"
  "cloud-facebook-watcher"
  "cloud-instagram-watcher"
  "cloud-draft-worker"
  "cloud-odoo-mcp"
  "cloud-git-sync"
)

check_online() {
  local app="$1"
  pm2 describe "$app" 2>/dev/null | grep -q "status[[:space:]]*online"
}

log() {
  echo "$(date -Is) $*" | tee -a "$LOG_FILE"
}

log "WATCHDOG_START interval=${WATCHDOG_INTERVAL_SECONDS:-30}s"
while true; do
  for app in "${WATCH_APPS[@]}"; do
    if ! check_online "$app"; then
      log "RESTART app=$app reason=not_online"
      pm2 restart "$app" >/dev/null 2>&1 || log "RESTART_FAIL app=$app"
    fi
  done

  # Odoo HTTP health probe (if URL configured)
  if [[ -n "${ODOO_URL:-}" ]]; then
    if ! curl -fsS "${ODOO_URL%/}/web/health" >/dev/null 2>&1; then
      log "ODOO_HEALTH_WARN url=${ODOO_URL} endpoint=/web/health"
    fi
  fi

  sleep "${WATCHDOG_INTERVAL_SECONDS:-30}"
done

