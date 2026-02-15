"""
Base Watcher Template - All watchers inherit from this class
"""
import time
import logging
import json
from pathlib import Path
from abc import ABC, abstractmethod
from datetime import datetime
from json import JSONDecodeError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class BaseWatcher(ABC):
    """Base class for all AI Employee watchers"""

    def __init__(self, vault_path: str, check_interval: int = 60):
        self.vault_path = Path(vault_path)
        self.inbox = self.vault_path / 'Inbox'
        self.needs_action = self.vault_path / 'Needs_Action'
        self.logs = self.vault_path / 'Logs'
        self.check_interval = check_interval
        self.logger = logging.getLogger(self.__class__.__name__)

        # Ensure directories exist
        self.inbox.mkdir(exist_ok=True)
        self.needs_action.mkdir(exist_ok=True)
        self.logs.mkdir(exist_ok=True)

    @abstractmethod
    def check_for_updates(self) -> list:
        """Return list of new items to process"""
        pass

    @abstractmethod
    def create_action_file(self, item) -> Path:
        """Create .md file in Needs_Action folder"""
        pass

    def log_action(self, action_type: str, details: dict):
        """Log action to daily log file"""
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.logs / f'{today}.json'

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action_type': action_type,
            'watcher': self.__class__.__name__,
            **details
        }

        # Read existing logs or create new
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
                if not isinstance(logs, list):
                    self.logger.warning(f"Log file has unexpected format, resetting: {log_file}")
                    logs = []
            except (JSONDecodeError, OSError) as e:
                self.logger.warning(f"Log file unreadable/corrupt, resetting: {log_file} ({e})")
                logs = []
        else:
            logs = []

        logs.append(log_entry)

        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2)

        self.logger.info(f"Logged: {action_type}")

    def run(self):
        """Main loop - continuously check for updates"""
        self.logger.info(f'Starting {self.__class__.__name__}')
        self.logger.info(f'Watching vault: {self.vault_path}')
        self.logger.info(f'Check interval: {self.check_interval} seconds')

        while True:
            try:
                items = self.check_for_updates()
                for item in items:
                    filepath = self.create_action_file(item)
                    self.logger.info(f'Created action file: {filepath}')
            except KeyboardInterrupt:
                self.logger.info('Watcher stopped by user')
                break
            except Exception as e:
                self.logger.error(f'Error: {e}')

            time.sleep(self.check_interval)
