#!/usr/bin/env python3
"""
Unit tests for action_items_to_tsv converter.
"""

from __future__ import annotations

import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from action_items_to_tsv import (
    COLUMNS,
    convert_action_items_to_tsv,
    escape_tsv_field,
    format_action_item_tsv_row,
    main,
    parse_action_items_payload,
)


class TestActionItemsToTSV(unittest.TestCase):

    def test_escape_tsv_field(self):
        self.assertEqual(escape_tsv_field("task\tdesc"), "task desc")
        self.assertEqual(escape_tsv_field("line1\r\nline2"), "line1\\nline2")
        self.assertEqual(escape_tsv_field(None), "")

    def test_parse_action_items_bare_array(self):
        bare = [{"id": "t1", "description": "Write doc"}]
        res = parse_action_items_payload(bare)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["id"], "t1")

    def test_parse_action_items_wrapped(self):
        for key in ("action_items", "items", "data", "results"):
            wrapped = {key: [{"id": f"t-{key}", "description": "Deploy"}]}
            res = parse_action_items_payload(wrapped)
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0]["id"], f"t-{key}")

    def test_format_action_item_tsv_row(self):
        item = {
            "id": "act-10",
            "completed": True,
            "due_at": "2026-05-01T00:00:00Z",
            "completed_at": "2026-04-30T12:00:00Z",
            "created_at": "2026-04-20T08:00:00Z",
            "conversation_id": "c-999",
            "description": "Send wire\ttransfer\nto bank",
        }
        row = format_action_item_tsv_row(item)
        self.assertEqual(row["id"], "act-10")
        self.assertEqual(row["completed"], "True")
        self.assertEqual(row["due_at"], "2026-05-01T00:00:00Z")
        self.assertEqual(row["conversation_id"], "c-999")
        self.assertEqual(row["description"], "Send wire transfer\\nto bank")

    def test_convert_action_items_to_tsv_output(self):
        sample = [
            {"id": "t1", "completed": False, "description": "Deploy server", "due_at": "2026-06-01"}
        ]
        tsv_text = convert_action_items_to_tsv(json.dumps(sample))
        lines = tsv_text.strip().split("\n")
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], "\t".join(COLUMNS))
        fields = lines[1].split("\t")
        self.assertEqual(fields[0], "t1")
        self.assertEqual(fields[1], "False")
        self.assertEqual(fields[2], "2026-06-01")
        self.assertEqual(fields[6], "Deploy server")

    def test_path_traversal_rejection(self):
        with self.assertRaises(ValueError):
            convert_action_items_to_tsv("[]", Path("out/../../hack.tsv"))

    def test_invalid_json_rejection(self):
        with self.assertRaises(ValueError):
            convert_action_items_to_tsv("not json")

    def test_atomic_file_write(self):
        sample = [{"id": "act-atom", "description": "Atomic test", "completed": True}]
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "tasks.tsv"
            convert_action_items_to_tsv(json.dumps(sample), out_file)
            self.assertTrue(out_file.is_file())
            content = out_file.read_text(encoding="utf-8")
            self.assertIn("act-atom", content)
            self.assertFalse(out_file.with_suffix(".tsv.partial").exists())

    def test_cli_execution_file(self):
        sample = [{"id": "act-cli", "description": "CLI task"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            in_file = Path(tmpdir) / "tasks.json"
            out_file = Path(tmpdir) / "tasks.tsv"
            in_file.write_text(json.dumps(sample), encoding="utf-8")

            exit_code = main([str(in_file), "-o", str(out_file)])
            self.assertEqual(exit_code, 0)
            self.assertTrue(out_file.is_file())
            self.assertIn("act-cli", out_file.read_text(encoding="utf-8"))

    def test_cli_missing_input(self):
        exit_code = main(["nonexistent.json"])
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
