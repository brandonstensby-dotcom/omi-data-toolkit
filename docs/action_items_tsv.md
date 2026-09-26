# Export action items to TSV for terminal task filtering

Use this recipe to export Omi action items into Tab-Separated Values (TSV) format for command-line parsing, automated shell alerts, and cron pipelines.

Tab-separated streams allow rapid querying with `awk` and `cut` without needing a heavy CSV parsing library. All newlines within descriptions are sanitized into `\n` to guarantee strict one-record-per-line integrity.

## 1. Export action items from the CLI

Export action items to a TSV file:

```sh
omi --json action-item list --limit 500 > action_items.json
python action_items_to_tsv.py action_items.json -o action_items.tsv
```

Or stream directly through stdin:

```sh
omi --json action-item list --limit 500 | python action_items_to_tsv.py - -o action_items.tsv
```

## 2. Shell Pipeline Examples

Query open and completed tasks directly in the terminal:

```sh
# Print open action items (where completed == "False")
awk -F'\t' '$2 == "False" { print $1, $3, $7 }' action_items.tsv

# Count completed vs pending tasks
tail -n +2 action_items.tsv | cut -f 2 | sort | uniq -c

# Search for urgent tasks due in 2026
awk -F'\t' '$2 == "False" && $3 ~ /^2026/ { print "DUE:", $3, "->", $7 }' action_items.tsv
```

## 3. Standalone Converter Script

Save the following as `action_items_to_tsv.py`:

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
    "due_at",
    "completed_at",
    "created_at",
    "conversation_id",
    "description",
]

def escape_tsv_field(val: Any) -> str:
    if val is None:
        return ""
    text = str(val).strip()
    return text.replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n").replace("\t", " ")

def parse_action_items_payload(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("action_items", "items", "data", "results"):
            candidate = data.get(key)
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
    return []

def format_action_item_tsv_row(item: Dict[str, Any]) -> Dict[str, str]:
    return {
        "id": str(item.get("id", "")).strip(),
        "completed": "True" if item.get("completed", False) else "False",
        "due_at": str(item.get("due_at", "") or "").strip(),
        "completed_at": str(item.get("completed_at", "") or "").strip(),
        "created_at": str(item.get("created_at", "") or "").strip(),
        "conversation_id": str(item.get("conversation_id", "") or "").strip(),
        "description": escape_tsv_field(item.get("description", "") or ""),
    }

def convert_action_items_to_tsv(raw_json_str: str, output_path: Optional[Path] = None) -> str:
    if output_path is not None and ".." in output_path.parts:
        raise ValueError(f"Output path cannot contain '..': {output_path}")

    data = json.loads(raw_json_str)
    items = parse_action_items_payload(data)
    rows = [format_action_item_tsv_row(i) for i in items]

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
    parser = argparse.ArgumentParser(description="Convert Omi action items JSON to TSV.")
    parser.add_argument("input", help="Path to action items JSON, or '-' for stdin.")
    parser.add_argument("-o", "--output", help="Output TSV path. Defaults to stdout.")
    args = parser.parse_args()

    data = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
    out = Path(args.output) if args.output else None
    res = convert_action_items_to_tsv(data, out)
    if not out:
        sys.stdout.write(res)
```

## 4. Guarantees

* **Single-line POSIX streamability**: safe for `awk`, `cut`, and `grep`.
* **Zero dependencies**: standard library only.
* **Atomic write safety**: no partial file corruption.
