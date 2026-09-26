# Export goals to standard todo.txt format

Use this recipe to export Omi goals into standard `todo.txt` format for synchronization with mobile and desktop todo managers such as Markor, Simpletask, TodoTxtMac, Todo.txt CLI, and the Obsidian Todo+ plugin.

The format encodes active priorities `(A)`, completion markers `x`, project tags `+OmiGoal`, context `@milestone`, and metadata key-value tags (`progress:XX%`, `id:XX`).

## 1. Export goals from the CLI

Export goals into a `todo.txt` file:

```sh
omi --json goal list --limit 100 > goals.json
python goals_to_todotxt.py goals.json -o todo.txt
```

Or stream directly through stdin:

```sh
omi --json goal list --limit 100 | python goals_to_todotxt.py - -o todo.txt
```

## 2. Sample todo.txt Output

```text
(A) 2026-03-01 Complete Phase 1 MVP +OmiGoal @milestone id:g-101 progress:75%
(A) 2026-03-10 Read 10 Technical Books +OmiGoal @milestone id:g-102 progress:40%
(C) 2026-01-01 Learn French +OmiGoal @milestone id:g-103 status:paused
x 2026-02-15 Deploy Production Server +OmiGoal @milestone id:g-100 progress:100%
```

## 3. Standalone Converter Script

Save the following as `goals_to_todotxt.py`:

```python
import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

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

def parse_goals_payload(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("goals", "items", "data", "results"):
            candidate = data.get(key)
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
    return []

def sanitize_text(text: str) -> str:
    return re.sub(r"[\r\n]+", " ", text).strip()

def format_goal_todotxt_line(goal: Dict[str, Any]) -> str:
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
        parts.append(f"x {comp_date}" if comp_date else "x")
    else:
        parts.append("(A)" if is_active else "(C)")

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
    if output_path is not None and ".." in output_path.parts:
        raise ValueError(f"Output path cannot contain '..': {output_path}")

    data = json.loads(raw_json_str)
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Omi goals JSON to todo.txt format.")
    parser.add_argument("input", help="Path to goals JSON, or '-' for stdin.")
    parser.add_argument("-o", "--output", help="Output todo.txt path. Defaults to stdout.")
    args = parser.parse_args()

    data = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
    out = Path(args.output) if args.output else None
    res = convert_goals_to_todotxt(data, out)
    if not out:
        sys.stdout.write(res)
```

## 4. Guarantees

* **Full todo.txt spec compliance**: strict single-line output, valid priority prefixes, and project/context tags.
* **Zero dependencies**: standard library only.
* **Atomic file writing**: temporary `.txt.partial` ensures intact files.
