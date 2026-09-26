#!/usr/bin/env python3
"""
Convert Omi action items JSON export into an executive task digest and audit report.

Usage:
    python action_items_to_digest.py action_items.json -o task_digest.md
    omi --json action-item list --limit 500 | python action_items_to_digest.py - -o task_digest.md

Categorizes tasks into Pending (with due date tracking) and Completed sections,
computes completion velocity metrics, and outputs clean Markdown checklists.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


def parse_action_items_payload(data: Any) -> List[Dict[str, Any]]:
    """Extract list of action items from bare array or envelope dict."""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("action_items", "items", "data", "results"):
            candidate = data.get(key)
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
    return []


def build_task_digest(
    items: List[Dict[str, Any]],
    title: str = "Omi Action Items Executive Digest",
    reference_dt: Optional[datetime] = None,
) -> str:
    """Build structured Markdown checklist report from action items."""
    total_count = len(items)
    if total_count == 0:
        return f"# {title}\n\n*No action items found in export.*\n"

    now_dt = reference_dt or datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()[:10]

    completed_items: List[Dict[str, Any]] = []
    pending_dated: List[Dict[str, Any]] = []
    pending_undated: List[Dict[str, Any]] = []

    for item in items:
        if item.get("completed", False):
            completed_items.append(item)
        else:
            if item.get("due_at"):
                pending_dated.append(item)
            else:
                pending_undated.append(item)

    # Sort dated pending items by due date ascending
    pending_dated.sort(key=lambda x: str(x.get("due_at", "")))

    comp_count = len(completed_items)
    pending_count = len(pending_dated) + len(pending_undated)
    rate_pct = (comp_count / total_count * 100.0) if total_count > 0 else 0.0

    lines: List[str] = [
        f"# {title}",
        "",
        "## Executive Summary",
        "",
        "| Metric | Value |",
        "| :--- | :--- |",
        f"| **Total Action Items** | {total_count} |",
        f"| **Completed Tasks** | {comp_count} ({rate_pct:.1f}%) |",
        f"| **Pending Tasks** | {pending_count} |",
        f"| **Scheduled Deadlines** | {len(pending_dated)} |",
        "",
        "## Pending Tasks",
        "",
    ]

    if pending_dated:
        lines.append("### Scheduled")
        lines.append("")
        for item in pending_dated:
            desc = str(item.get("description", "")).strip()
            due = str(item.get("due_at", "")).strip()[:10]
            tag = " *(OVERDUE)*" if due < now_iso else ""
            lines.append(f"- [ ] **[Due: {due}]** {desc}{tag}")
        lines.append("")

    if pending_undated:
        lines.append("### Unscheduled (No Deadline)")
        lines.append("")
        for item in pending_undated:
            desc = str(item.get("description", "")).strip()
            lines.append(f"- [ ] {desc}")
        lines.append("")

    if not pending_dated and not pending_undated:
        lines.append("*All tasks completed!*\n")

    if completed_items:
        lines.append(f"## Completed Tasks ({comp_count})")
        lines.append("")
        for item in completed_items:
            desc = str(item.get("description", "")).strip()
            comp_at = str(item.get("completed_at", "") or item.get("updated_at", "")).strip()
            date_tag = f" *(Completed: {comp_at[:10]})*" if comp_at else ""
            lines.append(f"- [x] {desc}{date_tag}")
        lines.append("")

    return "\n".join(lines)


def convert_action_items_to_digest(
    raw_json_str: str,
    output_path: Optional[Path] = None,
    title: str = "Omi Action Items Executive Digest",
    reference_dt: Optional[datetime] = None,
) -> str:
    """Convert raw action items JSON string to Markdown digest with atomic write safety."""
    if output_path is not None:
        parts = output_path.parts
        if ".." in parts:
            raise ValueError(f"Output path cannot contain directory traversal '..': {output_path}")

    try:
        data = json.loads(raw_json_str)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON payload: {exc}") from exc

    items = parse_action_items_payload(data)
    md_content = build_task_digest(items, title, reference_dt)

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        partial_path = output_path.with_suffix(".md.partial")
        try:
            with open(partial_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(md_content)
            os.replace(partial_path, output_path)
        except Exception:
            if partial_path.exists():
                partial_path.unlink()
            raise

    return md_content


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Convert Omi action items JSON to Markdown task digest.")
    parser.add_argument("input", help="Path to action items JSON export, or '-' to read from stdin.")
    parser.add_argument("-o", "--output", help="Path for generated Markdown file. Defaults to stdout.")
    parser.add_argument("--title", default="Omi Action Items Executive Digest", help="Report header title.")

    args = parser.parse_args(argv)

    try:
        if args.input == "-":
            raw_data = sys.stdin.read()
        else:
            in_path = Path(args.input)
            if not in_path.is_file():
                sys.stderr.write(f"Error: Input file not found: {in_path}\n")
                return 1
            raw_data = in_path.read_text(encoding="utf-8")

        out_path = Path(args.output) if args.output else None
        md_result = convert_action_items_to_digest(raw_data, out_path, title=args.title)

        if out_path is None:
            sys.stdout.write(md_result)
        else:
            sys.stderr.write(f"Successfully generated action items digest to {out_path}\n")

        return 0
    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
