#!/usr/bin/env bash
set -euo pipefail

# Setup Odoo Community + HTTPS reverse proxy + health monitoring baseline on VM.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "[setup] Installing Docker..."
  sudo apt-get update
  sudo apt-get install -y ca-certificates curl gnupg
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

if ! groups | grep -q docker; then
  echo "[setup] Adding current user to docker group..."
  sudo usermod -aG docker "$USER"
  echo "[setup] Re-login required for docker group. Continue with sudo for now."
fi

: "${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD first}"
: "${ODOO_DOMAIN:?Set ODOO_DOMAIN first (e.g. odoo.example.com)}"
: "${ODOO_EMAIL:?Set ODOO_EMAIL first (Lets Encrypt email)}"

echo "[setup] Starting Odoo Cloud stack..."
sudo POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  ODOO_DOMAIN="$ODOO_DOMAIN" \
  ODOO_EMAIL="$ODOO_EMAIL" \
  docker compose -f scripts/cloud/docker-compose.odoo-cloud.yml up -d

echo "[setup] Stack started."
echo "[setup] Health:"
sudo docker compose -f scripts/cloud/docker-compose.odoo-cloud.yml ps
echo "[setup] Try: https://${ODOO_DOMAIN}"
