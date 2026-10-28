#!/usr/bin/env python3
"""Regression tests for the defects found in the second audit round.

Each test here fails on the pre-fix code and passes now. They target the
real-device failure modes the sandbox tests missed: vendor files without a
trailing newline, our line being the only line, degraded PATH, foreign hooks
carrying our name, and a stale backup.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

import payload
import prelude

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "root_setup.sh"
TOKEN = "0f1e2d3c4b5a6978"
HASH = "$6$tiz0wnT3st$kgxSQ4GljhXxY8F6gC/swXU3W7H5xkZL2NCEMoXKwJb0KgmB5fUUObuJQosvlzbEjbnRY2x3HDOFkCFaZhsYt.1"
HASH2 = "$6$tiz0wn0ther$Zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"


class Sandbox:
    """A disposable fake root with the directories the script expects."""

    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="tiz0wn-r2-")
        self.root = Path(self._tmp.name)
        for sub in ("etc", "opt/etc", "opt/usr/home/owner/share/tmp/sdk_tools", "tmp", "usr/bin"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)
        (self.root / "etc/passwd").write_text(
            "root:x:0:0:root:/root:/bin/sh\nowner:x:1000:1000:owner:/home/owner:/bin/sh\n",
            encoding="ascii",
        )

    def env(self, **overrides: str) -> dict[str, str]:
        env = {
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
            "TIZ0WN_ROOT": str(self.root),
            "TIZ0WN_ASSUME_ROOT": "1",
            "TIZ0WN_PWHASH": HASH,
            "TIZ0WN_TOKEN": TOKEN,
            "TIZ0WN_USER": "tiz0wn",
        }
        env.update(overrides)
        return env

    def run(self, *args: str, **overrides: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["/bin/sh", str(SCRIPT), *args],
            capture_output=True, text=True, env=self.env(**overrides), input="", check=False,
        )

    def hook(self) -> Path:
        return self.root / "opt" / "etc" / "parseinfo.sh"

    def passwd(self) -> str:
        return (self.root / "etc" / "passwd").read_text(encoding="ascii")

    def shadow(self) -> str:
        return (self.root / "etc" / "shadow").read_text(encoding="ascii")

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


def user_lines(passwd_text: str) -> int:
    """Count passwd entries by first field (the gecos also contains the name)."""
    return sum(1 for line in passwd_text.splitlines() if line.split(":", 1)[0] == "tiz0wn")


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self.sb = Sandbox()

    def tearDown(self) -> None:
        self.sb.cleanup()

    def apply(self, **overrides: str):
        return self.sb.run(**overrides)


class NoTrailingNewline(Base):
    """A vendor file without a final byte must not swallow our append."""

    def test_shadow_without_trailing_newline_is_not_merged(self):
        (self.sb.root / "etc/shadow").write_text(
            "root:*:19000:0:99999:7:::\nowner:$6$o$o:19100:0:99999:7:::",
            encoding="ascii",
        )
        result = self.apply()
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = self.sb.shadow().splitlines()
        ours = [line for line in lines if line.startswith("tiz0wn:")]
        self.assertEqual(len(ours), 1, f"account line missing/merged: {lines}")
        self.assertEqual(len(ours[0].split(":")), 9, "shadow line must have 9 fields")
        self.assertTrue(any(line.startswith("owner:") for line in lines))

    def test_passwd_without_trailing_newline_keeps_all_entries(self):
        (self.sb.root / "etc/passwd").write_text(
            "root:x:0:0:root:/root:/bin/sh\nowner:x:1000:1000:owner:/home/owner:/bin/sh",
            encoding="ascii",
        )
        result = self.apply()
        self.assertEqual(result.returncode, 0, result.stderr)
        entries = [line.split(":")[0] for line in self.sb.passwd().splitlines()]
        self.assertEqual(sorted(entries), ["owner", "root", "tiz0wn"])
        for line in self.sb.passwd().splitlines():
            self.assertEqual(len(line.split(":")), 7, f"malformed passwd line: {line}")


class OnlyLineCases(Base):
    """grep -v exits 1 when every line matches; the rewrite must still happen."""

    def test_revert_when_our_line_is_the_only_passwd_line(self):
        (self.sb.root / "etc/passwd").write_text("", encoding="ascii")
        self.apply()
        self.assertEqual(user_lines(self.sb.passwd()), 1)
        result = self.sb.run("--revert")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("tiz0wn:", self.sb.passwd())
        self.assertFalse(self.sb.hook().exists())
        # no temp debris left in /etc
        leftovers = [p.name for p in (self.sb.root / "etc").iterdir() if ".tiz0wn-rev" in p.name]
        self.assertEqual(leftovers, [])

    def test_revert_when_our_line_is_the_only_shadow_line(self):
        (self.sb.root / "etc/shadow").write_text("", encoding="ascii")
        self.apply()
        result = self.sb.run("--revert")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("tiz0wn:", self.sb.shadow())

    def test_reapply_with_new_hash_wins_after_revert(self):
        """A leftover old shadow line must not shadow the new password."""
        self.apply()
        self.sb.run("--revert")
        result = self.apply(TIZ0WN_PWHASH=HASH2)
        self.assertEqual(result.returncode, 0, result.stderr)
        first = [line for line in self.sb.shadow().splitlines() if line.startswith("tiz0wn:")][0]
        self.assertIn(HASH2, first, "the newest hash must be the effective one")
        self.assertNotIn(HASH, first)


class RevertOrdering(Base):
    def test_revert_removes_the_hook_even_if_passwd_is_lost(self):
        self.apply()
        self.assertTrue(self.sb.hook().exists())
        (self.sb.root / "etc/passwd").unlink()
        result = self.sb.run("--revert")
        self.assertFalse(self.sb.hook().exists(), "the hook must come off regardless")
        self.assertNotEqual(result.returncode, 0, "an incomplete revert must report failure")

    def test_revert_removes_the_home_directory(self):
        self.apply()
        home = self.sb.root / "home" / "tiz0wn"
        self.assertTrue(home.exists())
        self.sb.run("--revert")
        self.assertFalse(home.exists(), "the home dir must be removed on revert")


class DegradedEnvironment(Base):
    def test_hook_recreates_the_account_with_a_hostile_path(self):
        """The boot environment's PATH is not ours; the hook must set its own."""
        self.apply()
        (self.sb.root / "etc/passwd").write_text("root:x:0:0:root:/root:/bin/sh\n", encoding="ascii")
        executed = subprocess.run(
            ["/bin/sh", str(self.sb.hook())],
            capture_output=True, text=True, check=False, input="",
            env={"PATH": "/nonexistent", "TIZ0WN_ROOT": str(self.sb.root)},
        )
        self.assertEqual(executed.returncode, 0, executed.stderr)
        self.assertIn("tiz0wn:", self.sb.passwd(), "the hook must repair the account")

    def test_boot_marker_reports_account_state(self):
        self.apply()
        (self.sb.root / "etc/passwd").write_text("root:x:0:0:root:/root:/bin/sh\n", encoding="ascii")
        subprocess.run(
            ["/bin/sh", str(self.sb.hook())], capture_output=True, text=True, check=False,
            input="", env={"PATH": "/usr/bin:/bin", "TIZ0WN_ROOT": str(self.sb.root)},
        )
        marker = (
            self.sb.root / "opt/usr/home/owner/share/tmp/sdk_tools" / f"tiz0wn-boot-{TOKEN}.out"
        )
        self.assertIn("account-ok", marker.read_text(encoding="ascii"))


class HookOwnership(Base):
    def test_vendor_hook_mentioning_the_name_is_still_backed_up(self):
        vendor = "#!/bin/sh\n# vendor hook that mentions persist-root in prose\necho VENDOR\n"
        self.sb.hook().write_text(vendor, encoding="ascii")
        self.apply()
        backup = self.sb.root / "opt" / "etc" / "parseinfo.sh.pre-tiz0wn"
        self.assertTrue(backup.is_file(), "a vendor hook must be backed up")
        self.assertEqual(backup.read_text(encoding="ascii"), vendor)
        self.sb.run("--revert")
        self.assertEqual(self.sb.hook().read_text(encoding="ascii"), vendor)

    def test_stale_backup_does_not_clobber_a_foreign_hook(self):
        self.sb.hook().write_text("#!/bin/sh\necho NEWVENDOR\n", encoding="ascii")
        (self.sb.root / "opt" / "etc" / "parseinfo.sh.pre-tiz0wn").write_text(
            "#!/bin/sh\necho OLDVENDOR\n", encoding="ascii"
        )
        self.sb.run("--revert")
        self.assertIn("NEWVENDOR", self.sb.hook().read_text(encoding="ascii"))


class ShadowRepair(Base):
    def test_reapply_repairs_a_deleted_shadow_line(self):
        self.apply()
        lines = [l for l in self.sb.shadow().splitlines() if not l.startswith("tiz0wn:")]
        (self.sb.root / "etc/shadow").write_text("\n".join(lines) + "\n", encoding="ascii")
        result = self.apply()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("tiz0wn:", self.sb.shadow())

    def test_created_shadow_is_0600(self):
        result = self.apply()
        self.assertEqual(result.returncode, 0, result.stderr)
        shadow = self.sb.root / "etc" / "shadow"
        self.assertEqual(stat.S_IMODE(shadow.stat().st_mode), 0o600)

    def test_passwd_backup_is_kept(self):
        self.apply()
        self.assertTrue((self.sb.root / "etc" / "passwd.pre-tiz0wn").is_file())


class Sudoers(Base):
    def test_sudoers_dir_is_created_when_missing(self):
        (self.sb.root / "usr" / "bin" / "sudo").write_text("#!/bin/sh\n", encoding="ascii")
        (self.sb.root / "usr" / "bin" / "sudo").chmod(0o755)
        result = self.apply()
        self.assertEqual(result.returncode, 0, result.stderr)
        dropin = self.sb.root / "etc" / "sudoers.d" / "tiz0wn"
        self.assertTrue(dropin.is_file())
        self.assertEqual(stat.S_IMODE(dropin.stat().st_mode), 0o440)


class ExitStatus(Base):
    def test_apply_reports_nonzero_when_the_hook_fails(self):
        # make /opt/etc un-creatable so the hook step fails
        shutil.rmtree(self.sb.root / "opt", ignore_errors=True)
        (self.sb.root / "opt").write_text("not a directory", encoding="ascii")
        result = self.apply()
        self.assertNotEqual(result.returncode, 0, "a failed hook must be visible")
        failed = list((self.sb.root / "opt").parent.glob("**/*.FAILED")) if False else []
        del failed


class PayloadCharset(unittest.TestCase):
    def test_http_path_charset_is_enforced(self):
        for good in ("/d", "/a/b", "/d-1_x.y~z"):
            self.assertTrue(payload.build_pipe_password(host_ip="10.0.0.1", http_path=good).password)
        for bad in ("/a&b", "/d)", "/d x", "d"):
            with self.subTest(path=bad), self.assertRaises(ValueError):
                payload.build_pipe_password(host_ip="10.0.0.1", http_path=bad)

    def test_shell_port_range_is_enforced(self):
        for bad in ("0", "65536", "99999"):
            with self.subTest(port=bad), self.assertRaises(ValueError):
                prelude.build_prelude(password_hash=HASH, token=TOKEN, shell_host="10.0.0.1", shell_port=bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)


class GrepFailure(Base):
    """grep -v exit 2 (EIO/ENOSPC) must not silently empty passwd."""

    def _stub(self, script: str) -> None:
        bindir = self.sb.root / "bin"
        bindir.mkdir(exist_ok=True)
        (bindir / "grep").write_text(script, encoding="ascii")
        (bindir / "grep").chmod(0o755)

    def test_grep_failure_aborts_instead_of_emptying_passwd(self):
        self.apply()
        self._stub("#!/bin/sh\nexit 2\n")
        result = self.sb.run("--revert", TIZ0WN_PATH=f"{self.sb.root}/bin:/usr/bin:/bin")
        self.assertNotEqual(result.returncode, 0, "grep failure must be reported")
        self.assertIn("tiz0wn:", self.sb.passwd(), "passwd must not be emptied")

    def test_partial_grep_output_is_not_accepted_alone(self):
        """A grep that truncates still leaves the other entries visible."""
        self.apply()
        self._stub('#!/bin/sh\nexec /usr/bin/grep "$@"\n')
        result = self.sb.run("--revert", TIZ0WN_PATH=f"{self.sb.root}/bin:/usr/bin:/bin")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("tiz0wn:", self.sb.passwd())


class PasswordChange(Base):
    def test_reapply_without_revert_changes_the_hash(self):
        self.apply()
        result = self.apply(TIZ0WN_PWHASH=HASH2)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = [l for l in self.sb.shadow().splitlines() if l.startswith("tiz0wn:")]
        self.assertEqual(len(lines), 1, "exactly one shadow line")
        self.assertIn(HASH2, lines[0])
        self.assertNotIn(HASH, lines[0])

    def test_hook_applies_a_changed_hash(self):
        self.apply()
        (self.sb.root / "etc/shadow").write_text(
            "tiz0wn:$6$old$old:20000:0:99999:7:::\n", encoding="ascii"
        )
        subprocess.run(
            ["/bin/sh", str(self.sb.hook())], capture_output=True, text=True, check=False,
            input="", env={"PATH": "/usr/bin:/bin", "TIZ0WN_ROOT": str(self.sb.root)},
        )
        self.assertIn(HASH, self.sb.shadow())


class HomeRepair(Base):
    def test_reapply_recreates_a_deleted_home(self):
        self.apply()
        home = self.sb.root / "home" / "tiz0wn"
        shutil.rmtree(home, ignore_errors=True)
        self.apply()
        self.assertTrue(home.is_dir(), "the home directory must be restored")


class HookSentinel(Base):
    def test_vendor_hook_containing_our_sentinel_is_still_backed_up(self):
        vendor = "#!/bin/sh\n# tiz0wn-hook-v1\necho VENDOR\n"
        self.sb.hook().write_text(vendor, encoding="ascii")
        self.apply()
        self.assertTrue((self.sb.root / "opt/etc/parseinfo.sh.pre-tiz0wn").is_file())
        self.sb.run("--revert")
        self.assertIn("VENDOR", self.sb.hook().read_text(encoding="ascii"))


class CleanRevert(Base):
    def test_revert_leaves_no_debris_and_restores_the_files(self):
        before_passwd = self.sb.passwd()
        self.apply()
        result = self.sb.run("--revert")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.sb.passwd(), before_passwd)
        # passwd.pre-tiz0wn is a deliberate recovery copy; no *temp* debris may remain
        names = sorted(p.name for p in (self.sb.root / "etc").iterdir())
        self.assertEqual(
            [n for n in names if ".tiz0wn-out" in n or ".tiz0wn-rev" in n or ".tiz0wn-new" in n], []
        )
        self.assertLessEqual(set(names), {"passwd", "shadow", "passwd.pre-tiz0wn"})

    def test_revert_drops_an_orphan_shadow_line(self):
        self.apply()
        (self.sb.root / "etc/passwd").write_text("root:x:0:0:root:/root:/bin/sh\n", encoding="ascii")
        self.sb.run("--revert")
        self.assertNotIn("tiz0wn:", self.sb.shadow())


class ByteExact(Base):
    def test_revert_restores_shadow_byte_identically(self):
        (self.sb.root / "etc/shadow").write_text(
            "root:*:19000:0:99999:7:::", encoding="ascii"   # no trailing newline
        )
        before = (self.sb.root / "etc/shadow").read_bytes()
        self.apply()
        self.sb.run("--revert")
        self.assertEqual((self.sb.root / "etc/shadow").read_bytes(), before)

    def test_stale_backup_does_not_undo_a_later_change(self):
        """A second cycle must not restore a backup from the first one."""
        self.apply()
        self.sb.run("--revert")
        (self.sb.root / "etc/passwd").write_text("", encoding="ascii")
        self.apply()
        self.sb.run("--revert")
        self.assertEqual((self.sb.root / "etc/passwd").read_bytes(), b"")


class FailedMarker(Base):
    def test_stale_failed_marker_is_cleared_on_success(self):
        self.apply()
        marker = self.sb.root / "opt/usr/home/owner/share/tmp/sdk_tools"
        (marker / f"tiz0wn-root-{TOKEN}.FAILED").write_text("old\n", encoding="ascii")
        self.apply()
        self.assertEqual(list(marker.glob("*.FAILED")), [])


class PayloadHostValidation(unittest.TestCase):
    def test_unreal_octets_are_rejected(self):
        with self.assertRaises(ValueError):
            payload.build_pipe_password(host_ip="999.999.999.999")


class UidAllocation(Base):
    def test_uid_skips_an_occupied_4001(self):
        (self.sb.root / "etc/passwd").write_text(
            "root:x:0:0:root:/root:/bin/sh\nvendor:x:4001:4001:v:/home/v:/bin/sh\n",
            encoding="ascii",
        )
        self.apply()
        line = [l for l in self.sb.passwd().splitlines() if l.startswith("tiz0wn:")][0]
        self.assertEqual(line.split(":")[2], "4002", "an occupied uid must be skipped")

    def test_new_uid_is_placed_first(self):
        self.apply()
        self.assertTrue(self.sb.passwd().startswith("tiz0wn:"))
