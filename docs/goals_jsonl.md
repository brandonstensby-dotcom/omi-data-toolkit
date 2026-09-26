# Export goals to JSONL for streaming & data lakes

Use this recipe to export Omi goals into JSON Lines (JSONL) format, where each goal is represented as a standalone, valid JSON object on its own line with enriched completion metrics.

JSONL is the industry-standard format for vector databases, big data warehouses, Apache Spark pipelines, and LLM fine-tuning datasets.

## 1. Export goals from the CLI

Export goals to a JSONL file:

```sh
omi --json goal list --limit 100 > goals.json
python goals_to_jsonl.py goals.json -o goals.jsonl
```

Or stream directly through stdin:

```sh
omi --json goal list --limit 100 | python goals_to_jsonl.py - -o goals.jsonl
```

## 2. Stream Processing Examples

Process goals line-by-line using `jq`:

```sh
# Extract active goals with their completion percentages
jq 'select(.is_active == true) | {title: .title, progress: .progress_pct}' goals.jsonl

# Count goals above 80% completion
jq 'select(.progress_pct != null and .progress_pct >= 80)' goals.jsonl | wc -l
```

## 3. Standalone Converter Script

Save the following as `goals_to_jsonl.py`:

```python
import argparse
import json
import os
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

    return round((curr_f / targ_f) * 100.0, 2)

def parse_goals_payload(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("goals", "items", "data", "results"):
            candidate = data.get(key)
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
    return []

def format_goal_jsonl_item(goal: Dict[str, Any]) -> Dict[str, Any]:
    current = goal.get("current_value")
    target = goal.get("target_value")
    goal_type = str(goal.get("goal_type", "qualitative")).strip()

    progress = compute_progress_pct(current, target, goal_type)

    return {
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

def convert_goals_to_jsonl(raw_json_str: str, output_path: Optional[Path] = None) -> str:
    if output_path is not None and ".." in output_path.parts:
        raise ValueError(f"Output path cannot contain '..': {output_path}")

    data = json.loads(raw_json_str)
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Omi goals JSON to JSONL.")
    parser.add_argument("input", help="Path to goals JSON, or '-' for stdin.")
    parser.add_argument("-o", "--output", help="Output JSONL path. Defaults to stdout.")
    args = parser.parse_args()

    data = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
    out = Path(args.output) if args.output else None
    res = convert_goals_to_jsonl(data, out)
    if not out:
        sys.stdout.write(res)
```

## 4. Guarantees

* **Standard JSON Lines compliance**: each row is a fully valid JSON document.
* **Zero dependencies**: standard library only.
* **Safe floating-point progress calculation**: handles missing targets, boolean values, and division by zero.
