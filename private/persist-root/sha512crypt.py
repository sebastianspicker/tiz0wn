#!/usr/bin/env python3
"""SHA-512-crypt (``$6$``) password hashing, pure Python.

The TV's ``/etc/shadow`` uses the standard glibc SHA-512 crypt encoding. macOS
ships LibreSSL at ``/usr/bin/openssl``, which has no ``passwd -6``, so relying
on an openssl binary is brittle. This module implements the published
SHA-512-crypt algorithm directly and is verified against a known vector and
against ``openssl passwd -6`` when a capable openssl is available.

Reference: Ulrich Drepper, "Unix crypt using SHA-256 and SHA-512"
(https://www.akkadia.org/drepper/SHA-crypt.txt), step order preserved.
"""

from __future__ import annotations

import hashlib
import secrets

ALPHABET = "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
MAX_PASSWORD_BYTES = 128
SALT_ALPHABET = frozenset(ALPHABET)
MAX_SALT_LENGTH = 16


def _b64_from_24bit(b2: int, b1: int, b0: int, count: int) -> str:
    w = (b2 << 16) | (b1 << 8) | b0
    out = []
    for _ in range(count):
        out.append(ALPHABET[w & 0x3F])
        w >>= 6
    return "".join(out)


def _sha512(data: bytes) -> bytes:
    return hashlib.sha512(data).digest()


def hash_password(password: str, *, salt: str | None = None, rounds: int = 5000) -> str:
    """Return the ``$6$salt$digest`` string for ``password``."""
    if not password:
        raise ValueError("password must not be empty")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError(f"password exceeds {MAX_PASSWORD_BYTES} bytes")
    if rounds != 5000:
        # The TV's shadow parser assumes the standard $6$ encoding, which is
        # fixed to 5000 rounds; a different count would never verify there.
        raise ValueError("only the standard 5000 rounds are supported")
    if salt is None:
        salt = "".join(secrets.choice(ALPHABET) for _ in range(MAX_SALT_LENGTH))
    if not salt or not set(salt) <= SALT_ALPHABET:
        raise ValueError("salt must be 1-16 characters of the crypt alphabet")
    salt = salt[:MAX_SALT_LENGTH]

    password_bytes = password.encode("utf-8")
    salt_bytes = salt.encode("ascii")

    # Step 4-6: digest B.
    b = _sha512(password_bytes + salt_bytes + password_bytes)

    # Step 7-9: digest A with the repeated B digest.
    a = hashlib.sha512()
    a.update(password_bytes)
    a.update(salt_bytes)
    remaining = len(password_bytes)
    while remaining > 0:
        a.update(b[: min(64, remaining)])
        remaining -= 64
    length = len(password_bytes)
    while length:
        a.update(b if length & 1 else password_bytes)
        length >>= 1
    a_digest = a.digest()

    # Step 11-12: byte-sequence DP.
    dp = hashlib.sha512()
    for _ in range(len(password_bytes)):
        dp.update(password_bytes)
    dp_digest = dp.digest()

    # Step 13-15: P sequence = DP repeated, truncated to the password length.
    p = (dp_digest * (len(password_bytes) // 64 + 1))[: len(password_bytes)]

    # Step 16-18: byte-sequence DS.
    ds = hashlib.sha512()
    for _ in range(16 + a_digest[0]):
        ds.update(salt_bytes)
    ds_digest = ds.digest()
    s = (ds_digest * (len(salt_bytes) // 64 + 1))[: len(salt_bytes)]

    # Step 20-21: 5000 rounds of digest C.
    c = a_digest
    for round_number in range(rounds):
        ctx = hashlib.sha512()
        ctx.update(p if round_number & 1 else c)
        if round_number % 3:
            ctx.update(s)
        if round_number % 7:
            ctx.update(p)
        ctx.update(c if round_number & 1 else p)
        c = ctx.digest()

    # Step 22: base64-style output in the fixed permuted order.
    parts = [
        _b64_from_24bit(c[0], c[21], c[42], 4),
        _b64_from_24bit(c[22], c[43], c[1], 4),
        _b64_from_24bit(c[44], c[2], c[23], 4),
        _b64_from_24bit(c[3], c[24], c[45], 4),
        _b64_from_24bit(c[25], c[46], c[4], 4),
        _b64_from_24bit(c[47], c[5], c[26], 4),
        _b64_from_24bit(c[6], c[27], c[48], 4),
        _b64_from_24bit(c[28], c[49], c[7], 4),
        _b64_from_24bit(c[50], c[8], c[29], 4),
        _b64_from_24bit(c[9], c[30], c[51], 4),
        _b64_from_24bit(c[31], c[52], c[10], 4),
        _b64_from_24bit(c[53], c[11], c[32], 4),
        _b64_from_24bit(c[12], c[33], c[54], 4),
        _b64_from_24bit(c[34], c[55], c[13], 4),
        _b64_from_24bit(c[56], c[14], c[35], 4),
        _b64_from_24bit(c[15], c[36], c[57], 4),
        _b64_from_24bit(c[37], c[58], c[16], 4),
        _b64_from_24bit(c[59], c[17], c[38], 4),
        _b64_from_24bit(c[18], c[39], c[60], 4),
        _b64_from_24bit(c[40], c[61], c[19], 4),
        _b64_from_24bit(c[62], c[20], c[41], 4),
        _b64_from_24bit(0, 0, c[63], 2),
    ]
    return f"$6${salt}${''.join(parts)}"


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("password")
    parser.add_argument("--salt", default=None)
    args = parser.parse_args()
    print(hash_password(args.password, salt=args.salt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
