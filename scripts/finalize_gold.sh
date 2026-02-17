#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TS="$(date +%Y%m%d_%H%M%S)"
PACK_DIR="evidence_pack/final_gold_${TS}"
OUT_DIR="${PACK_DIR}/outputs"
LOG_DIR="${PACK_DIR}/logs"
mkdir -p "$OUT_DIR" "$LOG_DIR" "${PACK_DIR}/screenshots"

UV_CACHE_DIR="${UV_CACHE_DIR:-.uv-cache}"
export UV_CACHE_DIR

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

REQ_1_SILVER="false"
REQ_2_CROSS_DOMAIN="false"
REQ_3_ODOO_LOCAL="false"
REQ_4_FB_IG="false"
REQ_5_TWITTER="false"
REQ_6_MULTI_MCP="false"
REQ_7_CEO_BRIEFING="false"
REQ_8_ERROR_RECOVERY="false"
REQ_9_AUDIT_LOGGING="false"
REQ_10_RALPH="false"
REQ_11_DOCS="false"
REQ_12_SKILLS="false"

ODDO_URL_VAL=""
if [[ -f ".env" ]]; then
  ODDO_URL_VAL="$(awk -F= '/^ODOO_URL=/{print $2}' .env | tail -n1 || true)"
fi
if [[ -z "${ODDO_URL_VAL}" ]]; then
  ODDO_URL_VAL="${ODOO_URL:-}"
fi

SELF_HOSTED_PASS="false"
if [[ "${ODDO_URL_VAL}" =~ ^https?://(localhost|127\.0\.0\.1)(:8069)?$ ]]; then
  SELF_HOSTED_PASS="true"
fi

PORT_PASS="false"
if ss -lntp 2>/dev/null | grep -Eq "[:.]8069([[:space:]]|$)"; then
  PORT_PASS="true"
fi

if [[ "${SELF_HOSTED_PASS}" == "true" && "${PORT_PASS}" == "true" ]]; then
  REQ_3_ODOO_LOCAL="true"
fi

{
  echo "ODOO_URL=${ODDO_URL_VAL:-<unset>}"
  echo "SELF_HOSTED_URL_PASS=${SELF_HOSTED_PASS}"
  echo "PORT_8069_LISTEN_PASS=${PORT_PASS}"
} | tee "${OUT_DIR}/00_self_hosted_checks.txt"

# Requirement 1: Silver must already pass
LATEST_SILVER_PACK="$(ls -1dt evidence_pack/final_silver_* 2>/dev/null | head -n1 || true)"
if [[ -n "${LATEST_SILVER_PACK}" && -f "${LATEST_SILVER_PACK}/README.md" ]]; then
  SILVER_STATUS="$(awk '/## Overall Status/{getline; gsub(/^[[:space:]]+|[[:space:]]+$/, "", $0); print; exit}' "${LATEST_SILVER_PACK}/README.md")"
  if [[ "${SILVER_STATUS}" == "PASS" ]]; then
    REQ_1_SILVER="true"
  fi
fi
{
  echo "LATEST_SILVER_PACK=${LATEST_SILVER_PACK:-<missing>}"
  echo "SILVER_STATUS=${SILVER_STATUS:-<missing>}"
} | tee "${OUT_DIR}/01_silver_dependency.txt"

# Odoo baseline commands (also used for multi-MCP validation)
ODOO_CONNECT_OK="false"
if run_and_capture "02_odoo_connect" uv run python mcp_servers/odoo_server.py connect; then
  ODOO_CONNECT_OK="true"
fi
run_and_capture "03_customers" uv run python mcp_servers/odoo_server.py customers || true
run_and_capture "04_invoices" uv run python mcp_servers/odoo_server.py invoices || true

# Email MCP + HITL creation
EMAIL_MCP_OK="false"
EMAIL_TARGET="gold.check.${TS}@example.com"
if run_and_capture "05_email_mcp_send" uv run python mcp_servers/email_server.py send "${EMAIL_TARGET}" "Gold MCP Check ${TS}" "Gold requirement check email."; then
  if grep -q "pending_approval" "${OUT_DIR}/05_email_mcp_send.txt"; then
    EMAIL_MCP_OK="true"
  fi
fi

if [[ "${ODOO_CONNECT_OK}" == "true" && "${EMAIL_MCP_OK}" == "true" ]]; then
  REQ_6_MULTI_MCP="true"
fi

# Requirement 4: Facebook + Instagram post + summary (DRY_RUN)
REQ4_MARKER="Gold Social Validation ${TS}"
run_and_capture "06_social_create_approval" env DRY_RUN=true uv run python watchers/social_poster.py "${REQ4_MARKER}" || true

FB_PENDING_FILE="$(grep -l "${REQ4_MARKER}" AI_Employee_Vault/Pending_Approval/FACEBOOK_POST_*.md 2>/dev/null | head -n1 || true)"
IG_PENDING_FILE="$(grep -l "${REQ4_MARKER}" AI_Employee_Vault/Pending_Approval/INSTAGRAM_POST_*.md 2>/dev/null | head -n1 || true)"
{
  echo "FB_PENDING_FILE=${FB_PENDING_FILE:-<missing>}"
  echo "IG_PENDING_FILE=${IG_PENDING_FILE:-<missing>}"
} | tee "${OUT_DIR}/06_social_pending_check.txt"

if [[ -n "${FB_PENDING_FILE}" && -n "${IG_PENDING_FILE}" ]]; then
  mv "${FB_PENDING_FILE}" "AI_Employee_Vault/Approved/$(basename "${FB_PENDING_FILE}")"
  mv "${IG_PENDING_FILE}" "AI_Employee_Vault/Approved/$(basename "${IG_PENDING_FILE}")"
  run_and_capture "07_social_process_approved" env DRY_RUN=true uv run python watchers/social_poster.py --approve || true
  run_and_capture "08_social_summary" env DRY_RUN=true uv run python watchers/social_poster.py --summary --days 7 || true

  FB_DONE_FILE="AI_Employee_Vault/Done/$(basename "${FB_PENDING_FILE}")"
  IG_DONE_FILE="AI_Employee_Vault/Done/$(basename "${IG_PENDING_FILE}")"
  SOCIAL_SUMMARY_FILE="$(ls -1t AI_Employee_Vault/Reports/SOCIAL_SUMMARY_*.md 2>/dev/null | head -n1 || true)"

  {
    echo "FB_DONE_FILE=${FB_DONE_FILE}"
    echo "IG_DONE_FILE=${IG_DONE_FILE}"
    echo "SOCIAL_SUMMARY_FILE=${SOCIAL_SUMMARY_FILE:-<missing>}"
  } | tee "${OUT_DIR}/08_social_done_check.txt"

  if [[ -f "${FB_DONE_FILE}" && -f "${IG_DONE_FILE}" && -n "${SOCIAL_SUMMARY_FILE}" ]]; then
    REQ_4_FB_IG="true"
  fi
fi

# Requirement 5: Twitter post workflow (DRY_RUN)
TW_MARKER="Gold Twitter Validation ${TS}"
run_and_capture "09_twitter_create_approval" env DRY_RUN=true uv run python watchers/twitter_poster.py "${TW_MARKER}" || true
TW_PENDING_FILE="$(grep -l "${TW_MARKER}" AI_Employee_Vault/Pending_Approval/TWITTER_POST_APPROVAL_*.md 2>/dev/null | head -n1 || true)"
echo "TW_PENDING_FILE=${TW_PENDING_FILE:-<missing>}" | tee "${OUT_DIR}/09_twitter_pending_check.txt"
if [[ -n "${TW_PENDING_FILE}" ]]; then
  TW_APPROVED_FILE="AI_Employee_Vault/Approved/$(basename "${TW_PENDING_FILE}")"
  mv "${TW_PENDING_FILE}" "${TW_APPROVED_FILE}"
  run_and_capture "10_twitter_process_approved" env DRY_RUN=true uv run python watchers/twitter_poster.py --approve || true
  TW_COMPLETED_FILE="AI_Employee_Vault/Approved/COMPLETED_$(basename "${TW_PENDING_FILE}")"
  echo "TW_COMPLETED_FILE=${TW_COMPLETED_FILE}" | tee "${OUT_DIR}/10_twitter_done_check.txt"
  if [[ -f "${TW_COMPLETED_FILE}" ]]; then
    REQ_5_TWITTER="true"
  fi
fi

# Requirement 7: Weekly CEO briefing + business audit
if run_and_capture "11_ceo_briefing" uv run python scheduler/tasks/ceo_briefing.py; then
  LATEST_CEO_FILE="$(ls -1t AI_Employee_Vault/Briefings/CEO_BRIEFING_*.md 2>/dev/null | head -n1 || true)"
  if [[ -n "${LATEST_CEO_FILE}" ]]; then
    REQ_7_CEO_BRIEFING="true"
  fi
fi
echo "LATEST_CEO_FILE=${LATEST_CEO_FILE:-<missing>}" | tee "${OUT_DIR}/11_ceo_file_check.txt"

# Requirement 8: Error recovery module availability
if run_and_capture "12_error_recovery_check" uv run python -c "from utils.error_recovery import OfflineQueue, ServiceHealthMonitor, with_retry, graceful; q=OfflineQueue('AI_Employee_Vault'); item=q.enqueue('gold_test','social',{'ok': True}); print('QUEUE_ITEM', item); print('PENDING_COUNT', len(q.get_pending('social'))); h=ServiceHealthMonitor('AI_Employee_Vault'); h.record_success('social'); print('HEALTH_OK', h.get_status('social').value)"; then
  REQ_8_ERROR_RECOVERY="true"
fi

# Requirement 9: Comprehensive audit logging
run_and_capture "13_process_approved" uv run python main.py process-approved || true
TODAY_LOG="AI_Employee_Vault/Logs/$(date +%F).json"
if [[ -f "${TODAY_LOG}" ]]; then
  REQ_9_AUDIT_LOGGING="true"
fi
echo "TODAY_LOG=${TODAY_LOG}" | tee "${OUT_DIR}/13_audit_log_check.txt"

# Requirement 10: Ralph Wiggum loop hook validation (file-movement strategy)
if run_and_capture "14_ralph_hook_check" uv run python -c "from pathlib import Path; from utils.ralph_wiggum import RalphWiggumLoop; r=RalphWiggumLoop('AI_Employee_Vault'); tid='gold_ralph_${TS}'; f='RalphTask_${TS}.md'; na=Path('AI_Employee_Vault/Needs_Action')/f; d=Path('AI_Employee_Vault/Done')/f; na.parent.mkdir(parents=True, exist_ok=True); d.parent.mkdir(parents=True, exist_ok=True); na.write_text('ralph test'); sf=r.create_state(task_id=tid, prompt='hook test', completion_file=f, max_iterations=2); before=r.hook_mode(str(sf)); na.rename(d); after=r.hook_mode(str(sf)); print('HOOK_BEFORE', before); print('HOOK_AFTER', after);"; then
  if grep -q "HOOK_BEFORE 1" "${OUT_DIR}/14_ralph_hook_check.txt" && grep -q "HOOK_AFTER 0" "${OUT_DIR}/14_ralph_hook_check.txt"; then
    REQ_10_RALPH="true"
  fi
fi

# Requirement 11: Documentation
if [[ -f "README.md" && -f "AGENTS.md" ]]; then
  REQ_11_DOCS="true"
fi
echo "README_EXISTS=$(test -f README.md && echo true || echo false)" | tee "${OUT_DIR}/15_docs_check.txt"
echo "AGENTS_EXISTS=$(test -f AGENTS.md && echo true || echo false)" | tee -a "${OUT_DIR}/15_docs_check.txt"

# Requirement 12: Agent Skills count
SKILL_COUNT="$(find .claude/skills -name 'SKILL.md' | wc -l | tr -d ' ')"
if [[ "${SKILL_COUNT}" -ge 12 ]]; then
  REQ_12_SKILLS="true"
fi
echo "SKILL_COUNT=${SKILL_COUNT}" | tee "${OUT_DIR}/16_skills_count.txt"

# Requirement 2: Cross-domain integration (personal + business)
if [[ "${REQ_1_SILVER}" == "true" && "${REQ_4_FB_IG}" == "true" && "${REQ_5_TWITTER}" == "true" && "${REQ_6_MULTI_MCP}" == "true" && "${REQ_7_CEO_BRIEFING}" == "true" ]]; then
  REQ_2_CROSS_DOMAIN="true"
fi

# Keep strict Gold PASS gate tied to local self-hosted Odoo requirement.
OVERALL_STATUS="PASS"
if [[ "${REQ_1_SILVER}" != "true" || "${REQ_2_CROSS_DOMAIN}" != "true" || "${REQ_3_ODOO_LOCAL}" != "true" || "${REQ_4_FB_IG}" != "true" || "${REQ_5_TWITTER}" != "true" || "${REQ_6_MULTI_MCP}" != "true" || "${REQ_7_CEO_BRIEFING}" != "true" || "${REQ_8_ERROR_RECOVERY}" != "true" || "${REQ_9_AUDIT_LOGGING}" != "true" || "${REQ_10_RALPH}" != "true" || "${REQ_11_DOCS}" != "true" || "${REQ_12_SKILLS}" != "true" ]]; then
  OVERALL_STATUS="PARTIAL"
fi

run_and_capture "17_port_check" bash -lc "ss -lntp 2>/dev/null | grep -E '[:.]8069([[:space:]]|$)' || echo 'No local listener on 8069 detected'" || true

# Copy useful runtime artifacts if available
cp AI_Employee_Vault/Logs/"$(date +%F)".json "${LOG_DIR}/" 2>/dev/null || true
cp AI_Employee_Vault/Logs/processed_approvals.json "${LOG_DIR}/" 2>/dev/null || true
cp AI_Employee_Vault/Done/ODOO_* "${LOG_DIR}/" 2>/dev/null || true
cp AI_Employee_Vault/Done/DUPLICATE_ODOO_* "${LOG_DIR}/" 2>/dev/null || true

cat > "${PACK_DIR}/README.md" <<EOF
# Final Gold Evidence Pack

Generated: $(date -Is)
Path: ${PACK_DIR}

## Overall Status
${OVERALL_STATUS}

## Strict Self-Hosted Odoo Checks
- ODOO_URL local (localhost/127.0.0.1): ${SELF_HOSTED_PASS}
- Local listener on port 8069: ${PORT_PASS}

## Gold Requirements Status
- 1. All Silver requirements: ${REQ_1_SILVER}
- 2. Full cross-domain integration (Personal + Business): ${REQ_2_CROSS_DOMAIN}
- 3. Odoo Community self-hosted local + MCP integration: ${REQ_3_ODOO_LOCAL}
- 4. Facebook + Instagram integration with posting and summary: ${REQ_4_FB_IG}
- 5. Twitter integration with posting workflow: ${REQ_5_TWITTER}
- 6. Multiple MCP servers: ${REQ_6_MULTI_MCP}
- 7. Weekly CEO briefing + business audit: ${REQ_7_CEO_BRIEFING}
- 8. Error recovery + graceful degradation: ${REQ_8_ERROR_RECOVERY}
- 9. Comprehensive audit logging: ${REQ_9_AUDIT_LOGGING}
- 10. Ralph Wiggum loop validation: ${REQ_10_RALPH}
- 11. Documentation: ${REQ_11_DOCS}
- 12. AI functionality as Agent Skills: ${REQ_12_SKILLS}

## Captured Outputs
- outputs/00_self_hosted_checks.txt
- outputs/01_silver_dependency.txt
- outputs/02_odoo_connect.txt
- outputs/03_customers.txt
- outputs/04_invoices.txt
- outputs/05_email_mcp_send.txt
- outputs/06_social_create_approval.txt
- outputs/06_social_pending_check.txt
- outputs/07_social_process_approved.txt
- outputs/08_social_summary.txt
- outputs/08_social_done_check.txt
- outputs/09_twitter_create_approval.txt
- outputs/09_twitter_pending_check.txt
- outputs/10_twitter_process_approved.txt
- outputs/10_twitter_done_check.txt
- outputs/11_ceo_briefing.txt
- outputs/11_ceo_file_check.txt
- outputs/12_error_recovery_check.txt
- outputs/13_process_approved.txt
- outputs/13_audit_log_check.txt
- outputs/14_ralph_hook_check.txt
- outputs/15_docs_check.txt
- outputs/16_skills_count.txt
- outputs/17_port_check.txt

## Captured Logs/Artifacts
- logs/<today>.json (if present)
- logs/processed_approvals.json (if present)
- logs/ODOO_*.md and logs/DUPLICATE_ODOO_*.md (if present)

## Notes
- If status is PARTIAL and only requirement #3 is false, run Odoo Community locally on :8069 and re-run this script.
EOF

echo "Created: ${PACK_DIR}"
