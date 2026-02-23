#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[local] Starting Local Executive Agent..."
pm2 start scripts/local/ecosystem.local.cjs
pm2 save

echo
echo "[local] Started."
echo "Use: pm2 status"
echo "Logs: pm2 logs local-executive-agent"
