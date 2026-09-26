#!/usr/bin/env python3
"""
Unit tests for memories_to_tsv converter.
"""

from __future__ import annotations

import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from memories_to_tsv import (
    COLUMNS,
    convert_memories_to_tsv,
    escape_tsv_field,
    format_memory_row,
    main,
    parse_memories_payload,
)


class TestMemoriesToTSV(unittest.TestCase):

    def test_escape_tsv_field(self):
        self.assertEqual(escape_tsv_field("hello\tworld"), "hello world")
        self.assertEqual(escape_tsv_field("line1\r\nline2"), "line1\\nline2")
        self.assertEqual(escape_tsv_field("line1\nline2"), "line1\\nline2")
        self.assertEqual(escape_tsv_field(None), "")
        self.assertEqual(escape_tsv_field(""), "")

    def test_parse_memories_bare_array(self):
        bare = [{"id": "m1", "content": "Memory content"}]
        res = parse_memories_payload(bare)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["id"], "m1")

    def test_parse_memories_wrapped(self):
        for key in ("memories", "items", "data", "results"):
            wrapped = {key: [{"id": f"m-{key}", "content": "Sample"}]}
            res = parse_memories_payload(wrapped)
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0]["id"], f"m-{key}")

    def test_format_memory_row(self):
        item = {
            "id": "mem-123",
            "category": "work",
            "created_at": "2026-02-01T10:00:00Z",
            "updated_at": "2026-02-01T11:00:00Z",
            "content": "Discussed roadmap\nwith Alice\tand Bob",
        }
        row = format_memory_row(item)
        self.assertEqual(row["id"], "mem-123")
        self.assertEqual(row["category"], "work")
        self.assertEqual(row["created_at"], "2026-02-01T10:00:00Z")
        self.assertEqual(row["updated_at"], "2026-02-01T11:00:00Z")
        self.assertEqual(row["content"], "Discussed roadmap\\nwith Alice and Bob")

    def test_convert_memories_to_tsv_delimiter(self):
        sample = [
            {"id": "m1", "category": "idea", "created_at": "2026-01-01", "updated_at": "", "content": "Build tool"}
        ]
        tsv_text = convert_memories_to_tsv(json.dumps(sample))
        lines = tsv_text.strip().split("\n")
        self.assertEqual(len(lines), 2)
        # Header has tabs
        self.assertEqual(lines[0], "\t".join(COLUMNS))
        # Line 2 has tab separated fields
        fields = lines[1].split("\t")
        self.assertEqual(fields[0], "m1")
        self.assertEqual(fields[1], "idea")
        self.assertEqual(fields[4], "Build tool")

    def test_path_traversal_rejection(self):
        with self.assertRaises(ValueError):
            convert_memories_to_tsv("[]", Path("out/../../blocked.tsv"))

    def test_invalid_json_rejection(self):
        with self.assertRaises(ValueError):
            convert_memories_to_tsv("invalid json")

    def test_atomic_file_write(self):
        sample = [{"id": "m-atomic", "content": "Atomic check"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "memories.tsv"
            convert_memories_to_tsv(json.dumps(sample), out_file)
            self.assertTrue(out_file.is_file())
            content = out_file.read_text(encoding="utf-8")
            self.assertIn("m-atomic", content)
            self.assertFalse(out_file.with_suffix(".tsv.partial").exists())

    def test_cli_execution_file(self):
        sample = [{"id": "m-cli", "content": "CLI memory"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            in_file = Path(tmpdir) / "in.json"
            out_file = Path(tmpdir) / "out.tsv"
            in_file.write_text(json.dumps(sample), encoding="utf-8")

            exit_code = main([str(in_file), "-o", str(out_file)])
            self.assertEqual(exit_code, 0)
            self.assertTrue(out_file.is_file())
            self.assertIn("m-cli", out_file.read_text(encoding="utf-8"))

    def test_cli_missing_input(self):
        exit_code = main(["missing_file.json"])
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
