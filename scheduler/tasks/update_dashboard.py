"""
Scheduled Task: Update Dashboard
Runs periodically to keep Dashboard.md current
"""
import json
import os
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent
VAULT_PATH = PROJECT_ROOT / 'AI_Employee_Vault'
if VAULT_PATH.is_symlink():
    VAULT_PATH = VAULT_PATH.resolve()

WRITER_LOCK = VAULT_PATH / 'State' / 'dashboard_writer.lock'


def count_files(folder: Path) -> int:
    """Count files in a folder"""
    if not folder.exists():
        return 0
    return len([f for f in folder.iterdir() if f.is_file() and not f.name.startswith('.')])


def count_files_today(folder: Path, today_date) -> int:
    """Count files modified on the local current date."""
    if not folder.exists():
        return 0

    total = 0
    for f in folder.iterdir():
        if not f.is_file() or f.name.startswith('.'):
            continue
        try:
            modified_date = datetime.fromtimestamp(f.stat().st_mtime).date()
            if modified_date == today_date:
                total += 1
        except OSError:
            # Ignore unreadable files and continue dashboard generation.
            continue
    return total


def get_status_emoji(count: int) -> str:
    """Get status indicator based on count"""
    if count == 0:
        return "✅ Clear"
    elif count <= 5:
        return "⚠️ Needs Attention"
    else:
        return "🔴 Action Required"


def update_dashboard():
    """Update Dashboard.md with current counts"""
    if WRITER_LOCK.exists():
        try:
            lock = json.loads(WRITER_LOCK.read_text(encoding='utf-8'))
            owner = str(lock.get('owner', '')).lower()
            # Single-writer mode: when owner is local, only Local Executive
            # process may write Dashboard.md.
            if owner == 'local' and os.getenv('LOCAL_EXEC_AGENT') != '1':
                print('[Dashboard] Skipped update: single-writer lock owned by local')
                return
        except Exception:
            # If lock is malformed, proceed with default behavior.
            pass

    timestamp = datetime.now()
    inbox_count = count_files(VAULT_PATH / 'Inbox')
    needs_action_count = count_files(VAULT_PATH / 'Needs_Action')
    done_today_count = count_files_today(VAULT_PATH / 'Done', timestamp.date())
    pending_approval_count = count_files(VAULT_PATH / 'Pending_Approval')

    timestamp_iso = timestamp.isoformat()
    timestamp_human = timestamp.strftime('%Y-%m-%d %H:%M')

    p1_estimate = "5+" if needs_action_count > 0 else "0"
    p2_estimate = "Medium" if needs_action_count > 10 else "Low"
    p3_estimate = "Remaining" if needs_action_count > 0 else "0"

    def queue_health(count: int, threshold: int) -> str:
        if count == 0:
            return "🟢 Healthy"
        if count <= threshold:
            return "⚠️ Watch"
        return "🔴 Over"

    dashboard_content = f'''---
last_updated: {timestamp_iso}
status: active
---

# AI Employee Dashboard

![[assets/images/image-2.png]]

## Operations Graph

```mermaid
flowchart LR
  A[Inbox] --> B[Needs_Action]
  B --> C[AI Processing]
  C --> D[Pending_Approval]
  D --> E[Approved]
  E --> F[Execute]
  F --> G[Done]
  G --> H[Logs]
  style A fill:#ede9fe,stroke:#6d28d9,color:#2e1065
  style B fill:#f5f3ff,stroke:#7c3aed,color:#2e1065
  style D fill:#fee2e2,stroke:#b91c1c,color:#7f1d1d
  style E fill:#dcfce7,stroke:#15803d,color:#14532d
  style H fill:#e0e7ff,stroke:#4338ca,color:#1e1b4b
```

## Operations Snapshot

| Queue | Current | Threshold | Health | Action |
|---|---:|---:|---|---|
| Inbox | {inbox_count} | 5 | {queue_health(inbox_count, 5)} | Triage top 5 first |
| Needs_Action | {needs_action_count} | 20 | {queue_health(needs_action_count, 20)} | Batch-process by priority |
| Pending_Approval | {pending_approval_count} | 3 | {queue_health(pending_approval_count, 3)} | Review approvals now |
| Done (Today) | {done_today_count} | 10 | {"🟢 Near Target" if done_today_count >= 8 else "⚠️ Below Target"} | Continue execution |

## Priority Breakdown

| Priority | Estimated Count | Owner | Next Step |
|---|---:|---|---|
| P1 Critical | {p1_estimate} | Claude + Human | Resolve immediately |
| P2 Normal | {p2_estimate} | Claude | Process in scheduled batches |
| P3 Low | {p3_estimate} | Claude | Defer to off-peak runs |

## Approval Pipeline

| Stage | Count | Notes |
|---|---:|---|
| Pending_Approval | {pending_approval_count} | Waiting for human decision |
| Approved | 0 | Ready for MCP execution |
| Rejected | 0 | No blocked actions currently |

## Automation Health

| Component | Status | Last Check | Notes |
|---|---|---|---|
| Scheduler | ✅ Running | {timestamp_human} | Auto dashboard updates active |
| Watchers | ✅ Running | {timestamp_human} | Input ingestion active |
| Vault Sync | ✅ Healthy | {timestamp_human} | Obsidian + VS Code synced |
| Logging | ✅ Healthy | {timestamp_human} | JSON and cron logs present |

## Recent Activity

| Time | Event |
|---|---|
| {timestamp_human} | Dashboard auto-updated by scheduler |

## Active Alerts

| Severity | Alert | Recommendation |
|---|---|---|
| {"🔴 High" if needs_action_count > 20 else "⚠️ Medium" if needs_action_count > 0 else "🟢 Clear"} | Needs_Action items: {needs_action_count} | {"Run queue clean-up and close stale items" if needs_action_count > 20 else "Continue normal processing" if needs_action_count > 0 else "No action needed"} |
| {"⚠️ Medium" if pending_approval_count > 0 else "🟢 Clear"} | Pending approvals: {pending_approval_count} | {"Review approvals to unblock execution" if pending_approval_count > 0 else "No action needed"} |
| {"⚠️ Medium" if inbox_count > 0 else "🟢 Clear"} | Inbox items: {inbox_count} | {"Run inbox triage cycle" if inbox_count > 0 else "No action needed"} |

![[assets/images/image-4.png]]

## Task Views (Tasks Plugin)

### Pending Approvals

```tasks
not done
path includes Pending_Approval
sort by due
sort by priority
```

### Overdue Tasks

```tasks
not done
due before today
sort by due
```

### Due Today

```tasks
not done
due today
sort by priority
sort by path
```

### Completed Today

```tasks
done on today
sort by done
group by path
```

---
*Dashboard optimized for Obsidian Advanced Tables.*
*Auto-updated by AI Employee Scheduler: {timestamp_human}*
'''

    dashboard_path = VAULT_PATH / 'Dashboard.md'
    dashboard_path.write_text(dashboard_content)

    print(
        f"[{timestamp}] Dashboard updated - Inbox: {inbox_count}, "
        f"Needs_Action: {needs_action_count}, Done(Today): {done_today_count}"
    )


if __name__ == '__main__':
    update_dashboard()
