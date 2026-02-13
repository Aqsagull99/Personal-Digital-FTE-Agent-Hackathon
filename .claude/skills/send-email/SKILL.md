---
name: send-email
description: Send email via Gmail API with human-in-the-loop approval. Use when user says "send email", "email someone", "reply to email", or "compose email".
---

# Send Email Skill

## Purpose
Send emails via Gmail API with approval workflow for unknown contacts.

## Human-in-the-Loop
- **Known contacts**: Emails sent automatically
- **Unknown contacts**: Creates approval file first

## Workflow

### Step 1: Check if approval needed
- If recipient in known contacts → send directly
- If unknown → create approval file

### Step 2: Send or Create Approval
```bash
# Send email (creates approval if unknown contact)
uv run python mcp_servers/email_server.py send "to@example.com" "Subject" "Body text"

# Create draft only (no approval needed)
uv run python mcp_servers/email_server.py draft "to@example.com" "Subject" "Body text"
```

### Step 3: Process Approved Emails
```bash
uv run python mcp_servers/email_server.py process-approved
```

## Commands

### Send Email
```bash
uv run python mcp_servers/email_server.py send "recipient@email.com" "Subject Line" "Email body here"
```

### Create Draft
```bash
uv run python mcp_servers/email_server.py draft "recipient@email.com" "Subject" "Body"
```

### Add Known Contact
```bash
uv run python mcp_servers/email_server.py add-contact "trusted@email.com"
```

### Process Approved Emails
```bash
uv run python mcp_servers/email_server.py process-approved
```

## Approval Workflow

1. Unknown recipient → `/Pending_Approval/EMAIL_SEND_*.md` created
2. User reviews and moves to `/Approved/`
3. Run `process-approved` to send
4. File moves to `/Done/`

## Known Contacts
Stored in: `AI_Employee_Vault/known_contacts.json`

Add trusted contacts to skip approval:
```bash
uv run python mcp_servers/email_server.py add-contact "email@example.com"
```

## Prerequisites
- `credentials.json` in project root
- First run requires Gmail OAuth (send permission)
- Token saved as `token_send.json`

## Output
- Success: Email sent, logged
- Pending: Approval file created in `/Pending_Approval/`
- Logs: `/Logs/[date].json`

## Security
- Unknown contacts always require approval
- All actions logged
- Separate token for send permission
