#!/usr/bin/env bash
set -euo pipefail

# Cloud security gate:
# - Block WhatsApp session artifacts on cloud
# - Block obvious banking token artifacts on cloud

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

VAULT_PATH="${VAULT_PATH:-$ROOT_DIR/AI_Employee_Vault}"
if [[ -L "$VAULT_PATH" ]]; then
  VAULT_PATH="$(readlink -f "$VAULT_PATH")"
fi

echo "[guard] root=$ROOT_DIR"
echo "[guard] vault=$VAULT_PATH"

status=0

# 1) WhatsApp browser/session data must never live on cloud.
if [[ -d ".whatsapp_session" ]]; then
  echo "[guard][ERROR] .whatsapp_session exists on cloud instance."
  status=1
fi

# 2) Detect likely banking/payment token artifacts.
mapfile -t matches < <(
  find "$ROOT_DIR" "$VAULT_PATH" \
    -type f \
    \( -iname "*bank*token*" -o -iname "*payment*token*" -o -iname "*wallet*token*" \) \
    2>/dev/null || true
)

if [[ "${#matches[@]}" -gt 0 ]]; then
  echo "[guard][ERROR] Found potential sensitive token artifacts:"
  for m in "${matches[@]}"; do
    echo "  - $m"
  done
  status=1
fi

if [[ "$status" -ne 0 ]]; then
  echo "[guard] FAILED: cloud-sensitive data policy violation."
  exit 1
fi

echo "[guard] OK: no blocked sensitive artifacts found."
