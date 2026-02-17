#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TS="$(date +%Y%m%d_%H%M%S)"
PACK_DIR="evidence_pack/final_silver_${TS}"
OUT_DIR="${PACK_DIR}/outputs"
mkdir -p "$OUT_DIR"

UV_CACHE_DIR="${UV_CACHE_DIR:-.uv-cache}"
export UV_CACHE_DIR

run_and_capture() {
  local name="$1"
  shift
  {
    echo "[START] $(date -Is)"
    echo "[CMD] $*"
    "$@"
    echo "[END] $(date -Is)"
  } | tee "${OUT_DIR}/${name}.txt"
}

SILVER_PASS=true

REQ_1_BRONZE=true
REQ_2_WATCHERS=true
REQ_3_LINKEDIN=true
REQ_4_PLAN=true
REQ_5_MCP=true
REQ_6_HITL=true
REQ_7_SCHEDULER=true
REQ_8_SKILLS=true

# Requirement 1: Bronze baseline
for d in "AI_Employee_Vault/Inbox" "AI_Employee_Vault/Needs_Action" "AI_Employee_Vault/Done"; do
  if [[ ! -d "$d" ]]; then
    REQ_1_BRONZE=false
  fi
done

# Requirement 2: Two or more watchers
WATCHER_COUNT="$(find watchers -maxdepth 1 -name '*_watcher.py' | wc -l | tr -d ' ')"
if [[ "${WATCHER_COUNT}" -lt 2 ]]; then
  REQ_2_WATCHERS=false
fi
echo "WATCHER_COUNT=${WATCHER_COUNT}" | tee "${OUT_DIR}/01_watchers_count.txt"

# Requirement 8: Agent skills baseline
SKILL_COUNT="$(find .claude/skills -name 'SKILL.md' | wc -l | tr -d ' ')"
if [[ "${SKILL_COUNT}" -lt 8 ]]; then
  REQ_8_SKILLS=false
fi
echo "SKILL_COUNT=${SKILL_COUNT}" | tee "${OUT_DIR}/02_skills_count.txt"

# Requirement 4: Plan.md creation
PLAN_MARKER="silver_plan_${TS}"
run_and_capture "03_plan_create" uv run python -c "from utils.plan_creator import PlanCreator; c=PlanCreator('AI_Employee_Vault'); r=c.create_plan(title='${PLAN_MARKER}', objective='Silver validation', steps=['step one','step two']); print(r)"
PLAN_FILE="$(ls -1t AI_Employee_Vault/Plans/PLAN_${PLAN_MARKER}_*.md 2>/dev/null | head -n 1 || true)"
if [[ -z "${PLAN_FILE}" ]]; then
  REQ_4_PLAN=false
fi
echo "PLAN_FILE=${PLAN_FILE:-<missing>}" | tee "${OUT_DIR}/03_plan_file_check.txt"

# Requirement 5 + 6: Working MCP + HITL approval file creation (email unknown contact)
EMAIL_TARGET="silver.check.${TS}@example.com"
run_and_capture "04_email_mcp_send" uv run python mcp_servers/email_server.py send "${EMAIL_TARGET}" "Silver HITL Check ${TS}" "This is a Silver tier HITL validation email."
if ! rg -q "pending_approval" "${OUT_DIR}/04_email_mcp_send.txt"; then
  REQ_5_MCP=false
  REQ_6_HITL=false
fi
EMAIL_APPROVAL_FILE="$(ls -1t AI_Employee_Vault/Pending_Approval/EMAIL_SEND_*.md 2>/dev/null | head -n 1 || true)"
if [[ -z "${EMAIL_APPROVAL_FILE}" ]]; then
  REQ_6_HITL=false
fi
echo "EMAIL_APPROVAL_FILE=${EMAIL_APPROVAL_FILE:-<missing>}" | tee "${OUT_DIR}/04_email_approval_check.txt"

# Requirement 7: Scheduler command available
if ! run_and_capture "05_scheduler_list" uv run python scheduler/scheduler.py list; then
  REQ_7_SCHEDULER=false
fi

# Requirement 3: LinkedIn post workflow (HITL -> Approved -> Published) using DRY_RUN
LINKEDIN_MARKER="Silver LinkedIn post validation ${TS}"
run_and_capture "06_linkedin_create_approval" env DRY_RUN=true uv run python watchers/linkedin_poster.py "${LINKEDIN_MARKER}"

LINKEDIN_PENDING_FILE="$(rg -l "${LINKEDIN_MARKER}" AI_Employee_Vault/Pending_Approval/LINKEDIN_POST_*.md 2>/dev/null | head -n 1 || true)"
if [[ -z "${LINKEDIN_PENDING_FILE}" ]]; then
  REQ_3_LINKEDIN=false
else
  LINKEDIN_APPROVED_FILE="AI_Employee_Vault/Approved/$(basename "${LINKEDIN_PENDING_FILE}")"
  mv "${LINKEDIN_PENDING_FILE}" "${LINKEDIN_APPROVED_FILE}"
  run_and_capture "07_linkedin_process_approved" env DRY_RUN=true uv run python watchers/linkedin_poster.py --approve
  LINKEDIN_DONE_FILE="AI_Employee_Vault/Done/$(basename "${LINKEDIN_APPROVED_FILE}")"
  if [[ ! -f "${LINKEDIN_DONE_FILE}" ]]; then
    REQ_3_LINKEDIN=false
  fi
  echo "LINKEDIN_DONE_FILE=${LINKEDIN_DONE_FILE}" | tee "${OUT_DIR}/07_linkedin_done_check.txt"
fi

for flag in \
  "$REQ_1_BRONZE" "$REQ_2_WATCHERS" "$REQ_3_LINKEDIN" "$REQ_4_PLAN" \
  "$REQ_5_MCP" "$REQ_6_HITL" "$REQ_7_SCHEDULER" "$REQ_8_SKILLS"; do
  if [[ "$flag" != "true" ]]; then
    SILVER_PASS=false
  fi
done

OVERALL_STATUS="PASS"
if [[ "$SILVER_PASS" != "true" ]]; then
  OVERALL_STATUS="PARTIAL"
fi

cat > "${PACK_DIR}/README.md" <<EOF
# Final Silver Evidence Pack

Generated: $(date -Is)
Path: ${PACK_DIR}

## Overall Status
${OVERALL_STATUS}

## Silver Requirements Status
- 1. All Bronze requirements: ${REQ_1_BRONZE}
- 2. Two or more watchers: ${REQ_2_WATCHERS} (count=${WATCHER_COUNT})
- 3. Auto LinkedIn posting workflow: ${REQ_3_LINKEDIN}
- 4. Plan.md creation loop: ${REQ_4_PLAN}
- 5. One working MCP server: ${REQ_5_MCP}
- 6. HITL approval workflow: ${REQ_6_HITL}
- 7. Basic scheduling via cron: ${REQ_7_SCHEDULER}
- 8. AI as Agent Skills: ${REQ_8_SKILLS} (count=${SKILL_COUNT})

## Captured Outputs
- outputs/01_watchers_count.txt
- outputs/02_skills_count.txt
- outputs/03_plan_create.txt
- outputs/03_plan_file_check.txt
- outputs/04_email_mcp_send.txt
- outputs/04_email_approval_check.txt
- outputs/05_scheduler_list.txt
- outputs/06_linkedin_create_approval.txt
- outputs/07_linkedin_process_approved.txt
- outputs/07_linkedin_done_check.txt
EOF

echo "Created: ${PACK_DIR}"
