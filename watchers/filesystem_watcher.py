"""
File System Watcher - Monitors Inbox folder for new files
Bronze Tier Requirement: One working Watcher script
"""
import sys
import time
from pathlib import Path
from datetime import datetime
from watchdog.observers.polling import PollingObserver as Observer  # Use polling for cross-filesystem support
from watchdog.events import FileSystemEventHandler

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from base_watcher import BaseWatcher


class InboxHandler(FileSystemEventHandler):
    """Handle file system events in Inbox folder"""

    def __init__(self, watcher: 'FileSystemWatcher'):
        self.watcher = watcher
        self.processed_files = set()

    def on_created(self, event):
        """Triggered when a new file is created in Inbox"""
        if event.is_directory:
            return

        filepath = Path(event.src_path)

        # Skip hidden files and already processed
        if filepath.name.startswith('.'):
            return
        if filepath in self.processed_files:
            return

        self.watcher.logger.info(f'New file detected: {filepath.name}')
        self.processed_files.add(filepath)

        # Process the file
        self.watcher.process_new_file(filepath)


class FileSystemWatcher(BaseWatcher):
    """
    Watches the Inbox folder for new files and processes them.

    Usage:
        python filesystem_watcher.py [vault_path]

    Example:
        python filesystem_watcher.py /path/to/AI_Employee_Vault
    """

    def __init__(self, vault_path: str):
        super().__init__(vault_path, check_interval=5)
        self.observer = None
        self.processed_files = set()

        # Keywords that indicate priority
        self.urgent_keywords = ['urgent', 'asap', 'critical', 'important', 'payment', 'invoice']
        self.high_keywords = ['request', 'help', 'needed', 'deadline']

    def check_for_updates(self) -> list:
        """Check Inbox for unprocessed files"""
        new_files = []
        for filepath in self.inbox.iterdir():
            if filepath.is_file() and not filepath.name.startswith('.'):
                if filepath not in self.processed_files:
                    new_files.append(filepath)
        return new_files

    def determine_priority(self, content: str) -> str:
        """Determine priority based on content keywords"""
        content_lower = content.lower()

        for keyword in self.urgent_keywords:
            if keyword in content_lower:
                return 'P1'

        for keyword in self.high_keywords:
            if keyword in content_lower:
                return 'P2'

        return 'P3'

    def determine_type(self, filepath: Path, content: str) -> str:
        """Determine file type based on name and content"""
        name_lower = filepath.name.lower()

        if name_lower.startswith('email_') or 'from:' in content.lower():
            return 'email'
        elif name_lower.startswith('task_') or '- [ ]' in content:
            return 'task'
        elif name_lower.startswith('doc_') or name_lower.startswith('file_'):
            return 'document'
        else:
            return 'general'

    def create_action_file(self, item: Path) -> Path:
        """Create action file in Needs_Action folder"""
        content = item.read_text() if item.suffix == '.md' else f'File: {item.name}'

        file_type = self.determine_type(item, content)
        priority = self.determine_priority(content)
        timestamp = datetime.now().isoformat()

        action_content = f'''---
type: {file_type}
source: inbox_watcher
priority: {priority}
created: {timestamp}
original_file: {item.name}
status: pending
---

## Summary
New {file_type} received via Inbox folder.

## Original Content
{content}

## Suggested Actions
- [ ] Review content
- [ ] Take appropriate action
- [ ] Move to Done when complete
'''

        # Create action file
        action_filename = f'ACTION_{item.stem}_{datetime.now().strftime("%H%M%S")}.md'
        action_path = self.needs_action / action_filename
        action_path.write_text(action_content)

        # Log the action
        self.log_action('file_processed', {
            'original_file': item.name,
            'action_file': action_filename,
            'type': file_type,
            'priority': priority
        })

        return action_path

    def process_new_file(self, filepath: Path):
        """Process a newly detected file"""
        try:
            action_path = self.create_action_file(filepath)
            self.processed_files.add(filepath)
            self.logger.info(f'Processed: {filepath.name} -> {action_path.name}')

            # Optionally move original to processed or delete
            # For now, we keep it in Inbox for reference

        except Exception as e:
            self.logger.error(f'Error processing {filepath.name}: {e}')

    def run_with_watchdog(self):
        """Run using watchdog for real-time monitoring"""
        self.logger.info(f'Starting FileSystem Watcher (watchdog mode)')
        self.logger.info(f'Watching: {self.inbox}')

        # First, process any existing files in Inbox
        existing_files = self.check_for_updates()
        if existing_files:
            self.logger.info(f'Found {len(existing_files)} existing files in Inbox')
            for filepath in existing_files:
                self.process_new_file(filepath)

        # Set up watchdog observer
        handler = InboxHandler(self)
        self.observer = Observer()
        self.observer.schedule(handler, str(self.inbox), recursive=False)
        self.observer.start()

        self.logger.info('Watcher is running. Press Ctrl+C to stop.')

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info('Stopping watcher...')
            self.observer.stop()

        self.observer.join()
        self.logger.info('Watcher stopped.')


def main():
    """Main entry point"""
    # Default vault path - resolve symlinks to get real path
    default_vault = Path(__file__).parent.parent / 'AI_Employee_Vault'

    # Resolve symlink to actual path (important for cross-filesystem watching)
    if default_vault.is_symlink():
        default_vault = default_vault.resolve()

    # Allow custom vault path via command line
    if len(sys.argv) > 1:
        vault_path = sys.argv[1]
    else:
        vault_path = str(default_vault)

    print(f'''
╔══════════════════════════════════════════════════════════════╗
║           AI Employee - File System Watcher                  ║
║                    Bronze Tier                               ║
╠══════════════════════════════════════════════════════════════╣
║  Monitoring: {vault_path}/Inbox
║  Actions:    {vault_path}/Needs_Action
║  Logs:       {vault_path}/Logs
╚══════════════════════════════════════════════════════════════╝
''')

    watcher = FileSystemWatcher(vault_path)
    watcher.run_with_watchdog()


if __name__ == '__main__':
    main()
