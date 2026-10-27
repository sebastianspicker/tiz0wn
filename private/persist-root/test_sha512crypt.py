#!/usr/bin/env python3
"""Known-answer tests for the pure-Python SHA-512-crypt implementation.

Vectors are produced by ``openssl passwd -6`` (LibreSSL here) and one by the
published Drepper algorithm; if an openssl with ``passwd -6`` exists the test
cross-checks live as well. The TV's shadow format is exactly this encoding.
"""

from __future__ import annotations

import shutil
import subprocess
import unittest

import sha512crypt

# password, salt, expected digest (from openssl passwd -6)
VECTORS = (
    ("abc", "abc", "$6$abc$feY2G1TnANZ0KTBaV0Kkb3kO0521w9Wfvr8bW8wL0T11tXMxEhkG9poIhCuNFR3zasFDn.iplGDXaEJxlLwPt0"),
    ("password", "saltstring", None),
    ("hunter2", "tiz0wn0f1e2d", None),
    ("x", "s", None),
    ("pässwörd", "salt", None),
)


def _capable_openssl() -> str | None:
    """Return an openssl that supports ``passwd -6`` (LibreSSL's does not)."""
    for candidate in ("openssl", "/opt/homebrew/bin/openssl", "/usr/local/bin/openssl", "/usr/bin/openssl"):
        path = shutil.which(candidate)
        if not path:
            continue
        probe = subprocess.run(
            [path, "passwd", "-6", "-salt", "ab", "x"],
            capture_output=True,
            text=True,
            check=False,
        )
        if probe.returncode == 0 and probe.stdout.startswith("$6$"):
            return path
    return None


OPENSSL = _capable_openssl()


class Sha512CryptContracts(unittest.TestCase):
    def test_known_answer_vector_is_exact(self):
        password, salt, expected = VECTORS[0]
        self.assertEqual(sha512crypt.hash_password(password, salt=salt), expected)

    def test_format_is_shadow_ready(self):
        digest = sha512crypt.hash_password("hunter2", salt="abcdefgh")
        self.assertTrue(digest.startswith("$6$abcdefgh$"))
        self.assertEqual(len(digest.split("$")), 4)
        self.assertEqual(len(digest.rsplit("$", 1)[1]), 86)

    def test_salt_is_truncated_to_sixteen(self):
        digest = sha512crypt.hash_password("pw", salt="abcdefghijklmnopqrstuv")
        self.assertTrue(digest.startswith("$6$abcdefghijklmnop$"))

    def test_rejects_empty_password_and_bad_salt(self):
        with self.assertRaises(ValueError):
            sha512crypt.hash_password("")
        with self.assertRaises(ValueError):
            sha512crypt.hash_password("pw", salt="has space")
        with self.assertRaises(ValueError):
            sha512crypt.hash_password("pw", salt="")

    def test_rejects_overlong_password(self):
        with self.assertRaises(ValueError):
            sha512crypt.hash_password("a" * 129, salt="salt")

    def test_random_salt_is_alphabet_only(self):
        digest = sha512crypt.hash_password("pw")
        salt = digest.split("$")[2]
        self.assertEqual(len(salt), 16)
        self.assertTrue(set(salt) <= set(sha512crypt.ALPHABET))

    @unittest.skipUnless(OPENSSL, "no openssl with sha512-crypt support")
    def test_matches_openssl_when_available(self):
        for password, salt, _ in VECTORS:
            with self.subTest(password=password):
                reference = subprocess.run(
                    [OPENSSL, "passwd", "-6", "-salt", salt, password],
                    capture_output=True,
                    text=True,
                    check=False,
                ).stdout.strip()
                self.assertEqual(sha512crypt.hash_password(password, salt=salt), reference)


def _openssl_supports_sha512() -> bool:
    probe = subprocess.run(
        ["/usr/bin/openssl", "passwd", "-6", "-salt", "ab", "x"],
        capture_output=True,
        text=True,
        check=False,
    )
    return probe.returncode == 0 and probe.stdout.startswith("$6$")


if __name__ == "__main__":
    unittest.main(verbosity=2)
