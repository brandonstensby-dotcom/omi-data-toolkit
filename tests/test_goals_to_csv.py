#!/usr/bin/env python3
"""
Unit tests for goals_to_csv converter.
"""

from __future__ import annotations

import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from goals_to_csv import compute_progress_pct, convert_goals_to_csv, main, parse_goals_payload


class TestGoalsToCSV(unittest.TestCase):

    def test_compute_progress_pct_numeric(self):
        self.assertEqual(compute_progress_pct(50, 100, "numeric"), "50.0%")
        self.assertEqual(compute_progress_pct(33.333, 100, "numeric"), "33.3%")
        self.assertEqual(compute_progress_pct(0, 50, "numeric"), "0.0%")

    def test_compute_progress_pct_boolean(self):
        self.assertEqual(compute_progress_pct(1.0, None, "boolean"), "100.0%")
        self.assertEqual(compute_progress_pct(0.0, None, "boolean"), "0.0%")

    def test_compute_progress_pct_edge_cases(self):
        self.assertEqual(compute_progress_pct(None, 100, "numeric"), "N/A")
        self.assertEqual(compute_progress_pct(10, None, "numeric"), "N/A")
        self.assertEqual(compute_progress_pct(5, 0, "numeric"), "100.0%")
        self.assertEqual(compute_progress_pct("invalid", 10, "numeric"), "N/A")

    def test_parse_goals_payload_formats(self):
        bare = [{"id": "g1", "title": "Run marathon"}]
        self.assertEqual(len(parse_goals_payload(bare)), 1)

        wrapped = {"goals": [{"id": "g2", "title": "Learn Rust"}]}
        self.assertEqual(len(parse_goals_payload(wrapped)), 1)

        items_wrap = {"items": [{"id": "g3", "title": "Save $5000"}]}
        self.assertEqual(len(parse_goals_payload(items_wrap)), 1)

        empty = {}
        self.assertEqual(len(parse_goals_payload(empty)), 0)

    def test_convert_goals_to_csv_output(self):
        sample = [
            {
                "id": "g101",
                "title": "Read 24 Books",
                "goal_type": "numeric",
                "current_value": 12,
                "target_value": 24,
                "unit": "books",
                "is_active": True,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-06-01T12:00:00Z",
            }
        ]
        csv_text = convert_goals_to_csv(json.dumps(sample))
        reader = list(csv.DictReader(io.StringIO(csv_text)))

        self.assertEqual(len(reader), 1)
        row = reader[0]
        self.assertEqual(row["id"], "g101")
        self.assertEqual(row["title"], "Read 24 Books")
        self.assertEqual(row["progress_pct"], "50.0%")
        self.assertEqual(row["unit"], "books")
        self.assertEqual(row["is_active"], "True")

    def test_path_traversal_rejection(self):
        with self.assertRaises(ValueError):
            convert_goals_to_csv("[]", Path("sub/../../escaped.csv"))

    def test_atomic_file_write(self):
        sample = [{"id": "g200", "title": "Finish Project", "is_active": True}]
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "output.csv"
            convert_goals_to_csv(json.dumps(sample), out_file)

            self.assertTrue(out_file.is_file())
            content = out_file.read_text(encoding="utf-8")
            self.assertIn("g200", content)
            self.assertIn("Finish Project", content)
            self.assertFalse(out_file.with_suffix(".csv.partial").exists())

    def test_invalid_json_rejection(self):
        with self.assertRaises(ValueError):
            convert_goals_to_csv("{not-valid-json}")

    def test_cli_execution_file(self):
        sample = [{"id": "g300", "title": "CLI Test"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            in_file = Path(tmpdir) / "input.json"
            out_file = Path(tmpdir) / "out.csv"
            in_file.write_text(json.dumps(sample), encoding="utf-8")

            exit_code = main([str(in_file), "-o", str(out_file)])
            self.assertEqual(exit_code, 0)
            self.assertTrue(out_file.is_file())
            self.assertIn("g300", out_file.read_text(encoding="utf-8"))

    def test_cli_missing_input_file(self):
        exit_code = main(["nonexistent_goals_file.json"])
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
