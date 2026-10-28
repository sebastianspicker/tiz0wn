#!/usr/bin/env python3
"""Build a distributable tarball of the persist-root exploit package.

Refuses to build unless the offline gate is green, then packs only the
reviewed files (no caches, no run evidence, no lock) plus a MANIFEST.sha256
over the exact bytes, so a recipient can verify what they received.

    python3 private/persist-root/pack.py            # -> dist/persist-root-<ver>.tar.gz
    python3 private/persist-root/pack.py --skip-check

`--skip-check` is for a quick look only; a release should always be verified.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import tarfile
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIST = HERE / "dist"
VERSION = "1.0.0"

# Exact allowlist. Anything not listed cannot leak into the package.
FILES = (
    "README.md",
    "HANDOFF-SAMSUNG.md",
    "PLAN.md",
    "payload.py",
    "prelude.py",
    "sha512crypt.py",
    "serve.py",
    "root_setup.sh",
    "ledger.py",
    "LEDGER.jsonl",
    "LEDGER.head",
    "Makefile",
    "test_persist_root.py",
    "test_regressions.py",
    "test_serve.py",
    "test_sha512crypt.py",
    "test_ledger.py",
    "repro/mount.smb.sh",
    "repro/run_offline.py",
    "repro/busybox_check.py",
    "repro/proof_run.py",
    "repro/smbpath_payload.py",
    ".gitignore",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-check", action="store_true")
    args = parser.parse_args()

    missing = [name for name in FILES if not (HERE / name).is_file()]
    if missing:
        raise SystemExit(f"missing package files: {missing}")

    if not args.skip_check:
        print("running make check (offline; nothing contacts the TV)…")
        gate = subprocess.run(["make", "-C", str(HERE), "check"], capture_output=True, text=True)
        if gate.returncode != 0:
            print(gate.stdout[-3000:], gate.stderr[-3000:])
            raise SystemExit("make check failed; refusing to package")
        print("gate green")

    DIST.mkdir(exist_ok=True)
    target = DIST / f"persist-root-{VERSION}.tar.gz"
    stem = f"persist-root-{VERSION}"

    with tempfile.TemporaryDirectory(prefix="persist-root-pack-") as temporary:
        staging = Path(temporary) / stem
        for name in FILES:
            destination = staging / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((HERE / name).read_bytes())
        manifest = "".join(
            f"{sha256(staging / name)}  {name}\n" for name in FILES
        )
        (staging / "MANIFEST.sha256").write_text(manifest, encoding="ascii")

        with tarfile.open(target, "w:gz") as archive:
            archive.add(staging, arcname=stem)

    print(f"wrote {target}")
    print(f"  files:    {len(FILES)} + MANIFEST.sha256")
    print(f"  sha256:   {sha256(target)}")
    print(f"  size:     {target.stat().st_size} bytes")
    print("\nverify a copy with:  shasum -a 256 <file>   then   tar tzf <file>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
