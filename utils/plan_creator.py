"""
Plan Creator - Creates Plan.md files for complex tasks
Silver Tier Requirement: Claude reasoning loop that creates Plan.md files
"""
import sys
import json
from pathlib import Path
from datetime import datetime


class PlanCreator:
    """
    Creates structured Plan.md files for task breakdown.

    Usage:
        from plan_creator import PlanCreator
        creator = PlanCreator(vault_path)
        creator.create_plan(title, objective, steps)
    """

    def __init__(self, vault_path: str = None):
        if vault_path is None:
            vault_path = Path(__file__).parent.parent / 'AI_Employee_Vault'

        self.vault_path = Path(vault_path)
        if self.vault_path.is_symlink():
            self.vault_path = self.vault_path.resolve()

        self.plans_path = self.vault_path / 'Plans'
        self.needs_action = self.vault_path / 'Needs_Action'
        self.logs_path = self.vault_path / 'Logs'

        # Ensure directories exist
        self.plans_path.mkdir(exist_ok=True)
        self.needs_action.mkdir(exist_ok=True)
        self.logs_path.mkdir(exist_ok=True)

    def create_plan(
        self,
        title: str,
        objective: str,
        steps: list,
        context: str = "",
        priority: str = "P2",
        effort: str = "medium",
        dependencies: list = None,
        risks: list = None,
        success_criteria: list = None,
        create_action_items: bool = False
    ) -> dict:
        """
        Create a new Plan.md file.

        Args:
            title: Plan title
            objective: What needs to be accomplished
            steps: List of steps or dict with phases
            context: Background information
            priority: P1/P2/P3
            effort: simple/medium/complex
            dependencies: List of dependencies
            risks: List of dicts with risk/impact/mitigation
            success_criteria: List of success criteria
            create_action_items: Create files in Needs_Action for each step

        Returns:
            dict with status and file path
        """
        timestamp = datetime.now()
        safe_title = "".join(c for c in title[:30] if c.isalnum() or c in ' -_').strip()
        safe_title = safe_title.replace(' ', '_')
        filename = f"PLAN_{safe_title}_{timestamp.strftime('%Y%m%d')}.md"

        # Build plan content
        content = self._build_plan_content(
            title=title,
            objective=objective,
            steps=steps,
            context=context,
            priority=priority,
            effort=effort,
            timestamp=timestamp,
            dependencies=dependencies,
            risks=risks,
            success_criteria=success_criteria
        )

        # Save plan
        plan_path = self.plans_path / filename
        plan_path.write_text(content)

        # Create action items if requested
        action_files = []
        if create_action_items:
            action_files = self._create_action_items(title, steps, priority)

        # Log the action
        self._log_action('plan_created', {
            'title': title,
            'file': filename,
            'priority': priority,
            'action_items_created': len(action_files)
        })

        return {
            'status': 'success',
            'message': f'Plan created: {filename}',
            'plan_file': str(plan_path),
            'action_files': action_files
        }

    def _build_plan_content(
        self,
        title: str,
        objective: str,
        steps: list,
        context: str,
        priority: str,
        effort: str,
        timestamp: datetime,
        dependencies: list,
        risks: list,
        success_criteria: list
    ) -> str:
        """Build the markdown content for the plan"""

        content = f'''---
type: plan
created: {timestamp.isoformat()}
status: active
project: {title}
priority: {priority}
estimated_effort: {effort}
---

# Plan: {title}

## Objective
{objective}

'''

        if context:
            content += f'''## Context
{context}

'''

        # Build steps section
        content += "## Steps\n\n"

        if isinstance(steps, dict):
            # Steps organized by phases
            for phase_name, phase_steps in steps.items():
                content += f"### {phase_name}\n"
                for i, step in enumerate(phase_steps, 1):
                    if isinstance(step, dict):
                        step_text = step.get('text', step.get('description', str(step)))
                        step_priority = step.get('priority', 'P3')
                        content += f"- [ ] Step {i}: {step_text} (Priority: {step_priority})\n"
                    else:
                        content += f"- [ ] Step {i}: {step}\n"
                content += "\n"
        else:
            # Flat list of steps
            for i, step in enumerate(steps, 1):
                if isinstance(step, dict):
                    step_text = step.get('text', step.get('description', str(step)))
                    step_priority = step.get('priority', 'P3')
                    content += f"- [ ] Step {i}: {step_text} (Priority: {step_priority})\n"
                else:
                    content += f"- [ ] Step {i}: {step}\n"
            content += "\n"

        # Dependencies
        if dependencies:
            content += "## Dependencies\n"
            for dep in dependencies:
                content += f"- {dep}\n"
            content += "\n"

        # Risks
        if risks:
            content += "## Risks & Mitigations\n"
            content += "| Risk | Impact | Mitigation |\n"
            content += "|------|--------|------------|\n"
            for risk in risks:
                if isinstance(risk, dict):
                    content += f"| {risk.get('risk', '')} | {risk.get('impact', 'Medium')} | {risk.get('mitigation', '')} |\n"
                else:
                    content += f"| {risk} | Medium | TBD |\n"
            content += "\n"

        # Success Criteria
        if success_criteria:
            content += "## Success Criteria\n"
            for criterion in success_criteria:
                content += f"- [ ] {criterion}\n"
            content += "\n"

        content += f'''---
*Plan created by AI Employee: {timestamp.strftime('%Y-%m-%d %H:%M')}*
'''

        return content

    def _create_action_items(self, plan_title: str, steps: list, priority: str) -> list:
        """Create action item files for each step"""
        action_files = []
        timestamp = datetime.now()

        # Flatten steps if in phases
        flat_steps = []
        if isinstance(steps, dict):
            for phase_steps in steps.values():
                flat_steps.extend(phase_steps)
        else:
            flat_steps = steps

        for i, step in enumerate(flat_steps, 1):
            if isinstance(step, dict):
                step_text = step.get('text', step.get('description', str(step)))
                step_priority = step.get('priority', priority)
            else:
                step_text = step
                step_priority = priority

            safe_title = "".join(c for c in plan_title[:15] if c.isalnum() or c in ' -_').strip()
            safe_title = safe_title.replace(' ', '_')
            filename = f"TASK_{safe_title}_step{i}.md"

            content = f'''---
type: task
source: plan
priority: {step_priority}
created: {timestamp.isoformat()}
plan: {plan_title}
step: {i}
status: pending
---

## Task: {step_text}

**From Plan:** {plan_title}
**Step:** {i}
**Priority:** {step_priority}

## Suggested Actions
- [ ] Complete this step
- [ ] Update plan when done

## Notes
This task was auto-generated from a plan.
'''

            action_path = self.needs_action / filename
            action_path.write_text(content)
            action_files.append(str(action_path))

        return action_files

    def _log_action(self, action_type: str, details: dict):
        """Log plan creation"""
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.logs_path / f'{today}.json'

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action_type': action_type,
            'component': 'plan_creator',
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

    def update_plan_status(self, plan_file: str, status: str) -> dict:
        """Update the status of a plan"""
        plan_path = self.plans_path / plan_file

        if not plan_path.exists():
            return {'status': 'error', 'message': f'Plan not found: {plan_file}'}

        content = plan_path.read_text()
        content = content.replace('status: active', f'status: {status}')
        content = content.replace('status: blocked', f'status: {status}')
        plan_path.write_text(content)

        return {'status': 'success', 'message': f'Plan status updated to: {status}'}

    def list_plans(self, status: str = None) -> list:
        """List all plans, optionally filtered by status"""
        plans = []

        for plan_file in self.plans_path.glob('PLAN_*.md'):
            content = plan_file.read_text()

            # Extract status from frontmatter
            plan_status = 'unknown'
            for line in content.split('\n'):
                if line.startswith('status:'):
                    plan_status = line.split(':')[1].strip()
                    break

            if status is None or plan_status == status:
                plans.append({
                    'file': plan_file.name,
                    'status': plan_status
                })

        return plans


def main():
    """Command line interface"""
    if len(sys.argv) < 2:
        print('''
Plan Creator
============

Usage:
    python plan_creator.py create <title> <objective> <step1> <step2> ...
    python plan_creator.py list [status]
    python plan_creator.py update <plan_file> <status>

Examples:
    python plan_creator.py create "Email Campaign" "Launch marketing emails" "Draft content" "Review" "Send"
    python plan_creator.py list active
    python plan_creator.py update PLAN_Email_Campaign_20260211.md completed
''')
        sys.exit(1)

    creator = PlanCreator()
    command = sys.argv[1]

    if command == 'create' and len(sys.argv) >= 4:
        title = sys.argv[2]
        objective = sys.argv[3]
        steps = sys.argv[4:] if len(sys.argv) > 4 else ["Complete the task"]

        result = creator.create_plan(title, objective, steps)
        print(json.dumps(result, indent=2))

    elif command == 'list':
        status = sys.argv[2] if len(sys.argv) > 2 else None
        plans = creator.list_plans(status)
        for plan in plans:
            print(f"{plan['file']} - {plan['status']}")

    elif command == 'update' and len(sys.argv) >= 4:
        plan_file = sys.argv[2]
        status = sys.argv[3]
        result = creator.update_plan_status(plan_file, status)
        print(json.dumps(result, indent=2))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
