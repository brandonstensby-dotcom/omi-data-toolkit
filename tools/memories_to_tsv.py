#!/usr/bin/env python3
"""
Convert Omi memories JSON export to a clean TSV (Tab-Separated Values) format.

Usage:
    python memories_to_tsv.py memories.json -o memories.tsv
    omi --json memory list --limit 1000 | python memories_to_tsv.py - -o memories.tsv

Normalizes memories into a tab-delimited stream with newline/tab character escaping
to guarantee strict single-line records for fast terminal pipelines (awk, cut, grep).
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
    "category",
    "created_at",
    "updated_at",
    "content",
]


def escape_tsv_field(val: Any) -> str:
    """Sanitize and escape internal newlines and tabs to preserve 1-line-per-record TSV."""
    if val is None:
        return ""
    text = str(val).strip()
    return text.replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n").replace("\t", " ")


def parse_memories_payload(data: Any) -> List[Dict[str, Any]]:
    """Extract list of memory items from bare array or envelope dict."""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("memories", "items", "data", "results"):
            candidate = data.get(key)
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
    return []


def format_memory_row(item: Dict[str, Any]) -> Dict[str, str]:
    """Format and normalize a memory record for TSV output."""
    mem_id = str(item.get("id", "")).strip()
    category = str(item.get("category", "") or item.get("structured", {}).get("category", "") or "").strip()
    created_at = str(item.get("created_at", "") or "").strip()
    updated_at = str(item.get("updated_at", "") or "").strip()
    content = escape_tsv_field(item.get("content", "") or item.get("structured", {}).get("overview", ""))

    return {
        "id": mem_id,
        "category": category,
        "created_at": created_at,
        "updated_at": updated_at,
        "content": content,
    }


def convert_memories_to_tsv(raw_json_str: str, output_path: Optional[Path] = None) -> str:
    """Convert raw memories JSON string to TSV text with atomic write safety."""
    if output_path is not None:
        parts = output_path.parts
        if ".." in parts:
            raise ValueError(f"Output path cannot contain directory traversal '..': {output_path}")

    try:
        data = json.loads(raw_json_str)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON payload: {exc}") from exc

    memories = parse_memories_payload(data)
    rows = [format_memory_row(m) for m in memories]

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
    parser = argparse.ArgumentParser(description="Convert Omi memories JSON to TSV.")
    parser.add_argument("input", help="Path to memories JSON export, or '-' to read from stdin.")
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
        tsv_result = convert_memories_to_tsv(raw_data, out_path)

        if out_path is None:
            sys.stdout.write(tsv_result)
        else:
            sys.stderr.write(f"Successfully converted memories to {out_path}\n")

        return 0
    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
