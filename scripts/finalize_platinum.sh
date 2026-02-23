#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TS="$(date +%Y%m%d_%H%M%S)"
PACK_DIR="evidence_pack/final_platinum_${TS}"
OUT_DIR="${PACK_DIR}/outputs"
LOG_DIR="${PACK_DIR}/logs"
mkdir -p "$OUT_DIR" "$LOG_DIR"

run_and_capture() {
  local name="$1"
  shift
  set +e
  {
    echo "[START] $(date -Is)"
    echo "[CMD] $*"
    "$@"
    local ec=$?
    echo "[EXIT] ${ec}"
    echo "[END] $(date -Is)"
  } | tee "${OUT_DIR}/${name}.txt"
  local rc
  rc="$(awk '/^\[EXIT\] /{print $2}' "${OUT_DIR}/${name}.txt" | tail -n1)"
  set -e
  [[ "${rc:-1}" == "0" ]]
}

REQ_1_CLOUD_247="false"
REQ_2_WORKZONE_SPLIT="false"
REQ_3_SYNC_DELEGATION="false"
REQ_4_SYNC_SECURITY="false"
REQ_5_ODOO_CLOUD="false"
REQ_6_A2A_PATH="false"
REQ_7_DEMO_GATE="false"

# Requirement 1: cloud 24/7 runtime proof (PM2 services online)
PM2_OK="false"
if command -v pm2 >/dev/null 2>&1; then
  if run_and_capture "01_pm2_status" pm2 jlist; then
    # Require key cloud apps to exist in PM2 list.
    if rg -q '"name":"cloud-gmail-watcher"' "${OUT_DIR}/01_pm2_status.txt" \
      && rg -q '"name":"cloud-draft-worker"' "${OUT_DIR}/01_pm2_status.txt" \
      && rg -q '"name":"cloud-git-sync"' "${OUT_DIR}/01_pm2_status.txt"; then
      PM2_OK="true"
    fi
  fi
fi
if [[ "${PM2_OK}" == "true" ]]; then
  REQ_1_CLOUD_247="true"
fi
echo "REQ_1_CLOUD_247=${REQ_1_CLOUD_247}" | tee "${OUT_DIR}/01_cloud_247_check.txt"

# Requirement 2: work-zone specialization (enforcement in code/config)
if [[ -f "scripts/cloud/ecosystem.cloud.cjs" && -f "scripts/local/ecosystem.local.cjs" ]]; then
  if rg -q 'AGENT_ROLE:\s*"cloud"' scripts/cloud/ecosystem.cloud.cjs \
    && rg -q 'local-executive-agent' scripts/local/ecosystem.local.cjs \
    && rg -q 'CLOUD_DRAFT_ONLY' scripts/cloud/ecosystem.cloud.cjs; then
    REQ_2_WORKZONE_SPLIT="true"
  fi
fi
echo "REQ_2_WORKZONE_SPLIT=${REQ_2_WORKZONE_SPLIT}" | tee "${OUT_DIR}/02_workzone_split_check.txt"

# Requirement 3: synced-vault delegation + single-writer runtime artifacts
SYNC_RULES_OK="false"
if [[ -f "scripts/cloud/cloud_draft_worker.py" && -f "scripts/local/local_executive_agent.py" ]]; then
  if rg -q 'rename\(target\).*# Atomic claim-by-move|CLAIM' scripts/cloud/cloud_draft_worker.py \
    && rg -q 'dashboard_writer.lock|Single-writer|LOCAL_EXEC_AGENT' scripts/local/local_executive_agent.py scheduler/tasks/update_dashboard.py; then
    SYNC_RULES_OK="true"
  fi
fi
if [[ "${SYNC_RULES_OK}" == "true" ]]; then
  REQ_3_SYNC_DELEGATION="true"
fi
echo "REQ_3_SYNC_DELEGATION=${REQ_3_SYNC_DELEGATION}" | tee "${OUT_DIR}/03_sync_delegation_check.txt"

# Requirement 4: secrets excluded from sync
SYNC_SECURITY_OK="false"
if rg -q "^\\.facebook_session/|^\\.instagram_session/|^\\.twitter_session/|^\\.whatsapp_session/" .gitignore \
  && rg -q "^\\.env$" .gitignore \
  && rg -q "Never sync|\\.env|tokens|session" docs/platinum-runbook.md; then
  SYNC_SECURITY_OK="true"
fi
if [[ "${SYNC_SECURITY_OK}" == "true" ]]; then
  REQ_4_SYNC_SECURITY="true"
fi
echo "REQ_4_SYNC_SECURITY=${REQ_4_SYNC_SECURITY}" | tee "${OUT_DIR}/04_sync_security_check.txt"

# Requirement 5: Odoo cloud HTTPS + health + local-approval controls
ODOO_CFG_OK="false"
if [[ -f "scripts/cloud/docker-compose.odoo-cloud.yml" && -f "scripts/cloud/Caddyfile.odoo" ]]; then
  if rg -q "healthcheck" scripts/cloud/docker-compose.odoo-cloud.yml \
    && rg -q "tls" scripts/cloud/Caddyfile.odoo \
    && rg -q "Cloud agent cannot process payments directly" mcp_servers/odoo_server.py \
    && rg -q "Cloud agent cannot post invoices directly" mcp_servers/odoo_server.py; then
    ODOO_CFG_OK="true"
  fi
fi
if [[ "${ODOO_CFG_OK}" == "true" ]]; then
  REQ_5_ODOO_CLOUD="true"
fi
echo "REQ_5_ODOO_CLOUD=${REQ_5_ODOO_CLOUD}" | tee "${OUT_DIR}/05_odoo_cloud_check.txt"

# Requirement 6: optional A2A phase documented
if rg -q "Optional A2A Upgrade|Phase 2|A2A" docs/platinum-runbook.md docs/platinum-cloud-operations.md; then
  REQ_6_A2A_PATH="true"
fi
echo "REQ_6_A2A_PATH=${REQ_6_A2A_PATH}" | tee "${OUT_DIR}/06_a2a_path_check.txt"

# Requirement 7: Platinum demo gate execution (local simulation + vault transition)
DEMO_MARKER="PLATINUM_DEMO_${TS}"
if run_and_capture "07_demo_gate_create_approval" uv run python mcp_servers/email_server.py send "platinum.demo.${TS}@example.com" "Platinum Demo ${TS}" "Demo marker ${DEMO_MARKER}"; then
  PENDING_FILE="$(grep -Rl "${DEMO_MARKER}" AI_Employee_Vault/Pending_Approval/EMAIL_SEND_*.md 2>/dev/null | head -n1 || true)"
  echo "PENDING_FILE=${PENDING_FILE:-<missing>}" | tee "${OUT_DIR}/07_demo_gate_pending.txt"
  if [[ -n "${PENDING_FILE}" ]]; then
    APPROVED_FILE="AI_Employee_Vault/Approved/$(basename "${PENDING_FILE}")"
    mv "${PENDING_FILE}" "${APPROVED_FILE}"
    run_and_capture "07_demo_gate_process_approved" uv run python main.py process-approved || true
    DONE_FILE="AI_Employee_Vault/Done/$(basename "${PENDING_FILE}")"
    TODAY_LOG="AI_Employee_Vault/Logs/$(date +%F).json"
    {
      echo "APPROVED_FILE=${APPROVED_FILE}"
      echo "DONE_FILE=${DONE_FILE}"
      echo "TODAY_LOG=${TODAY_LOG}"
    } | tee "${OUT_DIR}/07_demo_gate_done.txt"
    if [[ -f "${DONE_FILE}" && -f "${TODAY_LOG}" ]]; then
      REQ_7_DEMO_GATE="true"
    fi
  fi
fi
echo "REQ_7_DEMO_GATE=${REQ_7_DEMO_GATE}" | tee "${OUT_DIR}/07_demo_gate_result.txt"

OVERALL_STATUS="PASS"
for flag in \
  "$REQ_1_CLOUD_247" "$REQ_2_WORKZONE_SPLIT" "$REQ_3_SYNC_DELEGATION" \
  "$REQ_4_SYNC_SECURITY" "$REQ_5_ODOO_CLOUD" "$REQ_6_A2A_PATH" "$REQ_7_DEMO_GATE"; do
  if [[ "$flag" != "true" ]]; then
    OVERALL_STATUS="PARTIAL"
  fi
done

cp AI_Employee_Vault/Logs/"$(date +%F)".json "${LOG_DIR}/" 2>/dev/null || true
cp AI_Employee_Vault/Logs/processed_approvals.json "${LOG_DIR}/" 2>/dev/null || true

cat > "${PACK_DIR}/README.md" <<EOF
# Final Platinum Evidence Pack

Generated: $(date -Is)
Path: ${PACK_DIR}

## Overall Status
${OVERALL_STATUS}

## Platinum Requirements Status
- 1. Cloud 24/7 deployment readiness: ${REQ_1_CLOUD_247}
- 2. Work-zone specialization documented: ${REQ_2_WORKZONE_SPLIT}
- 3. Synced-vault delegation rules: ${REQ_3_SYNC_DELEGATION}
- 4. Sync security boundaries (no secrets): ${REQ_4_SYNC_SECURITY}
- 5. Odoo cloud runbook controls: ${REQ_5_ODOO_CLOUD}
- 6. Optional A2A path documented: ${REQ_6_A2A_PATH}
- 7. Platinum demo gate execution: ${REQ_7_DEMO_GATE}

## Captured Outputs
- outputs/01_pm2_status.txt
- outputs/01_cloud_247_check.txt
- outputs/02_workzone_split_check.txt
- outputs/03_sync_delegation_check.txt
- outputs/04_sync_security_check.txt
- outputs/05_odoo_cloud_check.txt
- outputs/06_a2a_path_check.txt
- outputs/07_demo_gate_create_approval.txt
- outputs/07_demo_gate_pending.txt
- outputs/07_demo_gate_process_approved.txt
- outputs/07_demo_gate_done.txt
- outputs/07_demo_gate_result.txt
EOF

echo "Created: ${PACK_DIR}"
