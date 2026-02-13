"""
AI Employee Utilities

Gold Tier components:
- audit_logger: Comprehensive audit logging (Requirement #9)
- error_recovery: Error recovery & graceful degradation (Requirement #8)
- ralph_wiggum: Autonomous multi-step task completion (Requirement #10)
"""

from .audit_logger import (
    AuditLogger,
    ActionCategory,
    ApprovalStatus,
    get_logger,
    log_action
)

from .error_recovery import (
    with_retry,
    graceful,
    TransientError,
    PermanentError,
    ServiceStatus,
    OfflineQueue,
    ServiceHealthMonitor,
    GracefulDegradation
)

from .ralph_wiggum import RalphWiggumLoop

__all__ = [
    # Audit Logger
    'AuditLogger',
    'ActionCategory',
    'ApprovalStatus',
    'get_logger',
    'log_action',

    # Error Recovery
    'with_retry',
    'graceful',
    'TransientError',
    'PermanentError',
    'ServiceStatus',
    'OfflineQueue',
    'ServiceHealthMonitor',
    'GracefulDegradation',

    # Ralph Wiggum
    'RalphWiggumLoop'
]
