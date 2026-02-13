"""
AI Employee Scheduler - Manages scheduled tasks and cron jobs
Silver Tier Requirement: Basic scheduling via cron or Task Scheduler

This module handles:
- Running watchers on schedule
- Daily briefings
- Periodic inbox processing
- Dashboard updates
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from crontab import CronTab

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
VAULT_PATH = PROJECT_ROOT / 'AI_Employee_Vault'
if VAULT_PATH.is_symlink():
    VAULT_PATH = VAULT_PATH.resolve()


class AIEmployeeScheduler:
    """
    Manages scheduled tasks for AI Employee.

    Usage:
        scheduler = AIEmployeeScheduler()
        scheduler.setup_default_schedule()
    """

    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.vault_path = VAULT_PATH
        self.logs_path = self.vault_path / 'Logs'
        self.logs_path.mkdir(exist_ok=True)

        # Get current user's crontab
        self.cron = CronTab(user=True)

        # Python executable path
        self.python_path = self.project_root / '.venv' / 'bin' / 'python'
        if not self.python_path.exists():
            self.python_path = 'python3'

    def _get_job_command(self, script: str, args: str = "") -> str:
        """Build command for cron job"""
        script_path = self.project_root / script
        log_file = self.logs_path / f'cron_{Path(script).stem}.log'

        cmd = f'cd {self.project_root} && {self.python_path} {script_path}'
        if args:
            cmd += f' {args}'
        cmd += f' >> {log_file} 2>&1'

        return cmd

    def add_job(self, name: str, script: str, schedule: str, args: str = "") -> dict:
        """
        Add a scheduled job.

        Args:
            name: Job identifier (used in comment)
            script: Path to Python script (relative to project root)
            schedule: Cron schedule (e.g., "*/5 * * * *" for every 5 minutes)
            args: Additional arguments for the script

        Returns:
            dict with status
        """
        # Remove existing job with same name
        self.remove_job(name)

        # Create new job
        command = self._get_job_command(script, args)
        job = self.cron.new(command=command, comment=f'ai_employee_{name}')

        try:
            job.setall(schedule)
            self.cron.write()

            self._log_action('job_added', {
                'name': name,
                'script': script,
                'schedule': schedule
            })

            return {
                'status': 'success',
                'message': f'Job "{name}" scheduled: {schedule}',
                'command': command
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to add job: {str(e)}'
            }

    def remove_job(self, name: str) -> dict:
        """Remove a scheduled job by name"""
        removed = False
        for job in self.cron:
            if job.comment == f'ai_employee_{name}':
                self.cron.remove(job)
                removed = True

        if removed:
            self.cron.write()
            return {'status': 'success', 'message': f'Job "{name}" removed'}

        return {'status': 'not_found', 'message': f'Job "{name}" not found'}

    def list_jobs(self) -> list:
        """List all AI Employee scheduled jobs"""
        jobs = []
        for job in self.cron:
            if job.comment and job.comment.startswith('ai_employee_'):
                name = job.comment.replace('ai_employee_', '')
                jobs.append({
                    'name': name,
                    'schedule': str(job.slices),
                    'command': job.command,
                    'enabled': job.is_enabled()
                })
        return jobs

    def setup_default_schedule(self) -> list:
        """Set up default AI Employee schedule"""
        results = []

        # Gmail check - every 5 minutes
        results.append(self.add_job(
            name='gmail_check',
            script='watchers/gmail_watcher.py',
            schedule='*/5 * * * *'
        ))

        # Filesystem watcher - every 2 minutes
        results.append(self.add_job(
            name='inbox_scan',
            script='watchers/filesystem_watcher.py',
            schedule='*/2 * * * *'
        ))

        # Dashboard update - every 15 minutes
        results.append(self.add_job(
            name='dashboard_update',
            script='scheduler/tasks/update_dashboard.py',
            schedule='*/15 * * * *'
        ))

        # Daily morning briefing - 8:00 AM
        results.append(self.add_job(
            name='morning_briefing',
            script='scheduler/tasks/morning_briefing.py',
            schedule='0 8 * * *'
        ))

        # Weekly status report - Sunday 8:00 PM
        results.append(self.add_job(
            name='weekly_report',
            script='scheduler/tasks/weekly_report.py',
            schedule='0 20 * * 0'
        ))

        return results

    def clear_all_jobs(self) -> dict:
        """Remove all AI Employee scheduled jobs"""
        removed = 0
        jobs_to_remove = []

        for job in self.cron:
            if job.comment and job.comment.startswith('ai_employee_'):
                jobs_to_remove.append(job)

        for job in jobs_to_remove:
            self.cron.remove(job)
            removed += 1

        self.cron.write()

        return {
            'status': 'success',
            'message': f'Removed {removed} jobs'
        }

    def _log_action(self, action_type: str, details: dict):
        """Log scheduler action"""
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.logs_path / f'{today}.json'

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action_type': action_type,
            'component': 'scheduler',
            **details
        }

        if log_file.exists():
            with open(log_file, 'r') as f:
                logs = json.load(f)
        else:
            logs = []

        logs.append(log_entry)

        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)


def main():
    """Command line interface"""
    if len(sys.argv) < 2:
        print('''
AI Employee Scheduler
=====================

Usage:
    python scheduler.py setup          Set up default schedule
    python scheduler.py list           List all scheduled jobs
    python scheduler.py add <name> <script> <schedule>
    python scheduler.py remove <name>  Remove a job
    python scheduler.py clear          Remove all jobs

Schedule Format (cron):
    */5 * * * *     Every 5 minutes
    0 * * * *       Every hour
    0 8 * * *       Daily at 8:00 AM
    0 8 * * 1       Every Monday at 8:00 AM
    0 20 * * 0      Every Sunday at 8:00 PM

Examples:
    python scheduler.py setup
    python scheduler.py add hourly_check watchers/gmail_watcher.py "0 * * * *"
    python scheduler.py remove hourly_check
''')
        sys.exit(1)

    scheduler = AIEmployeeScheduler()
    command = sys.argv[1]

    if command == 'setup':
        results = scheduler.setup_default_schedule()
        print("Default schedule configured:")
        for r in results:
            print(f"  - {r['message']}")

    elif command == 'list':
        jobs = scheduler.list_jobs()
        if jobs:
            print("Scheduled Jobs:")
            print("-" * 60)
            for job in jobs:
                status = "✓" if job['enabled'] else "✗"
                print(f"  [{status}] {job['name']}: {job['schedule']}")
        else:
            print("No AI Employee jobs scheduled.")

    elif command == 'add' and len(sys.argv) >= 5:
        name = sys.argv[2]
        script = sys.argv[3]
        schedule = sys.argv[4]
        result = scheduler.add_job(name, script, schedule)
        print(json.dumps(result, indent=2))

    elif command == 'remove' and len(sys.argv) >= 3:
        name = sys.argv[2]
        result = scheduler.remove_job(name)
        print(json.dumps(result, indent=2))

    elif command == 'clear':
        result = scheduler.clear_all_jobs()
        print(json.dumps(result, indent=2))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
