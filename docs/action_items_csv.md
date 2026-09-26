# Export action items to CSV for spreadsheets

Use this recipe to export Omi action items, completion states, due dates, and linked conversation IDs into a clean CSV spreadsheet compatible with Microsoft Excel, Google Sheets, Airtable, and automated task-tracking pipelines.

The converter makes no network requests, normalizes completion flags cleanly, handles multi-line descriptions and embedded quotes according to RFC 4180, and performs atomic disk writes.

## 1. Export action items from the CLI

Export your action items in JSON format:

```sh
omi --json action-item list --limit 500 > action_items.json
```

Or pipe directly into the converter without writing an intermediate JSON file:

```sh
omi --json action-item list --limit 500 | python action_items_to_csv.py - -o action_items.csv
```

## 2. Standalone Converter Script

Save the following as `action_items_to_csv.py`:

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
    "completed",
    "description",
    "due_at",
    "completed_at",
    "created_at",
    "updated_at",
    "conversation_id",
]

def parse_action_items_payload(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("action_items", "items", "data", "results"):
            candidate = data.get(key)
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
    return []

def format_action_item_row(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(item.get("id", "")).strip(),
        "completed": "True" if item.get("completed", False) else "False",
        "description": str(item.get("description", "") or "").strip(),
        "due_at": str(item.get("due_at", "") or "").strip(),
        "completed_at": str(item.get("completed_at", "") or "").strip(),
        "created_at": str(item.get("created_at", "") or "").strip(),
        "updated_at": str(item.get("updated_at", "") or "").strip(),
        "conversation_id": str(item.get("conversation_id", "") or "").strip(),
    }

def convert_action_items_to_csv(raw_json_str: str, output_path: Optional[Path] = None) -> str:
    if output_path is not None and ".." in output_path.parts:
        raise ValueError(f"Output path cannot contain '..': {output_path}")

    data = json.loads(raw_json_str)
    items = parse_action_items_payload(data)
    rows = [format_action_item_row(i) for i in items]

    import io
    output_stream = io.StringIO()
    writer = csv.DictWriter(output_stream, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    csv_content = output_stream.getvalue()

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        partial_path = output_path.with_suffix(".csv.partial")
        with open(partial_path, "w", encoding="utf-8", newline="") as f:
            f.write(csv_content)
        os.replace(partial_path, output_path)

    return csv_content

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Omi action items JSON to CSV.")
    parser.add_argument("input", help="Path to action items JSON, or '-' for stdin.")
    parser.add_argument("-o", "--output", help="Output CSV path. Defaults to stdout.")
    args = parser.parse_args()

    data = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
    out = Path(args.output) if args.output else None
    res = convert_action_items_to_csv(data, out)
    if not out:
        sys.stdout.write(res)
```

## 3. Guarantees

* **Zero third-party dependencies**: uses Python standard library only (`csv`, `json`, `argparse`, `pathlib`).
* **Normalized Boolean status**: converts truthy/falsy completion markers to clean `"True"` or `"False"` values for reliable spreadsheet filtering.
* **Atomic file writing**: temporary `.partial` files prevent corrupted or half-written spreadsheets if the pipeline terminates abruptly.
* **Directory traversal protection**: output path is verified against `..` components before file handles are opened.
