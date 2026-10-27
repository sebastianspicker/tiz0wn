#!/usr/bin/env python3
"""Append-only, hash-chained work ledger for the persist-root package.

Schema (version 1), modeled on the tracked Remote PC/CIFS canary manifest:

- ``LEDGER.jsonl`` contains one canonical JSON document per line.
- Record 0 is the genesis record; ``previous_sha256`` is the SHA-256 of the
  canonical zero record (64 zeros).
- Every later record carries ``previous_sha256`` = SHA-256 of the exact raw
  bytes of the previous line, a monotonically increasing ``sequence``, an
  ``action`` from the allowlist, and free-form ``details``.
- Verification re-derives the whole chain; any edit, reorder, or extra record
  fails closed.

The ledger records operator actions and test outcomes. It never contains the
generated password payload, a password hash, or any TV identifier beyond the
pinned model/firmware strings.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEDGER = HERE / "LEDGER.jsonl"

SCHEMA = 1
ZERO_HASH = "0" * 64
MAX_BYTES = 262144
MAX_DETAIL_BYTES = 8192

ACTIONS = (
    "plan-saved",
    "package-created",
    "payload-implemented",
    "root-setup-implemented",
    "serve-implemented",
    "tests-written",
    "unittest-passed",
    "offline-repro-passed",
    "checklist-passed",
    "note",
)

RESERVED = {"schema", "sequence", "action", "previous_sha256", "timestamp"}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def canonical(document: dict) -> bytes:
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _read_records() -> list[tuple[bytes, dict]]:
    if not LEDGER.is_file():
        return []
    raw = LEDGER.read_bytes()
    if len(raw) > MAX_BYTES:
        raise SystemExit(f"ledger exceeds {MAX_BYTES} bytes")
    records: list[tuple[bytes, dict]] = []
    previous = ZERO_HASH
    for number, line in enumerate(raw.splitlines(), 1):
        if not line:
            raise SystemExit(f"ledger line {number}: blank line in append-only file")
        try:
            document = json.loads(line.decode("ascii"))
        except (UnicodeDecodeError, ValueError) as error:
            raise SystemExit(f"ledger line {number}: not canonical JSON") from error
        if document.get("schema") != SCHEMA:
            raise SystemExit(f"ledger line {number}: unexpected schema")
        if not isinstance(document.get("sequence"), int) or document["sequence"] != len(records):
            raise SystemExit(f"ledger line {number}: bad sequence")
        if document.get("action") not in ACTIONS:
            raise SystemExit(f"ledger line {number}: unknown action")
        if document.get("previous_sha256") != previous:
            raise SystemExit(f"ledger line {number}: broken hash chain")
        details = document.get("details")
        if not isinstance(details, dict):
            raise SystemExit(f"ledger line {number}: missing details")
        expected_detail_digest = hashlib.sha256(canonical(details)).hexdigest()
        if document.get("details_sha256") != expected_detail_digest:
            raise SystemExit(f"ledger line {number}: detail digest mismatch")
        records.append((line, document))
        previous = hashlib.sha256(line).hexdigest()
    return records


def append(action: str, **details: str) -> dict:
    if action not in ACTIONS:
        raise SystemExit(f"unknown ledger action: {action}")
    clash = RESERVED & set(details)
    if clash:
        raise SystemExit(f"reserved ledger detail keys: {sorted(clash)}")
    for key, value in details.items():
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key):
            raise SystemExit(f"detail key must be lower_snake_case: {key}")
        if len(value) > 512 or "`" in value or "$" in value:
            raise SystemExit(f"detail {key}: value must be plain text without shell syntax")
    detail_blob = json.dumps(details, sort_keys=True, separators=(",", ":"))
    if len(detail_blob) > MAX_DETAIL_BYTES:
        raise SystemExit("detail blob exceeds its bound")
    records = _read_records()
    payload = {
        "schema": SCHEMA,
        "sequence": len(records),
        "action": action,
        "previous_sha256": hashlib.sha256(records[-1][0]).hexdigest() if records else ZERO_HASH,
        "timestamp": _now(),
        "details": details,
        "details_sha256": hashlib.sha256(canonical(details)).hexdigest(),
    }
    raw = canonical(payload) + b"\n"
    with open(LEDGER, "ab" if LEDGER.exists() else "wb") as stream:
        stream.write(raw)
    print(f"ledger: appended {action} (sequence {payload['sequence']})")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="verify the chain and exit")
    parser.add_argument("--list", action="store_true", help="list allowed actions")
    parser.add_argument("action", nargs="?", help="action name")
    parser.add_argument("detail", nargs="*", help="KEY=VALUE detail entries")
    args = parser.parse_args()
    if args.list:
        for name in ACTIONS:
            print(name)
        return 0
    if args.verify:
        records = _read_records()
        print(f"ledger: {len(records)} records verified, chain intact")
        return 0
    if not args.action:
        parser.error("an action or --verify is required")
    details = {}
    for item in args.detail:
        if "=" not in item:
            raise SystemExit(f"detail must be KEY=VALUE: {item}")
        key, value = item.split("=", 1)
        details[key] = value
    append(args.action, **details)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
