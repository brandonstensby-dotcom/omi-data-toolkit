#!/usr/bin/env python3
"""
Convert Omi goals JSON export into an executive goal progress report with visual bars.

Usage:
    python goals_to_digest.py goals.json -o goals_digest.md
    omi --json goal list --limit 100 | python goals_to_digest.py - -o goals_digest.md

Generates an executive milestone briefing with visual completion bars, active vs
achieved goal classification, and metric breakdowns.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


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


def render_progress_bar(pct: Optional[float], width: int = 15) -> str:
    """Render a text-based ASCII/Unicode progress bar."""
    if pct is None:
        return f"[{'·' * width}] N/A"

    clamped = max(0.0, min(100.0, pct))
    filled = int(round((clamped / 100.0) * width))
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {pct:.1f}%"


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


def build_goals_digest(goals: List[Dict[str, Any]], title: str = "Omi Goals & Milestones Digest") -> str:
    """Build structured Markdown report from goals."""
    total_count = len(goals)
    if total_count == 0:
        return f"# {title}\n\n*No goals found in export.*\n"

    active_goals: List[Tuple[Dict[str, Any], Optional[float]]] = []
    completed_goals: List[Tuple[Dict[str, Any], Optional[float]]] = []
    paused_goals: List[Tuple[Dict[str, Any], Optional[float]]] = []

    for g in goals:
        curr = g.get("current_value")
        targ = g.get("target_value")
        g_type = str(g.get("goal_type", "qualitative")).strip()
        pct = compute_progress_pct(curr, targ, g_type)
        is_active = bool(g.get("is_active", True))

        if not is_active:
            paused_goals.append((g, pct))
        elif pct is not None and pct >= 100.0:
            completed_goals.append((g, pct))
        else:
            active_goals.append((g, pct))

    # Sort active goals by progress descending
    active_goals.sort(key=lambda x: (x[1] if x[1] is not None else -1.0), reverse=True)

    lines: List[str] = [
        f"# {title}",
        "",
        "## Executive Summary",
        "",
        "| Metric | Count |",
        "| :--- | :--- |",
        f"| **Total Goals** | {total_count} |",
        f"| **In Progress** | {len(active_goals)} |",
        f"| **Achieved / Completed** | {len(completed_goals)} |",
        f"| **Inactive / Paused** | {len(paused_goals)} |",
        "",
    ]

    if active_goals:
        lines.append("## Active Goals in Progress")
        lines.append("")
        for g, pct in active_goals:
            g_title = str(g.get("title", "")).strip()
            curr = g.get("current_value")
            targ = g.get("target_value")
            unit = str(g.get("unit", "") or "").strip()
            unit_str = f" {unit}" if unit else ""

            val_str = f" ({curr} / {targ}{unit_str})" if (curr is not None and targ is not None) else ""
            lines.append(f"### {g_title}{val_str}")
            lines.append(f"`{render_progress_bar(pct)}`")
            lines.append("")

    if completed_goals:
        lines.append("## Achieved Goals (100% Complete)")
        lines.append("")
        for g, pct in completed_goals:
            g_title = str(g.get("title", "")).strip()
            lines.append(f"- [x] **{g_title}** `{render_progress_bar(pct, width=10)}`")
        lines.append("")

    if paused_goals:
        lines.append("## Inactive / Paused Goals")
        lines.append("")
        for g, pct in paused_goals:
            g_title = str(g.get("title", "")).strip()
            lines.append(f"- [ ] *{g_title}* (Paused)")
        lines.append("")

    return "\n".join(lines)


def convert_goals_to_digest(
    raw_json_str: str,
    output_path: Optional[Path] = None,
    title: str = "Omi Goals & Milestones Digest",
) -> str:
    """Convert raw goals JSON string to Markdown digest with atomic write safety."""
    if output_path is not None:
        parts = output_path.parts
        if ".." in parts:
            raise ValueError(f"Output path cannot contain directory traversal '..': {output_path}")

    try:
        data = json.loads(raw_json_str)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON payload: {exc}") from exc

    goals = parse_goals_payload(data)
    md_content = build_goals_digest(goals, title)

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
    parser = argparse.ArgumentParser(description="Convert Omi goals JSON to visual Markdown progress digest.")
    parser.add_argument("input", help="Path to goals JSON export, or '-' to read from stdin.")
    parser.add_argument("-o", "--output", help="Path for generated Markdown file. Defaults to stdout.")
    parser.add_argument("--title", default="Omi Goals & Milestones Digest", help="Report header title.")

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
        md_result = convert_goals_to_digest(raw_data, out_path, title=args.title)

        if out_path is None:
            sys.stdout.write(md_result)
        else:
            sys.stderr.write(f"Successfully generated goals digest to {out_path}\n")

        return 0
    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
