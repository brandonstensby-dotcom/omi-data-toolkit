# Generate task audit reports & checklists from action items

Use this recipe to convert Omi action items into an executive task audit report and Markdown checklist, highlighting overdue deadlines, tracking scheduled vs unscheduled items, and calculating completion velocity.

The script runs with zero external dependencies, performs atomic writes, and outputs standard GitHub Flavored Markdown checkboxes compatible with Obsidian, Notion, and project wikis.

## 1. Export action items from the CLI

Generate a task digest:

```sh
omi --json action-item list --limit 500 > action_items.json
python action_items_to_digest.py action_items.json -o task_digest.md --title "Daily Task Briefing"
```

Or stream directly through stdin:

```sh
omi --json action-item list --limit 500 | python action_items_to_digest.py - -o task_digest.md
```

## 2. Sample Output

The generated report features an executive summary table, pending deadlines, and a completed task log:

```markdown
# Daily Task Briefing

## Executive Summary

| Metric | Value |
| :--- | :--- |
| **Total Action Items** | 20 |
| **Completed Tasks** | 12 (60.0%) |
| **Pending Tasks** | 8 |
| **Scheduled Deadlines** | 5 |

## Pending Tasks

### Scheduled

- [ ] **[Due: 2026-03-24]** Review security disclosure *(OVERDUE)*
- [ ] **[Due: 2026-04-01]** Submit quarterly metrics

### Unscheduled (No Deadline)

- [ ] Refactor telemetry pipeline

## Completed Tasks (12)

- [x] Merge PR #19267 *(Completed: 2026-03-26)*
```

## 3. Standalone Converter Script

Save the following as `action_items_to_digest.py`:

```python
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

def parse_action_items_payload(data: Any) -> List[Dict[str, Any]]:
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
    if output_path is not None and ".." in output_path.parts:
        raise ValueError(f"Output path cannot contain '..': {output_path}")

    data = json.loads(raw_json_str)
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Omi action items JSON to Markdown task digest.")
    parser.add_argument("input", help="Path to action items JSON, or '-' for stdin.")
    parser.add_argument("-o", "--output", help="Output Markdown path. Defaults to stdout.")
    parser.add_argument("--title", default="Omi Action Items Executive Digest", help="Report header title.")
    args = parser.parse_args()

    data = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
    out = Path(args.output) if args.output else None
    res = convert_action_items_to_digest(data, out, title=args.title)
    if not out:
        sys.stdout.write(res)
```

## 4. Guarantees

* **Zero third-party dependencies**: standard library only.
* **Overdue detection**: compares UTC ISO dates automatically against local or custom reference dates.
* **Atomic file writing**: temporary `.md.partial` ensures clean, non-corrupted document generation.
