#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

VAULT_PATH="${VAULT_PATH:-$ROOT_DIR/AI_Employee_Vault}"
if [[ -L "$VAULT_PATH" ]]; then
  VAULT_PATH="$(readlink -f "$VAULT_PATH")"
fi
LOG_DIR="$VAULT_PATH/Logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/odoo_health_$(date +%F).log"

if [[ -z "${ODOO_URL:-}" ]]; then
  echo "$(date -Is) ODOO_URL missing" | tee -a "$LOG_FILE"
  exit 1
fi

while true; do
  if curl -fsS "${ODOO_URL%/}/web/health" >/dev/null 2>&1; then
    echo "$(date -Is) ODOO_HEALTH ok url=${ODOO_URL}" >> "$LOG_FILE"
  else
    echo "$(date -Is) ODOO_HEALTH fail url=${ODOO_URL}" | tee -a "$LOG_FILE"
  fi
  sleep "${ODOO_HEALTH_INTERVAL_SECONDS:-60}"
done
