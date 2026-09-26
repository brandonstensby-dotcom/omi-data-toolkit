#!/usr/bin/env python3
"""
Convert Omi goals JSON export into standard todo.txt format.

Usage:
    python goals_to_todotxt.py goals.json -o todo.txt
    omi --json goal list --limit 100 | python goals_to_todotxt.py - -o todo.txt

Formats goals into compliant todo.txt lines compatible with mobile and desktop
todo.txt clients, Markor, Obsidian plugins, and CLI tools.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


def compute_progress_pct(current: Any, target: Any, goal_type: str) -> Optional[float]:
    """Safely calculate progress percentage."""
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

    return round((curr_f / targ_f) * 100.0, 1)


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


def sanitize_text(text: str) -> str:
    """Strip newlines and carriage returns to ensure 1-line-per-task in todo.txt."""
    clean = re.sub(r"[\r\n]+", " ", text).strip()
    return clean


def format_goal_todotxt_line(goal: Dict[str, Any]) -> str:
    """Format single goal into a todo.txt compliant string."""
    title = sanitize_text(str(goal.get("title", "") or "Untitled Goal"))
    goal_id = str(goal.get("id", "")).strip()
    goal_type = str(goal.get("goal_type", "qualitative")).strip()
    curr = goal.get("current_value")
    targ = goal.get("target_value")
    pct = compute_progress_pct(curr, targ, goal_type)
    is_active = bool(goal.get("is_active", True))
    created_at = str(goal.get("created_at", "")).strip()[:10]
    updated_at = str(goal.get("updated_at", "")).strip()[:10]

    is_completed = (pct is not None and pct >= 100.0) or (not is_active and goal.get("completed", False))

    parts: List[str] = []

    if is_completed:
        comp_date = updated_at or created_at
        if comp_date:
            parts.append(f"x {comp_date}")
        else:
            parts.append("x")
    else:
        # Assign high priority (A) to active goals, (B) to inactive
        prio = "(A)" if is_active else "(C)"
        parts.append(prio)

    if created_at and not is_completed:
        parts.append(created_at)

    parts.append(title)
    parts.append("+OmiGoal")
    parts.append("@milestone")

    if goal_id:
        parts.append(f"id:{goal_id}")
    if pct is not None:
        parts.append(f"progress:{pct:.0f}%")
    if not is_active and not is_completed:
        parts.append("status:paused")

    return " ".join(parts)


def convert_goals_to_todotxt(raw_json_str: str, output_path: Optional[Path] = None) -> str:
    """Convert raw goals JSON string to todo.txt text with atomic write safety."""
    if output_path is not None:
        parts = output_path.parts
        if ".." in parts:
            raise ValueError(f"Output path cannot contain directory traversal '..': {output_path}")

    try:
        data = json.loads(raw_json_str)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON payload: {exc}") from exc

    goals = parse_goals_payload(data)
    lines = [format_goal_todotxt_line(g) for g in goals]
    todotxt_content = "\n".join(lines) + ("\n" if lines else "")

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        partial_path = output_path.with_suffix(".txt.partial")
        try:
            with open(partial_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(todotxt_content)
            os.replace(partial_path, output_path)
        except Exception:
            if partial_path.exists():
                partial_path.unlink()
            raise

    return todotxt_content


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Convert Omi goals JSON to todo.txt format.")
    parser.add_argument("input", help="Path to goals JSON export, or '-' to read from stdin.")
    parser.add_argument("-o", "--output", help="Path for generated todo.txt file. Defaults to stdout.")

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
        txt_result = convert_goals_to_todotxt(raw_data, out_path)

        if out_path is None:
            sys.stdout.write(txt_result)
        else:
            sys.stderr.write(f"Successfully converted goals to {out_path}\n")

        return 0
    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
