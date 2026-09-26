#!/usr/bin/env python3
"""
Unit tests for memories_to_digest converter.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from memories_to_digest import (
    build_markdown_digest,
    convert_memories_to_digest,
    main,
    parse_memories_payload,
)


class TestMemoriesToDigest(unittest.TestCase):

    def test_empty_memories(self):
        digest = build_markdown_digest([])
        self.assertIn("No memories found", digest)

    def test_parse_memories_formats(self):
        bare = [{"id": "m1", "content": "Sample"}]
        self.assertEqual(len(parse_memories_payload(bare)), 1)
        wrapped = {"memories": [{"id": "m2"}]}
        self.assertEqual(len(parse_memories_payload(wrapped)), 1)

    def test_digest_grouping_and_metrics(self):
        memories = [
            {"id": "m1", "category": "Work", "content": "Review proposal", "created_at": "2026-03-01T10:00:00Z"},
            {"id": "m2", "category": "Work", "content": "Team sync", "created_at": "2026-03-02T10:00:00Z"},
            {"id": "m3", "category": "Personal", "content": "Buy running shoes", "created_at": "2026-03-03T10:00:00Z"},
        ]
        digest = build_markdown_digest(memories, title="Test Digest")
        self.assertIn("# Test Digest", digest)
        self.assertIn("**Total Memories:** 3", digest)
        self.assertIn("| Work | 2 | 66.7% |", digest)
        self.assertIn("| Personal | 1 | 33.3% |", digest)
        self.assertIn("### Work (2)", digest)
        self.assertIn("1. Review proposal *(2026-03-01)*", digest)
        self.assertIn("2. Team sync *(2026-03-02)*", digest)
        self.assertIn("### Personal (1)", digest)
        self.assertIn("1. Buy running shoes *(2026-03-03)*", digest)

    def test_path_traversal_rejection(self):
        with self.assertRaises(ValueError):
            convert_memories_to_digest("[]", Path("out/../../blocked.md"))

    def test_invalid_json_rejection(self):
        with self.assertRaises(ValueError):
            convert_memories_to_digest("malformed json")

    def test_atomic_file_write(self):
        sample = [{"id": "m-atom", "content": "Atomic check", "category": "General"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "digest.md"
            convert_memories_to_digest(json.dumps(sample), out_file)
            self.assertTrue(out_file.is_file())
            content = out_file.read_text(encoding="utf-8")
            self.assertIn("Atomic check", content)
            self.assertFalse(out_file.with_suffix(".md.partial").exists())

    def test_cli_execution_file(self):
        sample = [{"id": "m-cli", "content": "CLI memory", "category": "Code"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            in_file = Path(tmpdir) / "in.json"
            out_file = Path(tmpdir) / "out.md"
            in_file.write_text(json.dumps(sample), encoding="utf-8")

            exit_code = main([str(in_file), "-o", str(out_file), "--title", "CLI Digest"])
            self.assertEqual(exit_code, 0)
            self.assertTrue(out_file.is_file())
            content = out_file.read_text(encoding="utf-8")
            self.assertIn("# CLI Digest", content)
            self.assertIn("CLI memory", content)

    def test_cli_missing_input(self):
        exit_code = main(["nonexistent_file.json"])
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
