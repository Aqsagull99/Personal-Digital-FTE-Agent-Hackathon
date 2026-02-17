"""
Ralph Wiggum Loop - Gold Tier Requirement #10

The "Ralph Wiggum" pattern keeps Claude Code working autonomously
until a task is complete. It intercepts Claude's exit and feeds
the prompt back if the task isn't done.

Two completion strategies:
1. Promise-based: Claude outputs <promise>TASK_COMPLETE</promise>
2. File movement: Task file moves to /Done folder

Usage:
    # Start a Ralph loop via CLI
    python ralph_wiggum.py --task "Process all files in /Needs_Action" \\
        --completion-promise "TASK_COMPLETE" \\
        --max-iterations 10

    # Or use as Stop hook
    python ralph_wiggum.py --hook-mode --state-file /path/to/state.json
"""
import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any


class RalphWiggumLoop:
    """
    Keeps Claude Code iterating until task completion.

    The loop:
    1. Orchestrator creates state file with prompt
    2. Claude works on task
    3. Claude tries to exit
    4. Stop hook checks: Is task complete?
    5. YES -> Allow exit
    6. NO -> Block exit, re-inject prompt, continue
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

        self.state_path = self.vault_path / 'State'
        self.state_path.mkdir(parents=True, exist_ok=True)

        self.done_path = self.vault_path / 'Done'
        self.needs_action_path = self.vault_path / 'Needs_Action'
        self.logs_path = self.vault_path / 'Logs'

    def create_state(
        self,
        task_id: str,
        prompt: str,
        completion_promise: str = "TASK_COMPLETE",
        max_iterations: int = 10,
        completion_file: Optional[str] = None
    ) -> Path:
        """
        Create state file for Ralph Wiggum loop.

        Args:
            task_id: Unique identifier for this task
            prompt: The prompt to send to Claude
            completion_promise: String Claude outputs when done
            max_iterations: Maximum loop iterations
            completion_file: Optional file to watch for movement to /Done

        Returns:
            Path to state file
        """
        state = {
            "task_id": task_id,
            "prompt": prompt,
            "completion_promise": completion_promise,
            "max_iterations": max_iterations,
            "completion_file": completion_file,
            "current_iteration": 0,
            "status": "pending",
            "started_at": datetime.now().isoformat(),
            "last_output": None,
            "completed": False
        }

        state_file = self.state_path / f"ralph_{task_id}.json"
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)

        return state_file

    def load_state(self, state_file: Path) -> Dict:
        """Load state from file"""
        with open(state_file, 'r') as f:
            return json.load(f)

    def save_state(self, state_file: Path, state: Dict):
        """Save state to file"""
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2, default=str)

    def check_promise_completion(self, output: str, promise: str) -> bool:
        """Check if output contains completion promise"""
        if output is None:
            output = ""

        # Check for <promise>PROMISE</promise> pattern
        promise_tag = f"<promise>{promise}</promise>"
        if promise_tag in output:
            return True

        # Also check for plain promise string
        if promise in output:
            return True

        return False

    def check_file_completion(self, completion_file: str) -> bool:
        """Check if file has moved to /Done folder"""
        if not completion_file:
            return False

        # Check if file exists in Done
        done_file = self.done_path / Path(completion_file).name
        if done_file.exists():
            return True

        # Check if original file no longer exists in Needs_Action
        original_file = self.needs_action_path / Path(completion_file).name
        if not original_file.exists():
            # File moved somewhere, check Done
            return done_file.exists()

        return False

    def is_complete(self, state: Dict, last_output: str = "") -> bool:
        """Check if task is complete using either strategy"""
        # Strategy 1: Promise-based
        if state.get('completion_promise'):
            if self.check_promise_completion(last_output, state['completion_promise']):
                return True

        # Strategy 2: File movement
        if state.get('completion_file'):
            if self.check_file_completion(state['completion_file']):
                return True

        return False

    def run_claude(self, prompt: str, timeout: int = 600) -> str:
        """
        Run Claude Code with prompt and capture output.

        Args:
            prompt: Prompt to send
            timeout: Timeout in seconds (default 10 min)

        Returns:
            Claude's output
        """
        try:
            # Build claude command
            cmd = ['claude', '--print', '-p', prompt]

            # Copy env and unset CLAUDECODE to allow spawning from within
            # an existing Claude Code session (avoids nested session error)
            env = os.environ.copy()
            env.pop('CLAUDECODE', None)

            # Use project root as cwd (not vault — vault may be on slow
            # Windows FS via WSL symlink)
            project_root = Path(__file__).parent.parent
            cwd = str(project_root)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                env=env
            )

            return result.stdout + result.stderr

        except subprocess.TimeoutExpired:
            return "[TIMEOUT] Claude did not respond within time limit"
        except Exception as e:
            return f"[ERROR] {str(e)}"

    def execute_loop(
        self,
        task_id: str,
        prompt: str,
        completion_promise: str = "TASK_COMPLETE",
        max_iterations: int = 10,
        completion_file: Optional[str] = None,
        verbose: bool = True
    ) -> Dict:
        """
        Execute the Ralph Wiggum loop.

        Args:
            task_id: Unique task identifier
            prompt: Initial prompt
            completion_promise: Completion marker
            max_iterations: Max iterations before stopping
            completion_file: Optional file to watch
            verbose: Print progress

        Returns:
            Final state dictionary
        """
        # Create state
        state_file = self.create_state(
            task_id=task_id,
            prompt=prompt,
            completion_promise=completion_promise,
            max_iterations=max_iterations,
            completion_file=completion_file
        )

        state = self.load_state(state_file)
        state['status'] = 'running'

        if verbose:
            print(f"Starting Ralph Wiggum loop for task: {task_id}")
            print(f"Max iterations: {max_iterations}")
            print(f"Completion promise: {completion_promise}")
            if completion_file:
                print(f"Watching file: {completion_file}")
            print("-" * 50)

        # Build enhanced prompt with instructions
        enhanced_prompt = f"""{prompt}

IMPORTANT: When you have completed this task, output:
<promise>{completion_promise}</promise>

If you cannot complete the task, explain why and still output the promise tag.
"""

        while state['current_iteration'] < max_iterations:
            state['current_iteration'] += 1
            iteration = state['current_iteration']

            if verbose:
                print(f"\n[Iteration {iteration}/{max_iterations}]")

            # Run Claude
            output = self.run_claude(enhanced_prompt)
            state['last_output'] = output

            if verbose:
                # Print truncated output
                output_preview = output[:500] + "..." if len(output) > 500 else output
                print(f"Output: {output_preview}")

            # Check completion
            if self.is_complete(state, output):
                state['completed'] = True
                state['status'] = 'completed'
                state['completed_at'] = datetime.now().isoformat()

                if verbose:
                    print(f"\n✅ Task completed at iteration {iteration}")

                self.save_state(state_file, state)
                self._log_completion(state)
                return state

            # Update prompt for next iteration with previous output context
            enhanced_prompt = f"""Continue working on this task. Previous output:
{output[:2000]}

Original task: {prompt}

Continue from where you left off. When complete, output:
<promise>{completion_promise}</promise>
"""

            self.save_state(state_file, state)

        # Max iterations reached
        state['status'] = 'max_iterations_reached'
        state['completed_at'] = datetime.now().isoformat()

        if verbose:
            print(f"\n⚠️ Max iterations ({max_iterations}) reached without completion")

        self.save_state(state_file, state)
        self._log_completion(state)
        return state

    def _log_completion(self, state: Dict):
        """Log completion to audit log"""
        log_file = self.logs_path / f'{datetime.now().strftime("%Y-%m-%d")}.json'
        logs = []
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    logs = json.load(f)
            except:
                pass

        logs.append({
            'timestamp': datetime.now().isoformat(),
            'action_type': 'ralph_wiggum_loop',
            'task_id': state['task_id'],
            'iterations': state['current_iteration'],
            'status': state['status'],
            'completed': state['completed']
        })

        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)

    def hook_mode(self, state_file: str) -> int:
        """
        Run as Stop hook - check if should allow exit.

        Returns:
            0 to allow exit
            1 to block exit (continue loop)
        """
        state_path = Path(state_file)
        if not state_path.exists():
            return 0  # No state file, allow exit

        state = self.load_state(state_path)

        # Check if complete
        last_output = state.get('last_output', '')
        if self.is_complete(state, last_output):
            state['completed'] = True
            state['status'] = 'completed'
            self.save_state(state_path, state)
            return 0  # Allow exit

        # Check max iterations
        if state['current_iteration'] >= state['max_iterations']:
            state['status'] = 'max_iterations_reached'
            self.save_state(state_path, state)
            return 0  # Allow exit

        # Block exit - need more iterations
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='Ralph Wiggum Loop - Keep Claude working until task complete'
    )
    parser.add_argument('--task', type=str, help='Task prompt to execute')
    parser.add_argument('--task-id', type=str, help='Unique task ID')
    parser.add_argument('--completion-promise', type=str, default='TASK_COMPLETE',
                        help='Completion promise string')
    parser.add_argument('--max-iterations', type=int, default=10,
                        help='Maximum iterations')
    parser.add_argument('--completion-file', type=str,
                        help='File to watch for movement to /Done')
    parser.add_argument('--hook-mode', action='store_true',
                        help='Run as Stop hook')
    parser.add_argument('--state-file', type=str,
                        help='State file path (for hook mode)')
    parser.add_argument('--vault', type=str,
                        help='Vault path')
    parser.add_argument('--quiet', action='store_true',
                        help='Suppress output')

    args = parser.parse_args()

    ralph = RalphWiggumLoop(args.vault)

    if args.hook_mode:
        if not args.state_file:
            print("Error: --state-file required for hook mode")
            sys.exit(1)
        sys.exit(ralph.hook_mode(args.state_file))

    if not args.task:
        print("Error: --task required")
        parser.print_help()
        sys.exit(1)

    task_id = args.task_id or f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    result = ralph.execute_loop(
        task_id=task_id,
        prompt=args.task,
        completion_promise=args.completion_promise,
        max_iterations=args.max_iterations,
        completion_file=args.completion_file,
        verbose=not args.quiet
    )

    print("\nFinal Result:")
    print(json.dumps({
        'task_id': result['task_id'],
        'status': result['status'],
        'iterations': result['current_iteration'],
        'completed': result['completed']
    }, indent=2))

    sys.exit(0 if result['completed'] else 1)


if __name__ == '__main__':
    main()
