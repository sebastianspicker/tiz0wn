"""Synthetic CI security controls. No firmware image, TV or live tool is used."""
from __future__ import annotations

import importlib.util
import os
import socket
import stat
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "exploits/tiz0wn-root"
sys.path.insert(0, str(PACKAGE / "builder"))
from private_io import write_private  # noqa: E402
from sha512crypt import hash_password  # noqa: E402

spec = importlib.util.spec_from_file_location("callback_receiver", PACKAGE / "live/listen.py")
receiver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(receiver)


class SecurityChecks(unittest.TestCase):
    def test_crypt_target_compatibility(self):
        expected = "$6$saltstring$svn8UoSVapNtMuq1ukKS4tPQd8iKwSMHWjl/O817G3uBnIFNjnQJuesI68u4OTLiBFdcbYEdFCoEOfaS35inz1"
        self.assertEqual(hash_password("Hello world!", salt="saltstring"), expected)
        with self.assertRaises(ValueError):
            hash_password("example", rounds=5001)

    def test_sensitive_artifact_is_private_and_does_not_follow_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "original"
            original.write_bytes(b"unchanged")
            output = root / "shadow.window"
            output.symlink_to(original)
            old_mask = os.umask(0)
            try:
                write_private(output, b"synthetic shadow bytes")
            finally:
                os.umask(old_mask)
            self.assertEqual(original.read_bytes(), b"unchanged")
            self.assertEqual(output.read_bytes(), b"synthetic shadow bytes")
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            self.assertFalse(list(root.glob(".tiz0wn-private-*")))

    def callback(self, data, *, peer="127.0.0.1", maximum=64, trickle=False):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name) / "result"
        output.write_bytes(b"previous complete output")
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        failures = []
        def receive():
            try:
                receiver.receive(port, output, "127.0.0.1", peer, max_bytes=maximum,
                                 accept_timeout=0.4, idle_timeout=0.2, total_timeout=0.8)
            except (OSError, ValueError) as error:
                failures.append(error)
        worker = threading.Thread(target=receive)
        worker.start()
        self.addCleanup(worker.join, 2)
        deadline = time.monotonic() + 0.5
        while True:
            try:
                connection = socket.create_connection(("127.0.0.1", port), timeout=0.1)
                break
            except ConnectionRefusedError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.01)
        with connection:
            try:
                if trickle:
                    for _ in range(40):
                        connection.sendall(b"x")
                        time.sleep(0.04)
                else:
                    connection.sendall(data)
            except (ConnectionResetError, BrokenPipeError):
                pass
        worker.join(2)
        self.assertFalse(worker.is_alive())
        self.assertFalse(list(output.parent.glob(".tiz0wn-private-*")))
        return output, failures

    def test_expected_callback_preserves_bytes_and_private_mode(self):
        output, failures = self.callback(b"c3ludGhldGljCg==")
        self.assertFalse(failures)
        self.assertEqual(output.read_bytes(), b"c3ludGhldGljCg==")
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)

    def test_wrong_peer_and_oversized_callbacks_do_not_replace_output(self):
        for data, peer, limit in [(b"unexpected", "127.0.0.2", 64), (b"x" * 65, "127.0.0.1", 64)]:
            output, failures = self.callback(data, peer=peer, maximum=limit)
            self.assertTrue(failures)
            self.assertEqual(output.read_bytes(), b"previous complete output")

    def test_trickled_callback_cannot_extend_total_deadline(self):
        output, failures = self.callback(b"", trickle=True)
        self.assertTrue(failures)
        self.assertEqual(output.read_bytes(), b"previous complete output")

    def test_bind_addresses_cannot_be_wildcard_or_public(self):
        for address in ["0.0.0.0", "8.8.8.8", "localhost", "::1"]:
            with self.assertRaises(ValueError):
                receiver.lab_address(address)


if __name__ == "__main__":
    unittest.main()
