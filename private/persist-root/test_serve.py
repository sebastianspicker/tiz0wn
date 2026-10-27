#!/usr/bin/env python3
"""Contract tests for the serve/host-delivery half.

No TV, no foreign network: one loopback server on an ephemeral port that is
started and stopped inside the test, plus one end-to-end fetch that runs the
served body against a temporary fake root.
"""

from __future__ import annotations

import http.client
import shutil
import socket
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

import payload
import prelude
import serve

TOKEN = "0f1e2d3c4b5a6978"
HASH = (
    "$6$tiz0wnT3st$kgxSQ4GljhXxY8F6gC/swXU3W7H5xkZL2NCEMoXKwJb0KgmB5fUUObuJQo"
    "svlzbEjbnRY2x3HDOFkCFaZhsYt.1"
)


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


class ServeContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.body = serve.prepare_body(
            user="tiz0wn",
            password_hash=HASH,
            token=TOKEN,
            shell_host="",
            shell_port="",
            extra_args="",
        ).encode("ascii")
        cls.port = free_port()
        cls.server = serve.build_server(bind="127.0.0.1", port=cls.port, body=cls.body)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def fetch(self, path: str = "/d") -> tuple[int, bytes]:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        connection.request("GET", path)
        response = connection.getresponse()
        body = response.read()
        connection.close()
        return response.status, body

    def test_serves_exact_body(self):
        status, body = self.fetch()
        self.assertEqual(status, 200)
        self.assertEqual(body, self.body)

    def test_unknown_path_is_404(self):
        status, _ = self.fetch("/nope")
        self.assertEqual(status, 404)

    def test_body_has_no_unresolved_live_placeholders(self):
        """Placeholders may only survive inside the embedded hook template,
        which the applying script resolves itself with sed."""
        text = self.body.decode("ascii")
        marker = "<<'HOOK'\n"
        head, sep, hook = text.partition(marker)   # before vs. inside the template
        self.assertTrue(sep, "the embedded hook heredoc must be present")
        head_code = "\n".join(
            line for line in head.splitlines() if not line.lstrip().startswith("#")
        )
        for placeholder in ("@USER@", "@PWHASH@", "@TOKEN@", "@SHELL_HOST@", "@SHELL_PORT@"):
            self.assertNotIn(placeholder, head_code, f"{placeholder} left unresolved in the body head")
            self.assertIn(placeholder, hook, f"{placeholder} missing from the hook template")

    def test_served_body_is_valid_sh_and_silent(self):
        check = subprocess.run(["/bin/sh", "-n", "/dev/stdin"], input=self.body.decode("ascii"), capture_output=True, text=True, check=False)
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertIn("exec 1>&2", self.body.decode("ascii"))

    def test_served_body_applies_against_fake_root(self):
        with tempfile.TemporaryDirectory(prefix="tiz0wn-serve-") as temporary:
            sandbox = Path(temporary)
            for sub in ("etc", "opt/etc", "opt/usr/home/owner/share/tmp/sdk_tools", "tmp", "usr/bin"):
                (sandbox / sub).mkdir(parents=True, exist_ok=True)
            (sandbox / "etc" / "passwd").write_text("root:x:0:0:root:/root:/bin/sh\n", encoding="ascii")
            result = subprocess.run(
                ["/bin/sh", "/dev/stdin"],
                input=self.body.decode("ascii"),
                capture_output=True,
                text=True,
                check=False,
                env={
                    "PATH": "/usr/bin:/bin",
                    "TIZ0WN_ROOT": str(sandbox),
                    "TIZ0WN_ASSUME_ROOT": "1",
                },
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            passwd = (sandbox / "etc" / "passwd").read_text(encoding="ascii")
            self.assertTrue(passwd.startswith("tiz0wn:"), "the account must be prepended")
            self.assertIn("root:x:0:0:root:/root:/bin/sh", passwd, "existing lines must be preserved")


class ServeArgumentContracts(unittest.TestCase):
    def test_private_bind_enforced(self):
        self.assertEqual(serve.require_private_bind("192.168.8.138"), "192.168.8.138")
        for bad in ("8.8.8.8", "192.168.008.1", "localhost"):
            with self.subTest(bad=bad):
                with self.assertRaises(SystemExit):
                    serve.require_private_bind(bad)

    def test_token_shape(self):
        self.assertTrue(serve.token_shape(TOKEN))
        for bad in ("0F1E2D3C4B5A6978", "abc", TOKEN + "0"):
            with self.subTest(bad=bad):
                self.assertFalse(serve.token_shape(bad))

    def test_prepared_body_inlines_the_payload_grammar_check(self):
        body = serve.prepare_body(
            user="tiz0wn",
            password_hash=HASH,
            token=TOKEN,
            shell_host="192.168.8.138",
            shell_port="4444",
            extra_args="--revert",
        )
        self.assertIn("TIZ0WN_SHELL_HOST='192.168.8.138'", body)
        self.assertIn("TIZ0WN_ARGS='--revert'", body)
        # the payload builder agrees on the bound for the same host
        built = payload.build_pipe_password(host_ip="192.168.8.138", port=18080)
        self.assertLessEqual(built.password_length, payload.REVIEWED_BOUND)


if __name__ == "__main__":
    unittest.main(verbosity=2)
