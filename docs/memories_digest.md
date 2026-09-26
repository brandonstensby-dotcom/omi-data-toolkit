# Generate Markdown knowledge digests from memories

Use this recipe to summarize Omi memories into an executive Markdown knowledge digest, categorized by topic with distribution metrics and formatted for Obsidian, Notion, or email distribution.

The script runs with zero third-party dependencies, groups and tallies records dynamically, sorts categories by frequency, and writes atomically.

## 1. Export memories from the CLI

Generate a digest report:

```sh
omi --json memory list --limit 500 > memories.json
python memories_to_digest.py memories.json -o digest.md --title "Weekly Knowledge Digest"
```

Or stream directly through stdin:

```sh
omi --json memory list --limit 500 | python memories_to_digest.py - -o digest.md
```

## 2. Sample Output

The generated report features a category breakdown table followed by numbered entries:

```markdown
# Omi Memories Knowledge Digest

**Total Memories:** 42 | **Categories:** 4

## Category Summary

| Category | Count | Percentage |
| :--- | :--- | :--- |
| Work | 24 | 57.1% |
| Ideas | 10 | 23.8% |
| Personal | 6 | 14.3% |
| Books | 2 | 4.8% |

## Knowledge Entries

### Work (24)
1. Team architectural review for micro-VM runtime *(2026-03-24)*
...
```

## 3. Standalone Converter Script

Save the following as `memories_to_digest.py`:

```python
import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

def parse_memories_payload(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("memories", "items", "data", "results"):
            candidate = data.get(key)
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
    return []

def build_markdown_digest(memories: List[Dict[str, Any]], title: str = "Omi Memories Knowledge Digest") -> str:
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
            date_str = f" *({created_at[:10]})*" if created_at else ""
            lines.append(f"{idx}. {content}{date_str}")
        lines.append("")

    return "\n".join(lines)

def convert_memories_to_digest(
    raw_json_str: str,
    output_path: Optional[Path] = None,
    title: str = "Omi Memories Knowledge Digest",
) -> str:
    if output_path is not None and ".." in output_path.parts:
        raise ValueError(f"Output path cannot contain '..': {output_path}")

    data = json.loads(raw_json_str)
    memories = parse_memories_payload(data)
    md_content = build_markdown_digest(memories, title)

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        partial_path = output_path.with_suffix(".md.partial")
        with open(partial_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(md_content)
        os.replace(partial_path, output_path)

    return md_content

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Omi memories JSON to Markdown digest.")
    parser.add_argument("input", help="Path to memories JSON, or '-' for stdin.")
    parser.add_argument("-o", "--output", help="Output Markdown path. Defaults to stdout.")
    parser.add_argument("--title", default="Omi Memories Knowledge Digest", help="Report header title.")
    args = parser.parse_args()

    data = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
    out = Path(args.output) if args.output else None
    res = convert_memories_to_digest(data, out, title=args.title)
    if not out:
        sys.stdout.write(res)
```

## 4. Guarantees

* **Zero third-party dependencies**: standard library only (`argparse`, `json`, `collections`, `pathlib`).
* **Atomic file writing**: temporary `.md.partial` ensures intact documents.
* **Deterministic sorting**: sorted by category frequency in descending order.
