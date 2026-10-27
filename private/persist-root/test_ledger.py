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
        self._previous = ledger.LEDGER
        ledger.LEDGER = self.path

    def tearDown(self):
        import shutil

        ledger.LEDGER = self._previous
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

    def test_records_are_canonical_json_lines(self):
        ledger.append("note", message="x")
        line = self.path.read_text(encoding="ascii").strip()
        self.assertEqual(line, json.dumps(json.loads(line), sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
