"""
Scheduled Task: Update Dashboard
Runs periodically to keep Dashboard.md current
"""
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent
VAULT_PATH = PROJECT_ROOT / 'AI_Employee_Vault'
if VAULT_PATH.is_symlink():
    VAULT_PATH = VAULT_PATH.resolve()


def count_files(folder: Path) -> int:
    """Count files in a folder"""
    if not folder.exists():
        return 0
    return len([f for f in folder.iterdir() if f.is_file() and not f.name.startswith('.')])


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
    inbox_count = count_files(VAULT_PATH / 'Inbox')
    needs_action_count = count_files(VAULT_PATH / 'Needs_Action')
    done_count = count_files(VAULT_PATH / 'Done')
    pending_approval_count = count_files(VAULT_PATH / 'Pending_Approval')

    timestamp = datetime.now()

    dashboard_content = f'''---
last_updated: {timestamp.isoformat()}
status: active
---

# AI Employee Dashboard

## Quick Status
| Category | Count | Status |
|----------|-------|--------|
| Inbox | {inbox_count} | {get_status_emoji(inbox_count)} |
| Needs Action | {needs_action_count} | {get_status_emoji(needs_action_count)} |
| Done Today | {done_count} | - |
| Pending Approval | {pending_approval_count} | {get_status_emoji(pending_approval_count)} |

## Recent Activity
- [{timestamp.strftime('%Y-%m-%d %H:%M')}] Dashboard auto-updated by scheduler

## Alerts
'''

    if needs_action_count > 10:
        dashboard_content += f"- 🔴 High volume: {needs_action_count} items in Needs_Action\n"
    if pending_approval_count > 0:
        dashboard_content += f"- ⚠️ {pending_approval_count} items awaiting approval\n"
    if inbox_count > 0:
        dashboard_content += f"- 📥 {inbox_count} new items in Inbox\n"

    if needs_action_count == 0 and pending_approval_count == 0 and inbox_count == 0:
        dashboard_content += "- ✅ All clear!\n"

    dashboard_content += f'''
---
*Auto-updated by AI Employee Scheduler: {timestamp.strftime('%Y-%m-%d %H:%M')}*
'''

    dashboard_path = VAULT_PATH / 'Dashboard.md'
    dashboard_path.write_text(dashboard_content)

    print(f"[{timestamp}] Dashboard updated - Inbox: {inbox_count}, Needs_Action: {needs_action_count}")


if __name__ == '__main__':
    update_dashboard()
