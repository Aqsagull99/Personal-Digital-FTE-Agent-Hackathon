"""
Comprehensive Audit Logger - Gold Tier Requirement #9
Centralized logging for all AI Employee actions with:
- JSON structured logs
- 90-day retention
- Action categorization
- Human-readable audit trail
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Literal
from enum import Enum


class ActionCategory(str, Enum):
    EMAIL = "email"
    SOCIAL = "social"
    PAYMENT = "payment"
    FILE = "file"
    TASK = "task"
    APPROVAL = "approval"
    SYSTEM = "system"
    ACCOUNTING = "accounting"


class ApprovalStatus(str, Enum):
    AUTO = "auto_approved"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NA = "not_required"


class AuditLogger:
    """
    Centralized audit logging for AI Employee.

    Logs all actions in JSON format with:
    - Timestamp
    - Action type & category
    - Actor (claude_code, watcher, user)
    - Target
    - Parameters
    - Approval status
    - Result
    """

    def __init__(self, vault_path: Optional[str] = None):
        if vault_path:
            self.vault_path = Path(vault_path)
        else:
            # Try to find vault
            project_root = Path(__file__).parent.parent
            vault_link = project_root / 'AI_Employee_Vault'
            if vault_link.exists():
                self.vault_path = vault_link.resolve() if vault_link.is_symlink() else vault_link
            else:
                self.vault_path = Path.home() / 'AI_Employee_Vault'

        self.logs_path = self.vault_path / 'Logs'
        self.logs_path.mkdir(parents=True, exist_ok=True)

        # Retention period
        self.retention_days = 90

    def _get_log_file(self, date: Optional[datetime] = None) -> Path:
        """Get log file path for a specific date"""
        if date is None:
            date = datetime.now()
        return self.logs_path / f'{date.strftime("%Y-%m-%d")}.json'

    def _load_logs(self, date: Optional[datetime] = None) -> list:
        """Load existing logs for a date"""
        log_file = self._get_log_file(date)
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save_logs(self, logs: list, date: Optional[datetime] = None):
        """Save logs for a date"""
        log_file = self._get_log_file(date)
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2, default=str)

    def log(
        self,
        action_type: str,
        category: ActionCategory,
        target: str,
        parameters: Optional[Dict[str, Any]] = None,
        actor: str = "claude_code",
        approval_status: ApprovalStatus = ApprovalStatus.NA,
        approved_by: Optional[str] = None,
        result: Literal["success", "failure", "pending"] = "success",
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict:
        """
        Log an action with full audit trail.

        Args:
            action_type: Specific action (e.g., "email_send", "invoice_create")
            category: Action category for filtering
            target: Target of action (email, file, invoice number, etc.)
            parameters: Action parameters
            actor: Who performed action (claude_code, gmail_watcher, user, etc.)
            approval_status: Whether approval was needed/given
            approved_by: Who approved (if applicable)
            result: Action result
            error_message: Error details if failed
            metadata: Additional context

        Returns:
            The log entry that was created
        """
        timestamp = datetime.now()

        entry = {
            "timestamp": timestamp.isoformat(),
            "action_type": action_type,
            "category": category.value if isinstance(category, ActionCategory) else category,
            "actor": actor,
            "target": target,
            "parameters": parameters or {},
            "approval_status": approval_status.value if isinstance(approval_status, ApprovalStatus) else approval_status,
            "approved_by": approved_by,
            "result": result,
            "error_message": error_message,
            "metadata": metadata or {}
        }

        # Load, append, save
        logs = self._load_logs(timestamp)
        logs.append(entry)
        self._save_logs(logs, timestamp)

        return entry

    # Convenience methods for common actions

    def log_email_sent(
        self,
        to: str,
        subject: str,
        approval_status: ApprovalStatus = ApprovalStatus.APPROVED,
        approved_by: str = "user"
    ):
        """Log email send action"""
        return self.log(
            action_type="email_send",
            category=ActionCategory.EMAIL,
            target=to,
            parameters={"subject": subject},
            approval_status=approval_status,
            approved_by=approved_by
        )

    def log_email_processed(self, email_id: str, from_addr: str, subject: str):
        """Log email processing"""
        return self.log(
            action_type="email_processed",
            category=ActionCategory.EMAIL,
            target=email_id,
            parameters={"from": from_addr, "subject": subject},
            actor="gmail_watcher"
        )

    def log_social_post(
        self,
        platform: str,
        content_preview: str,
        approval_status: ApprovalStatus = ApprovalStatus.APPROVED
    ):
        """Log social media post"""
        return self.log(
            action_type=f"social_post_{platform}",
            category=ActionCategory.SOCIAL,
            target=platform,
            parameters={"content_preview": content_preview[:100]},
            approval_status=approval_status
        )

    def log_task_created(self, task_id: str, task_type: str, source: str):
        """Log task creation"""
        return self.log(
            action_type="task_created",
            category=ActionCategory.TASK,
            target=task_id,
            parameters={"type": task_type, "source": source},
            actor=source
        )

    def log_task_completed(self, task_id: str, task_type: str):
        """Log task completion"""
        return self.log(
            action_type="task_completed",
            category=ActionCategory.TASK,
            target=task_id,
            parameters={"type": task_type}
        )

    def log_invoice_created(
        self,
        invoice_number: str,
        amount: float,
        customer: str,
        approval_status: ApprovalStatus = ApprovalStatus.PENDING
    ):
        """Log invoice creation"""
        return self.log(
            action_type="invoice_created",
            category=ActionCategory.ACCOUNTING,
            target=invoice_number,
            parameters={"amount": amount, "customer": customer},
            approval_status=approval_status
        )

    def log_payment_recorded(
        self,
        payment_ref: str,
        amount: float,
        approval_status: ApprovalStatus = ApprovalStatus.APPROVED,
        approved_by: str = "user"
    ):
        """Log payment recording"""
        return self.log(
            action_type="payment_recorded",
            category=ActionCategory.PAYMENT,
            target=payment_ref,
            parameters={"amount": amount},
            approval_status=approval_status,
            approved_by=approved_by
        )

    def log_approval_request(self, request_type: str, request_id: str, details: Dict):
        """Log approval request creation"""
        return self.log(
            action_type="approval_requested",
            category=ActionCategory.APPROVAL,
            target=request_id,
            parameters={"type": request_type, **details},
            result="pending"
        )

    def log_approval_granted(self, request_id: str, approved_by: str = "user"):
        """Log approval granted"""
        return self.log(
            action_type="approval_granted",
            category=ActionCategory.APPROVAL,
            target=request_id,
            approval_status=ApprovalStatus.APPROVED,
            approved_by=approved_by
        )

    def log_error(
        self,
        action_type: str,
        category: ActionCategory,
        error_message: str,
        target: str = "system"
    ):
        """Log an error"""
        return self.log(
            action_type=action_type,
            category=category,
            target=target,
            result="failure",
            error_message=error_message
        )

    def log_system_event(self, event_type: str, details: Optional[Dict] = None):
        """Log system event (startup, shutdown, etc.)"""
        return self.log(
            action_type=event_type,
            category=ActionCategory.SYSTEM,
            target="system",
            parameters=details or {},
            actor="system"
        )

    # Query methods

    def get_logs_for_date(self, date: datetime) -> list:
        """Get all logs for a specific date"""
        return self._load_logs(date)

    def get_logs_for_period(self, days: int = 7) -> list:
        """Get logs for the past N days"""
        all_logs = []
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            all_logs.extend(self._load_logs(date))
        return sorted(all_logs, key=lambda x: x['timestamp'], reverse=True)

    def get_logs_by_category(self, category: ActionCategory, days: int = 7) -> list:
        """Get logs filtered by category"""
        all_logs = self.get_logs_for_period(days)
        cat_value = category.value if isinstance(category, ActionCategory) else category
        return [log for log in all_logs if log.get('category') == cat_value]

    def get_failed_actions(self, days: int = 7) -> list:
        """Get all failed actions"""
        all_logs = self.get_logs_for_period(days)
        return [log for log in all_logs if log.get('result') == 'failure']

    def get_pending_approvals(self) -> list:
        """Get pending approval requests"""
        all_logs = self.get_logs_for_period(7)
        return [
            log for log in all_logs
            if log.get('approval_status') == 'pending'
            and log.get('result') == 'pending'
        ]

    def cleanup_old_logs(self):
        """Remove logs older than retention period"""
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        removed = 0

        for log_file in self.logs_path.glob('*.json'):
            try:
                file_date = datetime.strptime(log_file.stem, '%Y-%m-%d')
                if file_date < cutoff:
                    log_file.unlink()
                    removed += 1
            except:
                pass

        return removed

    def generate_audit_report(self, days: int = 7) -> str:
        """Generate human-readable audit report"""
        logs = self.get_logs_for_period(days)

        # Count by category
        by_category = {}
        by_result = {"success": 0, "failure": 0, "pending": 0}

        for log in logs:
            cat = log.get('category', 'unknown')
            by_category[cat] = by_category.get(cat, 0) + 1
            result = log.get('result', 'unknown')
            if result in by_result:
                by_result[result] += 1

        report = f"""# Audit Report
## Period: Last {days} days
## Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Summary
- Total Actions: {len(logs)}
- Successful: {by_result['success']}
- Failed: {by_result['failure']}
- Pending: {by_result['pending']}

## By Category
"""
        for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
            report += f"- {cat.title()}: {count}\n"

        # Recent failures
        failures = self.get_failed_actions(days)
        if failures:
            report += f"\n## Recent Failures ({len(failures)})\n"
            for f in failures[:10]:
                report += f"- [{f['timestamp'][:10]}] {f['action_type']}: {f.get('error_message', 'Unknown error')}\n"

        # Pending approvals
        pending = self.get_pending_approvals()
        if pending:
            report += f"\n## Pending Approvals ({len(pending)})\n"
            for p in pending:
                report += f"- {p['action_type']}: {p['target']}\n"

        return report


# Singleton instance
_logger = None

def get_logger(vault_path: Optional[str] = None) -> AuditLogger:
    """Get or create the singleton audit logger"""
    global _logger
    if _logger is None:
        _logger = AuditLogger(vault_path)
    return _logger


# Convenience functions
def log_action(
    action_type: str,
    category: ActionCategory,
    target: str,
    **kwargs
) -> Dict:
    """Quick log function"""
    return get_logger().log(action_type, category, target, **kwargs)


if __name__ == '__main__':
    # Test the logger
    logger = AuditLogger()

    # Log some test actions
    logger.log_system_event("audit_logger_test", {"test": True})
    logger.log_email_processed("test123", "test@example.com", "Test Subject")
    logger.log_task_created("TASK_001", "email", "gmail_watcher")

    # Generate report
    print(logger.generate_audit_report(7))
