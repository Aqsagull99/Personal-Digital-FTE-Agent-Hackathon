#!/usr/bin/env bash
set -euo pipefail

pm2 delete local-executive-agent 2>/dev/null || true
echo "[local] Local Executive Agent stopped."
