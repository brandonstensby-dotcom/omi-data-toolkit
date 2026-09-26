# Export memories to TSV for terminal analytics

Use this recipe to export Omi memories into Tab-Separated Values (TSV) format for fast, streamable terminal processing with tools like `awk`, `cut`, `grep`, `sort`, and `uniq`.

Unlike CSV, tab-delimited streams allow single-line inspection without multi-line quoting issues breaking standard POSIX utilities. Internal newlines and tabs are cleanly escaped to ensure each record occupies exactly one row.

## 1. Export memories from the CLI

Export memories to a TSV file:

```sh
omi --json memory list --limit 1000 > memories.json
python memories_to_tsv.py memories.json -o memories.tsv
```

Or stream directly through stdin:

```sh
omi --json memory list --limit 1000 | python memories_to_tsv.py - -o memories.tsv
```

## 2. Unix Pipeline Examples

Filter memories by category using standard terminal utilities:

```sh
# Print category and content columns
cut -f 2,5 memories.tsv

# Count memories by category
tail -n +2 memories.tsv | cut -f 2 | sort | uniq -c | sort -nr

# Search for work-related memories using awk
awk -F'\t' '$2 == "work" { print $1, $5 }' memories.tsv
```

## 3. Standalone Converter Script

Save the following as `memories_to_tsv.py`:

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
    "category",
    "created_at",
    "updated_at",
    "content",
]

def escape_tsv_field(val: Any) -> str:
    if val is None:
        return ""
    text = str(val).strip()
    return text.replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n").replace("\t", " ")

def parse_memories_payload(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("memories", "items", "data", "results"):
            candidate = data.get(key)
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
    return []

def format_memory_row(item: Dict[str, Any]) -> Dict[str, str]:
    mem_id = str(item.get("id", "")).strip()
    category = str(item.get("category", "") or item.get("structured", {}).get("category", "") or "").strip()
    created_at = str(item.get("created_at", "") or "").strip()
    updated_at = str(item.get("updated_at", "") or "").strip()
    content = escape_tsv_field(item.get("content", "") or item.get("structured", {}).get("overview", ""))

    return {
        "id": mem_id,
        "category": category,
        "created_at": created_at,
        "updated_at": updated_at,
        "content": content,
    }

def convert_memories_to_tsv(raw_json_str: str, output_path: Optional[Path] = None) -> str:
    if output_path is not None and ".." in output_path.parts:
        raise ValueError(f"Output path cannot contain '..': {output_path}")

    data = json.loads(raw_json_str)
    memories = parse_memories_payload(data)
    rows = [format_memory_row(m) for m in memories]

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
    parser = argparse.ArgumentParser(description="Convert Omi memories JSON to TSV.")
    parser.add_argument("input", help="Path to memories JSON, or '-' for stdin.")
    parser.add_argument("-o", "--output", help="Output TSV path. Defaults to stdout.")
    args = parser.parse_args()

    data = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
    out = Path(args.output) if args.output else None
    res = convert_memories_to_tsv(data, out)
    if not out:
        sys.stdout.write(res)
```

## 4. Guarantees

* **Strict single-line records**: internal newlines and tabs are converted to `\n` and spaces to guarantee record boundaries for terminal utilities.
* **Zero third-party dependencies**: standard library only.
* **Atomic write safety**: `.tsv.partial` swapping prevents partial writes upon signal termination.
