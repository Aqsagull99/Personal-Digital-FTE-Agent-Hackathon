"""
Error Recovery & Graceful Degradation - Gold Tier Requirement #8

Provides:
- Exponential backoff retry logic
- Graceful degradation when services fail
- Queue management for offline processing
- Health monitoring for services
"""
import time
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Callable, Any, Optional, Dict, List
from functools import wraps
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class TransientError(Exception):
    """Errors that should be retried (network, rate limit, etc.)"""
    pass


class PermanentError(Exception):
    """Errors that should not be retried (auth, validation, etc.)"""
    pass


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple = (TransientError, ConnectionError, TimeoutError)
):
    """
    Decorator for retry with exponential backoff.

    Args:
        max_attempts: Maximum retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap
        exponential_base: Multiplier for each retry
        retryable_exceptions: Exception types to retry on
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        logger.error(f'{func.__name__} failed after {max_attempts} attempts: {e}')
                        raise

                    delay = min(base_delay * (exponential_base ** attempt), max_delay)
                    logger.warning(
                        f'{func.__name__} attempt {attempt + 1} failed, '
                        f'retrying in {delay:.1f}s: {e}'
                    )
                    time.sleep(delay)
                except Exception as e:
                    # Non-retryable exception
                    logger.error(f'{func.__name__} failed with non-retryable error: {e}')
                    raise

            raise last_exception

        return wrapper
    return decorator


class OfflineQueue:
    """
    Queue for storing actions when services are offline.
    Actions are persisted to disk and processed when services recover.
    """

    def __init__(self, vault_path: Optional[str] = None):
        if vault_path:
            self.vault_path = Path(vault_path)
        else:
            project_root = Path(__file__).parent.parent
            vault_link = project_root / 'AI_Employee_Vault'
            if vault_link.exists():
                self.vault_path = vault_link.resolve() if vault_link.is_symlink() else vault_link
            else:
                self.vault_path = Path.home() / 'AI_Employee_Vault'

        self.queue_path = self.vault_path / 'Offline_Queue'
        self.queue_path.mkdir(parents=True, exist_ok=True)

    def enqueue(
        self,
        action_type: str,
        service: str,
        data: Dict,
        priority: int = 5
    ) -> str:
        """
        Add action to offline queue.

        Args:
            action_type: Type of action (email_send, social_post, etc.)
            service: Service this action requires
            data: Action data/parameters
            priority: 1-10 (1 = highest)

        Returns:
            Queue item ID
        """
        timestamp = datetime.now()
        item_id = f"{service}_{action_type}_{timestamp.strftime('%Y%m%d_%H%M%S_%f')}"

        item = {
            "id": item_id,
            "action_type": action_type,
            "service": service,
            "data": data,
            "priority": priority,
            "queued_at": timestamp.isoformat(),
            "attempts": 0,
            "last_attempt": None,
            "status": "pending"
        }

        item_path = self.queue_path / f"{item_id}.json"
        with open(item_path, 'w') as f:
            json.dump(item, f, indent=2)

        logger.info(f'Queued offline action: {item_id}')
        return item_id

    def get_pending(self, service: Optional[str] = None) -> List[Dict]:
        """Get pending items, optionally filtered by service"""
        items = []
        for item_file in self.queue_path.glob('*.json'):
            try:
                with open(item_file, 'r') as f:
                    item = json.load(f)
                if item.get('status') == 'pending':
                    if service is None or item.get('service') == service:
                        items.append(item)
            except:
                pass

        # Sort by priority (lower = higher priority), then by queue time
        return sorted(items, key=lambda x: (x.get('priority', 5), x.get('queued_at', '')))

    def mark_completed(self, item_id: str):
        """Mark item as completed"""
        item_path = self.queue_path / f"{item_id}.json"
        if item_path.exists():
            with open(item_path, 'r') as f:
                item = json.load(f)
            item['status'] = 'completed'
            item['completed_at'] = datetime.now().isoformat()
            with open(item_path, 'w') as f:
                json.dump(item, f, indent=2)

            # Move to completed subfolder
            completed_path = self.queue_path / 'Completed'
            completed_path.mkdir(exist_ok=True)
            item_path.rename(completed_path / item_path.name)

    def mark_failed(self, item_id: str, error: str):
        """Mark item as failed after max retries"""
        item_path = self.queue_path / f"{item_id}.json"
        if item_path.exists():
            with open(item_path, 'r') as f:
                item = json.load(f)
            item['status'] = 'failed'
            item['error'] = error
            item['failed_at'] = datetime.now().isoformat()
            with open(item_path, 'w') as f:
                json.dump(item, f, indent=2)

            # Move to failed subfolder
            failed_path = self.queue_path / 'Failed'
            failed_path.mkdir(exist_ok=True)
            item_path.rename(failed_path / item_path.name)

    def increment_attempt(self, item_id: str):
        """Increment attempt count"""
        item_path = self.queue_path / f"{item_id}.json"
        if item_path.exists():
            with open(item_path, 'r') as f:
                item = json.load(f)
            item['attempts'] = item.get('attempts', 0) + 1
            item['last_attempt'] = datetime.now().isoformat()
            with open(item_path, 'w') as f:
                json.dump(item, f, indent=2)


class ServiceHealthMonitor:
    """
    Monitor health of external services.
    Tracks failures and determines service availability.
    """

    def __init__(self, vault_path: Optional[str] = None):
        if vault_path:
            self.vault_path = Path(vault_path)
        else:
            project_root = Path(__file__).parent.parent
            vault_link = project_root / 'AI_Employee_Vault'
            if vault_link.exists():
                self.vault_path = vault_link.resolve() if vault_link.is_symlink() else vault_link
            else:
                self.vault_path = Path.home() / 'AI_Employee_Vault'

        self.health_file = self.vault_path / 'Logs' / 'service_health.json'
        self.health_file.parent.mkdir(parents=True, exist_ok=True)

        # Thresholds
        self.failure_threshold = 3  # Consecutive failures before marking unavailable
        self.recovery_window = timedelta(minutes=5)  # Time to wait before retry

    def _load_health(self) -> Dict:
        """Load health status from file"""
        if self.health_file.exists():
            try:
                with open(self.health_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_health(self, health: Dict):
        """Save health status to file"""
        with open(self.health_file, 'w') as f:
            json.dump(health, f, indent=2, default=str)

    def record_success(self, service: str):
        """Record successful service call"""
        health = self._load_health()
        health[service] = {
            "status": ServiceStatus.HEALTHY.value,
            "consecutive_failures": 0,
            "last_success": datetime.now().isoformat(),
            "last_check": datetime.now().isoformat()
        }
        self._save_health(health)

    def record_failure(self, service: str, error: str):
        """Record failed service call"""
        health = self._load_health()

        current = health.get(service, {})
        failures = current.get('consecutive_failures', 0) + 1

        status = ServiceStatus.DEGRADED.value
        if failures >= self.failure_threshold:
            status = ServiceStatus.UNAVAILABLE.value

        health[service] = {
            "status": status,
            "consecutive_failures": failures,
            "last_failure": datetime.now().isoformat(),
            "last_error": error,
            "last_check": datetime.now().isoformat()
        }
        self._save_health(health)

        logger.warning(f'Service {service} failure #{failures}: {error}')

    def get_status(self, service: str) -> ServiceStatus:
        """Get current service status"""
        health = self._load_health()
        service_health = health.get(service, {})

        status_str = service_health.get('status', ServiceStatus.UNKNOWN.value)
        return ServiceStatus(status_str)

    def is_available(self, service: str) -> bool:
        """Check if service is available for use"""
        status = self.get_status(service)

        if status == ServiceStatus.HEALTHY:
            return True

        if status == ServiceStatus.UNAVAILABLE:
            # Check if recovery window has passed
            health = self._load_health()
            service_health = health.get(service, {})
            last_check = service_health.get('last_check')

            if last_check:
                last_check_dt = datetime.fromisoformat(last_check)
                if datetime.now() - last_check_dt > self.recovery_window:
                    # Allow retry after recovery window
                    return True

            return False

        # DEGRADED or UNKNOWN - allow with caution
        return True

    def get_all_status(self) -> Dict[str, str]:
        """Get status of all services"""
        health = self._load_health()
        return {
            service: data.get('status', ServiceStatus.UNKNOWN.value)
            for service, data in health.items()
        }


class GracefulDegradation:
    """
    Implements graceful degradation patterns.
    When primary services fail, fall back to alternatives.
    """

    def __init__(self, vault_path: Optional[str] = None):
        self.health_monitor = ServiceHealthMonitor(vault_path)
        self.offline_queue = OfflineQueue(vault_path)

    def execute_with_fallback(
        self,
        service: str,
        action: Callable,
        fallback_action: Optional[Callable] = None,
        queue_on_failure: bool = True,
        action_type: str = "unknown",
        action_data: Optional[Dict] = None
    ) -> Any:
        """
        Execute action with fallback and queuing.

        Args:
            service: Service name
            action: Primary action to execute
            fallback_action: Optional fallback if primary fails
            queue_on_failure: Whether to queue for later if all fail
            action_type: Type of action for queuing
            action_data: Data to store if queued

        Returns:
            Result of successful action, or None if queued
        """
        # Check if service is available
        if not self.health_monitor.is_available(service):
            logger.warning(f'Service {service} unavailable, using fallback/queue')
            if fallback_action:
                try:
                    return fallback_action()
                except Exception as e:
                    logger.error(f'Fallback also failed: {e}')

            if queue_on_failure and action_data:
                self.offline_queue.enqueue(action_type, service, action_data)
            return None

        # Try primary action
        try:
            result = action()
            self.health_monitor.record_success(service)
            return result
        except Exception as e:
            self.health_monitor.record_failure(service, str(e))

            # Try fallback
            if fallback_action:
                try:
                    logger.info(f'Primary failed, trying fallback for {service}')
                    return fallback_action()
                except Exception as fe:
                    logger.error(f'Fallback also failed: {fe}')

            # Queue for later
            if queue_on_failure and action_data:
                self.offline_queue.enqueue(action_type, service, action_data)

            return None

    def process_offline_queue(self, service: str, processor: Callable[[Dict], bool]):
        """
        Process queued items for a service.

        Args:
            service: Service to process queue for
            processor: Function that takes item data and returns success/failure
        """
        if not self.health_monitor.is_available(service):
            logger.info(f'Service {service} still unavailable, skipping queue processing')
            return

        pending = self.offline_queue.get_pending(service)
        logger.info(f'Processing {len(pending)} queued items for {service}')

        for item in pending:
            item_id = item['id']
            self.offline_queue.increment_attempt(item_id)

            try:
                success = processor(item['data'])
                if success:
                    self.offline_queue.mark_completed(item_id)
                    self.health_monitor.record_success(service)
                    logger.info(f'Processed queued item: {item_id}')
                else:
                    if item.get('attempts', 0) >= 5:
                        self.offline_queue.mark_failed(item_id, "Max attempts reached")
            except Exception as e:
                self.health_monitor.record_failure(service, str(e))
                if item.get('attempts', 0) >= 5:
                    self.offline_queue.mark_failed(item_id, str(e))
                break  # Stop processing if service is failing


# Convenience decorators

def graceful(
    service: str,
    queue_on_failure: bool = True,
    action_type: str = "unknown"
):
    """
    Decorator for graceful degradation.

    Usage:
        @graceful(service="gmail", action_type="email_send")
        def send_email(to, subject, body):
            ...
    """
    degradation = GracefulDegradation()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            def action():
                return func(*args, **kwargs)

            action_data = {
                "args": args,
                "kwargs": kwargs
            }

            return degradation.execute_with_fallback(
                service=service,
                action=action,
                queue_on_failure=queue_on_failure,
                action_type=action_type,
                action_data=action_data
            )

        return wrapper
    return decorator


if __name__ == '__main__':
    # Test retry decorator
    @with_retry(max_attempts=3, base_delay=0.1)
    def flaky_function():
        import random
        if random.random() < 0.7:
            raise TransientError("Random failure")
        return "Success!"

    # Test graceful degradation
    degradation = GracefulDegradation()

    print("Testing retry...")
    try:
        result = flaky_function()
        print(f"Result: {result}")
    except:
        print("Failed after retries")

    print("\nService health status:")
    print(degradation.health_monitor.get_all_status())
