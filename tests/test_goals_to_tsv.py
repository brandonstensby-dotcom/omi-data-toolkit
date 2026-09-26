#!/usr/bin/env python3
"""
Unit tests for goals_to_tsv converter.
"""

from __future__ import annotations

import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from goals_to_tsv import (
    COLUMNS,
    compute_progress_pct,
    convert_goals_to_tsv,
    escape_tsv_field,
    format_goal_tsv_row,
    main,
    parse_goals_payload,
)


class TestGoalsToTSV(unittest.TestCase):

    def test_escape_tsv_field(self):
        self.assertEqual(escape_tsv_field("title\tgoal"), "title goal")
        self.assertEqual(escape_tsv_field("part1\npart2"), "part1\\npart2")
        self.assertEqual(escape_tsv_field(None), "")

    def test_compute_progress_pct(self):
        self.assertEqual(compute_progress_pct(50, 100, "numeric"), "50.0%")
        self.assertEqual(compute_progress_pct(1.0, None, "boolean"), "100.0%")
        self.assertEqual(compute_progress_pct(None, 100, "numeric"), "N/A")
        self.assertEqual(compute_progress_pct(10, 0, "numeric"), "100.0%")

    def test_parse_goals_payload(self):
        bare = [{"id": "g1", "title": "Run"}]
        self.assertEqual(len(parse_goals_payload(bare)), 1)
        wrapped = {"goals": [{"id": "g2"}]}
        self.assertEqual(len(parse_goals_payload(wrapped)), 1)

    def test_format_goal_tsv_row(self):
        goal = {
            "id": "g-55",
            "title": "Save $10,000\tby year end\nurgent",
            "goal_type": "numeric",
            "current_value": 7500,
            "target_value": 10000,
            "unit": "USD",
            "is_active": True,
            "created_at": "2026-01-01",
            "updated_at": "2026-05-01",
        }
        row = format_goal_tsv_row(goal)
        self.assertEqual(row["id"], "g-55")
        self.assertEqual(row["title"], "Save $10,000 by year end\\nurgent")
        self.assertEqual(row["progress_pct"], "75.0%")
        self.assertEqual(row["unit"], "USD")
        self.assertEqual(row["is_active"], "True")

    def test_convert_goals_to_tsv_output(self):
        sample = [{"id": "g1", "title": "Goal 1", "current_value": 10, "target_value": 20}]
        tsv_text = convert_goals_to_tsv(json.dumps(sample))
        lines = tsv_text.strip().split("\n")
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], "\t".join(COLUMNS))
        fields = lines[1].split("\t")
        self.assertEqual(fields[0], "g1")
        self.assertEqual(fields[1], "Goal 1")
        self.assertEqual(fields[5], "50.0%")

    def test_path_traversal_rejection(self):
        with self.assertRaises(ValueError):
            convert_goals_to_tsv("[]", Path("out/../../hack.tsv"))

    def test_invalid_json_rejection(self):
        with self.assertRaises(ValueError):
            convert_goals_to_tsv("not-json")

    def test_atomic_file_write(self):
        sample = [{"id": "g-atom", "title": "Atomic"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "goals.tsv"
            convert_goals_to_tsv(json.dumps(sample), out_file)
            self.assertTrue(out_file.is_file())
            content = out_file.read_text(encoding="utf-8")
            self.assertIn("g-atom", content)
            self.assertFalse(out_file.with_suffix(".tsv.partial").exists())

    def test_cli_execution_file(self):
        sample = [{"id": "g-cli", "title": "CLI Goal"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            in_file = Path(tmpdir) / "goals.json"
            out_file = Path(tmpdir) / "goals.tsv"
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
