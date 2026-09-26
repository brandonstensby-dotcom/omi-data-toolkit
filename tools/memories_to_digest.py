#!/usr/bin/env python3
"""
Convert Omi memories JSON export into an executive Markdown knowledge digest.

Usage:
    python memories_to_digest.py memories.json -o digest.md
    omi --json memory list --limit 500 | python memories_to_digest.py - -o digest.md

Groups memories by category, calculates frequency metrics, and renders a structured
Markdown report suitable for personal knowledge bases, Obsidian, or team updates.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


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


def build_markdown_digest(memories: List[Dict[str, Any]], title: str = "Omi Memories Knowledge Digest") -> str:
    """Generate Markdown report from memories."""
    total_count = len(memories)
    if total_count == 0:
        return f"# {title}\n\n*No memories found in export.*\n"

    categories: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for mem in memories:
        cat = str(mem.get("category", "") or mem.get("structured", {}).get("category", "") or "General").strip()
        if not cat:
            cat = "General"
        categories[cat.capitalize()].append(mem)

    lines: List[str] = [
        f"# {title}",
        "",
        f"**Total Memories:** {total_count} | **Categories:** {len(categories)}",
        "",
        "## Category Summary",
        "",
        "| Category | Count | Percentage |",
        "| :--- | :--- | :--- |",
    ]

    sorted_cats = sorted(categories.items(), key=lambda x: len(x[1]), reverse=True)
    for cat_name, cat_items in sorted_cats:
        pct = (len(cat_items) / total_count) * 100.0
        lines.append(f"| {cat_name} | {len(cat_items)} | {pct:.1f}% |")

    lines.append("")
    lines.append("## Knowledge Entries")
    lines.append("")

    for cat_name, cat_items in sorted_cats:
        lines.append(f"### {cat_name} ({len(cat_items)})")
        lines.append("")
        for idx, item in enumerate(cat_items, 1):
            content = str(item.get("content", "") or item.get("structured", {}).get("overview", "")).strip()
            created_at = str(item.get("created_at", "")).strip()
            item_id = str(item.get("id", "")).strip()

            date_str = f" *({created_at[:10]})*" if created_at else ""
            lines.append(f"{idx}. {content}{date_str}")
        lines.append("")

    return "\n".join(lines)


def convert_memories_to_digest(
    raw_json_str: str,
    output_path: Optional[Path] = None,
    title: str = "Omi Memories Knowledge Digest",
) -> str:
    """Convert raw memories JSON string to Markdown digest with atomic write safety."""
    if output_path is not None:
        parts = output_path.parts
        if ".." in parts:
            raise ValueError(f"Output path cannot contain directory traversal '..': {output_path}")

    try:
        data = json.loads(raw_json_str)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON payload: {exc}") from exc

    memories = parse_memories_payload(data)
    md_content = build_markdown_digest(memories, title)

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
    parser = argparse.ArgumentParser(description="Convert Omi memories JSON to Markdown digest.")
    parser.add_argument("input", help="Path to memories JSON export, or '-' to read from stdin.")
    parser.add_argument("-o", "--output", help="Path for generated Markdown file. Defaults to stdout.")
    parser.add_argument("--title", default="Omi Memories Knowledge Digest", help="Report header title.")

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
        md_result = convert_memories_to_digest(raw_data, out_path, title=args.title)

        if out_path is None:
            sys.stdout.write(md_result)
        else:
            sys.stderr.write(f"Successfully generated memories digest to {out_path}\n")

        return 0
    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
