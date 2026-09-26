#!/usr/bin/env python3
"""
Unit tests for action_items_to_digest converter.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from action_items_to_digest import (
    build_task_digest,
    convert_action_items_to_digest,
    main,
    parse_action_items_payload,
)


class TestActionItemsToDigest(unittest.TestCase):

    def test_empty_action_items(self):
        digest = build_task_digest([])
        self.assertIn("No action items found", digest)

    def test_parse_formats(self):
        bare = [{"id": "a1", "description": "test"}]
        self.assertEqual(len(parse_action_items_payload(bare)), 1)
        wrapped = {"action_items": [{"id": "a2"}]}
        self.assertEqual(len(parse_action_items_payload(wrapped)), 1)

    def test_digest_categorization_and_overdue(self):
        ref_dt = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        items = [
            {"id": "1", "description": "Overdue task", "completed": False, "due_at": "2026-05-15T00:00:00Z"},
            {"id": "2", "description": "Future task", "completed": False, "due_at": "2026-06-15T00:00:00Z"},
            {"id": "3", "description": "Undated task", "completed": False, "due_at": None},
            {"id": "4", "description": "Done task", "completed": True, "completed_at": "2026-05-30T10:00:00Z"},
        ]
        digest = build_task_digest(items, title="Weekly Review", reference_dt=ref_dt)

        self.assertIn("# Weekly Review", digest)
        self.assertIn("| **Total Action Items** | 4 |", digest)
        self.assertIn("| **Completed Tasks** | 1 (25.0%) |", digest)
        self.assertIn("| **Pending Tasks** | 3 |", digest)
        self.assertIn("- [ ] **[Due: 2026-05-15]** Overdue task *(OVERDUE)*", digest)
        self.assertIn("- [ ] **[Due: 2026-06-15]** Future task", digest)
        self.assertNotIn("Future task *(OVERDUE)*", digest)
        self.assertIn("- [ ] Undated task", digest)
        self.assertIn("- [x] Done task *(Completed: 2026-05-30)*", digest)

    def test_path_traversal_rejection(self):
        with self.assertRaises(ValueError):
            convert_action_items_to_digest("[]", Path("out/../../blocked.md"))

    def test_invalid_json_rejection(self):
        with self.assertRaises(ValueError):
            convert_action_items_to_digest("malformed")

    def test_atomic_file_write(self):
        sample = [{"id": "act-atom", "description": "Atomic check", "completed": False}]
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "tasks.md"
            convert_action_items_to_digest(json.dumps(sample), out_file)
            self.assertTrue(out_file.is_file())
            content = out_file.read_text(encoding="utf-8")
            self.assertIn("Atomic check", content)
            self.assertFalse(out_file.with_suffix(".md.partial").exists())

    def test_cli_execution_file(self):
        sample = [{"id": "act-cli", "description": "CLI task", "completed": True}]
        with tempfile.TemporaryDirectory() as tmpdir:
            in_file = Path(tmpdir) / "in.json"
            out_file = Path(tmpdir) / "out.md"
            in_file.write_text(json.dumps(sample), encoding="utf-8")

            exit_code = main([str(in_file), "-o", str(out_file), "--title", "CLI Task Digest"])
            self.assertEqual(exit_code, 0)
            self.assertTrue(out_file.is_file())
            content = out_file.read_text(encoding="utf-8")
            self.assertIn("# CLI Task Digest", content)
            self.assertIn("- [x] CLI task", content)

    def test_cli_missing_input(self):
        exit_code = main(["nonexistent_file.json"])
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
