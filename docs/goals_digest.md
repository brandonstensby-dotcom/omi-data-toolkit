# Generate milestone briefings & visual progress reports from goals

Use this recipe to convert Omi goals into an executive milestone digest featuring text-based visual progress bars (`[██████░░░░] 60.0%`), active vs achieved classification, and summary metrics.

The generator runs without third-party packages, handles missing metrics safely, renders clean Markdown tables, and writes files atomically.

## 1. Export goals from the CLI

Generate a goals digest:

```sh
omi --json goal list --limit 100 > goals.json
python goals_to_digest.py goals.json -o goals_digest.md --title "Q2 Objectives Briefing"
```

Or stream directly through stdin:

```sh
omi --json goal list --limit 100 | python goals_to_digest.py - -o goals_digest.md
```

## 2. Sample Output

The generated report highlights progress bars and separates active goals from achieved and paused targets:

```markdown
# Q2 Objectives Briefing

## Executive Summary

| Metric | Count |
| :--- | :--- |
| **Total Goals** | 10 |
| **In Progress** | 6 |
| **Achieved / Completed** | 3 |
| **Inactive / Paused** | 1 |

## Active Goals in Progress

### Run 100km (65 / 100 km)
`[██████████░░░░░] 65.0%`

### Read 20 Books (14 / 20 books)
`[███████████░░░░] 70.0%`

## Achieved Goals (100% Complete)

- [x] **Deploy Production API** `[██████████] 100.0%`
- [x] **Refactor VM Opcodes** `[██████████] 100.0%`

## Inactive / Paused Goals

- [ ] *Learn French* (Paused)
```

## 3. Standalone Converter Script

Save the following as `goals_to_digest.py`:

```python
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

def compute_progress_pct(current: Any, target: Any, goal_type: str) -> Optional[float]:
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
    if pct is None:
        return f"[{'·' * width}] N/A"

    clamped = max(0.0, min(100.0, pct))
    filled = int(round((clamped / 100.0) * width))
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {pct:.1f}%"

def parse_goals_payload(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("goals", "items", "data", "results"):
            candidate = data.get(key)
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
    return []

def build_goals_digest(goals: List[Dict[str, Any]], title: str = "Omi Goals & Milestones Digest") -> str:
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
    if output_path is not None and ".." in output_path.parts:
        raise ValueError(f"Output path cannot contain '..': {output_path}")

    data = json.loads(raw_json_str)
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Omi goals JSON to visual Markdown progress digest.")
    parser.add_argument("input", help="Path to goals JSON, or '-' for stdin.")
    parser.add_argument("-o", "--output", help="Output Markdown path. Defaults to stdout.")
    parser.add_argument("--title", default="Omi Goals & Milestones Digest", help="Report header title.")
    args = parser.parse_args()

    data = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
    out = Path(args.output) if args.output else None
    res = convert_goals_to_digest(data, out, title=args.title)
    if not out:
        sys.stdout.write(res)
```

## 4. Guarantees

* **Zero third-party dependencies**: standard library only.
* **Deterministic progress visualization**: Unicode bars scale dynamically based on specified width.
* **Atomic file writing**: temporary `.md.partial` ensures reliable output.
