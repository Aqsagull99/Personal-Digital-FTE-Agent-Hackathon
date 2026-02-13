"""
CEO Briefing Generator - Weekly Business Audit with comprehensive report
Gold Tier Requirement: Weekly Business and Accounting Audit with CEO Briefing generation

Combines data from:
- Odoo (accounting)
- Task completion metrics
- Social media activity
- Email/communication stats
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any

PROJECT_ROOT = Path(__file__).parent.parent.parent
VAULT_PATH = PROJECT_ROOT / 'AI_Employee_Vault'
if VAULT_PATH.is_symlink():
    VAULT_PATH = VAULT_PATH.resolve()

# Try to import Odoo server
sys.path.insert(0, str(PROJECT_ROOT / 'mcp_servers'))
try:
    from odoo_server import OdooMCPServer
    ODOO_AVAILABLE = True
except:
    ODOO_AVAILABLE = False


class CEOBriefingGenerator:
    """
    Generates comprehensive CEO/Business briefing combining all data sources.

    The "Monday Morning CEO Briefing" - transforms AI from chatbot to business partner.
    """

    def __init__(self):
        self.vault_path = VAULT_PATH
        self.logs_path = VAULT_PATH / 'Logs'
        self.done_path = VAULT_PATH / 'Done'
        self.needs_action_path = VAULT_PATH / 'Needs_Action'
        self.briefings_path = VAULT_PATH / 'Briefings'
        self.reports_path = VAULT_PATH / 'Reports'

        self.briefings_path.mkdir(exist_ok=True)
        self.reports_path.mkdir(exist_ok=True)

        # Initialize Odoo if available
        self.odoo = OdooMCPServer() if ODOO_AVAILABLE else None

    def gather_task_metrics(self, days: int = 7) -> Dict:
        """Gather task completion metrics"""
        metrics = {
            'completed': 0,
            'pending': 0,
            'by_type': {},
            'by_priority': {'P1': 0, 'P2': 0, 'P3': 0},
            'completion_rate': 0
        }

        cutoff = datetime.now() - timedelta(days=days)

        # Count completed tasks
        if self.done_path.exists():
            for f in self.done_path.glob('*.md'):
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime >= cutoff:
                    metrics['completed'] += 1

                    # Categorize by type
                    content = f.read_text()
                    for type_name in ['EMAIL', 'TASK', 'LINKEDIN', 'TWITTER', 'FACEBOOK', 'INSTAGRAM', 'WHATSAPP']:
                        if type_name in f.name or f'type: {type_name.lower()}' in content:
                            metrics['by_type'][type_name] = metrics['by_type'].get(type_name, 0) + 1
                            break

        # Count pending tasks
        if self.needs_action_path.exists():
            for f in self.needs_action_path.glob('*.md'):
                metrics['pending'] += 1
                content = f.read_text()

                # Count by priority
                if 'priority: P1' in content or 'priority:P1' in content:
                    metrics['by_priority']['P1'] += 1
                elif 'priority: P2' in content:
                    metrics['by_priority']['P2'] += 1
                else:
                    metrics['by_priority']['P3'] += 1

        # Calculate completion rate
        total = metrics['completed'] + metrics['pending']
        if total > 0:
            metrics['completion_rate'] = round(metrics['completed'] / total * 100, 1)

        return metrics

    def gather_communication_metrics(self, days: int = 7) -> Dict:
        """Gather communication metrics from logs"""
        metrics = {
            'emails_processed': 0,
            'emails_sent': 0,
            'social_posts': 0,
            'messages_handled': 0,
            'by_platform': {}
        }

        cutoff = datetime.now() - timedelta(days=days)

        for log_file in self.logs_path.glob('*.json'):
            try:
                log_date = datetime.strptime(log_file.stem, '%Y-%m-%d')
                if log_date < cutoff:
                    continue

                with open(log_file, 'r') as f:
                    logs = json.load(f)

                for entry in logs:
                    action = entry.get('action_type', '')

                    if 'email' in action:
                        if 'sent' in action:
                            metrics['emails_sent'] += 1
                        else:
                            metrics['emails_processed'] += 1

                    if 'post' in action:
                        metrics['social_posts'] += 1

                    # Track by platform
                    for platform in ['gmail', 'linkedin', 'twitter', 'facebook', 'instagram', 'whatsapp']:
                        if platform in action:
                            metrics['by_platform'][platform] = metrics['by_platform'].get(platform, 0) + 1
                            if 'message' in action or 'dm' in action:
                                metrics['messages_handled'] += 1

            except:
                pass

        return metrics

    def gather_financial_metrics(self) -> Dict:
        """Gather financial metrics from Odoo"""
        metrics = {
            'available': ODOO_AVAILABLE,
            'total_invoiced': 0,
            'total_received': 0,
            'outstanding': 0,
            'overdue_count': 0,
            'overdue_amount': 0
        }

        if not ODOO_AVAILABLE or not self.odoo:
            return metrics

        try:
            if not self.odoo.connect():
                return metrics

            # Get invoices
            invoices = self.odoo.get_invoices(limit=100)
            unpaid = self.odoo.get_unpaid_invoices()

            week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

            for inv in invoices:
                if inv.get('invoice_date', '') >= week_ago:
                    metrics['total_invoiced'] += inv.get('amount_total', 0)

            metrics['outstanding'] = sum(inv.get('amount_residual', 0) for inv in unpaid)

            # Check overdue
            today = datetime.now().strftime('%Y-%m-%d')
            for inv in unpaid:
                due = inv.get('invoice_date_due', '')
                if due and due < today:
                    metrics['overdue_count'] += 1
                    metrics['overdue_amount'] += inv.get('amount_residual', 0)

            # Get payments
            payments = self.odoo.get_payments(limit=100)
            for pay in payments:
                if pay.get('date', '') >= week_ago:
                    metrics['total_received'] += pay.get('amount', 0)

        except Exception as e:
            metrics['error'] = str(e)

        return metrics

    def identify_bottlenecks(self, task_metrics: Dict) -> List[str]:
        """Identify operational bottlenecks"""
        bottlenecks = []

        if task_metrics['by_priority']['P1'] > 3:
            bottlenecks.append(f"🔴 {task_metrics['by_priority']['P1']} critical (P1) tasks pending")

        if task_metrics['pending'] > 20:
            bottlenecks.append(f"⚠️ High backlog: {task_metrics['pending']} tasks pending")

        if task_metrics['completion_rate'] < 50:
            bottlenecks.append(f"📉 Low completion rate: {task_metrics['completion_rate']}%")

        # Check for stale tasks (older than 3 days)
        stale_count = 0
        cutoff = datetime.now() - timedelta(days=3)
        if self.needs_action_path.exists():
            for f in self.needs_action_path.glob('*.md'):
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < cutoff:
                    stale_count += 1

        if stale_count > 5:
            bottlenecks.append(f"⏰ {stale_count} tasks older than 3 days")

        return bottlenecks

    def generate_proactive_suggestions(
        self,
        task_metrics: Dict,
        comm_metrics: Dict,
        financial_metrics: Dict
    ) -> List[str]:
        """Generate proactive suggestions based on data"""
        suggestions = []

        # Financial suggestions
        if financial_metrics['available']:
            if financial_metrics['overdue_amount'] > 1000:
                suggestions.append(
                    f"💰 Send payment reminders for ${financial_metrics['overdue_amount']:,.2f} overdue"
                )

            if financial_metrics['outstanding'] > 10000:
                suggestions.append(
                    "📊 Review accounts receivable - high outstanding balance"
                )

        # Task suggestions
        if task_metrics['by_priority']['P1'] > 0:
            suggestions.append(
                f"🎯 Prioritize {task_metrics['by_priority']['P1']} critical tasks today"
            )

        if task_metrics['pending'] > task_metrics['completed']:
            suggestions.append(
                "📈 Consider batch processing to reduce backlog"
            )

        # Communication suggestions
        if comm_metrics['emails_processed'] > 50 and comm_metrics['emails_sent'] < 10:
            suggestions.append(
                "📧 High email volume - consider response templates"
            )

        # Social media suggestions
        if comm_metrics['social_posts'] < 3:
            suggestions.append(
                "📱 Increase social media presence - less than 3 posts this week"
            )

        return suggestions

    def generate_briefing(self) -> Dict:
        """Generate comprehensive CEO briefing"""
        timestamp = datetime.now()
        week_start = timestamp - timedelta(days=7)

        # Gather all metrics
        task_metrics = self.gather_task_metrics()
        comm_metrics = self.gather_communication_metrics()
        financial_metrics = self.gather_financial_metrics()
        bottlenecks = self.identify_bottlenecks(task_metrics)
        suggestions = self.generate_proactive_suggestions(task_metrics, comm_metrics, financial_metrics)

        # Generate briefing content
        briefing_content = f'''---
type: ceo_briefing
generated: {timestamp.isoformat()}
period: {week_start.strftime('%Y-%m-%d')} to {timestamp.strftime('%Y-%m-%d')}
---

# 📊 CEO Briefing
## Week of {week_start.strftime('%B %d')} - {timestamp.strftime('%B %d, %Y')}

---

## Executive Summary

Your AI Employee processed **{task_metrics['completed']} tasks** this week with a **{task_metrics['completion_rate']}% completion rate**.

'''

        # Financial Section
        if financial_metrics['available']:
            net_flow = financial_metrics['total_received'] - financial_metrics['total_invoiced']
            flow_indicator = "📈" if net_flow >= 0 else "📉"

            briefing_content += f'''## 💰 Financial Overview

| Metric | Amount |
|--------|--------|
| Revenue (Invoiced) | ${financial_metrics['total_invoiced']:,.2f} |
| Cash Received | ${financial_metrics['total_received']:,.2f} |
| Net Cash Flow | {flow_indicator} ${abs(net_flow):,.2f} |
| Outstanding Balance | ${financial_metrics['outstanding']:,.2f} |
| Overdue Invoices | {financial_metrics['overdue_count']} (${financial_metrics['overdue_amount']:,.2f}) |

'''
        else:
            briefing_content += '''## 💰 Financial Overview

*Odoo not connected. Configure ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD environment variables.*

'''

        # Task Performance
        briefing_content += f'''## ✅ Task Performance

| Metric | Count |
|--------|-------|
| Completed This Week | {task_metrics['completed']} |
| Currently Pending | {task_metrics['pending']} |
| Completion Rate | {task_metrics['completion_rate']}% |

### By Priority
- 🔴 Critical (P1): {task_metrics['by_priority']['P1']}
- 🟡 High (P2): {task_metrics['by_priority']['P2']}
- 🟢 Normal (P3): {task_metrics['by_priority']['P3']}

### By Type
'''
        for type_name, count in task_metrics['by_type'].items():
            briefing_content += f"- {type_name}: {count}\n"

        if not task_metrics['by_type']:
            briefing_content += "- No categorized tasks\n"

        # Communication Stats
        briefing_content += f'''
## 📧 Communication Stats

| Channel | Activity |
|---------|----------|
| Emails Processed | {comm_metrics['emails_processed']} |
| Emails Sent | {comm_metrics['emails_sent']} |
| Social Posts | {comm_metrics['social_posts']} |
| Messages Handled | {comm_metrics['messages_handled']} |

### By Platform
'''
        for platform, count in comm_metrics['by_platform'].items():
            briefing_content += f"- {platform.title()}: {count} actions\n"

        if not comm_metrics['by_platform']:
            briefing_content += "- No platform activity logged\n"

        # Bottlenecks
        briefing_content += f'''
## ⚠️ Bottlenecks Identified

'''
        if bottlenecks:
            for b in bottlenecks:
                briefing_content += f"- {b}\n"
        else:
            briefing_content += "- ✅ No significant bottlenecks detected\n"

        # Proactive Suggestions
        briefing_content += f'''
## 💡 Proactive Suggestions

'''
        if suggestions:
            for i, s in enumerate(suggestions, 1):
                briefing_content += f"{i}. {s}\n"
        else:
            briefing_content += "- 🎉 Everything looks great! Keep up the good work.\n"

        # Action Items
        briefing_content += f'''
## 📋 Recommended Actions This Week

'''
        action_items = []
        if financial_metrics['overdue_count'] > 0:
            action_items.append(f"[ ] Follow up on {financial_metrics['overdue_count']} overdue invoices")
        if task_metrics['by_priority']['P1'] > 0:
            action_items.append(f"[ ] Address {task_metrics['by_priority']['P1']} critical tasks")
        if task_metrics['pending'] > 10:
            action_items.append(f"[ ] Review and prioritize {task_metrics['pending']} pending tasks")
        if comm_metrics['social_posts'] < 5:
            action_items.append("[ ] Schedule more social media content")

        if action_items:
            for item in action_items:
                briefing_content += f"- {item}\n"
        else:
            briefing_content += "- ✅ No urgent actions required\n"

        briefing_content += f'''
---

*This CEO Briefing was automatically generated by your AI Employee.*
*Generated: {timestamp.strftime('%Y-%m-%d %H:%M')}*
'''

        # Save briefing
        filename = f"CEO_BRIEFING_{timestamp.strftime('%Y-%m-%d')}.md"
        briefing_path = self.briefings_path / filename
        briefing_path.write_text(briefing_content)

        # Also save to Inbox for visibility
        inbox_path = self.vault_path / 'Inbox' / f"WEEKLY_CEO_BRIEFING_{timestamp.strftime('%Y-%m-%d')}.md"
        inbox_path.write_text(briefing_content)

        # Log
        log_file = self.logs_path / f'{timestamp.strftime("%Y-%m-%d")}.json'
        logs = []
        if log_file.exists():
            with open(log_file, 'r') as f:
                logs = json.load(f)

        logs.append({
            'timestamp': timestamp.isoformat(),
            'action_type': 'ceo_briefing_generated',
            'tasks_completed': task_metrics['completed'],
            'completion_rate': task_metrics['completion_rate']
        })

        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)

        return {
            'status': 'success',
            'briefing_file': str(briefing_path),
            'summary': {
                'tasks_completed': task_metrics['completed'],
                'completion_rate': task_metrics['completion_rate'],
                'bottlenecks': len(bottlenecks),
                'suggestions': len(suggestions)
            }
        }


def main():
    generator = CEOBriefingGenerator()
    result = generator.generate_briefing()
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
