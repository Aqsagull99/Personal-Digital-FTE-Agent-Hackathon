---
name: odoo-accounting
description: Manage Odoo accounting - invoices, payments, customers, reports. Use when user says "check invoices", "odoo", "accounting", "create invoice", "record payment", "business audit", or "financial report".
---

# Odoo Accounting Skill

## Purpose
Integrate with Odoo Community ERP for accounting operations.

## Prerequisites

### 1. Install Odoo Community
```bash
# Docker (recommended)
docker run -d -p 8069:8069 --name odoo -e POSTGRES_USER=odoo odoo:19
```

Or install locally: https://www.odoo.com/documentation

### 2. Configure Connection
```bash
export ODOO_URL=http://localhost:8069
export ODOO_DB=odoo
export ODOO_USERNAME=admin
export ODOO_PASSWORD=your_odoo_password_here
```

## Commands

### Test Connection
```bash
uv run python mcp_servers/odoo_server.py connect
```

### List Invoices
```bash
uv run python mcp_servers/odoo_server.py invoices
uv run python mcp_servers/odoo_server.py invoices posted  # Filter by state
```

### Unpaid Invoices
```bash
uv run python mcp_servers/odoo_server.py unpaid
```

### List Payments
```bash
uv run python mcp_servers/odoo_server.py payments
```

### List Customers
```bash
uv run python mcp_servers/odoo_server.py customers
```

### Weekly Business Audit
```bash
uv run python mcp_servers/odoo_server.py audit
```

## Features

### Invoices
- List all invoices
- Filter by state (draft, posted, paid)
- Create new invoices (with approval)
- Track unpaid/overdue

### Payments
- List payments
- Record incoming payments
- Human-in-the-loop for amounts

### Customers
- List customers
- Create new customers
- View credit/debit balances

### Reports
- Weekly business audit
- Financial summary
- Overdue invoice alerts
- Cash flow analysis

## Approval Workflow

Creating invoices/payments requires approval:
1. Command creates `/Pending_Approval/ODOO_*.md`
2. Human reviews and moves to `/Approved/`
3. Action executed in Odoo

## Weekly Audit Output

Generated report includes:
- Total invoiced this week
- Total received this week
- Outstanding balance
- Overdue invoices list
- Recommendations

Output: `/Reports/AUDIT_[date].md`

## API Reference

Uses Odoo XML-RPC API:
- `/xmlrpc/2/common` - Authentication
- `/xmlrpc/2/object` - Model operations

Models used:
- `account.move` - Invoices
- `account.payment` - Payments
- `res.partner` - Customers
