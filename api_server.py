"""
FastAPI bridge for the Next.js frontend.

Exposes normalized API endpoints backed by Obsidian vault files.
If vault paths/files are missing, endpoints return safe empty/default payloads.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import signal
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).parent


def _resolve_vault_path() -> Path:
    env_value = os.getenv("VAULT_PATH")
    if env_value:
        return Path(env_value).expanduser()

    vault = PROJECT_ROOT / "AI_Employee_Vault"
    if vault.is_symlink():
        try:
            return vault.resolve()
        except Exception:
            return vault
    return vault


VAULT_PATH = _resolve_vault_path()
NEEDS_ACTION = VAULT_PATH / "Needs_Action"
PENDING_APPROVAL = VAULT_PATH / "Pending_Approval"
APPROVED = VAULT_PATH / "Approved"
REJECTED = VAULT_PATH / "Rejected"
PLANS = VAULT_PATH / "Plans"
BRIEFINGS = VAULT_PATH / "Briefings"
REPORTS = VAULT_PATH / "Reports"
LOGS = VAULT_PATH / "Logs"
STATE = VAULT_PATH / "State"
WATCHER_PID_FILE = STATE / "watcher_pids.json"
AI_LOOP_STATE_FILE = STATE / "ai_loop_process.json"
RBAC_ENFORCE = os.getenv("RBAC_ENFORCE", "false").strip().lower() == "true"

WATCHER_SCRIPTS: Dict[str, str] = {
    "gmail_watcher": "watchers/gmail_watcher.py",
    "twitter_watcher": "watchers/twitter_watcher.py",
    "filesystem_watcher": "watchers/filesystem_watcher.py",
    "whatsapp_watcher": "watchers/whatsapp_watcher.py",
    "linkedin_watcher": "watchers/linkedin_watcher.py",
    "facebook_watcher": "watchers/facebook_watcher.py",
    "instagram_watcher": "watchers/instagram_watcher.py",
}

ROLE_PERMISSIONS: Dict[str, set] = {
    "admin": {"read_console", "approve_actions", "manual_override", "watcher_control", "finance_write"},
    "finance": {"read_console", "approve_actions", "finance_write"},
    "ops_reviewer": {"read_console", "approve_actions"},
    "observer": {"read_console"},
}

DEFAULT_INTERVALS: Dict[str, str] = {
    "gmail_watcher": "120s",
    "twitter_watcher": "60s",
    "filesystem_watcher": "real-time",
    "whatsapp_watcher": "30s",
    "linkedin_watcher": "120s",
    "facebook_watcher": "120s",
    "instagram_watcher": "120s",
}

KNOWN_WATCHERS = list(DEFAULT_INTERVALS.keys())

cors_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
cors_origins = [origin.strip() for origin in cors_origins_raw.split(",") if origin.strip()]

app = FastAPI(title="AI Employee API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthzResponse(BaseModel):
    status: Literal["ok"]


class TaskItem(BaseModel):
    id: str
    type: str
    title: str
    source: str
    received: str
    priority: Literal["low", "medium", "high"]
    status: Literal["pending", "in_progress", "approved", "done"]
    preview: str


class TaskDetail(TaskItem):
    body: str
    metadata: Dict[str, str]
    filePath: str


class ApprovalItem(BaseModel):
    id: str
    action: str
    target: str
    amount: Optional[float] = None
    reason: str
    requestedAt: str
    riskLevel: Literal["low", "medium", "high"]


class PlanStep(BaseModel):
    label: str
    done: bool


class PlanItem(BaseModel):
    id: str
    title: str
    progress: int = Field(ge=0, le=100)
    owner: str
    dueDate: str
    steps: List[PlanStep]


class AuditItem(BaseModel):
    id: str
    actionType: str
    actor: str
    target: str
    status: Literal["success", "failed"]
    timestamp: str


class HealthItem(BaseModel):
    name: str
    status: Literal["healthy", "degraded", "offline"]
    lastSeen: str
    interval: str


class DashboardResponse(BaseModel):
    tasks: List[TaskItem]
    approvals: List[ApprovalItem]
    health: List[HealthItem]
    auditTrail: List[AuditItem]


class ActionResponse(BaseModel):
    status: Literal["success", "error"]
    message: str
    fromPath: Optional[str] = None
    toPath: Optional[str] = None


class RunTaskRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=4000)
    title: Optional[str] = Field(default=None, max_length=200)
    priority: Literal["low", "medium", "high"] = "medium"
    source: str = Field(default="frontend_console", max_length=100)


class CreateDraftRequest(BaseModel):
    to: str = Field(min_length=3, max_length=320)
    subject: str = Field(min_length=1, max_length=250)
    body: str = Field(min_length=1, max_length=10000)


class DraftHistoryItem(BaseModel):
    timestamp: str
    to: str
    subject: str
    draftId: Optional[str] = None
    status: Literal["success", "failed"]


class CleanupResponse(BaseModel):
    status: Literal["success", "error"]
    message: str
    deletedCount: int = 0
    matchedCount: int = 0
    pattern: str


class AiLoopStatusResponse(BaseModel):
    running: bool
    pid: Optional[int] = None
    startedAt: Optional[str] = None
    task: Optional[str] = None
    logFile: str


class RevenuePoint(BaseModel):
    date: str
    value: float


class ExecutiveSummaryResponse(BaseModel):
    revenueTotal: float
    revenueSeries: List[RevenuePoint]
    activeTaskCount: int
    pendingApprovals: int
    completedTaskCount: int
    watchersRunning: int
    watchersStopped: int
    watcherHealth: List[HealthItem]
    recentActivity: List[AuditItem]


class WatcherControlItem(BaseModel):
    name: str
    script: str
    running: bool
    pid: Optional[int] = None
    logFile: str
    lastActivity: Optional[str] = None


class WatcherControlResponse(BaseModel):
    status: Literal["success", "error"]
    message: str
    watcher: Optional[WatcherControlItem] = None


class LogRecord(BaseModel):
    id: str
    timestamp: str
    actionType: str
    channel: Literal["email", "payment", "social", "system", "file", "other"]
    actor: str
    status: Literal["success", "failed"]
    raw: Dict[str, Any]


class SystemMonitorResponse(BaseModel):
    claudeStatus: Literal["running", "idle", "unknown"]
    watcherStatus: List[WatcherControlItem]
    watcherHealth: List[HealthItem]
    lastExecutionTime: Optional[str]
    loopIterationCount: int
    errorAlerts: List[LogRecord]


class BriefingFile(BaseModel):
    id: str
    title: str
    date: str
    weekLabel: str
    filePath: str


class BriefingDetail(BaseModel):
    id: str
    title: str
    date: str
    weekLabel: str
    markdown: str
    filePath: str


class AccountingSummaryResponse(BaseModel):
    monthlyRevenue: List[RevenuePoint]
    currentMonthRevenue: float
    subscriptionRevenue: float
    flaggedCosts: List[LogRecord]
    erpSyncStatus: Literal["healthy", "degraded", "offline"]


class ExecutionTask(BaseModel):
    id: str
    title: str
    status: str
    source: str
    progress: int = Field(ge=0, le=100)


class ExecutionMonitorResponse(BaseModel):
    runningTasks: List[ExecutionTask]
    planVisualization: List[PlanItem]
    loopIterationCount: int
    completionPromisesDetected: int


class OversightQueueResponse(BaseModel):
    highRiskActions: List[ApprovalItem]
    financialApprovals: List[ApprovalItem]
    socialApprovals: List[ApprovalItem]
    totalPending: int


class CompliancePanelResponse(BaseModel):
    actionLogs: List[LogRecord]
    approvalHistory: List[LogRecord]
    failureRecoveryLogs: List[LogRecord]
    retryAttempts: int


class SystemHealthResponse(BaseModel):
    watchdogStatus: Literal["healthy", "degraded", "offline"]
    cpuLoadPercent: float
    processStatus: List[WatcherControlItem]
    queueSize: Dict[str, int]


def _safe_glob_md(path: Path) -> List[Path]:
    try:
        if not path.exists():
            return []
        return sorted(path.glob("*.md"), reverse=True)
    except Exception:
        return []


def _safe_mkdir(path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def _safe_read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_watcher_pid_map() -> Dict[str, int]:
    try:
        if WATCHER_PID_FILE.exists():
            payload = json.loads(WATCHER_PID_FILE.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return {str(k): int(v) for k, v in payload.items() if str(v).isdigit()}
    except Exception:
        pass
    return {}


def _save_watcher_pid_map(pid_map: Dict[str, int]) -> None:
    _safe_mkdir(STATE)
    try:
        WATCHER_PID_FILE.write_text(json.dumps(pid_map, indent=2), encoding="utf-8")
    except Exception:
        pass


def _pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return False


def _watcher_log_file(name: str) -> Path:
    _safe_mkdir(LOGS)
    return LOGS / f"{name}.log"


def _watcher_api_name(name: str) -> str:
    if name.endswith("_watcher"):
        return name[:-8]
    return name


def _resolve_watcher_name(name: str) -> Optional[str]:
    key = name.strip().lower().replace("-", "_")
    if key in WATCHER_SCRIPTS:
        return key
    candidate = f"{key}_watcher"
    if candidate in WATCHER_SCRIPTS:
        return candidate
    return None


def _watcher_item(name: str, pid_map: Optional[Dict[str, int]] = None) -> WatcherControlItem:
    current = pid_map if pid_map is not None else _load_watcher_pid_map()
    pid = current.get(name)
    running = _pid_running(pid) if pid is not None else False
    if pid is not None and not running:
        current.pop(name, None)
        _save_watcher_pid_map(current)
        pid = None
    log_file = _watcher_log_file(name)
    last_activity: Optional[str] = None
    try:
        if log_file.exists():
            last_activity = datetime.fromtimestamp(log_file.stat().st_mtime, tz=timezone.utc).isoformat()
    except Exception:
        last_activity = None

    return WatcherControlItem(
        name=_watcher_api_name(name),
        script=WATCHER_SCRIPTS[name],
        running=running,
        pid=pid,
        logFile=str(log_file),
        lastActivity=last_activity,
    )


def _start_watcher(name: str) -> WatcherControlResponse:
    resolved_name = _resolve_watcher_name(name)
    if not resolved_name:
        return WatcherControlResponse(status="error", message=f"Unknown watcher '{name}'")

    pid_map = _load_watcher_pid_map()
    existing_pid = pid_map.get(resolved_name)
    if existing_pid and _pid_running(existing_pid):
        return WatcherControlResponse(
            status="success",
            message=f"{_watcher_api_name(resolved_name)} already running",
            watcher=_watcher_item(resolved_name, pid_map),
        )

    script_path = PROJECT_ROOT / WATCHER_SCRIPTS[resolved_name]
    if not script_path.exists():
        return WatcherControlResponse(status="error", message=f"Script not found: {script_path}")

    log_path = _watcher_log_file(resolved_name)
    try:
        with open(log_path, "a", encoding="utf-8") as log_file:
            process = subprocess.Popen(
                ["python3", str(script_path), str(VAULT_PATH)],
                cwd=str(PROJECT_ROOT),
                stdout=log_file,
                stderr=log_file,
                start_new_session=True,
            )
    except Exception as exc:
        return WatcherControlResponse(status="error", message=str(exc))

    pid_map[resolved_name] = process.pid
    _save_watcher_pid_map(pid_map)
    return WatcherControlResponse(
        status="success",
        message=f"Started {_watcher_api_name(resolved_name)}",
        watcher=_watcher_item(resolved_name, pid_map),
    )


def _stop_watcher(name: str) -> WatcherControlResponse:
    resolved_name = _resolve_watcher_name(name)
    if not resolved_name:
        return WatcherControlResponse(status="error", message=f"Unknown watcher '{name}'")

    pid_map = _load_watcher_pid_map()
    pid = pid_map.get(resolved_name)
    if not pid:
        return WatcherControlResponse(
            status="success",
            message=f"{_watcher_api_name(resolved_name)} already stopped",
            watcher=_watcher_item(resolved_name, pid_map),
        )

    if _pid_running(pid):
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except Exception as exc:
            return WatcherControlResponse(status="error", message=str(exc))

    pid_map.pop(resolved_name, None)
    _save_watcher_pid_map(pid_map)
    return WatcherControlResponse(
        status="success",
        message=f"Stopped {_watcher_api_name(resolved_name)}",
        watcher=_watcher_item(resolved_name, pid_map),
    )


def _safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _extract_frontmatter(text: str) -> Dict[str, str]:
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return {}

    metadata: Dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip().lower()] = value.strip()
    return metadata


def _strip_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text
    return parts[2]


def _to_iso_or_now(value: Optional[str], fallback: Optional[datetime] = None) -> str:
    if value:
        candidate = value.strip()
        if candidate.endswith("Z"):
            candidate = candidate.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except Exception:
            pass

    dt = fallback or datetime.now(timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _apply_limit(items: List[Any], limit: int) -> List[Any]:
    safe_limit = max(1, min(limit, 500))
    return items[:safe_limit]


def _resolve_approval_file(approval_id: str) -> Optional[Path]:
    candidate = PENDING_APPROVAL / f"{approval_id}.md"
    if candidate.exists():
        return candidate

    try:
        for file_path in PENDING_APPROVAL.glob("*.md"):
            if file_path.stem == approval_id:
                return file_path
    except Exception:
        return None
    return None


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    normalized = normalized.strip("_")
    return normalized[:80] or "task"


def _queue_manual_task(payload: RunTaskRequest) -> ActionResponse:
    _safe_mkdir(NEEDS_ACTION)
    now = datetime.now(timezone.utc)
    iso_now = now.isoformat().replace("+00:00", "Z")

    title = (payload.title or payload.prompt.splitlines()[0]).strip()
    title = re.sub(r"\s+", " ", title)[:140] or "Manual task"
    file_name = f"{now.strftime('%Y%m%d_%H%M%S')}_{_slugify(title)}.md"
    task_file = NEEDS_ACTION / file_name

    frontmatter = [
        "---",
        "type: manual_task",
        f"title: {title}",
        f"source: {payload.source}",
        f"received: {iso_now}",
        f"priority: {payload.priority}",
        "status: pending",
        "---",
        "",
        "## Task Request",
        payload.prompt.strip(),
        "",
        "## Requested Via",
        "- frontend control center",
    ]
    content = "\n".join(frontmatter).strip() + "\n"

    try:
        task_file.write_text(content, encoding="utf-8")
    except Exception as exc:
        return ActionResponse(status="error", message=str(exc))

    return ActionResponse(
        status="success",
        message=f"Queued task '{title}'",
        toPath=str(task_file),
    )


def _ai_loop_log_file() -> Path:
    _safe_mkdir(LOGS)
    return LOGS / "ai_loop.log"


def _load_ai_loop_state() -> Dict[str, Any]:
    payload = _safe_read_json(AI_LOOP_STATE_FILE)
    if isinstance(payload, dict):
        return payload
    return {}


def _save_ai_loop_state(payload: Dict[str, Any]) -> None:
    _safe_mkdir(STATE)
    try:
        AI_LOOP_STATE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        pass


def _current_ai_loop_status() -> AiLoopStatusResponse:
    state = _load_ai_loop_state()
    raw_pid = state.get("pid")
    pid = int(raw_pid) if isinstance(raw_pid, int) or (isinstance(raw_pid, str) and str(raw_pid).isdigit()) else None
    running = _pid_running(pid) if pid else False

    if pid and not running:
        _save_ai_loop_state({})
        pid = None

    return AiLoopStatusResponse(
        running=running,
        pid=pid,
        startedAt=state.get("started_at") if running else None,
        task=state.get("task") if running else None,
        logFile=str(_ai_loop_log_file()),
    )


def _start_ai_loop(task: str, max_iterations: int = 20) -> ActionResponse:
    current = _current_ai_loop_status()
    if current.running:
        return ActionResponse(status="success", message="AI loop already running")

    cmd = [
        "python3",
        str(PROJECT_ROOT / "utils/ralph_wiggum.py"),
        "--vault",
        str(VAULT_PATH),
        "--task",
        task,
        "--max-iterations",
        str(max(1, min(max_iterations, 200))),
    ]

    try:
        with open(_ai_loop_log_file(), "a", encoding="utf-8") as log_file:
            process = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                stdout=log_file,
                stderr=log_file,
                start_new_session=True,
            )
    except Exception as exc:
        return ActionResponse(status="error", message=str(exc))

    _save_ai_loop_state(
        {
            "pid": process.pid,
            "started_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "task": task,
        }
    )
    return ActionResponse(status="success", message="AI loop started")


def _stop_ai_loop() -> ActionResponse:
    current = _current_ai_loop_status()
    if not current.running or not current.pid:
        return ActionResponse(status="success", message="AI loop already stopped")

    try:
        os.kill(current.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    except Exception as exc:
        return ActionResponse(status="error", message=str(exc))

    _save_ai_loop_state({})
    return ActionResponse(status="success", message="AI loop stopped")


def _run_orchestrator_command(command: Literal["process-approved", "process-all"]) -> ActionResponse:
    try:
        result = subprocess.run(
            ["python3", str(PROJECT_ROOT / "main.py"), command],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except Exception as exc:
        return ActionResponse(status="error", message=str(exc))

    if result.returncode != 0:
        msg = (result.stderr or result.stdout or f"{command} failed").strip()
        return ActionResponse(status="error", message=msg[:4000])

    raw = (result.stdout or "").strip()
    message = _summarize_orchestrator_output(command, raw)
    return ActionResponse(status="success", message=message[:4000])


def _summarize_channel_results(label: str, items: Any) -> str:
    if not isinstance(items, list):
        return f"{label}: 0"
    success = 0
    failed = 0
    skipped = 0
    for entry in items:
        if not isinstance(entry, dict):
            continue
        status = str(entry.get("status", "")).lower()
        if status == "success":
            success += 1
        elif "skip" in status:
            skipped += 1
        elif status:
            failed += 1
    total = len(items)
    return f"{label}: {total} total ({success} success, {failed} failed, {skipped} skipped)"


def _summarize_orchestrator_output(command: str, raw: str) -> str:
    if not raw:
        return f"{command} completed."

    try:
        payload = json.loads(raw)
    except Exception:
        return raw

    if command == "process-approved" and isinstance(payload, dict):
        parts = [
            _summarize_channel_results("Email", payload.get("email")),
            _summarize_channel_results("LinkedIn", payload.get("linkedin")),
            _summarize_channel_results("Twitter", payload.get("twitter")),
            _summarize_channel_results("Facebook", payload.get("facebook")),
            _summarize_channel_results("Instagram", payload.get("instagram")),
            _summarize_channel_results("Odoo", payload.get("odoo")),
            _summarize_channel_results("Duplicates", payload.get("duplicates")),
        ]
        return "Approved queue processed. " + " | ".join(parts)

    if command == "process-all" and isinstance(payload, dict):
        approved = payload.get("approved")
        rejected = payload.get("rejected")
        approved_summary = ""
        rejected_summary = ""
        if isinstance(approved, dict):
            approved_summary = (
                _summarize_channel_results("Email", approved.get("email"))
                + "; "
                + _summarize_channel_results("Odoo", approved.get("odoo"))
            )
        if isinstance(rejected, dict):
            moved = rejected.get("moved_count", 0)
            rejected_summary = f"Rejected moved: {moved}"
        text = "Process all completed."
        if approved_summary:
            text += f" Approved => {approved_summary}."
        if rejected_summary:
            text += f" {rejected_summary}."
        return text

    return raw


def _create_email_draft(payload: CreateDraftRequest) -> ActionResponse:
    try:
        from mcp_servers.email_server import EmailMCPServer
    except Exception as exc:
        return ActionResponse(status="error", message=f"Email server unavailable: {exc}")

    try:
        result = EmailMCPServer().create_draft(payload.to, payload.subject, payload.body)
    except Exception as exc:
        return ActionResponse(status="error", message=str(exc))

    if result.get("status") != "success":
        return ActionResponse(status="error", message=str(result.get("message") or "Failed to create draft"))

    draft_id = result.get("draft_id")
    message = f"Draft created for {payload.to}"
    if draft_id:
        message += f" (id: {draft_id})"
    return ActionResponse(status="success", message=message)


def _request_email_approval(payload: CreateDraftRequest) -> ActionResponse:
    _safe_mkdir(PENDING_APPROVAL)
    ts = datetime.now(timezone.utc)
    name = f"EMAIL_SEND_{ts.strftime('%Y%m%d_%H%M%S')}.md"
    approval_path = PENDING_APPROVAL / name

    content = f"""---
type: email_send_approval
action: send_email
to: {payload.to}
subject: {payload.subject}
created: {ts.isoformat().replace("+00:00", "Z")}
status: pending
priority: high
source: frontend_console
---

## Email Send Request

### Recipient
**To:** {payload.to}

### Subject
{payload.subject}

### Body
{payload.body}

---
"""
    try:
        approval_path.write_text(content, encoding="utf-8")
    except Exception as exc:
        return ActionResponse(status="error", message=str(exc))

    return ActionResponse(
        status="success",
        message=f"Approval request created: {approval_path.name}",
        toPath=str(approval_path),
    )


def _load_draft_history(limit: int = 20) -> List[DraftHistoryItem]:
    items: List[DraftHistoryItem] = []
    for record in _load_raw_logs():
        if record.get("actionType") != "draft_created":
            continue
        raw = record.get("raw", {})
        if not isinstance(raw, dict):
            continue
        items.append(
            DraftHistoryItem(
                timestamp=record.get("timestamp", _to_iso_or_now(None)),
                to=str(raw.get("to", "")),
                subject=str(raw.get("subject", "")),
                draftId=str(raw.get("draft_id")) if raw.get("draft_id") else None,
                status="success" if record.get("status") == "success" else "failed",
            )
        )
        if len(items) >= limit:
            break
    return items


def _cleanup_needs_action(pattern: str, dry_run: bool = False) -> CleanupResponse:
    normalized = pattern.strip()
    if not normalized:
        return CleanupResponse(status="error", message="Pattern cannot be empty", pattern=pattern)

    try:
        candidates = list(NEEDS_ACTION.glob(normalized)) if NEEDS_ACTION.exists() else []
    except Exception as exc:
        return CleanupResponse(status="error", message=str(exc), pattern=normalized)

    files = [item for item in candidates if item.is_file()]
    deleted = 0
    if not dry_run:
        for file_path in files:
            try:
                file_path.unlink()
                deleted += 1
            except Exception:
                continue

    matched_count = len(files)
    if dry_run:
        return CleanupResponse(
            status="success",
            message=f"Dry run matched {matched_count} files",
            deletedCount=0,
            matchedCount=matched_count,
            pattern=normalized,
        )

    return CleanupResponse(
        status="success",
        message=f"Deleted {deleted} files (matched {matched_count})",
        deletedCount=deleted,
        matchedCount=matched_count,
        pattern=normalized,
    )


def _move_approval_file(approval_id: str, destination: Path) -> ActionResponse:
    _safe_mkdir(destination)
    source = _resolve_approval_file(approval_id)
    if source is None:
        return ActionResponse(status="error", message=f"Approval '{approval_id}' not found")

    target = destination / source.name
    if target.exists():
        stamped = f"{source.stem}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}{source.suffix}"
        target = destination / stamped

    try:
        source.rename(target)
    except Exception as exc:
        return ActionResponse(status="error", message=str(exc), fromPath=str(source), toPath=str(target))

    return ActionResponse(
        status="success",
        message=f"Moved {source.name} to {destination.name}",
        fromPath=str(source),
        toPath=str(target),
    )


def _status(value: Optional[str]) -> str:
    normalized = (value or "pending").strip().lower()
    if normalized in {"pending", "in_progress", "approved", "done"}:
        return normalized
    if normalized in {"in progress", "processing"}:
        return "in_progress"
    if normalized in {"complete", "completed", "success"}:
        return "done"
    return "pending"


def _priority(value: Optional[str]) -> str:
    normalized = (value or "medium").strip().lower()
    if normalized in {"low", "medium", "high"}:
        return normalized
    if normalized in {"p1", "urgent", "critical"}:
        return "high"
    if normalized in {"p3", "minor"}:
        return "low"
    return "medium"


def _risk_from(priority: str, amount: Optional[float]) -> str:
    if amount is not None and amount > 100:
        return "high"
    if priority == "high":
        return "high"
    if amount is not None and amount > 50:
        return "medium"
    if priority == "low":
        return "low"
    return "medium"


def _extract_excerpt(text: str, max_len: int = 180) -> str:
    body = _strip_frontmatter(text)
    for line in body.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        if candidate.startswith("#"):
            continue
        if candidate.startswith("- ["):
            continue
        excerpt = re.sub(r"\s+", " ", candidate)
        return excerpt[:max_len]
    return "No details available."


def _parse_amount(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    match = re.search(r"[-+]?\d*\.?\d+", value.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(0))
    except Exception:
        return None


def _channel_for_action(action_type: str) -> Literal["email", "payment", "social", "system", "file", "other"]:
    action = action_type.lower()
    if "email" in action:
        return "email"
    if any(token in action for token in ["payment", "invoice", "odoo", "financial"]):
        return "payment"
    if any(token in action for token in ["twitter", "linkedin", "facebook", "instagram", "social"]):
        return "social"
    if any(token in action for token in ["watcher", "scheduler", "orchestrator", "claude", "approval"]):
        return "system"
    if "file" in action:
        return "file"
    return "other"


def _load_raw_logs() -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    if not LOGS.exists():
        return records
    for file_path in sorted(LOGS.glob("*.json"), reverse=True):
        if file_path.name in {"processed_approvals.json", "service_health.json"}:
            continue
        payload = _safe_read_json(file_path)
        if not isinstance(payload, list):
            continue
        for index, entry in enumerate(payload):
            if not isinstance(entry, dict):
                continue
            timestamp = _to_iso_or_now(
                str(entry.get("timestamp")) if entry.get("timestamp") else None,
                fallback=datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc),
            )
            action_type = str(entry.get("action_type", "unknown"))
            status = _normalize_audit_status(entry)
            actor = str(entry.get("actor") or entry.get("component") or entry.get("watcher") or "system")
            records.append(
                {
                    "id": f"{file_path.stem}-{index}",
                    "timestamp": timestamp,
                    "actionType": action_type,
                    "channel": _channel_for_action(action_type),
                    "actor": actor,
                    "status": status,
                    "raw": entry,
                }
            )
    records.sort(key=lambda item: item["timestamp"], reverse=True)
    return records


def _parse_iso_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        candidate = value.strip()
        if len(candidate) == 10:
            return datetime.fromisoformat(candidate).replace(tzinfo=timezone.utc)
        if candidate.endswith("Z"):
            candidate = candidate.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(candidate)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _extract_revenue_from_raw(entry: Dict[str, Any]) -> float:
    amount_fields = ["amount", "total", "payment_amount", "invoice_amount", "price_unit"]
    raw = entry.get("raw", {})
    if not isinstance(raw, dict):
        return 0.0
    for key in amount_fields:
        amount = _parse_amount(str(raw.get(key))) if raw.get(key) is not None else None
        if amount is not None and amount > 0:
            return float(amount)
    message = str(raw.get("message", ""))
    parsed = _parse_amount(message)
    return float(parsed) if parsed is not None and parsed > 0 else 0.0


def _load_revenue_series() -> List[Dict[str, Any]]:
    by_day: Dict[str, float] = {}
    for entry in _load_raw_logs():
        if entry["channel"] != "payment":
            continue
        value = _extract_revenue_from_raw(entry)
        if value <= 0:
            continue
        day = entry["timestamp"][:10]
        by_day[day] = by_day.get(day, 0.0) + value

    if by_day:
        return [{"date": day, "value": round(value, 2)} for day, value in sorted(by_day.items())]

    # Fallback: parse possible totals from report markdown files.
    fallback: Dict[str, float] = {}
    for report in sorted(REPORTS.glob("*.md")) if REPORTS.exists() else []:
        text = _safe_read_text(report)
        totals = re.findall(r"(?:revenue|total)[:\s\$]*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", text, flags=re.IGNORECASE)
        if not totals:
            continue
        day = _mtime_iso(report)[:10]
        value = sum(float(token.replace(",", "")) for token in totals)
        fallback[day] = fallback.get(day, 0.0) + value
    return [{"date": day, "value": round(value, 2)} for day, value in sorted(fallback.items())]


def _claude_status(last_execution_time: Optional[str]) -> Literal["running", "idle", "unknown"]:
    if not last_execution_time:
        return "unknown"
    parsed = _parse_iso_date(last_execution_time)
    if parsed is None:
        return "unknown"
    age_seconds = (datetime.now(timezone.utc) - parsed).total_seconds()
    return "running" if age_seconds <= 300 else "idle"


def _mtime_iso(path: Path) -> str:
    try:
        dt = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
    except Exception:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_tasks() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for file_path in _safe_glob_md(NEEDS_ACTION):
        text = _safe_read_text(file_path)
        meta = _extract_frontmatter(text)
        received = _to_iso_or_now(
            meta.get("received") or meta.get("created") or meta.get("timestamp"),
            fallback=datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
            if file_path.exists()
            else None,
        )
        task_type = (meta.get("type") or "task").lower()
        title = meta.get("subject") or meta.get("title") or file_path.stem.replace("_", " ")
        source = (
            meta.get("source")
            or meta.get("platform")
            or ("Gmail" if task_type == "email" else task_type.title())
        )

        items.append(
            {
                "id": file_path.stem,
                "type": task_type,
                "title": title,
                "source": source,
                "received": received,
                "priority": _priority(meta.get("priority")),
                "status": _status(meta.get("status")),
                "preview": _extract_excerpt(text),
            }
        )

    return sorted(items, key=lambda item: item["received"], reverse=True)


def _task_file_by_id(task_id: str) -> Optional[Path]:
    direct = NEEDS_ACTION / f"{task_id}.md"
    if direct.exists():
        return direct
    try:
        for file_path in NEEDS_ACTION.glob("*.md"):
            if file_path.stem == task_id:
                return file_path
    except Exception:
        return None
    return None


def _load_task_detail(task_id: str) -> Optional[Dict[str, Any]]:
    file_path = _task_file_by_id(task_id)
    if file_path is None:
        return None

    text = _safe_read_text(file_path)
    meta = _extract_frontmatter(text)
    received = _to_iso_or_now(
        meta.get("received") or meta.get("created") or meta.get("timestamp"),
        fallback=datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
        if file_path.exists()
        else None,
    )
    task_type = (meta.get("type") or "task").lower()
    title = meta.get("subject") or meta.get("title") or file_path.stem.replace("_", " ")
    source = meta.get("source") or meta.get("platform") or task_type.title()

    return {
        "id": file_path.stem,
        "type": task_type,
        "title": title,
        "source": source,
        "received": received,
        "priority": _priority(meta.get("priority")),
        "status": _status(meta.get("status")),
        "preview": _extract_excerpt(text),
        "body": _strip_frontmatter(text).strip(),
        "metadata": meta,
        "filePath": str(file_path),
    }


def _load_approvals() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for file_path in _safe_glob_md(PENDING_APPROVAL):
        text = _safe_read_text(file_path)
        meta = _extract_frontmatter(text)
        amount = _parse_amount(meta.get("amount"))
        priority = _priority(meta.get("priority"))
        requested_at = _to_iso_or_now(
            meta.get("requested_at") or meta.get("requested") or meta.get("timestamp"),
            fallback=datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
            if file_path.exists()
            else None,
        )

        approval_item: Dict[str, Any] = {
            "id": file_path.stem,
            "action": meta.get("action") or meta.get("action_type") or meta.get("subject") or file_path.stem,
            "target": meta.get("target") or meta.get("to") or meta.get("recipient") or "Unspecified target",
            "reason": meta.get("reason") or _extract_excerpt(text),
            "requestedAt": requested_at,
            "riskLevel": _risk_from(priority=priority, amount=amount),
        }
        if amount is not None:
            approval_item["amount"] = round(amount, 2)
        items.append(approval_item)

    return sorted(items, key=lambda item: item["requestedAt"], reverse=True)


def _load_plans() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    checkbox = re.compile(r"^\s*-\s*\[( |x|X)\]\s*(.+?)\s*$")

    for file_path in _safe_glob_md(PLANS):
        text = _safe_read_text(file_path)
        meta = _extract_frontmatter(text)
        steps: List[Dict[str, Any]] = []
        for line in _strip_frontmatter(text).splitlines():
            match = checkbox.match(line)
            if not match:
                continue
            steps.append({"label": match.group(2), "done": match.group(1).lower() == "x"})

        done_count = sum(1 for step in steps if step["done"])
        total_count = len(steps)
        progress = int(round((done_count / total_count) * 100)) if total_count else 0

        title = meta.get("title")
        if not title:
            for line in _strip_frontmatter(text).splitlines():
                stripped = line.strip()
                if stripped.startswith("#"):
                    title = stripped.lstrip("#").strip()
                    break
        if not title:
            title = file_path.stem.replace("_", " ")

        due_raw = meta.get("due_date") or meta.get("due") or meta.get("date")
        due_date = due_raw or _mtime_iso(file_path)[:10]

        items.append(
            {
                "id": file_path.stem,
                "title": title,
                "progress": progress,
                "owner": meta.get("owner") or meta.get("actor") or "claude_code",
                "dueDate": due_date,
                "steps": steps,
            }
        )

    return items


def _normalize_audit_status(entry: Dict[str, Any]) -> str:
    raw = str(entry.get("status", "")).lower()
    if raw in {"success", "ok", "done"}:
        return "success"
    if raw in {"failed", "error"}:
        return "failed"

    result = str(entry.get("result", "")).lower()
    if any(token in result for token in ["success", "ok", "done"]):
        return "success"
    if any(token in result for token in ["fail", "error"]):
        return "failed"
    return "success"


def _load_audit() -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    try:
        if not LOGS.exists():
            return events
        log_files = sorted(LOGS.glob("*.json"), reverse=True)
    except Exception:
        return events

    for file_path in log_files:
        if file_path.name in {"processed_approvals.json", "service_health.json"}:
            continue
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, list):
            continue
        for index, entry in enumerate(payload):
            if not isinstance(entry, dict):
                continue
            timestamp = _to_iso_or_now(
                str(entry.get("timestamp")) if entry.get("timestamp") else None,
                fallback=datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc),
            )
            target = (
                entry.get("target")
                or entry.get("recipient")
                or entry.get("to")
                or entry.get("file")
                or "n/a"
            )
            events.append(
                {
                    "id": f"{file_path.stem}-{index}",
                    "actionType": entry.get("action_type", "unknown"),
                    "actor": entry.get("actor") or entry.get("component") or "system",
                    "target": str(target),
                    "status": _normalize_audit_status(entry),
                    "timestamp": timestamp,
                }
            )

    events.sort(key=lambda event: event["timestamp"], reverse=True)
    return events[:200]


def _humanize_last_seen(iso_value: Optional[str]) -> str:
    if not iso_value:
        return "never"
    normalized = iso_value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except Exception:
        return "unknown"

    delta = datetime.now(timezone.utc) - dt.astimezone(timezone.utc)
    minutes = int(delta.total_seconds() // 60)
    if minutes <= 1:
        return "just now"
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"


def _map_health_status(value: Optional[str]) -> str:
    normalized = (value or "").lower()
    if normalized in {"healthy", "up", "ok"}:
        return "healthy"
    if normalized in {"degraded", "warning"}:
        return "degraded"
    if normalized in {"down", "offline", "failed", "unknown"}:
        return "offline"
    return "degraded"


def _load_health() -> List[Dict[str, Any]]:
    health_file = LOGS / "service_health.json"
    data: Dict[str, Any] = {}
    if health_file.exists():
        try:
            payload = json.loads(health_file.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                data = payload
        except Exception:
            data = {}

    response: List[Dict[str, Any]] = []
    for watcher in KNOWN_WATCHERS:
        item = data.get(watcher, {}) if isinstance(data.get(watcher), dict) else {}
        status = _map_health_status(item.get("status"))
        last_check = item.get("last_check") or item.get("updated_at")
        response.append(
            {
                "name": watcher,
                "status": status,
                "lastSeen": _humanize_last_seen(last_check),
                "interval": DEFAULT_INTERVALS.get(watcher, "unknown"),
            }
        )
    return response


def _approval_file_by_id(approval_id: str) -> Optional[Path]:
    candidate = PENDING_APPROVAL / f"{approval_id}.md"
    if candidate.exists():
        return candidate
    try:
        for file_path in PENDING_APPROVAL.glob("*.md"):
            if file_path.stem == approval_id:
                return file_path
    except Exception:
        return None
    return None


def _load_approval_detail(approval_id: str) -> Optional[Dict[str, Any]]:
    file_path = _approval_file_by_id(approval_id)
    if file_path is None:
        return None

    text = _safe_read_text(file_path)
    meta = _extract_frontmatter(text)
    amount = _parse_amount(meta.get("amount"))
    priority = _priority(meta.get("priority"))
    requested_at = _to_iso_or_now(
        meta.get("requested_at") or meta.get("requested") or meta.get("timestamp"),
        fallback=datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc),
    )

    payload: Dict[str, Any] = {
        "id": file_path.stem,
        "action": meta.get("action") or meta.get("action_type") or meta.get("subject") or file_path.stem,
        "target": meta.get("target") or meta.get("to") or meta.get("recipient") or "Unspecified target",
        "reason": meta.get("reason") or _extract_excerpt(text),
        "requestedAt": requested_at,
        "riskLevel": _risk_from(priority=priority, amount=amount),
    }
    if amount is not None:
        payload["amount"] = round(amount, 2)
    return payload


def _load_briefings() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for file_path in sorted(BRIEFINGS.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True) if BRIEFINGS.exists() else []:
        iso = _mtime_iso(file_path)
        dt = _parse_iso_date(iso) or datetime.now(timezone.utc)
        week_label = f"{dt.year}-W{dt.isocalendar().week:02d}"
        title = file_path.stem.replace("_", " ")
        items.append(
            {
                "id": file_path.stem,
                "title": title,
                "date": iso[:10],
                "weekLabel": week_label,
                "filePath": str(file_path),
            }
        )
    return items


def _load_briefing_detail(briefing_id: str) -> Optional[Dict[str, Any]]:
    target = BRIEFINGS / f"{briefing_id}.md"
    if not target.exists():
        for file_path in BRIEFINGS.glob("*.md") if BRIEFINGS.exists() else []:
            if file_path.stem == briefing_id:
                target = file_path
                break
    if not target.exists():
        return None
    iso = _mtime_iso(target)
    dt = _parse_iso_date(iso) or datetime.now(timezone.utc)
    return {
        "id": target.stem,
        "title": target.stem.replace("_", " "),
        "date": iso[:10],
        "weekLabel": f"{dt.year}-W{dt.isocalendar().week:02d}",
        "markdown": _safe_read_text(target),
        "filePath": str(target),
    }


def _detect_erp_sync_status(records: List[Dict[str, Any]]) -> Literal["healthy", "degraded", "offline"]:
    odoo = [r for r in records if "odoo" in r["actionType"].lower() or "invoice" in r["actionType"].lower() or "payment" in r["actionType"].lower()]
    if not odoo:
        return "degraded"
    failures = [r for r in odoo if r["status"] == "failed"]
    if not failures:
        return "healthy"
    ratio = len(failures) / max(1, len(odoo))
    if ratio > 0.4:
        return "offline"
    return "degraded"


def _parse_month(iso_ts: str) -> str:
    return iso_ts[:7]


def _cpu_load_percent() -> float:
    try:
        load1, _, _ = os.getloadavg()
        cpu_count = os.cpu_count() or 1
        return round(min(100.0, (load1 / cpu_count) * 100.0), 2)
    except Exception:
        return 0.0


def _watchdog_status(health: List[Dict[str, Any]]) -> Literal["healthy", "degraded", "offline"]:
    if not health:
        return "offline"
    states = {item["status"] for item in health}
    if states == {"healthy"}:
        return "healthy"
    if "offline" in states:
        return "degraded" if "healthy" in states else "offline"
    return "degraded"


def _request_role(request: Request) -> str:
    role = request.headers.get("x-user-role", "").strip().lower()
    return role if role in ROLE_PERMISSIONS else "observer"


def _enforce_permission(request: Request, permission: str) -> None:
    if not RBAC_ENFORCE:
        return
    role = _request_role(request)
    allowed = ROLE_PERMISSIONS.get(role, set())
    if permission not in allowed:
        raise HTTPException(status_code=403, detail=f"Role '{role}' lacks permission '{permission}'")


@app.get("/healthz", response_model=HealthzResponse)
def healthz() -> HealthzResponse:
    return HealthzResponse(status="ok")


@app.get("/api/tasks", response_model=List[TaskItem])
def tasks(
    limit: int = Query(default=100, ge=1, le=500),
    priority: Optional[Literal["low", "medium", "high"]] = None,
    status: Optional[Literal["pending", "in_progress", "approved", "done"]] = None,
    source: Optional[str] = None,
    task_type: Optional[str] = Query(default=None, alias="type"),
) -> List[TaskItem]:
    records = _load_tasks()
    if priority:
        records = [item for item in records if item["priority"] == priority]
    if status:
        records = [item for item in records if item["status"] == status]
    if source:
        records = [item for item in records if item["source"].lower() == source.strip().lower()]
    if task_type:
        records = [item for item in records if item["type"].lower() == task_type.strip().lower()]
    return [TaskItem(**item) for item in _apply_limit(records, limit)]


@app.get("/api/tasks/{task_id}", response_model=TaskDetail)
def task_detail(task_id: str) -> TaskDetail:
    record = _load_task_detail(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return TaskDetail(**record)


@app.get("/api/approvals", response_model=List[ApprovalItem])
def approvals(
    limit: int = Query(default=100, ge=1, le=500),
    risk_level: Optional[Literal["low", "medium", "high"]] = Query(default=None, alias="riskLevel"),
    min_amount: Optional[float] = Query(default=None, ge=0),
) -> List[ApprovalItem]:
    records = _load_approvals()
    if risk_level:
        records = [item for item in records if item["riskLevel"] == risk_level]
    if min_amount is not None:
        records = [item for item in records if float(item.get("amount") or 0.0) >= min_amount]
    return [ApprovalItem(**item) for item in _apply_limit(records, limit)]


@app.get("/api/approvals/{approval_id}", response_model=ApprovalItem)
def approval_detail(approval_id: str) -> ApprovalItem:
    record = _load_approval_detail(approval_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Approval '{approval_id}' not found")
    return ApprovalItem(**record)


@app.get("/api/plans", response_model=List[PlanItem])
def plans(
    limit: int = Query(default=100, ge=1, le=500),
    owner: Optional[str] = None,
    min_progress: int = Query(default=0, ge=0, le=100),
    max_progress: int = Query(default=100, ge=0, le=100),
) -> List[PlanItem]:
    records = _load_plans()
    if owner:
        records = [item for item in records if item["owner"].lower() == owner.strip().lower()]
    low = min(min_progress, max_progress)
    high = max(min_progress, max_progress)
    records = [item for item in records if low <= int(item["progress"]) <= high]
    return [PlanItem(**item) for item in _apply_limit(records, limit)]


@app.get("/api/audit", response_model=List[AuditItem])
def audit(
    limit: int = Query(default=200, ge=1, le=500),
    status: Optional[Literal["success", "failed"]] = None,
    action_type: Optional[str] = Query(default=None, alias="actionType"),
    actor: Optional[str] = None,
) -> List[AuditItem]:
    records = _load_audit()
    if status:
        records = [item for item in records if item["status"] == status]
    if action_type:
        records = [item for item in records if item["actionType"].lower() == action_type.strip().lower()]
    if actor:
        records = [item for item in records if item["actor"].lower() == actor.strip().lower()]
    return [AuditItem(**item) for item in _apply_limit(records, limit)]


@app.get("/api/health", response_model=List[HealthItem])
def health(
    status: Optional[Literal["healthy", "degraded", "offline"]] = None,
) -> List[HealthItem]:
    records = _load_health()
    if status:
        records = [item for item in records if item["status"] == status]
    return [HealthItem(**item) for item in records]


@app.get("/api/dashboard", response_model=DashboardResponse)
def dashboard(
    tasks_limit: int = Query(default=20, ge=1, le=500),
    approvals_limit: int = Query(default=20, ge=1, le=500),
    audit_limit: int = Query(default=50, ge=1, le=500),
) -> DashboardResponse:
    return DashboardResponse(
        tasks=[TaskItem(**item) for item in _apply_limit(_load_tasks(), tasks_limit)],
        approvals=[ApprovalItem(**item) for item in _apply_limit(_load_approvals(), approvals_limit)],
        health=[HealthItem(**item) for item in _load_health()],
        auditTrail=[AuditItem(**item) for item in _apply_limit(_load_audit(), audit_limit)],
    )


@app.post("/api/approvals/{approval_id}/approve", response_model=ActionResponse)
def approve_approval(approval_id: str, request: Request) -> ActionResponse:
    _enforce_permission(request, "approve_actions")
    return _move_approval_file(approval_id=approval_id, destination=APPROVED)


@app.post("/api/approvals/{approval_id}/reject", response_model=ActionResponse)
def reject_approval(approval_id: str, request: Request) -> ActionResponse:
    _enforce_permission(request, "approve_actions")
    return _move_approval_file(approval_id=approval_id, destination=REJECTED)


@app.get("/api/watchers", response_model=List[WatcherControlItem])
def watchers() -> List[WatcherControlItem]:
    pid_map = _load_watcher_pid_map()
    return [_watcher_item(name, pid_map) for name in WATCHER_SCRIPTS]


@app.post("/api/watchers/{watcher_name}/start", response_model=WatcherControlResponse)
def start_watcher(watcher_name: str, request: Request) -> WatcherControlResponse:
    _enforce_permission(request, "watcher_control")
    return _start_watcher(watcher_name)


@app.post("/api/watchers/{watcher_name}/stop", response_model=WatcherControlResponse)
def stop_watcher(watcher_name: str, request: Request) -> WatcherControlResponse:
    _enforce_permission(request, "watcher_control")
    return _stop_watcher(watcher_name)


@app.post("/api/watchers/{watcher_name}/restart", response_model=WatcherControlResponse)
def restart_watcher(watcher_name: str, request: Request) -> WatcherControlResponse:
    _enforce_permission(request, "watcher_control")
    stop_result = _stop_watcher(watcher_name)
    if stop_result.status == "error":
        return stop_result
    return _start_watcher(watcher_name)


@app.post("/api/watchers/start", response_model=WatcherControlResponse)
def start_watcher_query(
    request: Request,
    name: str = Query(..., description="Watcher name, e.g. gmail or gmail_watcher"),
) -> WatcherControlResponse:
    _enforce_permission(request, "watcher_control")
    return _start_watcher(name)


@app.post("/api/watchers/stop", response_model=WatcherControlResponse)
def stop_watcher_query(
    request: Request,
    name: str = Query(..., description="Watcher name, e.g. gmail or gmail_watcher"),
) -> WatcherControlResponse:
    _enforce_permission(request, "watcher_control")
    return _stop_watcher(name)


@app.post("/api/ai/run-task", response_model=ActionResponse)
def run_ai_task(payload: RunTaskRequest, request: Request) -> ActionResponse:
    _enforce_permission(request, "manual_override")
    return _queue_manual_task(payload)


@app.post("/api/ai/create-draft", response_model=ActionResponse)
def create_email_draft(payload: CreateDraftRequest, request: Request) -> ActionResponse:
    _enforce_permission(request, "manual_override")
    return _create_email_draft(payload)


@app.post("/api/ai/email/request-approval", response_model=ActionResponse)
def request_email_approval(payload: CreateDraftRequest, request: Request) -> ActionResponse:
    _enforce_permission(request, "manual_override")
    return _request_email_approval(payload)


@app.get("/api/ai/drafts", response_model=List[DraftHistoryItem])
def draft_history(limit: int = Query(default=20, ge=1, le=100)) -> List[DraftHistoryItem]:
    return _load_draft_history(limit)


@app.get("/api/ai/loop/status", response_model=AiLoopStatusResponse)
def ai_loop_status() -> AiLoopStatusResponse:
    return _current_ai_loop_status()


@app.post("/api/ai/loop/start", response_model=ActionResponse)
def ai_loop_start(
    request: Request,
    task: str = Query(
        default="Process pending files in /Needs_Action, create plans, route sensitive actions to /Pending_Approval, execute safe actions, and move completed work to /Done.",
        min_length=10,
        max_length=4000,
    ),
    max_iterations: int = Query(default=20, ge=1, le=200),
) -> ActionResponse:
    _enforce_permission(request, "manual_override")
    return _start_ai_loop(task=task, max_iterations=max_iterations)


@app.post("/api/ai/loop/stop", response_model=ActionResponse)
def ai_loop_stop(request: Request) -> ActionResponse:
    _enforce_permission(request, "manual_override")
    return _stop_ai_loop()


@app.post("/api/ai/process-approved", response_model=ActionResponse)
def ai_process_approved(request: Request) -> ActionResponse:
    _enforce_permission(request, "manual_override")
    return _run_orchestrator_command("process-approved")


@app.post("/api/ai/process-all", response_model=ActionResponse)
def ai_process_all(request: Request) -> ActionResponse:
    _enforce_permission(request, "manual_override")
    return _run_orchestrator_command("process-all")


@app.post("/api/maintenance/cleanup-needs-action", response_model=CleanupResponse)
def cleanup_needs_action(
    request: Request,
    pattern: str = Query(..., min_length=1, max_length=255),
    dry_run: bool = Query(default=False),
) -> CleanupResponse:
    _enforce_permission(request, "manual_override")
    return _cleanup_needs_action(pattern=pattern, dry_run=dry_run)


@app.get("/api/executive/summary", response_model=ExecutiveSummaryResponse)
def executive_summary() -> ExecutiveSummaryResponse:
    revenue_series = [RevenuePoint(**item) for item in _load_revenue_series()]
    revenue_total = round(sum(point.value for point in revenue_series), 2)

    watcher_status = watchers()
    watchers_running = sum(1 for item in watcher_status if item.running)
    watchers_stopped = len(watcher_status) - watchers_running

    recent = [AuditItem(**item) for item in _apply_limit(_load_audit(), 20)]
    completed = len([item for item in _load_raw_logs() if item["status"] == "success"])

    return ExecutiveSummaryResponse(
        revenueTotal=revenue_total,
        revenueSeries=revenue_series,
        activeTaskCount=len(_load_tasks()),
        pendingApprovals=len(_load_approvals()),
        completedTaskCount=completed,
        watchersRunning=watchers_running,
        watchersStopped=watchers_stopped,
        watcherHealth=[HealthItem(**item) for item in _load_health()],
        recentActivity=recent,
    )


@app.get("/api/system/monitor", response_model=SystemMonitorResponse)
def system_monitor() -> SystemMonitorResponse:
    raw_logs = _load_raw_logs()
    last_execution = raw_logs[0]["timestamp"] if raw_logs else None
    loop_iterations = len(raw_logs)
    errors = [LogRecord(**item) for item in raw_logs if item["status"] == "failed"][:25]

    return SystemMonitorResponse(
        claudeStatus=_claude_status(last_execution),
        watcherStatus=watchers(),
        watcherHealth=[HealthItem(**item) for item in _load_health()],
        lastExecutionTime=last_execution,
        loopIterationCount=loop_iterations,
        errorAlerts=errors,
    )


@app.get("/api/logs", response_model=List[LogRecord])
def logs(
    channel: Optional[Literal["email", "payment", "social", "system", "file", "other"]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(default=200, ge=1, le=1000),
) -> List[LogRecord]:
    records = _load_raw_logs()

    if channel:
        records = [item for item in records if item["channel"] == channel]

    start = _parse_iso_date(date_from)
    end = _parse_iso_date(date_to)
    if start:
        records = [item for item in records if (_parse_iso_date(item["timestamp"]) or start) >= start]
    if end:
        # include full day for date-only inputs
        end_cap = end.replace(hour=23, minute=59, second=59) if len(date_to or "") == 10 else end
        records = [item for item in records if (_parse_iso_date(item["timestamp"]) or end_cap) <= end_cap]

    return [LogRecord(**item) for item in _apply_limit(records, limit)]


@app.get("/api/briefings", response_model=List[BriefingFile])
def briefings() -> List[BriefingFile]:
    return [BriefingFile(**item) for item in _load_briefings()]


@app.get("/api/briefings/{briefing_id}", response_model=BriefingDetail)
def briefing_detail(briefing_id: str) -> BriefingDetail:
    payload = _load_briefing_detail(briefing_id)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"Briefing '{briefing_id}' not found")
    return BriefingDetail(**payload)


@app.get("/api/accounting/summary", response_model=AccountingSummaryResponse)
def accounting_summary() -> AccountingSummaryResponse:
    raw_logs = _load_raw_logs()
    monthly: Dict[str, float] = {}
    subscription_revenue = 0.0

    for record in raw_logs:
        if record["channel"] != "payment":
            continue
        amount = _extract_revenue_from_raw(record)
        if amount <= 0:
            continue
        month = _parse_month(record["timestamp"])
        monthly[month] = monthly.get(month, 0.0) + amount
        raw = record.get("raw", {})
        if isinstance(raw, dict):
            message = str(raw.get("message", "")).lower()
            if "subscription" in message or "recurring" in message:
                subscription_revenue += amount

    monthly_series = [RevenuePoint(date=f"{month}-01", value=round(value, 2)) for month, value in sorted(monthly.items())]
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    current_value = round(monthly.get(current_month, 0.0), 2)

    flagged_costs = [
        LogRecord(**item)
        for item in raw_logs
        if item["channel"] == "payment"
        and (
            item["status"] == "failed"
            or _extract_revenue_from_raw(item) >= 500
            or "anomaly" in str(item.get("raw", {})).lower()
        )
    ][:50]

    return AccountingSummaryResponse(
        monthlyRevenue=monthly_series,
        currentMonthRevenue=current_value,
        subscriptionRevenue=round(subscription_revenue, 2),
        flaggedCosts=flagged_costs,
        erpSyncStatus=_detect_erp_sync_status(raw_logs),
    )


@app.get("/api/execution/monitor", response_model=ExecutionMonitorResponse)
def execution_monitor() -> ExecutionMonitorResponse:
    tasks = _load_tasks()
    running_tasks = [
        ExecutionTask(
            id=item["id"],
            title=item["title"],
            status=item["status"],
            source=item["source"],
            progress=35 if item["status"] == "in_progress" else 10 if item["status"] == "pending" else 100,
        )
        for item in tasks[:100]
    ]
    plans_payload = [PlanItem(**item) for item in _load_plans()]
    raw_logs = _load_raw_logs()
    promise_hits = 0
    for item in raw_logs:
        raw = item.get("raw", {})
        if isinstance(raw, dict):
            blob = json.dumps(raw).lower()
            if "task_complete" in blob or "<promise>" in blob:
                promise_hits += 1

    return ExecutionMonitorResponse(
        runningTasks=running_tasks,
        planVisualization=plans_payload,
        loopIterationCount=len(raw_logs),
        completionPromisesDetected=promise_hits,
    )


@app.get("/api/oversight/queue", response_model=OversightQueueResponse)
def oversight_queue() -> OversightQueueResponse:
    all_approvals = [ApprovalItem(**item) for item in _load_approvals()]
    high_risk = [item for item in all_approvals if item.riskLevel == "high"]
    financial = [
        item
        for item in all_approvals
        if item.amount is not None or any(token in item.action.lower() for token in ["invoice", "payment", "odoo", "amount"])
    ]
    social = [
        item
        for item in all_approvals
        if any(token in item.action.lower() for token in ["linkedin", "twitter", "facebook", "instagram", "social", "post"])
    ]
    return OversightQueueResponse(
        highRiskActions=high_risk,
        financialApprovals=financial,
        socialApprovals=social,
        totalPending=len(all_approvals),
    )


@app.get("/api/compliance/panel", response_model=CompliancePanelResponse)
def compliance_panel(limit: int = Query(default=300, ge=1, le=1000)) -> CompliancePanelResponse:
    records = _apply_limit(_load_raw_logs(), limit)
    action_logs = [LogRecord(**item) for item in records]
    approval_history = [LogRecord(**item) for item in records if "approval" in item["actionType"].lower()]
    failure_recovery = [
        LogRecord(**item)
        for item in records
        if item["status"] == "failed"
        or "retry" in item["actionType"].lower()
        or "recovery" in item["actionType"].lower()
    ]
    retry_attempts = 0
    for item in records:
        raw = item.get("raw", {})
        if isinstance(raw, dict):
            retry_attempts += int(raw.get("retry_count", 0) or 0)
            if "retry" in json.dumps(raw).lower():
                retry_attempts += 1

    return CompliancePanelResponse(
        actionLogs=action_logs,
        approvalHistory=approval_history[:100],
        failureRecoveryLogs=failure_recovery[:100],
        retryAttempts=retry_attempts,
    )


@app.get("/api/system/health", response_model=SystemHealthResponse)
def system_health() -> SystemHealthResponse:
    process_state = watchers()
    health = _load_health()
    queue_size = {
        "needs_action": len(_load_tasks()),
        "pending_approval": len(_load_approvals()),
        "plans": len(_load_plans()),
        "logs_today": len(_load_raw_logs()),
    }
    return SystemHealthResponse(
        watchdogStatus=_watchdog_status(health),
        cpuLoadPercent=_cpu_load_percent(),
        processStatus=process_state,
        queueSize=queue_size,
    )


@app.websocket("/ws/events")
async def ws_events(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "summary": executive_summary().dict(),
                "monitor": system_monitor().dict(),
                "health": system_health().dict(),
            }
            await websocket.send_json(payload)
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        return
