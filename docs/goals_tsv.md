# Export goals to TSV for terminal progress tracking

Use this recipe to export Omi goals, target values, units, and progress metrics into Tab-Separated Values (TSV) format for command-line dashboards and daily status reporting.

The script runs without external libraries, computes completion percentages safely with zero-division protection, and serializes each goal as a clean, single-line record.

## 1. Export goals from the CLI

Export goals to a TSV file:

```sh
omi --json goal list --limit 100 > goals.json
python goals_to_tsv.py goals.json -o goals.tsv
```

Or stream directly through stdin:

```sh
omi --json goal list --limit 100 | python goals_to_tsv.py - -o goals.tsv
```

## 2. Shell Pipeline Examples

Monitor goal progress with lightweight shell commands:

```sh
# Print goal title and progress percentage
tail -n +2 goals.tsv | cut -f 2,6

# Filter active goals that are not yet 100% complete
awk -F'\t' '$8 == "True" && $6 != "100.0%" { print $2, "(" $6 ")" }' goals.tsv

# Sort goals by completion percentage
tail -n +2 goals.tsv | sort -k6,6nr
```

## 3. Standalone Converter Script

Save the following as `goals_to_tsv.py`:

```python
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
    if val is None:
        return ""
    text = str(val).strip()
    return text.replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n").replace("\t", " ")

def compute_progress_pct(current: Any, target: Any, goal_type: str) -> str:
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
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("goals", "items", "data", "results"):
            candidate = data.get(key)
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
    return []

def format_goal_tsv_row(goal: Dict[str, Any]) -> Dict[str, str]:
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
    if output_path is not None and ".." in output_path.parts:
        raise ValueError(f"Output path cannot contain '..': {output_path}")

    data = json.loads(raw_json_str)
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
        with open(partial_path, "w", encoding="utf-8", newline="") as f:
            f.write(tsv_content)
        os.replace(partial_path, output_path)

    return tsv_content

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Omi goals JSON to TSV.")
    parser.add_argument("input", help="Path to goals JSON, or '-' for stdin.")
    parser.add_argument("-o", "--output", help="Output TSV path. Defaults to stdout.")
    args = parser.parse_args()

    data = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
    out = Path(args.output) if args.output else None
    res = convert_goals_to_tsv(data, out)
    if not out:
        sys.stdout.write(res)
```

## 4. Guarantees

* **Single-line POSIX streamability**: safe for `awk`, `cut`, and `grep`.
* **Zero dependencies**: standard library only.
* **Atomic write safety**: no partial file corruption.
