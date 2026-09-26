#!/usr/bin/env python3
"""
Unit tests for action_items_to_csv converter.
"""

from __future__ import annotations

import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from action_items_to_csv import (
    COLUMNS,
    convert_action_items_to_csv,
    format_action_item_row,
    main,
    parse_action_items_payload,
)


class TestActionItemsToCSV(unittest.TestCase):

    def test_parse_action_items_bare_array(self):
        bare = [{"id": "act-1", "description": "Call vendor", "completed": False}]
        result = parse_action_items_payload(bare)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "act-1")

    def test_parse_action_items_wrapped_payloads(self):
        for key in ("action_items", "items", "data", "results"):
            wrapped = {key: [{"id": f"act-{key}", "description": "Task", "completed": True}]}
            res = parse_action_items_payload(wrapped)
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0]["id"], f"act-{key}")

    def test_parse_action_items_empty_or_invalid(self):
        self.assertEqual(parse_action_items_payload({}), [])
        self.assertEqual(parse_action_items_payload([]), [])
        self.assertEqual(parse_action_items_payload("not-a-dict"), [])
        self.assertEqual(parse_action_items_payload(123), [])

    def test_format_action_item_row(self):
        item = {
            "id": "act-99",
            "completed": True,
            "description": "Send quarterly review",
            "due_at": "2026-03-31T23:59:59Z",
            "completed_at": "2026-03-30T10:15:00Z",
            "created_at": "2026-03-01T08:00:00Z",
            "updated_at": "2026-03-30T10:15:00Z",
            "conversation_id": "conv-404",
        }
        row = format_action_item_row(item)
        self.assertEqual(row["id"], "act-99")
        self.assertEqual(row["completed"], "True")
        self.assertEqual(row["description"], "Send quarterly review")
        self.assertEqual(row["due_at"], "2026-03-31T23:59:59Z")
        self.assertEqual(row["completed_at"], "2026-03-30T10:15:00Z")
        self.assertEqual(row["conversation_id"], "conv-404")

    def test_format_action_item_row_defaults(self):
        row = format_action_item_row({})
        self.assertEqual(row["id"], "")
        self.assertEqual(row["completed"], "False")
        self.assertEqual(row["description"], "")
        self.assertEqual(row["due_at"], "")
        self.assertEqual(row["completed_at"], "")
        self.assertEqual(row["conversation_id"], "")

    def test_convert_action_items_to_csv_output(self):
        sample = [
            {
                "id": "a1",
                "completed": False,
                "description": "Order coffee beans",
                "due_at": "2026-04-01T12:00:00Z",
                "completed_at": None,
                "created_at": "2026-03-25T09:00:00Z",
                "updated_at": "2026-03-25T09:00:00Z",
                "conversation_id": "c1",
            }
        ]
        csv_text = convert_action_items_to_csv(json.dumps(sample))
        reader = list(csv.DictReader(io.StringIO(csv_text)))

        self.assertEqual(len(reader), 1)
        row = reader[0]
        self.assertEqual(row["id"], "a1")
        self.assertEqual(row["completed"], "False")
        self.assertEqual(row["description"], "Order coffee beans")
        self.assertEqual(row["due_at"], "2026-04-01T12:00:00Z")

    def test_special_characters_and_newlines(self):
        sample = [
            {
                "id": "a2",
                "completed": False,
                "description": "Item with, commas and \"quotes\" and\nnewlines",
                "due_at": "",
                "completed_at": "",
                "created_at": "",
                "updated_at": "",
                "conversation_id": "",
            }
        ]
        csv_text = convert_action_items_to_csv(json.dumps(sample))
        reader = list(csv.DictReader(io.StringIO(csv_text)))
        self.assertEqual(len(reader), 1)
        self.assertIn("commas and \"quotes\" and\nnewlines", reader[0]["description"])

    def test_path_traversal_rejection(self):
        with self.assertRaises(ValueError):
            convert_action_items_to_csv("[]", Path("folder/../../hacked.csv"))

    def test_invalid_json_rejection(self):
        with self.assertRaises(ValueError):
            convert_action_items_to_csv("malformed json {")

    def test_atomic_file_write(self):
        sample = [{"id": "act-atomic", "description": "Verify atomic write", "completed": True}]
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "action_items.csv"
            convert_action_items_to_csv(json.dumps(sample), out_file)

            self.assertTrue(out_file.is_file())
            content = out_file.read_text(encoding="utf-8")
            self.assertIn("act-atomic", content)
            self.assertIn("Verify atomic write", content)
            self.assertFalse(out_file.with_suffix(".csv.partial").exists())

    def test_cli_execution_file(self):
        sample = [{"id": "act-cli", "description": "CLI test", "completed": False}]
        with tempfile.TemporaryDirectory() as tmpdir:
            in_file = Path(tmpdir) / "tasks.json"
            out_file = Path(tmpdir) / "tasks.csv"
            in_file.write_text(json.dumps(sample), encoding="utf-8")

            exit_code = main([str(in_file), "-o", str(out_file)])
            self.assertEqual(exit_code, 0)
            self.assertTrue(out_file.is_file())
            self.assertIn("act-cli", out_file.read_text(encoding="utf-8"))

    def test_cli_missing_input_file(self):
        exit_code = main(["nonexistent_tasks_file.json"])
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
