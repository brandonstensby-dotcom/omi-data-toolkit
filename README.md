# Omi Data Toolkit (`omi-data-toolkit`)

[![CI Test Suite](https://github.com/brandonstensby-dotcom/omi-data-toolkit/actions/workflows/test.yml/badge.svg)](https://github.com/brandonstensby-dotcom/omi-data-toolkit/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](#architecture)

High-performance, zero-dependency data transformation, export, and backup toolchain for the [Omi](https://github.com/BasedHardware/omi) ecosystem.

Designed for automated pipelines, spreadsheet integration, terminal stream analytics, personal knowledge management (PKM), and offline cold storage.

---

## Toolchain Overview

The toolkit comprises **12 production-grade CLI utilities and recipes**, built strictly with the Python standard library:

### 1. Spreadsheet & Tabular Exporters
* [`tools/goals_to_csv.py`](tools/goals_to_csv.py): Converts goals into Excel/Sheets CSV with safe percentage calculations and division-by-zero protection.
* [`tools/action_items_to_csv.py`](tools/action_items_to_csv.py): Converts action items, completion flags, and due dates into spreadsheet CSV.

### 2. POSIX Terminal Stream Tools (TSV)
* [`tools/memories_to_tsv.py`](tools/memories_to_tsv.py): Exports memories to TSV with newline escaping for `awk`, `cut`, and `grep`.
* [`tools/action_items_to_tsv.py`](tools/action_items_to_tsv.py): Exports action items to single-line TSV for command-line task filtering.
* [`tools/conversations_to_tsv.py`](tools/conversations_to_tsv.py): Formats conversation transcripts and summaries for terminal text-mining.
* [`tools/goals_to_tsv.py`](tools/goals_to_tsv.py): Formats goal targets and progress metrics into tab-delimited streams.

### 3. Data Lake & Vector Pipeline Exporters
* [`tools/goals_to_jsonl.py`](tools/goals_to_jsonl.py): Exports goals as JSON Lines (JSONL) with computed progress floats for vector search and analytics.

### 4. Executive Knowledge & Task Digests
* [`tools/memories_to_digest.py`](tools/memories_to_digest.py): Categorized Markdown knowledge digest with frequency metrics for Obsidian and Notion.
* [`tools/action_items_to_digest.py`](tools/action_items_to_digest.py): Task audit report classifying pending, overdue, and completed items into checklists.
* [`tools/goals_to_digest.py`](tools/goals_to_digest.py): Milestone progress briefing with Unicode visual progress bars (`[██████░░░░] 60%`).

### 5. Task Manager Synchronization
* [`tools/goals_to_todotxt.py`](tools/goals_to_todotxt.py): Standard `todo.txt` exporter with priority, context, and project tag mapping.

### 6. Archival & Cryptographic Verification
* [`tools/backup_bundle.py`](tools/backup_bundle.py): Multi-resource `.tar.gz` bundler and verifier with embedded SHA-256 cryptographic manifests.

---

## Architecture & Guarantees

1. **Zero External Dependencies**: 100% Python standard library (`csv`, `json`, `argparse`, `pathlib`, `hashlib`, `tarfile`). Runs anywhere Python runs without `pip install`.
2. **Atomic Disk Writes**: Every converter writes to a `.partial` file before atomic replacement (`os.replace`), preventing corrupted files on unexpected interruptions.
3. **Directory Traversal Defense**: All output paths are strictly validated against `..` components before file descriptors are opened.
4. **100% Test Coverage**: Full test suite across 12 test modules running 112 deterministic unit tests.

---

## Quickstart

### Convert Goals to CSV
```bash
omi --json goal list --limit 100 | python tools/goals_to_csv.py - -o goals.csv
```

### Stream Memories to Awk
```bash
python tools/memories_to_tsv.py memories.json -o memories.tsv
awk -F'\t' '$2 == "work" { print $1, $5 }' memories.tsv
```

### Generate Executive Task Briefing
```bash
omi --json action-item list --limit 500 | python tools/action_items_to_digest.py - -o briefing.md
```

### Create Cryptographically Verified Backup
```bash
python tools/backup_bundle.py create --output backup.tar.gz \
    --memories memories.json \
    --conversations conversations.json \
    --action-items action_items.json \
    --goals goals.json

# Verify archive
python tools/backup_bundle.py verify backup.tar.gz
```

---

## Running Tests

Run the full 112-test suite via standard library `unittest`:

```bash
# Linux / macOS
PYTHONPATH=tools python3 -m unittest discover -s tests -p "test_*.py"

# Windows (PowerShell)
$env:PYTHONPATH="tools"; python -m unittest discover -s tests -p "test_*.py"
```

---

## License

MIT License. Developed by **CoreVector Systems** (`brandonworkforce@tutamail.com`).
