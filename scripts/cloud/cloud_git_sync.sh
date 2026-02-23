#!/usr/bin/env bash
set -euo pipefail

# Git-based vault state sync loop for cloud -> local collaboration.
# Cloud side: commits/pushes only vault state paths.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

BRANCH="${CLOUD_SYNC_BRANCH:-main}"
REMOTE="${CLOUD_SYNC_REMOTE:-origin}"
SLEEP_SECONDS="${CLOUD_SYNC_SECONDS:-60}"
GIT_USER_NAME="${CLOUD_GIT_USER_NAME:-Cloud Agent}"
GIT_USER_EMAIL="${CLOUD_GIT_USER_EMAIL:-cloud-agent@local}"

VAULT_PATH="${VAULT_PATH:-$ROOT_DIR/AI_Employee_Vault}"
if [[ -L "$VAULT_PATH" ]]; then
  VAULT_PATH="$(readlink -f "$VAULT_PATH")"
fi

SYNC_PATHS=(
  "AI_Employee_Vault/Needs_Action"
  "AI_Employee_Vault/In_Progress"
  "AI_Employee_Vault/Pending_Approval"
  "AI_Employee_Vault/Approved"
  "AI_Employee_Vault/Rejected"
  "AI_Employee_Vault/Done"
  "AI_Employee_Vault/Plans"
  "AI_Employee_Vault/Briefings"
  "AI_Employee_Vault/Reports"
  "AI_Employee_Vault/Logs"
  "AI_Employee_Vault/Dashboard.md"
)

echo "[sync] root=$ROOT_DIR"
echo "[sync] branch=$BRANCH remote=$REMOTE every=${SLEEP_SECONDS}s"

git config user.name "$GIT_USER_NAME"
git config user.email "$GIT_USER_EMAIL"

while true; do
  # Pull remote updates first (non-fatal when remote temporary unavailable).
  git pull --rebase "$REMOTE" "$BRANCH" >/tmp/cloud_git_pull.log 2>&1 || true

  git add "${SYNC_PATHS[@]}" >/tmp/cloud_git_add.log 2>&1 || true

  if ! git diff --cached --quiet; then
    msg="cloud-sync: vault state $(date -Is)"
    git commit -m "$msg" >/tmp/cloud_git_commit.log 2>&1 || true
    git push "$REMOTE" "$BRANCH" >/tmp/cloud_git_push.log 2>&1 || true
    echo "[sync] committed and pushed: $msg"
  fi

  sleep "$SLEEP_SECONDS"
done
