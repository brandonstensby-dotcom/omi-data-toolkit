# Export goals to CSV for spreadsheets

Use this recipe to export Omi goals, target metrics, and progress percentages into
a clean CSV spreadsheet compatible with Microsoft Excel, Google Sheets, LibreOffice,
and automated reporting pipelines.

The converter makes no network requests, calculates progress safely without
division-by-zero risks, and performs atomic disk writes.

## 1. Export goals from the CLI

Export your goals in JSON format:

```sh
omi --json goal list --limit 100 > goals.json
```

Or pipe directly into the converter without writing an intermediate JSON file:

```sh
omi --json goal list --limit 100 | python goals_to_csv.py - -o goals.csv
```

## 2. Standalone Converter Script

Save the following as `goals_to_csv.py`:

```python
import argparse
import csv
import json
import os
import sys
from pathlib import Path

COLUMNS = [
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

def compute_progress_pct(current, target, goal_type):
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
    return f"{(curr_f / targ_f) * 100.0:.1f}%"

def parse_goals_payload(data):
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("goals", "items", "data", "results"):
            candidate = data.get(key)
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
    return []

def format_row(goal):
    current = goal.get("current_value")
    target = goal.get("target_value")
    goal_type = str(goal.get("goal_type", "qualitative")).strip()
    return {
        "id": str(goal.get("id", "")).strip(),
        "title": str(goal.get("title", "")).strip(),
        "goal_type": goal_type,
        "current_value": str(current) if current is not None else "",
        "target_value": str(target) if target is not None else "",
        "progress_pct": compute_progress_pct(current, target, goal_type),
        "unit": str(goal.get("unit", "") or "").strip(),
        "is_active": "True" if goal.get("is_active", True) else "False",
        "created_at": str(goal.get("created_at", "") or "").strip(),
        "updated_at": str(goal.get("updated_at", "") or "").strip(),
    }

def convert_goals_to_csv(raw_json_str, output_path=None):
    if output_path is not None and ".." in output_path.parts:
        raise ValueError(f"Output path cannot contain '..': {output_path}")
    data = json.loads(raw_json_str)
    goals = parse_goals_payload(data)
    rows = [format_row(g) for g in goals]
    import io
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    content = stream.getvalue()
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        partial = output_path.with_suffix(".csv.partial")
        with open(partial, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        os.replace(partial, output_path)
    return content

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Omi goals JSON to CSV.")
    parser.add_argument("input", help="Path to goals JSON, or '-' for stdin.")
    parser.add_argument("-o", "--output", help="Output CSV path. Defaults to stdout.")
    args = parser.parse_args()
    data = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
    res = convert_goals_to_csv(data, Path(args.output) if args.output else None)
    if not args.output:
        sys.stdout.write(res)
```

## 3. Guarantees

* **Zero third-party dependencies**: uses Python standard library only (`csv`, `json`, `argparse`, `pathlib`).
* **Safe division & null coercion**: missing target values, empty strings, and zero targets produce clean outputs (`N/A` or `100.0%`) without throwing exceptions.
* **Atomic file writing**: temporary `.partial` files prevent corrupted or incomplete outputs if interrupted.
* **Directory traversal protection**: output path is verified against `..` components before file handles are opened.
