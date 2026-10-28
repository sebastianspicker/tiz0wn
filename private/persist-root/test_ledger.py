#!/usr/bin/env python3
"""Contract tests for the hash-chained work ledger (append-only integrity)."""

from __future__ import annotations

import json
import unittest

import ledger


class LedgerContracts(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path

        self._tmp = tempfile.TemporaryDirectory(prefix="tiz0wn-ledger-")
        self.path = Path(self._tmp.name) / "LEDGER.jsonl"
        self.head = Path(self._tmp.name) / "LEDGER.head"
        self._previous = ledger.LEDGER
        self._previous_head = ledger.HEAD_FILE
        ledger.LEDGER = self.path
        ledger.HEAD_FILE = self.head

    def tearDown(self):
        import shutil

        ledger.LEDGER = self._previous
        ledger.HEAD_FILE = self._previous_head
        shutil.rmtree(self._tmp.name, ignore_errors=True)

    def test_genesis_record_chains_from_zero(self):
        ledger.append("note", message="first")
        records = ledger._read_records()
        self.assertEqual(len(records), 1)
        record = records[0][1]
        self.assertEqual(record["previous_sha256"], ledger.ZERO_HASH)
        self.assertEqual(record["sequence"], 0)

    def test_chain_links_records(self):
        ledger.append("note", message="one")
        ledger.append("note", message="two")
        first_raw, _ = ledger._read_records()[0]
        second = ledger._read_records()[1][1]
        self.assertEqual(second["previous_sha256"], __import__("hashlib").sha256(first_raw).hexdigest())
        self.assertEqual(second["sequence"], 1)

    def test_verification_passes_on_intact_file(self):
        ledger.append("note", message="ok")
        ledger._read_records()  # must not raise

    def test_detects_edited_record(self):
        ledger.append("note", message="original")
        raw = self.path.read_text(encoding="ascii")
        self.path.write_text(raw.replace("original", "tampered"), encoding="ascii")
        with self.assertRaises(SystemExit):
            ledger._read_records()

    def test_detects_reordered_records(self):
        ledger.append("note", message="one")
        ledger.append("note", message="two")
        lines = self.path.read_text(encoding="ascii").splitlines(keepends=True)
        self.path.write_text("".join(reversed(lines)), encoding="ascii")
        with self.assertRaises(SystemExit):
            ledger._read_records()

    def test_rejects_unknown_action_and_reserved_key(self):
        with self.assertRaises(SystemExit):
            ledger.append("mystery")
        with self.assertRaises(SystemExit):
            ledger.append("note", sequence="7")

    def test_rejects_shell_syntax_in_details(self):
        with self.assertRaises(SystemExit):
            ledger.append("note", bad="a$b")
        with self.assertRaises(SystemExit):
            ledger.append("note", bad="a`b")

    def test_head_anchor_detects_a_full_chain_rewrite(self):
        """A rewrite that recomputes every link still fails the sealed anchor."""
        import hashlib

        ledger.append("note", message="original")
        ledger.seal()
        # rewrite the record and recompute the chain properly
        line = self.path.read_text(encoding="ascii").strip()
        document = json.loads(line)
        document["details"] = {"message": "rewritten"}
        document["details_sha256"] = hashlib.sha256(
            ledger.canonical(document["details"])
        ).hexdigest()
        self.path.write_text(ledger.canonical(document).decode("ascii") + "\n", encoding="ascii")
        ledger._read_records()  # the chain itself is still self-consistent
        with self.assertRaises(SystemExit):
            ledger.verify()

    def test_seal_refuses_to_overwrite_without_force(self):
        ledger.append("note", message="one")
        ledger.seal()
        ledger.append("note", message="two")
        with self.assertRaises(SystemExit):
            ledger.seal()
        ledger.seal(force=True)
        ledger.verify()

    def test_append_recovers_from_a_missing_trailing_newline(self):
        ledger.append("note", message="one")
        data = self.path.read_bytes().rstrip(b"\n")
        self.path.write_bytes(data)          # simulate a stripped final newline
        ledger.append("note", message="two")
        self.assertEqual(len(ledger._read_records()), 2)

    def test_seal_then_intact_file_verifies(self):
        ledger.append("note", message="ok")
        ledger.seal()
        ledger.verify()

    def test_records_are_canonical_json_lines(self):
        ledger.append("note", message="x")
        line = self.path.read_text(encoding="ascii").strip()
        self.assertEqual(line, json.dumps(json.loads(line), sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
