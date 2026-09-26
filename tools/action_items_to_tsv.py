#!/usr/bin/env python3
"""
Convert Omi action items JSON export to a clean TSV (Tab-Separated Values) format.

Usage:
    python action_items_to_tsv.py action_items.json -o action_items.tsv
    omi --json action-item list --limit 500 | python action_items_to_tsv.py - -o action_items.tsv

Normalizes action items into a tab-delimited stream with single-line guarantee
for fast terminal filtering with awk, cut, and grep.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

COLUMNS: Sequence[str] = [
    "id",
    "completed",
    "due_at",
    "completed_at",
    "created_at",
    "conversation_id",
    "description",
]


def escape_tsv_field(val: Any) -> str:
    """Sanitize and escape internal newlines and tabs to preserve 1-line-per-record TSV."""
    if val is None:
        return ""
    text = str(val).strip()
    return text.replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n").replace("\t", " ")


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


def format_action_item_tsv_row(item: Dict[str, Any]) -> Dict[str, str]:
    """Format and normalize an action-item record for TSV output."""
    item_id = str(item.get("id", "")).strip()
    is_completed = "True" if item.get("completed", False) else "False"
    due_at = str(item.get("due_at", "") or "").strip()
    completed_at = str(item.get("completed_at", "") or "").strip()
    created_at = str(item.get("created_at", "") or "").strip()
    convo_id = str(item.get("conversation_id", "") or "").strip()
    description = escape_tsv_field(item.get("description", "") or "")

    return {
        "id": item_id,
        "completed": is_completed,
        "due_at": due_at,
        "completed_at": completed_at,
        "created_at": created_at,
        "conversation_id": convo_id,
        "description": description,
    }


def convert_action_items_to_tsv(raw_json_str: str, output_path: Optional[Path] = None) -> str:
    """Convert raw action items JSON string to TSV text with atomic write safety."""
    if output_path is not None:
        parts = output_path.parts
        if ".." in parts:
            raise ValueError(f"Output path cannot contain directory traversal '..': {output_path}")

    try:
        data = json.loads(raw_json_str)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON payload: {exc}") from exc

    items = parse_action_items_payload(data)
    rows = [format_action_item_tsv_row(i) for i in items]

    import io
    output_stream = io.StringIO()
    writer = csv.DictWriter(output_stream, fieldnames=COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    tsv_content = output_stream.getvalue()

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        partial_path = output_path.with_suffix(".tsv.partial")
        try:
            with open(partial_path, "w", encoding="utf-8", newline="") as f:
                f.write(tsv_content)
            os.replace(partial_path, output_path)
        except Exception:
            if partial_path.exists():
                partial_path.unlink()
            raise

    return tsv_content


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Convert Omi action items JSON to TSV.")
    parser.add_argument("input", help="Path to action items JSON export, or '-' to read from stdin.")
    parser.add_argument("-o", "--output", help="Path for generated TSV file. Defaults to stdout.")

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
        tsv_result = convert_action_items_to_tsv(raw_data, out_path)

        if out_path is None:
            sys.stdout.write(tsv_result)
        else:
            sys.stderr.write(f"Successfully converted action items to {out_path}\n")

        return 0
    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
