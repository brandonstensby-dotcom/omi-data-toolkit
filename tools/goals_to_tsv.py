#!/usr/bin/env python3
"""
Convert Omi goals JSON export to a clean TSV (Tab-Separated Values) format.

Usage:
    python goals_to_tsv.py goals.json -o goals.tsv
    omi --json goal list --limit 100 | python goals_to_tsv.py - -o goals.tsv

Extracts goals, target values, units, and progress percentages into single-line
TSV records for rapid terminal tracking.
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
    "title",
    "goal_type",
    "current_value",
    "target_value",
    "progress_pct",
    "unit",
    "is_active",
    "created_at",
    "updated_at",
]


def escape_tsv_field(val: Any) -> str:
    """Sanitize and escape internal newlines and tabs to preserve 1-line-per-record TSV."""
    if val is None:
        return ""
    text = str(val).strip()
    return text.replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n").replace("\t", " ")


def compute_progress_pct(current: Any, target: Any, goal_type: str) -> str:
    """Safely calculate progress percentage without division-by-zero risks."""
    if goal_type == "boolean":
        if current is not None:
            try:
                curr_f = float(current)
                return "100.0%" if curr_f >= 1.0 else "0.0%"
            except (ValueError, TypeError):
                return "N/A"
        return "N/A"

    if current is None or target is None:
        return "N/A"

    try:
        curr_f = float(current)
        targ_f = float(target)
    except (ValueError, TypeError):
        return "N/A"

    if targ_f == 0.0:
        return "100.0%" if curr_f >= 0.0 else "0.0%"

    pct = (curr_f / targ_f) * 100.0
    return f"{pct:.1f}%"


def parse_goals_payload(data: Any) -> List[Dict[str, Any]]:
    """Extract list of goals from bare array or envelope dict."""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("goals", "items", "data", "results"):
            candidate = data.get(key)
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
    return []


def format_goal_tsv_row(goal: Dict[str, Any]) -> Dict[str, str]:
    """Format and normalize a goal record for TSV output."""
    current = goal.get("current_value")
    target = goal.get("target_value")
    goal_type = str(goal.get("goal_type", "qualitative")).strip()

    return {
        "id": str(goal.get("id", "")).strip(),
        "title": escape_tsv_field(goal.get("title", "")),
        "goal_type": goal_type,
        "current_value": str(current) if current is not None else "",
        "target_value": str(target) if target is not None else "",
        "progress_pct": compute_progress_pct(current, target, goal_type),
        "unit": escape_tsv_field(goal.get("unit", "") or ""),
        "is_active": "True" if goal.get("is_active", True) else "False",
        "created_at": str(goal.get("created_at", "") or "").strip(),
        "updated_at": str(goal.get("updated_at", "") or "").strip(),
    }


def convert_goals_to_tsv(raw_json_str: str, output_path: Optional[Path] = None) -> str:
    """Convert raw goals JSON string to TSV text with atomic write safety."""
    if output_path is not None:
        parts = output_path.parts
        if ".." in parts:
            raise ValueError(f"Output path cannot contain directory traversal '..': {output_path}")

    try:
        data = json.loads(raw_json_str)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON payload: {exc}") from exc

    goals = parse_goals_payload(data)
    rows = [format_goal_tsv_row(g) for g in goals]

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
    parser = argparse.ArgumentParser(description="Convert Omi goals JSON to TSV.")
    parser.add_argument("input", help="Path to goals JSON export, or '-' to read from stdin.")
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
        tsv_result = convert_goals_to_tsv(raw_data, out_path)

        if out_path is None:
            sys.stdout.write(tsv_result)
        else:
            sys.stderr.write(f"Successfully converted goals to {out_path}\n")

        return 0
    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
