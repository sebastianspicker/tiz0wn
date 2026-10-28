#!/usr/bin/env python3
"""Run the setup/revert cycle under a real busybox userland.

The TV is busybox, not GNU coreutils, and a flag that only exists in GNU
tooling is invisible to the host test suite. This drives the actual
``root_setup.sh`` through ``busybox ash`` in a throwaway container against a
fake TV root, and asserts the concrete outcomes that matter:

- apply creates exactly one account line with the right field count;
- a vendor shadow without a trailing newline is not merged;
- a re-apply with a new hash changes it;
- the hook self-heals a wiped passwd line;
- revert restores passwd and shadow byte-identically and leaves no backup.

Requires Docker (skipped otherwise). No TV, no SDB, no external network.

Run: ``python3 private/persist-root/repro/busybox_check.py``
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
SCRIPT = PACKAGE / "root_setup.sh"
IMAGE = "busybox:latest"
TOKEN = "0f1e2d3c4b5a6978"
HASH1 = "$6$aaa$bbb"
HASH2 = "$6$ccc$ddd"

HARNESS = r"""
#!/bin/sh
R=/tv
fail=0
check() { if [ "$2" = "$3" ]; then echo "[OK] $1"; else echo "[FAIL] $1: got '$2' want '$3'"; fail=1; fi; }

mkdir -p $R/etc $R/opt/etc $R/opt/usr/home/owner/share/tmp/sdk_tools $R/tmp $R/usr/bin
printf 'root:x:0:0:root:/root:/bin/sh\nowner:x:1000:1000:owner:/home/owner:/bin/sh\n' > $R/etc/passwd
printf 'root:*:19000:0:99999:7:::\nowner:$6$o$o:19100:0:99999:7:::' > $R/etc/shadow
cp $R/etc/passwd /tmp/passwd.before
cp $R/etc/shadow /tmp/shadow.before

export TIZ0WN_ROOT=$R TIZ0WN_ASSUME_ROOT=1 TIZ0WN_PWHASH="$1" TIZ0WN_TOKEN=$2 TIZ0WN_USER=tiz0wn

sh /w/root_setup.sh >/dev/null 2>&1
check "apply exit" "$?" "0"
check "one account line" "$(awk -F: '$1=="tiz0wn"' $R/etc/passwd | wc -l)" "1"
check "passwd field count" "$(awk -F: '$1=="tiz0wn"{print NF}' $R/etc/passwd)" "7"
check "shadow field count" "$(awk -F: '$1=="tiz0wn"{print NF}' $R/etc/shadow)" "9"
check "hook installed 0755" "$(ls -l $R/opt/etc/parseinfo.sh | cut -c1-10)" "-rwxr-xr-x"
check "vendor lines intact" "$(awk -F: 'END{print NR}' $R/etc/passwd)" "3"

TIZ0WN_PWHASH="$3" sh /w/root_setup.sh >/dev/null 2>&1
check "hash changed" "$(awk -F: '$1=="tiz0wn"{print $2}' $R/etc/shadow)" "$3"

awk -F: '$1!="tiz0wn"' $R/etc/passwd > $R/etc/p && mv $R/etc/p $R/etc/passwd
sh $R/opt/etc/parseinfo.sh >/dev/null 2>&1
check "hook self-heal" "$(awk -F: '$1=="tiz0wn"' $R/etc/passwd | wc -l)" "1"

sh /w/root_setup.sh --revert >/dev/null 2>&1
check "revert exit" "$?" "0"
cmp -s /tmp/passwd.before $R/etc/passwd && check "passwd byte-identical" ok ok || check "passwd byte-identical" differs same
cmp -s /tmp/shadow.before $R/etc/shadow && check "shadow byte-identical" ok ok || check "shadow byte-identical" differs same
check "no hook left" "$(ls $R/opt/etc | wc -l)" "0"
check "no backup left" "$(ls $R/etc | tr '\n' ' ')" "passwd shadow "

exit $fail
"""


def main() -> int:
    if not shutil.which("docker"):
        print("docker not found; skipping the busybox check")
        return 0
    if not SCRIPT.is_file():
        raise SystemExit(f"missing {SCRIPT}")
    with_path = subprocess.run(
        [
            "docker", "run", "--rm",
            "-v", f"{PACKAGE}:/w:ro",
            IMAGE, "sh", "-c", HARNESS, "sh", HASH1, TOKEN, HASH2,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    output = (with_path.stdout or "") + (with_path.stderr or "")
    print(output.rstrip())
    if with_path.returncode not in (0, 1):
        print(f"container failed ({with_path.returncode})")
        return 1
    passed = "[FAIL]" not in output
    print("busybox check passed" if passed else "busybox check FAILED")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
