#!/usr/bin/env python3
"""
Cloud Odoo MCP Service (Platinum)

Purpose:
- Keep Odoo JSON-RPC connectivity monitored on cloud.
- Process cloud-side draft invoice tasks only.

Task input pattern (in /Needs_Action/cloud):
- ODOO_DRAFT_INVOICE_*.md
"""

from __future__ import annotations

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def resolve_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


PROJECT_ROOT = resolve_project_root()
VAULT_PATH = Path(os.getenv("VAULT_PATH", str(PROJECT_ROOT / "AI_Employee_Vault")))
if VAULT_PATH.is_symlink():
    VAULT_PATH = VAULT_PATH.resolve()

NEEDS_ACTION_CLOUD = VAULT_PATH / "Needs_Action" / "cloud"
IN_PROGRESS_CLOUD = VAULT_PATH / "In_Progress" / "cloud"
DONE = VAULT_PATH / "Done"
LOGS = VAULT_PATH / "Logs"
POLL_SECONDS = int(os.getenv("CLOUD_ODOO_POLL_SECONDS", "30"))


def ensure_dirs() -> None:
    for folder in [NEEDS_ACTION_CLOUD, IN_PROGRESS_CLOUD, DONE, LOGS]:
        folder.mkdir(parents=True, exist_ok=True)


def log_line(message: str) -> None:
    log_file = LOGS / f"cloud_odoo_mcp_{datetime.now().strftime('%Y-%m-%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} {message}\n")


def parse_frontmatter(text: str) -> Dict[str, str]:
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return {}

    meta: Dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta


def safe_int(value: str, default: int = 0) -> int:
    try:
        return int(float(value.strip().replace("$", "").replace(",", "")))
    except Exception:
        return default


def safe_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value.strip().replace("$", "").replace(",", ""))
    except Exception:
        return default


def parse_invoice_lines(text: str) -> List[Dict]:
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

        product_id = safe_int(parts[0], default=0)
        quantity = safe_float(parts[1], default=1.0)
        price_unit = safe_float(parts[2], default=0.0)

        if product_id > 0:
            invoice_lines.append(
                {
                    "product_id": product_id,
                    "quantity": quantity,
                    "price_unit": price_unit,
                }
            )
    return invoice_lines


def claim(path: Path) -> Path | None:
    target = IN_PROGRESS_CLOUD / path.name
    try:
        path.rename(target)
        log_line(f"CLAIM {path.name} -> {target.name}")
        return target
    except FileNotFoundError:
        return None
    except OSError as exc:
        log_line(f"CLAIM_FAIL {path.name} error={exc}")
        return None


def process_draft_file(path: Path) -> None:
    from mcp_servers.odoo_server import OdooMCPServer

    text = path.read_text(encoding="utf-8", errors="ignore")
    meta = parse_frontmatter(text)
    partner_id = safe_int(meta.get("partner_id", "0"), default=0)
    lines = parse_invoice_lines(text)

    if partner_id <= 0 or not lines:
        log_line(f"INVALID_DRAFT file={path.name} partner_id={partner_id} lines={len(lines)}")
        target = DONE / f"ODOO_INVALID_{path.name}"
        path.rename(target)
        return

    server = OdooMCPServer()
    # AGENT_ROLE=cloud + CLOUD_DRAFT_ONLY=true should be set in process env.
    result = server.create_invoice(partner_id=partner_id, lines=lines, require_approval=False)
    log_line(f"DRAFT_RESULT file={path.name} result={result}")

    target = DONE / f"ODOO_DRAFT_PROCESSED_{path.name}"
    if target.exists():
        target = DONE / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_ODOO_DRAFT_PROCESSED_{path.name}"
    path.rename(target)


def run() -> None:
    ensure_dirs()
    log_line("START cloud odoo mcp service")

    while True:
        try:
            from mcp_servers.odoo_server import OdooMCPServer

            health = OdooMCPServer().connect()
            log_line(f"HEALTH connect={health}")

            for file_path in sorted(NEEDS_ACTION_CLOUD.glob("ODOO_DRAFT_INVOICE_*.md")):
                claimed = claim(file_path)
                if not claimed:
                    continue
                process_draft_file(claimed)
        except KeyboardInterrupt:
            log_line("STOP keyboard_interrupt")
            break
        except Exception as exc:
            log_line(f"ERROR {exc}")

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    run()

