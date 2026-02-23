"""
AI Employee Orchestrator

Provides a minimal orchestration CLI for the approval workflow:
- status: show vault queue/system status
- process-approved: execute approved actions and move completed items
- process-rejected: archive rejected items to Done
- run: continuously process approvals/rejections
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).parent
VAULT_PATH = PROJECT_ROOT / "AI_Employee_Vault"
if VAULT_PATH.is_symlink():
    VAULT_PATH = VAULT_PATH.resolve()

INBOX = VAULT_PATH / "Inbox"
NEEDS_ACTION = VAULT_PATH / "Needs_Action"
PENDING_APPROVAL = VAULT_PATH / "Pending_Approval"
APPROVED = VAULT_PATH / "Approved"
REJECTED = VAULT_PATH / "Rejected"
DONE = VAULT_PATH / "Done"
LOGS = VAULT_PATH / "Logs"
PROCESSED_APPROVALS = LOGS / "processed_approvals.json"


def ensure_vault_dirs() -> None:
    for folder in [INBOX, NEEDS_ACTION, PENDING_APPROVAL, APPROVED, REJECTED, DONE, LOGS]:
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # In restricted/sandboxed environments, vault may be read-only.
            # Commands should still run in read-only mode.
            pass


def _safe_int(value: str, default: int = 0) -> int:
    try:
        return int(float(value.strip().replace("$", "").replace(",", "")))
    except Exception:
        return default


def _safe_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value.strip().replace("$", "").replace(",", ""))
    except Exception:
        return default


def _daily_log_file() -> Path:
    return LOGS / f"{datetime.now().strftime('%Y-%m-%d')}.json"


def _load_processed_approvals() -> Dict:
    try:
        if PROCESSED_APPROVALS.exists():
            with open(PROCESSED_APPROVALS, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    data.setdefault("signatures", {})
                    return data
    except Exception:
        pass
    return {"signatures": {}}


def _save_processed_approvals(data: Dict) -> None:
    try:
        with open(PROCESSED_APPROVALS, "w") as f:
            json.dump(data, f, indent=2)
    except PermissionError:
        pass


def _approval_signature(file_path: Path) -> str:
    payload = file_path.read_text(encoding="utf-8")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return digest


def _record_processed_signature(
    seen: Dict[str, Dict],
    signature: str,
    file_name: str,
    processor: str,
    result_ref: Optional[object] = None,
) -> None:
    seen[signature] = {
        "file": file_name,
        "processor": processor,
        "processed_at": datetime.now().isoformat(),
        "result_ref": result_ref,
    }


def _filter_duplicate_approved_files(
    files: List[Path],
    seen: Dict[str, Dict],
    processor: str,
    summary: Dict[str, List],
) -> Tuple[List[Path], Dict[str, str]]:
    """
    Move duplicate approved files to Done and return only unique files.
    Also returns mapping: file_name -> signature for later success recording.
    """
    unique_files: List[Path] = []
    signature_map: Dict[str, str] = {}

    for file_path in files:
        signature = _approval_signature(file_path)
        if signature in seen:
            archived = _move_to_done(file_path, prefix="DUPLICATE")
            duplicate_info = {
                "status": "skipped_duplicate",
                "processor": processor,
                "file": file_path.name,
                "original_file": seen[signature].get("file"),
                "archived_as": archived.name,
            }
            summary["duplicates"].append(duplicate_info)
            continue

        unique_files.append(file_path)
        signature_map[file_path.name] = signature

    return unique_files, signature_map


def _finalize_processed_files(
    original_files: List[Path],
    signature_map: Dict[str, str],
    seen: Dict[str, Dict],
    processor: str,
) -> None:
    """
    Mark approval signatures as processed if their original approved file
    is no longer present after processing.
    """
    for file_path in original_files:
        if not file_path.exists():
            signature = signature_map.get(file_path.name)
            if signature:
                _record_processed_signature(
                    seen=seen,
                    signature=signature,
                    file_name=file_path.name,
                    processor=processor,
                )


def log_action(action_type: str, details: Dict) -> None:
    log_file = _daily_log_file()
    try:
        if log_file.exists():
            with open(log_file, "r") as f:
                try:
                    logs = json.load(f)
                    if not isinstance(logs, list):
                        logs = []
                except json.JSONDecodeError:
                    # Recover from malformed/partial log files without crashing workflow.
                    logs = []
        else:
            logs = []

        logs.append(
            {
                "timestamp": datetime.now().isoformat(),
                "action_type": action_type,
                "component": "main_orchestrator",
                **details,
            }
        )

        with open(log_file, "w") as f:
            json.dump(logs, f, indent=2)
    except PermissionError:
        pass


def count_md(path: Path) -> int:
    return len(list(path.glob("*.md"))) if path.exists() else 0


def get_status() -> Dict[str, int]:
    return {
        "inbox": count_md(INBOX),
        "needs_action": count_md(NEEDS_ACTION),
        "pending_approval": count_md(PENDING_APPROVAL),
        "approved": count_md(APPROVED),
        "rejected": count_md(REJECTED),
        "done": count_md(DONE),
    }


def _move_to_done(file_path: Path, prefix: Optional[str] = None) -> Path:
    name = f"{prefix}_{file_path.name}" if prefix else file_path.name
    target = DONE / name
    if target.exists():
        target = DONE / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{name}"
    file_path.rename(target)
    return target


def _parse_frontmatter(text: str) -> Dict[str, str]:
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


def _parse_odoo_invoice_lines(text: str) -> List[Dict]:
    lines = text.splitlines()
    invoice_lines: List[Dict] = []
    reading_table = False

    for line in lines:
        if line.strip().startswith("### Invoice Lines"):
            reading_table = True
            continue
        if reading_table and line.strip().startswith("### "):
            break
        if not reading_table or not line.strip().startswith("|"):
            continue
        if "Product ID" in line or "----" in line:
            continue

        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) < 3:
            continue

        product_id = _safe_int(parts[0], default=0)
        quantity = _safe_float(parts[1], default=1.0)
        price_unit = _safe_float(parts[2], default=0.0)

        if product_id > 0:
            invoice_lines.append(
                {
                    "product_id": product_id,
                    "quantity": quantity,
                    "price_unit": price_unit,
                }
            )

    return invoice_lines


def process_odoo_approved(seen: Dict[str, Dict]) -> List[Dict]:
    results: List[Dict] = []
    agent_role = os.getenv("AGENT_ROLE", "local").strip().lower()

    try:
        from mcp_servers.odoo_server import OdooMCPServer
    except Exception as e:
        return [{"status": "error", "processor": "odoo", "message": str(e)}]

    server = OdooMCPServer()

    if agent_role == "cloud":
        return [
            {
                "status": "skipped",
                "processor": "odoo",
                "message": "Cloud role does not execute approved Odoo financial actions.",
            }
        ]

    for file_path in APPROVED.glob("ODOO_INVOICE_*.md"):
        signature = _approval_signature(file_path)
        if signature in seen:
            archived = _move_to_done(file_path, prefix="DUPLICATE")
            results.append(
                {
                    "status": "skipped_duplicate",
                    "processor": "odoo_invoice",
                    "file": file_path.name,
                    "original_file": seen[signature].get("file"),
                    "archived_as": archived.name,
                }
            )
            continue

        text = file_path.read_text()
        meta = _parse_frontmatter(text)
        partner_id = _safe_int(meta.get("partner_id", "0"), default=0)
        invoice_lines = _parse_odoo_invoice_lines(text)

        if partner_id <= 0 or not invoice_lines:
            results.append(
                {
                    "status": "error",
                    "processor": "odoo_invoice",
                    "file": file_path.name,
                    "message": "invalid partner_id or invoice lines",
                }
            )
            continue

        result = server.create_invoice(partner_id, invoice_lines, require_approval=False)
        results.append({"processor": "odoo_invoice", "file": file_path.name, "result": result})

        if result.get("status") == "success":
            _move_to_done(file_path)
            _record_processed_signature(
                seen=seen,
                signature=signature,
                file_name=file_path.name,
                processor="odoo_invoice",
                result_ref=result.get("invoice_id"),
            )

    for file_path in APPROVED.glob("ODOO_POST_INVOICE_*.md"):
        signature = _approval_signature(file_path)
        if signature in seen:
            archived = _move_to_done(file_path, prefix="DUPLICATE")
            results.append(
                {
                    "status": "skipped_duplicate",
                    "processor": "odoo_post_invoice",
                    "file": file_path.name,
                    "original_file": seen[signature].get("file"),
                    "archived_as": archived.name,
                }
            )
            continue

        text = file_path.read_text()
        meta = _parse_frontmatter(text)
        invoice_id = _safe_int(meta.get("invoice_id", "0"), default=0)

        if invoice_id <= 0:
            results.append(
                {
                    "status": "error",
                    "processor": "odoo_post_invoice",
                    "file": file_path.name,
                    "message": "invalid invoice_id",
                }
            )
            continue

        result = server.post_invoice(invoice_id=invoice_id, require_approval=False)
        results.append({"processor": "odoo_post_invoice", "file": file_path.name, "result": result})

        if result.get("status") == "success":
            _move_to_done(file_path)
            _record_processed_signature(
                seen=seen,
                signature=signature,
                file_name=file_path.name,
                processor="odoo_post_invoice",
                result_ref=result.get("invoice_id"),
            )

    for file_path in APPROVED.glob("ODOO_PAYMENT_*.md"):
        signature = _approval_signature(file_path)
        if signature in seen:
            archived = _move_to_done(file_path, prefix="DUPLICATE")
            results.append(
                {
                    "status": "skipped_duplicate",
                    "processor": "odoo_payment",
                    "file": file_path.name,
                    "original_file": seen[signature].get("file"),
                    "archived_as": archived.name,
                }
            )
            continue

        text = file_path.read_text()
        meta = _parse_frontmatter(text)
        partner_id = _safe_int(meta.get("partner_id", "0"), default=0)
        amount = _safe_float(meta.get("amount", "0"), default=0.0)
        payment_type = meta.get("payment_type", "inbound")

        if partner_id <= 0 or amount <= 0:
            results.append(
                {
                    "status": "error",
                    "processor": "odoo_payment",
                    "file": file_path.name,
                    "message": "invalid partner_id or amount",
                }
            )
            continue

        result = server.record_payment(
            partner_id=partner_id,
            amount=amount,
            payment_type=payment_type,
            require_approval=False,
        )
        results.append({"processor": "odoo_payment", "file": file_path.name, "result": result})

        if result.get("status") == "success":
            _move_to_done(file_path)
            _record_processed_signature(
                seen=seen,
                signature=signature,
                file_name=file_path.name,
                processor="odoo_payment",
                result_ref=result.get("payment_id"),
            )

    return results


def process_approved() -> Dict:
    summary: Dict[str, List] = {
        "email": [],
        "linkedin": [],
        "twitter": [],
        "facebook": [],
        "instagram": [],
        "odoo": [],
        "duplicates": [],
    }
    registry = _load_processed_approvals()
    seen: Dict[str, Dict] = registry.get("signatures", {})

    email_files = list(APPROVED.glob("EMAIL_SEND_*.md"))
    linkedin_files = list(APPROVED.glob("LINKEDIN_POST_*.md"))
    twitter_files = list(APPROVED.glob("TWITTER_POST_APPROVAL_*.md"))
    facebook_files = list(APPROVED.glob("FACEBOOK_POST_*.md")) + list(
        APPROVED.glob("*FACEBOOK_POST_APPROVAL_*.md")
    )
    instagram_files = list(APPROVED.glob("INSTAGRAM_POST_*.md")) + list(
        APPROVED.glob("*INSTAGRAM_POST_APPROVAL_*.md")
    )
    odoo_files = list(APPROVED.glob("ODOO_INVOICE_*.md")) + list(APPROVED.glob("ODOO_PAYMENT_*.md"))
    odoo_files += list(APPROVED.glob("ODOO_POST_INVOICE_*.md"))

    email_files, email_sig_map = _filter_duplicate_approved_files(
        email_files, seen, "email", summary
    )
    linkedin_files, linkedin_sig_map = _filter_duplicate_approved_files(
        linkedin_files, seen, "linkedin", summary
    )
    twitter_files, twitter_sig_map = _filter_duplicate_approved_files(
        twitter_files, seen, "twitter", summary
    )
    facebook_files, facebook_sig_map = _filter_duplicate_approved_files(
        facebook_files, seen, "facebook", summary
    )
    instagram_files, instagram_sig_map = _filter_duplicate_approved_files(
        instagram_files, seen, "instagram", summary
    )

    if email_files:
        try:
            from mcp_servers.email_server import EmailMCPServer
            summary["email"] = EmailMCPServer().process_approved_emails()
            _finalize_processed_files(email_files, email_sig_map, seen, "email")
        except Exception as e:
            summary["email"] = [{"status": "error", "message": str(e)}]

    if linkedin_files:
        try:
            from watchers.linkedin_poster import LinkedInPoster
            result = LinkedInPoster().process_approved_posts()
            summary["linkedin"] = result if isinstance(result, list) else []
            _finalize_processed_files(linkedin_files, linkedin_sig_map, seen, "linkedin")
        except Exception as e:
            summary["linkedin"] = [{"status": "error", "message": str(e)}]

    if twitter_files:
        try:
            from watchers.twitter_poster import TwitterPoster
            TwitterPoster(str(VAULT_PATH)).process_approved_posts()
            summary["twitter"] = [{"status": "processed"}]
            _finalize_processed_files(twitter_files, twitter_sig_map, seen, "twitter")
        except Exception as e:
            summary["twitter"] = [{"status": "error", "message": str(e)}]

    if facebook_files:
        try:
            from watchers.facebook_poster import FacebookPoster
            summary["facebook"] = FacebookPoster(str(VAULT_PATH)).process_approved_posts()
            _finalize_processed_files(facebook_files, facebook_sig_map, seen, "facebook")
        except Exception as e:
            summary["facebook"] = [{"status": "error", "message": str(e)}]

    if instagram_files:
        try:
            from watchers.instagram_poster import InstagramPoster
            summary["instagram"] = InstagramPoster(str(VAULT_PATH)).process_approved_posts()
            _finalize_processed_files(instagram_files, instagram_sig_map, seen, "instagram")
        except Exception as e:
            summary["instagram"] = [{"status": "error", "message": str(e)}]

    if odoo_files:
        summary["odoo"] = process_odoo_approved(seen)
        for item in summary["odoo"]:
            if item.get("status") == "skipped_duplicate":
                summary["duplicates"].append(item)

    # Twitter poster marks approved files as COMPLETED_* in /Approved. Move those to /Done.
    for completed in APPROVED.glob("COMPLETED_TWITTER_POST_APPROVAL_*.md"):
        _move_to_done(completed)

    registry["signatures"] = seen
    _save_processed_approvals(registry)
    log_action("approved_processed", {"summary": summary})
    return summary


def process_rejected() -> Dict:
    moved = []
    for file_path in REJECTED.glob("*.md"):
        target = _move_to_done(file_path, prefix="REJECTED")
        moved.append({"from": file_path.name, "to": target.name})

    result = {"moved_count": len(moved), "files": moved}
    log_action("rejected_processed", result)
    return result


def print_status() -> None:
    status = get_status()
    print("AI Employee Status")
    print("==================")
    for key, value in status.items():
        print(f"{key}: {value}")


def main() -> None:
    ensure_vault_dirs()

    parser = argparse.ArgumentParser(description="AI Employee Orchestrator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Show queue status")
    subparsers.add_parser("process-approved", help="Process all approved actions")
    subparsers.add_parser("process-rejected", help="Archive rejected items to Done")
    subparsers.add_parser("process-all", help="Process approved and rejected queues")

    run_parser = subparsers.add_parser("run", help="Continuously process queues")
    run_parser.add_argument("--interval", type=int, default=30, help="Polling interval in seconds")

    args = parser.parse_args()

    if args.command == "status":
        print_status()
        return

    if args.command == "process-approved":
        print(json.dumps(process_approved(), indent=2))
        return

    if args.command == "process-rejected":
        print(json.dumps(process_rejected(), indent=2))
        return

    if args.command == "process-all":
        output = {"approved": process_approved(), "rejected": process_rejected()}
        print(json.dumps(output, indent=2))
        return

    if args.command == "run":
        print(f"Starting orchestrator loop (interval={args.interval}s)")
        while True:
            try:
                process_approved()
                process_rejected()
                time.sleep(args.interval)
            except KeyboardInterrupt:
                print("Stopped by user")
                break
            except Exception as e:
                log_action("orchestrator_error", {"error": str(e)})
                print(f"Loop error: {e}")
                time.sleep(args.interval)


if __name__ == "__main__":
    main()
