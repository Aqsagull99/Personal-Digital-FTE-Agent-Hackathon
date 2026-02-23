#!/usr/bin/env python3
"""
Local Executive Agent (Platinum Tier)

Responsibilities:
1. Monitor synced vault queues:
   - /Pending_Approval/
   - /Needs_Action/cloud/
2. Enforce single-writer dashboard flow:
   - Merge files from /Updates/ into dashboard notes
   - Update Dashboard.md from local agent only
3. Own sensitive execution paths:
   - Final approved actions (email/payment/social via main.process_approved)
   - WhatsApp final replies from /Approved/WHATSAPP_REPLY_*.md
4. Claim-by-move for cloud drafts:
   - /Needs_Action/cloud/*.md -> /In_Progress/local/*.md
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote_plus


def resolve_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


PROJECT_ROOT = resolve_project_root()
VAULT_PATH = Path(os.getenv("VAULT_PATH", str(PROJECT_ROOT / "AI_Employee_Vault")))
if VAULT_PATH.is_symlink():
    VAULT_PATH = VAULT_PATH.resolve()

NEEDS_ACTION_CLOUD = VAULT_PATH / "Needs_Action" / "cloud"
PENDING_APPROVAL = VAULT_PATH / "Pending_Approval"
APPROVED = VAULT_PATH / "Approved"
IN_PROGRESS_LOCAL = VAULT_PATH / "In_Progress" / "local"
DONE = VAULT_PATH / "Done"
UPDATES = VAULT_PATH / "Updates"
STATE = VAULT_PATH / "State"
LOGS = VAULT_PATH / "Logs"
DASHBOARD = VAULT_PATH / "Dashboard.md"
DASHBOARD_LOCK = STATE / "dashboard_writer.lock"
POLL_SECONDS = int(os.getenv("LOCAL_EXEC_POLL_SECONDS", "20"))


def ensure_dirs() -> None:
    for folder in [
        NEEDS_ACTION_CLOUD,
        PENDING_APPROVAL,
        APPROVED,
        IN_PROGRESS_LOCAL,
        DONE,
        UPDATES,
        STATE,
        LOGS,
    ]:
        folder.mkdir(parents=True, exist_ok=True)


def log_line(message: str) -> None:
    log_file = LOGS / f"local_executive_{datetime.now().strftime('%Y-%m-%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} {message}\n")


def parse_frontmatter(text: str) -> Dict[str, str]:
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return {}

    metadata: Dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()
    return metadata


def write_dashboard_lock() -> None:
    payload = {
        "owner": "local",
        "set_at": datetime.now().isoformat(),
        "note": "Single-writer rule: only Local Executive updates Dashboard.md",
    }
    DASHBOARD_LOCK.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def claim_cloud_draft(file_path: Path) -> Optional[Path]:
    target = IN_PROGRESS_LOCAL / file_path.name
    try:
        file_path.rename(target)
        log_line(f"CLAIM cloud_draft {file_path.name} -> {target.name}")
        return target
    except FileNotFoundError:
        return None
    except OSError as exc:
        log_line(f"CLAIM_FAIL {file_path.name} error={exc}")
        return None


def build_local_review_file(claimed: Path, content: str) -> Path:
    ts = datetime.now()
    review_name = f"LOCAL_REVIEW_{claimed.stem}_{ts.strftime('%H%M%S')}.md"
    review_path = PENDING_APPROVAL / review_name
    body = (
        "---\n"
        "type: local_review_approval\n"
        "source: local_executive_agent\n"
        f"created: {ts.isoformat()}\n"
        "status: pending\n"
        "owner: local\n"
        f"original_file: {claimed.name}\n"
        "---\n\n"
        "## Local Executive Review Required\n\n"
        "This item originated from `/Needs_Action/cloud/` and has been claimed by Local.\n\n"
        "### Action\n"
        "- Review this draft\n"
        "- Move to `/Approved/` if execution should proceed\n"
        "- Move to `/Rejected/` if declined\n\n"
        "## Original Cloud Draft\n\n"
        + content[:4000]
        + "\n"
    )
    review_path.write_text(body, encoding="utf-8")
    return review_path


def archive_claimed_source(claimed: Path) -> Path:
    target = DONE / f"CLOUD_CLAIMED_{claimed.name}"
    if target.exists():
        target = DONE / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_CLOUD_CLAIMED_{claimed.name}"
    claimed.rename(target)
    return target


def handoff_cloud_drafts() -> int:
    processed = 0
    for file_path in sorted(NEEDS_ACTION_CLOUD.glob("*.md")):
        claimed = claim_cloud_draft(file_path)
        if not claimed:
            continue
        text = claimed.read_text(encoding="utf-8", errors="ignore")
        review = build_local_review_file(claimed, text)
        archived = archive_claimed_source(claimed)
        log_line(f"HANDOFF created={review.name} archived={archived.name}")
        processed += 1
    return processed


def merge_updates() -> int:
    merged_count = 0
    lines: List[str] = []
    for update_file in sorted(UPDATES.glob("*")):
        if not update_file.is_file():
            continue

        payload = update_file.read_text(encoding="utf-8", errors="ignore")
        lines.append(f"- **{datetime.now().strftime('%Y-%m-%d %H:%M')}** `{update_file.name}`")
        lines.append("")
        lines.append(payload[:1200])
        lines.append("")

        target = DONE / f"MERGED_UPDATE_{update_file.name}"
        if target.exists():
            target = DONE / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_MERGED_UPDATE_{update_file.name}"
        update_file.rename(target)
        merged_count += 1

    if merged_count == 0:
        return 0

    updates_md = LOGS / "merged_updates.md"
    existing = updates_md.read_text(encoding="utf-8") if updates_md.exists() else ""
    append_block = "## Batch " + datetime.now().isoformat() + "\n\n" + "\n".join(lines) + "\n"
    updates_md.write_text(existing + append_block, encoding="utf-8")

    update_dashboard_single_writer()
    log_line(f"UPDATES_MERGED count={merged_count}")
    return merged_count


def update_dashboard_single_writer() -> None:
    write_dashboard_lock()
    # Local-only dashboard write gate.
    os.environ["LOCAL_EXEC_AGENT"] = "1"
    from scheduler.tasks.update_dashboard import update_dashboard

    update_dashboard()

    merged_path = LOGS / "merged_updates.md"
    if not merged_path.exists():
        return

    dashboard_text = DASHBOARD.read_text(encoding="utf-8", errors="ignore") if DASHBOARD.exists() else ""
    marker = "## Cloud Updates (Merged by Local Executive)"
    merged_excerpt = merged_path.read_text(encoding="utf-8", errors="ignore")[-5000:]
    section = f"\n{marker}\n\n{merged_excerpt}\n"

    if marker in dashboard_text:
        dashboard_text = dashboard_text.split(marker)[0].rstrip() + section
    else:
        dashboard_text = dashboard_text.rstrip() + section

    DASHBOARD.write_text(dashboard_text, encoding="utf-8")


def send_whatsapp_reply(phone: str, message: str) -> Tuple[bool, str]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return False, f"playwright import failed: {exc}"

    session_dir = PROJECT_ROOT / ".whatsapp_session" / "browser_profile"
    session_dir.mkdir(parents=True, exist_ok=True)
    headless = os.getenv("LOCAL_WHATSAPP_HEADLESS", "false").lower() == "true"

    phone_digits = "".join(ch for ch in phone if ch.isdigit())
    if not phone_digits:
        return False, "invalid phone"

    encoded_msg = quote_plus(message)
    target_url = f"https://web.whatsapp.com/send?phone={phone_digits}&text={encoded_msg}"

    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(session_dir),
                headless=headless,
                viewport={"width": 1280, "height": 800},
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(target_url, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)

            # If login screen/QR is present, we cannot proceed automatically.
            if page.query_selector("canvas[aria-label='Scan me!']") or page.query_selector("div[data-ref]"):
                context.close()
                return False, "whatsapp session not logged in (QR required)"

            sent = False
            for selector in ["button[data-testid='compose-btn-send']", "span[data-icon='send']"]:
                el = page.query_selector(selector)
                if el:
                    el.click()
                    sent = True
                    break

            page.wait_for_timeout(1200)
            context.close()

            if sent:
                return True, "sent"
            return False, "send button not found"
    except Exception as exc:
        return False, str(exc)


def process_whatsapp_approved() -> Dict[str, List[Dict[str, str]]]:
    results: List[Dict[str, str]] = []
    for file_path in sorted(APPROVED.glob("WHATSAPP_REPLY_*.md")):
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        meta = parse_frontmatter(text)
        phone = meta.get("phone") or meta.get("to") or meta.get("recipient", "")
        message = meta.get("message", "")
        if not message:
            # Fallback: first paragraph after frontmatter
            parts = text.split("---", 2)
            if len(parts) == 3:
                message = parts[2].strip().splitlines()[0] if parts[2].strip() else ""

        ok, detail = send_whatsapp_reply(phone=phone, message=message)
        if ok:
            target = DONE / file_path.name
            if target.exists():
                target = DONE / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_path.name}"
            file_path.rename(target)
            results.append({"file": file_path.name, "status": "success", "detail": detail})
            log_line(f"WHATSAPP_SENT file={file_path.name}")
        else:
            results.append({"file": file_path.name, "status": "error", "detail": detail})
            log_line(f"WHATSAPP_ERROR file={file_path.name} detail={detail}")
    return {"whatsapp": results}


def process_final_actions() -> Dict[str, object]:
    from main import process_approved, process_rejected

    approved_summary = process_approved()
    whatsapp_summary = process_whatsapp_approved()
    rejected_summary = process_rejected()
    return {
        "approved": approved_summary,
        "whatsapp": whatsapp_summary,
        "rejected": rejected_summary,
    }


def run() -> None:
    ensure_dirs()
    write_dashboard_lock()
    log_line(
        f"START poll_seconds={POLL_SECONDS} vault={VAULT_PATH} "
        "single_writer=local"
    )

    while True:
        try:
            handoff_count = handoff_cloud_drafts()
            merge_count = merge_updates()
            action_summary = process_final_actions()
            pending_count = len(list(PENDING_APPROVAL.glob("*.md")))
            cloud_queue_count = len(list(NEEDS_ACTION_CLOUD.glob("*.md")))
            log_line(
                "TICK "
                f"handoff={handoff_count} merged_updates={merge_count} "
                f"pending={pending_count} cloud_queue={cloud_queue_count} "
                f"approved_email={len(action_summary['approved'].get('email', []))}"
            )
        except KeyboardInterrupt:
            log_line("STOP keyboard_interrupt")
            break
        except Exception as exc:
            log_line(f"ERROR {exc}")

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    run()

