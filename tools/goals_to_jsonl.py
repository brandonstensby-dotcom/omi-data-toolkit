#!/usr/bin/env python3
"""
Convert Omi goals JSON export to JSON Lines (JSONL) format.

Usage:
    python goals_to_jsonl.py goals.json -o goals.jsonl
    omi --json goal list --limit 100 | python goals_to_jsonl.py - -o goals.jsonl

Transforms raw goals into a stream of line-delimited JSON objects with enriched
progress calculation, suitable for log aggregators, data lakes, and vector pipelines.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


def compute_progress_pct(current: Any, target: Any, goal_type: str) -> Optional[float]:
    """Safely calculate numerical progress percentage (0.0 to 100.0+)."""
    if goal_type == "boolean":
        if current is not None:
            try:
                curr_f = float(current)
                return 100.0 if curr_f >= 1.0 else 0.0
            except (ValueError, TypeError):
                return None
        return None

    if current is None or target is None:
        return None

    try:
        curr_f = float(current)
        targ_f = float(target)
    except (ValueError, TypeError):
        return None

    if targ_f == 0.0:
        return 100.0 if curr_f >= 0.0 else 0.0

    return round((curr_f / targ_f) * 100.0, 2)


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


def format_goal_jsonl_item(goal: Dict[str, Any]) -> Dict[str, Any]:
    """Format goal record with normalized progress calculation."""
    current = goal.get("current_value")
    target = goal.get("target_value")
    goal_type = str(goal.get("goal_type", "qualitative")).strip()

    progress = compute_progress_pct(current, target, goal_type)

    out: Dict[str, Any] = {
        "id": str(goal.get("id", "")).strip(),
        "title": str(goal.get("title", "")).strip(),
        "goal_type": goal_type,
        "current_value": current,
        "target_value": target,
        "progress_pct": progress,
        "unit": goal.get("unit"),
        "is_active": bool(goal.get("is_active", True)),
        "created_at": goal.get("created_at"),
        "updated_at": goal.get("updated_at"),
    }
    return out


def convert_goals_to_jsonl(raw_json_str: str, output_path: Optional[Path] = None) -> str:
    """Convert raw goals JSON string to JSONL text with atomic write safety."""
    if output_path is not None:
        parts = output_path.parts
        if ".." in parts:
            raise ValueError(f"Output path cannot contain directory traversal '..': {output_path}")

    try:
        data = json.loads(raw_json_str)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON payload: {exc}") from exc

    goals = parse_goals_payload(data)
    lines = [json.dumps(format_goal_jsonl_item(g), ensure_ascii=False) for g in goals]
    jsonl_content = "\n".join(lines) + ("\n" if lines else "")

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        partial_path = output_path.with_suffix(".jsonl.partial")
        try:
            with open(partial_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(jsonl_content)
            os.replace(partial_path, output_path)
        except Exception:
            if partial_path.exists():
                partial_path.unlink()
            raise

    return jsonl_content


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Convert Omi goals JSON to JSONL.")
    parser.add_argument("input", help="Path to goals JSON export, or '-' to read from stdin.")
    parser.add_argument("-o", "--output", help="Path for generated JSONL file. Defaults to stdout.")

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
        jsonl_result = convert_goals_to_jsonl(raw_data, out_path)

        if out_path is None:
            sys.stdout.write(jsonl_result)
        else:
            sys.stderr.write(f"Successfully converted goals to {out_path}\n")

        return 0
    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
