#!/usr/bin/env python3
"""
Unit tests for goals_to_digest converter.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from goals_to_digest import (
    build_goals_digest,
    compute_progress_pct,
    convert_goals_to_digest,
    main,
    parse_goals_payload,
    render_progress_bar,
)


class TestGoalsToDigest(unittest.TestCase):

    def test_empty_goals(self):
        digest = build_goals_digest([])
        self.assertIn("No goals found", digest)

    def test_progress_bar_rendering(self):
        self.assertEqual(render_progress_bar(None), "[···············] N/A")
        bar_100 = render_progress_bar(100.0, width=10)
        self.assertEqual(bar_100, "[██████████] 100.0%")
        bar_50 = render_progress_bar(50.0, width=10)
        self.assertEqual(bar_50, "[█████░░░░░] 50.0%")
        bar_0 = render_progress_bar(0.0, width=10)
        self.assertEqual(bar_0, "[░░░░░░░░░░] 0.0%")

    def test_compute_progress_pct(self):
        self.assertEqual(compute_progress_pct(10, 20, "numeric"), 50.0)
        self.assertEqual(compute_progress_pct(1.0, None, "boolean"), 100.0)
        self.assertEqual(compute_progress_pct(None, 20, "numeric"), None)
        self.assertEqual(compute_progress_pct(5, 0, "numeric"), 100.0)

    def test_build_digest_sections(self):
        goals = [
            {"id": "g1", "title": "Run 50km", "goal_type": "numeric", "current_value": 25, "target_value": 50, "unit": "km", "is_active": True},
            {"id": "g2", "title": "Ship MVP", "goal_type": "boolean", "current_value": 1.0, "target_value": 1.0, "is_active": True},
            {"id": "g3", "title": "Learn Latin", "goal_type": "qualitative", "is_active": False},
        ]
        digest = build_goals_digest(goals, title="Quarterly Targets")

        self.assertIn("# Quarterly Targets", digest)
        self.assertIn("| **Total Goals** | 3 |", digest)
        self.assertIn("| **In Progress** | 1 |", digest)
        self.assertIn("| **Achieved / Completed** | 1 |", digest)
        self.assertIn("| **Inactive / Paused** | 1 |", digest)
        self.assertIn("### Run 50km (25 / 50 km)", digest)
        self.assertIn("- [x] **Ship MVP**", digest)
        self.assertIn("- [ ] *Learn Latin* (Paused)", digest)

    def test_path_traversal_rejection(self):
        with self.assertRaises(ValueError):
            convert_goals_to_digest("[]", Path("out/../../blocked.md"))

    def test_invalid_json_rejection(self):
        with self.assertRaises(ValueError):
            convert_goals_to_digest("malformed json")

    def test_atomic_file_write(self):
        sample = [{"id": "g-atom", "title": "Atomic check", "is_active": True}]
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "goals.md"
            convert_goals_to_digest(json.dumps(sample), out_file)
            self.assertTrue(out_file.is_file())
            content = out_file.read_text(encoding="utf-8")
            self.assertIn("Atomic check", content)
            self.assertFalse(out_file.with_suffix(".md.partial").exists())

    def test_cli_execution_file(self):
        sample = [{"id": "g-cli", "title": "CLI goal", "is_active": True}]
        with tempfile.TemporaryDirectory() as tmpdir:
            in_file = Path(tmpdir) / "in.json"
            out_file = Path(tmpdir) / "out.md"
            in_file.write_text(json.dumps(sample), encoding="utf-8")

            exit_code = main([str(in_file), "-o", str(out_file), "--title", "CLI Goals Digest"])
            self.assertEqual(exit_code, 0)
            self.assertTrue(out_file.is_file())
            content = out_file.read_text(encoding="utf-8")
            self.assertIn("# CLI Goals Digest", content)

    def test_cli_missing_input(self):
        exit_code = main(["nonexistent_goals_file.json"])
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
