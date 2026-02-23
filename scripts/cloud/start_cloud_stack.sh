#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[cloud] Running sensitive-data guard..."
bash scripts/cloud/cloud_security_guard.sh

echo "[cloud] Starting PM2 cloud stack..."
pm2 start scripts/cloud/ecosystem.cloud.cjs
pm2 save

echo
echo "[cloud] Stack started."
echo "Use: pm2 status"
echo "Logs: pm2 logs cloud-draft-worker"
