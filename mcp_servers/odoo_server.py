"""
Odoo MCP Server - Integrates with Odoo Community for accounting
Gold Tier Requirement: Odoo accounting integration via MCP

Connects to Odoo via JSON-2 API (Odoo 19+) - NEW FORMAT
Supports: Invoices, Payments, Customers, Products, Reports
"""
import sys
import json
import requests
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
VAULT_PATH = PROJECT_ROOT / 'AI_Employee_Vault'
if VAULT_PATH.is_symlink():
    VAULT_PATH = VAULT_PATH.resolve()


class OdooMCPServer:
    """
    MCP Server for Odoo Community accounting integration using JSON-2 API (Odoo 19+).

    Setup:
    1. Have Odoo Community instance running (cloud or local)
    2. Configure connection in .env with API key
    3. Enable API access in Odoo (requires Custom plan)

    Usage:
        server = OdooMCPServer(url, db, username, api_key)
        contacts = server.get_contacts()
    """

    def __init__(
        self,
        url: str = None,
        db: str = None,
        username: str = None,
        api_key: str = None
    ):
        # Load from environment or use defaults
        self.url = url or os.getenv('ODOO_URL', 'https://giaic1.odoo.com')
        self.db = db or os.getenv('ODOO_DB', 'giaic1')
        self.username = username or os.getenv('ODOO_USERNAME', 'aqsa.gull.dev.ai99@gmail.com')
        self.api_key = api_key or os.getenv('ODOO_API_KEY') or os.getenv('ODOO_PASSWORD', 'd81dded5ab1c5e428e3058079937940e7837bc69')
        
        # Set up base URL for JSON-2 API
        self.base_url = f"{self.url.rstrip('/')}/json/2"
        
        # Vault paths
        self.logs_path = VAULT_PATH / 'Logs'
        self.pending_approval = VAULT_PATH / 'Pending_Approval'
        self.reports_path = VAULT_PATH / 'Reports'

        self.logs_path.mkdir(exist_ok=True)
        self.pending_approval.mkdir(exist_ok=True)
        self.reports_path.mkdir(exist_ok=True)

    def connect(self) -> bool:
        """Establish connection to Odoo using JSON-2 API with API key authentication"""
        try:
            # Test connection by getting version info
            headers = self._get_headers()
            
            # Make a simple request to test connection
            response = requests.post(
                f"{self.base_url}/res.users/search",
                headers=headers,
                json={
                    "domain": [("login", "=", self.username)],
                    "context": {"lang": "en_US"}
                }
            )

            if response.status_code == 200:
                result = response.json()
                # Connection successful if we get a valid response
                self._log_action('odoo_connected', {'status': 'success', 'url': self.url})
                return True
            else:
                raise Exception(f"Connection failed: HTTP {response.status_code}, {response.text}")

        except Exception as e:
            self._log_action('odoo_connection_failed', {'error': str(e)})
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for JSON-2 API requests"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Odoo-Database": self.db,
            "User-Agent": "AI_Employee_Odoo_Integration"
        }
        return headers

    def _json2_call(self, model: str, method: str, params: dict = None) -> Any:
        """Execute Odoo API call using JSON-2 API format"""
        if params is None:
            params = {}

        try:
            if not self.api_key:
                raise Exception("API key not provided")

            url = f"{self.base_url}/{model}/{method}"
            headers = self._get_headers()
            
            response = requests.post(
                url,
                headers=headers,
                json=params
            )

            if response.status_code == 200:
                result = response.json()
                return result
            else:
                raise Exception(f"HTTP Error: {response.status_code}, Response: {response.text}")

        except Exception as e:
            self._log_action('odoo_api_call_failed', {
                'model': model,
                'method': method,
                'error': str(e)
            })
            raise

    def _execute(self, model: str, method: str, *args, **kwargs) -> Any:
        """Execute Odoo API call using JSON-2 API format"""
        # Convert *args and **kwargs to the format expected by JSON-2 API
        params = {}
        
        # Handle different parameter structures based on the method
        if method == 'search':
            # For search methods, expect domain as first argument
            if args:
                params['domain'] = args[0]
            if 'domain' in kwargs:
                params['domain'] = kwargs['domain']
            if 'context' in kwargs:
                params['context'] = kwargs['context']
                
        elif method == 'search_read':
            # For search_read methods
            if args:
                params['domain'] = args[0] if args[0] is not None else []
            else:
                params['domain'] = kwargs.get('domain', [])
            
            if len(args) > 1:
                params['fields'] = args[1]
            elif 'fields' in kwargs:
                params['fields'] = kwargs['fields']
                
            if 'limit' in kwargs:
                params['limit'] = kwargs['limit']
            if 'order' in kwargs:
                params['order'] = kwargs['order']
            if 'context' in kwargs:
                params['context'] = kwargs['context']
                
        elif method == 'read':
            # For read methods, expect ids as first argument
            if args:
                params['ids'] = args[0]
            if 'ids' in kwargs:
                params['ids'] = kwargs['ids']
            if 'fields' in kwargs:
                params['fields'] = kwargs['fields']
            if 'context' in kwargs:
                params['context'] = kwargs['context']
                
        elif method == 'create':
            # For create methods, expect vals_list as the parameter
            if args:
                if isinstance(args[0], dict) and 'vals_list' in args[0]:
                    # Already in the correct format
                    params.update(args[0])
                else:
                    # Wrap the values in vals_list
                    if isinstance(args[0], dict):
                        params['vals_list'] = [args[0]]
                    else:
                        params['vals_list'] = args
            if kwargs and 'vals_list' not in kwargs:
                # If kwargs don't already contain vals_list, wrap them
                params['vals_list'] = [kwargs]
            elif kwargs:
                # If kwargs contain vals_list, merge directly
                params.update(kwargs)
                
        else:
            # For other methods
            if args:
                if isinstance(args[0], dict):
                    params['param'] = args[0]
                else:
                    params['param'] = args
            
            if kwargs:
                params.update(kwargs)
        
        return self._json2_call(model, method, params)

    # ==================== INVOICES ====================

    def get_invoices(self, state: str = None, limit: int = 50) -> List[Dict]:
        """Get invoices from Odoo"""
        domain = [['move_type', 'in', ['out_invoice', 'out_refund']]]
        if state:
            domain.append(['state', '=', state])

        invoices = self._execute(
            'account.move', 'search_read',
            domain,
            fields=['name', 'partner_id', 'amount_total', 'amount_residual',
                    'state', 'invoice_date', 'invoice_date_due'],
            limit=limit,
            order='invoice_date desc'
        )

        return invoices

    def get_unpaid_invoices(self) -> List[Dict]:
        """Get unpaid/overdue invoices"""
        return self.get_invoices(state='posted')

    def create_invoice(
        self,
        partner_id: int,
        lines: List[Dict],
        require_approval: bool = True
    ) -> Dict:
        """
        Create a new invoice.

        Args:
            partner_id: Customer ID
            lines: List of invoice lines [{'product_id': x, 'quantity': y, 'price_unit': z}]
            require_approval: If True, creates approval file first
        """
        if require_approval:
            return self._create_invoice_approval(partner_id, lines)

        try:
            # Create invoice
            result = self._execute(
                'account.move', 'create',
                {
                    'vals_list': [{
                        'move_type': 'out_invoice',
                        'partner_id': partner_id,
                        'invoice_line_ids': [(0, 0, line) for line in lines]
                    }]
                }
            )

            # The result from JSON-2 API is the record ID directly
            invoice_id = result

            self._log_action('invoice_created', {
                'invoice_id': invoice_id,
                'partner_id': partner_id
            })

            return {
                'status': 'success',
                'invoice_id': invoice_id,
                'message': f'Invoice created: {invoice_id}'
            }

        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _create_invoice_approval(self, partner_id: int, lines: List[Dict]) -> Dict:
        """Create approval request for invoice"""
        timestamp = datetime.now()
        filename = f"ODOO_INVOICE_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"

        total = sum(l.get('price_unit', 0) * l.get('quantity', 1) for l in lines)

        content = f'''---
type: odoo_invoice_approval
action: create_invoice
created: {timestamp.isoformat()}
partner_id: {partner_id}
total_amount: {total}
status: pending
---

## Odoo Invoice Request

### Customer ID: {partner_id}

### Invoice Lines
| Product ID | Quantity | Unit Price | Subtotal |
|------------|----------|------------|----------|
'''
        for line in lines:
            subtotal = line.get('price_unit', 0) * line.get('quantity', 1)
            content += f"| {line.get('product_id', 'N/A')} | {line.get('quantity', 1)} | ${line.get('price_unit', 0):.2f} | ${subtotal:.2f} |\n"

        content += f'''
### Total: ${total:.2f}

---

### To Approve
Move this file to /Approved folder.

### To Reject
Delete or move to /Done.

---
*Invoice requires human approval before creation.*
'''

        approval_path = self.pending_approval / filename
        approval_path.write_text(content)

        return {
            'status': 'pending_approval',
            'approval_file': str(approval_path),
            'total': total
        }

    # ==================== PAYMENTS ====================

    def get_payments(self, state: str = None, limit: int = 50) -> List[Dict]:
        """Get payments from Odoo"""
        domain = []
        if state:
            domain.append(['state', '=', state])

        payments = self._execute(
            'account.payment', 'search_read',
            domain,
            fields=['name', 'partner_id', 'amount', 'payment_type',
                    'state', 'date'],
            limit=limit,
            order='date desc'
        )

        return payments

    def record_payment(
        self,
        partner_id: int,
        amount: float,
        payment_type: str = 'inbound',
        require_approval: bool = True
    ) -> Dict:
        """Record a payment"""
        if require_approval:
            return self._create_payment_approval(partner_id, amount, payment_type)

        try:
            result = self._execute(
                'account.payment', 'create',
                {
                    'vals_list': [{
                        'partner_id': partner_id,
                        'amount': amount,
                        'payment_type': payment_type,
                    }]
                }
            )

            # The result from JSON-2 API is the record ID directly
            payment_id = result

            self._log_action('payment_recorded', {
                'payment_id': payment_id,
                'amount': amount
            })

            return {
                'status': 'success',
                'payment_id': payment_id,
                'message': f'Payment recorded: ${amount}'
            }

        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _create_payment_approval(self, partner_id: int, amount: float, payment_type: str) -> Dict:
        """Create approval request for payment"""
        timestamp = datetime.now()
        filename = f"ODOO_PAYMENT_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"

        content = f'''---
type: odoo_payment_approval
action: record_payment
created: {timestamp.isoformat()}
partner_id: {partner_id}
amount: {amount}
payment_type: {payment_type}
status: pending
---

## Odoo Payment Request

### Details
- **Customer ID:** {partner_id}
- **Amount:** ${amount:.2f}
- **Type:** {payment_type}
- **Date:** {timestamp.strftime('%Y-%m-%d')}

---

### To Approve
Move this file to /Approved folder.

### To Reject
Delete or move to /Done.

---
*Payment requires human approval before recording.*
'''

        approval_path = self.pending_approval / filename
        approval_path.write_text(content)

        return {
            'status': 'pending_approval',
            'approval_file': str(approval_path),
            'amount': amount
        }

    # ==================== CUSTOMERS ====================

    def get_customers(self, limit: int = 100) -> List[Dict]:
        """Get customers from Odoo"""
        customers = self._execute(
            'res.partner', 'search_read',
            [['customer_rank', '>', 0]],
            fields=['name', 'email', 'phone', 'credit', 'debit'],
            limit=limit
        )
        return customers

    def create_customer(self, name: str, email: str = None, phone: str = None) -> Dict:
        """Create a new customer"""
        try:
            result = self._execute(
                'res.partner', 'create',
                {
                    'vals_list': [{
                        'name': name,
                        'email': email,
                        'phone': phone
                    }]
                }
            )

            # The result from JSON-2 API is the record ID directly
            partner_id = result

            self._log_action('customer_created', {
                'partner_id': partner_id,
                'name': name
            })

            return {
                'status': 'success',
                'partner_id': partner_id,
                'message': f'Customer created: {name}'
            }

        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    # ==================== CONTACTS (CUSTOMERS/SUPPLIERS) ====================

    def get_contacts(self, limit: int = 100) -> List[Dict]:
        """Get all contacts (customers and suppliers) from Odoo"""
        contacts = self._execute(
            'res.partner', 'search_read',
            [['is_company', '=', False]],  # Get individuals (contacts)
            fields=['name', 'email', 'phone', 'function', 'parent_id'],
            limit=limit
        )
        return contacts

    def get_companies(self, limit: int = 100) -> List[Dict]:
        """Get companies (customers/suppliers) from Odoo"""
        companies = self._execute(
            'res.partner', 'search_read',
            [['is_company', '=', True]],  # Get companies
            fields=['name', 'email', 'phone', 'website'],
            limit=limit
        )
        return companies

    # ==================== REPORTS ====================

    def generate_weekly_audit(self) -> Dict:
        """Generate weekly business audit report"""
        timestamp = datetime.now()
        week_ago = timestamp - timedelta(days=7)

        try:
            # Get data
            invoices = self.get_invoices(limit=100)
            payments = self.get_payments(limit=100)
            unpaid = self.get_unpaid_invoices()

            # Calculate metrics
            total_invoiced = sum(inv.get('amount_total', 0) for inv in invoices
                                if inv.get('invoice_date') and inv.get('invoice_date') >= week_ago.strftime('%Y-%m-%d'))
            total_received = sum(pay.get('amount', 0) for pay in payments
                                if pay.get('date') and pay.get('date') >= week_ago.strftime('%Y-%m-%d'))
            total_outstanding = sum(inv.get('amount_residual', 0) for inv in unpaid)

            # Generate report
            report_content = f'''---
type: weekly_audit
generated: {timestamp.isoformat()}
period: {week_ago.strftime('%Y-%m-%d')} to {timestamp.strftime('%Y-%m-%d')}
---

# Weekly Business Audit
## {week_ago.strftime('%B %d')} - {timestamp.strftime('%B %d, %Y')}

## Financial Summary

| Metric | Amount |
|--------|--------|
| Total Invoiced (This Week) | ${total_invoiced:,.2f} |
| Total Received (This Week) | ${total_received:,.2f} |
| Outstanding Balance | ${total_outstanding:,.2f} |
| Net Cash Flow | ${total_received - total_invoiced:,.2f} |

## Invoices This Week
Total: {len([i for i in invoices if i.get('invoice_date', '') >= week_ago.strftime('%Y-%m-%d')])}

## Overdue Invoices
'''
            overdue_count = 0
            for inv in unpaid:
                due_date = inv.get('invoice_date_due')
                if due_date and due_date < timestamp.strftime('%Y-%m-%d'):
                    overdue_count += 1
                    report_content += f"- {inv.get('name')}: ${inv.get('amount_residual', 0):,.2f} (Due: {due_date})\n"

            if overdue_count == 0:
                report_content += "- No overdue invoices ✅\n"

            report_content += f'''
## Recommendations
'''
            if total_outstanding > 10000:
                report_content += "- ⚠️ High outstanding balance - consider follow-up on unpaid invoices\n"
            if overdue_count > 5:
                report_content += "- ⚠️ Multiple overdue invoices - prioritize collections\n"
            if total_received < total_invoiced:
                report_content += "- 📊 Cash flow negative this week - monitor closely\n"
            if total_outstanding == 0 and overdue_count == 0:
                report_content += "- ✅ All invoices paid - excellent financial health!\n"

            report_content += f'''
---
*Generated by AI Employee Odoo Integration: {timestamp.strftime('%Y-%m-%d %H:%M')}*
'''

            # Save report
            filename = f"AUDIT_{timestamp.strftime('%Y-%m-%d')}.md"
            report_path = self.reports_path / filename
            report_path.write_text(report_content)

            self._log_action('audit_generated', {
                'total_invoiced': total_invoiced,
                'total_received': total_received,
                'outstanding': total_outstanding
            })

            return {
                'status': 'success',
                'report_file': str(report_path),
                'summary': {
                    'total_invoiced': total_invoiced,
                    'total_received': total_received,
                    'outstanding': total_outstanding
                }
            }

        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _log_action(self, action_type: str, details: dict):
        """Log Odoo action"""
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.logs_path / f'{today}.json'

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action_type': action_type,
            'server': 'odoo_mcp',
            **details
        }

        logs = []
        if log_file.exists():
            with open(log_file, 'r') as f:
                logs = json.load(f)

        logs.append(log_entry)

        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)


def main():
    # Load environment variables
    load_dotenv()
    
    if len(sys.argv) < 2:
        print('''
Odoo MCP Server
===============

Usage:
    python odoo_server.py connect              Test connection
    python odoo_server.py invoices [state]     List invoices
    python odoo_server.py unpaid               List unpaid invoices
    python odoo_server.py payments             List payments
    python odoo_server.py customers            List customers
    python odoo_server.py contacts             List contacts
    python odoo_server.py companies            List companies
    python odoo_server.py audit                Generate weekly audit

Environment Variables:
    ODOO_URL       Odoo server URL (default: https://giaic1.odoo.com)
    ODOO_DB        Database name (default: giaic1)
    ODOO_USERNAME  Username (default: aqsa.gull.dev.ai99@gmail.com)
    ODOO_API_KEY   API key for authentication (alternative to ODOO_PASSWORD)
    ODOO_PASSWORD  Password/API key for authentication (default: your API key)

Examples:
    export ODOO_URL=https://yourcompany.odoo.com
    export ODOO_DB=your_database
    export ODOO_USERNAME=your_email@example.com
    export ODOO_API_KEY=your_api_key
    python odoo_server.py connect
    python odoo_server.py contacts
    python odoo_server.py invoices posted
''')
        sys.exit(1)

    server = OdooMCPServer()
    command = sys.argv[1]

    if command == 'connect':
        if server.connect():
            print("✅ Connected to Odoo successfully!")
        else:
            print("❌ Failed to connect to Odoo")

    elif command == 'invoices':
        state = sys.argv[2] if len(sys.argv) > 2 else None
        invoices = server.get_invoices(state=state)
        print(f"Found {len(invoices)} invoices:")
        for inv in invoices[:10]:
            print(f"  - {inv.get('name')}: ${inv.get('amount_total', 0):.2f} ({inv.get('state')})")

    elif command == 'unpaid':
        invoices = server.get_unpaid_invoices()
        print(f"Found {len(invoices)} unpaid invoices:")
        for inv in invoices:
            print(f"  - {inv.get('name')}: ${inv.get('amount_residual', 0):.2f}")

    elif command == 'payments':
        payments = server.get_payments()
        print(f"Found {len(payments)} payments:")
        for pay in payments[:10]:
            print(f"  - {pay.get('name')}: ${pay.get('amount', 0):.2f}")

    elif command == 'customers':
        customers = server.get_customers()
        print(f"Found {len(customers)} customers:")
        for cust in customers[:10]:
            print(f"  - {cust.get('name')} ({cust.get('email', 'N/A')})")

    elif command == 'contacts':
        contacts = server.get_contacts()
        print(f"Found {len(contacts)} contacts:")
        for contact in contacts[:10]:
            company = contact.get('parent_id', [None, ''])[1] if contact.get('parent_id') else 'N/A'
            print(f"  - {contact.get('name')} ({contact.get('email', 'N/A')}) - {company}")

    elif command == 'companies':
        companies = server.get_companies()
        print(f"Found {len(companies)} companies:")
        for company in companies[:10]:
            print(f"  - {company.get('name')} ({company.get('email', 'N/A')})")

    elif command == 'audit':
        result = server.generate_weekly_audit()
        print(json.dumps(result, indent=2))

    else:
        print(f"Unknown command: {command}")


if __name__ == '__main__':
    main()
