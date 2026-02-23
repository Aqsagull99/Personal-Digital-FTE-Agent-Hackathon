#!/usr/bin/env python3
"""
Cloud Draft Worker (Platinum Tier)

Behavior:
1. Watches AI_Employee_Vault/Needs_Action/*.md (top-level files only).
2. Claims each task by atomic move to /In_Progress/cloud/.
3. Generates a draft-only response/post file in /Needs_Action/cloud/.

This keeps cloud in "draft-only" mode and uses claim-by-move to avoid
double-processing by other agents.
"""

from __future__ import annotations

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict


def resolve_vault() -> Path:
    env_path = os.getenv("VAULT_PATH")
    if env_path:
        p = Path(env_path)
    else:
        p = Path(__file__).resolve().parents[2] / "AI_Employee_Vault"
    if p.is_symlink():
        p = p.resolve()
    return p


VAULT_PATH = resolve_vault()
NEEDS_ACTION = VAULT_PATH / "Needs_Action"
NEEDS_ACTION_CLOUD = NEEDS_ACTION / "cloud"
IN_PROGRESS_CLOUD = VAULT_PATH / "In_Progress" / "cloud"
LOGS_DIR = VAULT_PATH / "Logs"
POLL_SECONDS = int(os.getenv("CLOUD_DRAFT_POLL_SECONDS", "20"))
RUN_ONCE = os.getenv("CLOUD_DRAFT_ONCE", "0") == "1"


def ensure_dirs() -> None:
    for folder in [NEEDS_ACTION, NEEDS_ACTION_CLOUD, IN_PROGRESS_CLOUD, LOGS_DIR]:
        folder.mkdir(parents=True, exist_ok=True)


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


def append_log(msg: str) -> None:
    log_file = LOGS_DIR / f"cloud_draft_worker_{datetime.now().strftime('%Y-%m-%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} {msg}\n")


def build_draft(task_name: str, meta: Dict[str, str], body: str) -> str:
    task_type = (meta.get("type") or "task").lower()
    priority = meta.get("priority", "P3")
    source = meta.get("source", "cloud_worker")

    if "email" in task_type:
        draft_block = (
            "## Draft Reply (Cloud Draft-Only)\n\n"
            "Subject: Re: " + meta.get("subject", "Your request") + "\n\n"
            "Hello,\n\n"
            "Thanks for your message. I reviewed your request and prepared a draft response. "
            "Please confirm any details you want me to include before sending.\n\n"
            "Best regards,\n"
            "AI Assistant (Draft)\n"
        )
    elif any(x in task_type for x in ["twitter", "facebook", "instagram", "linkedin", "social"]):
        draft_block = (
            "## Draft Social Response/Post (Cloud Draft-Only)\n\n"
            "Draft caption/reply:\n"
            "\"Thanks for reaching out. Happy to help. Please share a bit more detail and "
            "we will follow up shortly.\"\n\n"
            "Suggested hashtags: #Support #Business #Update\n"
        )
    else:
        draft_block = (
            "## Draft Action Plan (Cloud Draft-Only)\n\n"
            "1. Confirm scope and expected output\n"
            "2. Validate required data and deadlines\n"
            "3. Prepare final response for Local approval\n"
        )

    return (
        "---\n"
        "type: cloud_draft\n"
        f"source: {source}\n"
        f"priority: {priority}\n"
        f"created: {datetime.now().isoformat()}\n"
        "status: pending\n"
        "agent: cloud\n"
        f"original_task: {task_name}\n"
        "---\n\n"
        "## Context\n\n"
        f"Original task file: `{task_name}`\n\n"
        f"{draft_block}\n"
        "## Original Excerpt\n\n"
        + (body[:1200] if body else "_No body found._")
        + "\n"
    )


def claim_file(path: Path) -> Path | None:
    target = IN_PROGRESS_CLOUD / path.name
    try:
        path.rename(target)  # Atomic claim-by-move on same filesystem.
        append_log(f"CLAIMED {path.name} -> {target}")
        return target
    except FileNotFoundError:
        return None
    except OSError as exc:
        append_log(f"CLAIM_FAILED {path.name} error={exc}")
        return None


def process_one(claimed: Path) -> None:
    text = claimed.read_text(encoding="utf-8", errors="ignore")
    meta = parse_frontmatter(text)

    draft_name = f"DRAFT_{claimed.stem}.md"
    draft_path = NEEDS_ACTION_CLOUD / draft_name
    if draft_path.exists():
        draft_name = f"DRAFT_{claimed.stem}_{datetime.now().strftime('%H%M%S')}.md"
        draft_path = NEEDS_ACTION_CLOUD / draft_name

    draft_text = build_draft(task_name=claimed.name, meta=meta, body=text)
    draft_path.write_text(draft_text, encoding="utf-8")
    append_log(f"DRAFT_CREATED {draft_path.name} from={claimed.name}")


def run_forever() -> None:
    ensure_dirs()
    append_log(
        f"START vault={VAULT_PATH} poll_seconds={POLL_SECONDS} "
        f"needs_action={NEEDS_ACTION}"
    )
    while True:
        candidates = sorted(NEEDS_ACTION.glob("*.md"))
        for file_path in candidates:
            if file_path.name.startswith("DRAFT_"):
                continue
            claimed = claim_file(file_path)
            if not claimed:
                continue
            process_one(claimed)
        if RUN_ONCE:
            append_log("EXIT run-once completed")
            break
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    run_forever()
