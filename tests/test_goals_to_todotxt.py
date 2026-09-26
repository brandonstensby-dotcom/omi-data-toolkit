#!/usr/bin/env python3
"""
Unit tests for goals_to_todotxt converter.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from goals_to_todotxt import (
    compute_progress_pct,
    convert_goals_to_todotxt,
    format_goal_todotxt_line,
    main,
    parse_goals_payload,
    sanitize_text,
)


class TestGoalsToTodoTxt(unittest.TestCase):

    def test_sanitize_text(self):
        self.assertEqual(sanitize_text("line1\nline2\r\nline3"), "line1 line2 line3")
        self.assertEqual(sanitize_text("   clean text   "), "clean text")

    def test_format_goal_active(self):
        goal = {
            "id": "g-101",
            "title": "Build Micro-VM",
            "goal_type": "numeric",
            "current_value": 75,
            "target_value": 100,
            "is_active": True,
            "created_at": "2026-03-01T08:00:00Z",
        }
        line = format_goal_todotxt_line(goal)
        self.assertTrue(line.startswith("(A) 2026-03-01 Build Micro-VM +OmiGoal @milestone"))
        self.assertIn("id:g-101", line)
        self.assertIn("progress:75%", line)

    def test_format_goal_completed(self):
        goal = {
            "id": "g-202",
            "title": "Pass Audit",
            "goal_type": "boolean",
            "current_value": 1.0,
            "target_value": 1.0,
            "is_active": True,
            "created_at": "2026-02-01",
            "updated_at": "2026-02-15",
        }
        line = format_goal_todotxt_line(goal)
        self.assertTrue(line.startswith("x 2026-02-15 Pass Audit +OmiGoal @milestone"))
        self.assertIn("progress:100%", line)

    def test_format_goal_paused(self):
        goal = {
            "id": "g-303",
            "title": "Learn Guitar",
            "is_active": False,
            "created_at": "2026-01-01",
        }
        line = format_goal_todotxt_line(goal)
        self.assertTrue(line.startswith("(C) 2026-01-01 Learn Guitar"))
        self.assertIn("status:paused", line)

    def test_convert_goals_to_todotxt_output(self):
        sample = [
            {"id": "g1", "title": "Goal One", "is_active": True, "created_at": "2026-01-01"},
            {"id": "g2", "title": "Goal Two", "is_active": True, "created_at": "2026-01-02"},
        ]
        text = convert_goals_to_todotxt(json.dumps(sample))
        lines = [l for l in text.strip().split("\n") if l]
        self.assertEqual(len(lines), 2)
        self.assertIn("Goal One", lines[0])
        self.assertIn("Goal Two", lines[1])

    def test_path_traversal_rejection(self):
        with self.assertRaises(ValueError):
            convert_goals_to_todotxt("[]", Path("out/../../blocked.txt"))

    def test_invalid_json_rejection(self):
        with self.assertRaises(ValueError):
            convert_goals_to_todotxt("not json")

    def test_atomic_file_write(self):
        sample = [{"id": "g-atom", "title": "Atomic check", "is_active": True}]
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "todo.txt"
            convert_goals_to_todotxt(json.dumps(sample), out_file)
            self.assertTrue(out_file.is_file())
            content = out_file.read_text(encoding="utf-8")
            self.assertIn("Atomic check", content)
            self.assertFalse(out_file.with_suffix(".txt.partial").exists())

    def test_cli_execution_file(self):
        sample = [{"id": "g-cli", "title": "CLI goal", "is_active": True}]
        with tempfile.TemporaryDirectory() as tmpdir:
            in_file = Path(tmpdir) / "in.json"
            out_file = Path(tmpdir) / "out.txt"
            in_file.write_text(json.dumps(sample), encoding="utf-8")

            exit_code = main([str(in_file), "-o", str(out_file)])
            self.assertEqual(exit_code, 0)
            self.assertTrue(out_file.is_file())
            content = out_file.read_text(encoding="utf-8")
            self.assertIn("CLI goal", content)

    def test_cli_missing_input(self):
        exit_code = main(["nonexistent_file.json"])
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
