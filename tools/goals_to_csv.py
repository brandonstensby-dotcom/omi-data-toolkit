#!/usr/bin/env python3
"""
Convert Omi goals JSON export to a clean CSV spreadsheet.

Usage:
    python goals_to_csv.py goals.json -o goals.csv
    omi --json goal list --limit 100 | python goals_to_csv.py - -o goals.csv

Reads a saved goals export, computes progress percentages, normalizes date
fields, and outputs a formatted CSV compatible with Excel, Google Sheets,
and data analysis pipelines. Stdlib-only, defensive, and atomic writes.
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


def compute_progress_pct(current: Optional[float], target: Optional[float], goal_type: Optional[str]) -> str:
    """Calculate progress percentage safely handling division by zero and nulls."""
    if goal_type == "boolean":
        if current is not None:
            return "100.0%" if current >= 1.0 else "0.0%"
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
    """Extract list of goals from raw JSON or wrapped envelope dictionary."""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("goals", "items", "data", "results"):
            candidate = data.get(key)
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
    return []


def format_row(goal: Dict[str, Any]) -> Dict[str, Any]:
    """Format and normalize a goal record into CSV column values."""
    goal_id = str(goal.get("id", "")).strip()
    title = str(goal.get("title", "")).strip()
    goal_type = str(goal.get("goal_type", "qualitative")).strip()
    current = goal.get("current_value")
    target = goal.get("target_value")
    unit = str(goal.get("unit", "") or "").strip()
    is_active = "True" if goal.get("is_active", True) else "False"
    created_at = str(goal.get("created_at", "") or "").strip()
    updated_at = str(goal.get("updated_at", "") or "").strip()

    progress = compute_progress_pct(current, target, goal_type)

    return {
        "id": goal_id,
        "title": title,
        "goal_type": goal_type,
        "current_value": str(current) if current is not None else "",
        "target_value": str(target) if target is not None else "",
        "progress_pct": progress,
        "unit": unit,
        "is_active": is_active,
        "created_at": created_at,
        "updated_at": updated_at,
    }


def convert_goals_to_csv(raw_json_str: str, output_path: Optional[Path] = None) -> str:
    """Convert raw goals JSON string to CSV text, optionally writing to disk."""
    if output_path is not None:
        parts = output_path.parts
        if ".." in parts:
            raise ValueError(f"Output path cannot contain directory traversal '..': {output_path}")

    try:
        data = json.loads(raw_json_str)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON payload: {exc}") from exc

    goals = parse_goals_payload(data)
    rows = [format_row(g) for g in goals]

    # Render CSV in-memory
    import io
    output_stream = io.StringIO()
    writer = csv.DictWriter(output_stream, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    csv_content = output_stream.getvalue()

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        partial_path = output_path.with_suffix(".csv.partial")
        try:
            with open(partial_path, "w", encoding="utf-8", newline="") as f:
                f.write(csv_content)
            os.replace(partial_path, output_path)
        except Exception:
            if partial_path.exists():
                partial_path.unlink()
            raise

    return csv_content


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Convert Omi goals JSON to CSV.")
    parser.add_argument("input", help="Path to goals JSON export, or '-' to read from stdin.")
    parser.add_argument("-o", "--output", help="Path for generated CSV file. Defaults to stdout.")

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
        csv_result = convert_goals_to_csv(raw_data, out_path)

        if out_path is None:
            sys.stdout.write(csv_result)
        else:
            sys.stderr.write(f"Successfully converted goals to {out_path}\n")

        return 0
    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
