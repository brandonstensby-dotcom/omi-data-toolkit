#!/usr/bin/env python3
"""
Unit tests for goals_to_jsonl converter.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from goals_to_jsonl import (
    compute_progress_pct,
    convert_goals_to_jsonl,
    format_goal_jsonl_item,
    main,
    parse_goals_payload,
)


class TestGoalsToJSONL(unittest.TestCase):

    def test_compute_progress_pct(self):
        self.assertEqual(compute_progress_pct(50, 100, "numeric"), 50.0)
        self.assertEqual(compute_progress_pct(1.0, None, "boolean"), 100.0)
        self.assertEqual(compute_progress_pct(0.0, None, "boolean"), 0.0)
        self.assertIsNone(compute_progress_pct(None, 100, "numeric"))
        self.assertEqual(compute_progress_pct(10, 0, "numeric"), 100.0)

    def test_parse_goals_payload(self):
        bare = [{"id": "g1", "title": "Run"}]
        self.assertEqual(len(parse_goals_payload(bare)), 1)
        wrapped = {"goals": [{"id": "g2"}]}
        self.assertEqual(len(parse_goals_payload(wrapped)), 1)

    def test_format_goal_jsonl_item(self):
        goal = {
            "id": "g10",
            "title": "Ship MVP",
            "goal_type": "numeric",
            "current_value": 3,
            "target_value": 4,
            "unit": "sprints",
            "is_active": True,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-03-01T00:00:00Z",
        }
        item = format_goal_jsonl_item(goal)
        self.assertEqual(item["id"], "g10")
        self.assertEqual(item["title"], "Ship MVP")
        self.assertEqual(item["progress_pct"], 75.0)
        self.assertEqual(item["unit"], "sprints")
        self.assertTrue(item["is_active"])

    def test_convert_goals_to_jsonl_output(self):
        sample = [
            {"id": "g1", "title": "Goal 1", "current_value": 1, "target_value": 2},
            {"id": "g2", "title": "Goal 2", "current_value": 10, "target_value": 10},
        ]
        jsonl_text = convert_goals_to_jsonl(json.dumps(sample))
        lines = [line for line in jsonl_text.strip().split("\n") if line]
        self.assertEqual(len(lines), 2)

        obj1 = json.loads(lines[0])
        self.assertEqual(obj1["id"], "g1")
        self.assertEqual(obj1["progress_pct"], 50.0)

        obj2 = json.loads(lines[1])
        self.assertEqual(obj2["id"], "g2")
        self.assertEqual(obj2["progress_pct"], 100.0)

    def test_path_traversal_rejection(self):
        with self.assertRaises(ValueError):
            convert_goals_to_jsonl("[]", Path("out/../../hack.jsonl"))

    def test_invalid_json_rejection(self):
        with self.assertRaises(ValueError):
            convert_goals_to_jsonl("invalid json string")

    def test_atomic_file_write(self):
        sample = [{"id": "g-atomic", "title": "Atomic"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "goals.jsonl"
            convert_goals_to_jsonl(json.dumps(sample), out_file)
            self.assertTrue(out_file.is_file())
            content = out_file.read_text(encoding="utf-8")
            self.assertIn("g-atomic", content)
            self.assertFalse(out_file.with_suffix(".jsonl.partial").exists())

    def test_cli_execution_file(self):
        sample = [{"id": "g-cli", "title": "CLI Goal"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            in_file = Path(tmpdir) / "goals.json"
            out_file = Path(tmpdir) / "goals.jsonl"
            in_file.write_text(json.dumps(sample), encoding="utf-8")

            exit_code = main([str(in_file), "-o", str(out_file)])
            self.assertEqual(exit_code, 0)
            self.assertTrue(out_file.is_file())
            self.assertIn("g-cli", out_file.read_text(encoding="utf-8"))

    def test_cli_missing_input(self):
        exit_code = main(["nonexistent.json"])
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
