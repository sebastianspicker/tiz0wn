#!/usr/bin/env python3
"""Serve-time prelude for the delivered root script.

The sink runs ``curl ... | /bin/sh`` with the TV's own environment, so the
setup script cannot receive parameters through environment variables or
arguments. ``serve.py`` therefore prepends a small prelude that pins the
values as shell variables before the template body runs. The builder lives
here so the tests and the offline repro share exactly one implementation.

Values are single-quote wrapped. A crypt hash may contain ``$``, ``/`` and
``.`` but never a single quote, and the builder refuses anything it cannot
quote safely.
"""

from __future__ import annotations

import re

import payload

USER_RE = re.compile(r"[a-z][a-z0-9_-]{0,31}")
HASH_RE = re.compile(r"^\$[0-9]\$[^!\"' \t\n\r]{1,128}$")
# Crypt hashes use the [./0-9A-Za-z] alphabet plus the $id$ separators;
# neither a single quote nor a backslash can appear.
HASH_SAFE_RE = re.compile(r"^[^'\\]*$")


def shell_quote(value: str) -> str:
    """Wrap one value in single quotes for the prelude."""
    if not HASH_SAFE_RE.match(value):
        raise ValueError(f"cannot quote value: {value!r}")
    return "'" + value + "'"


def build_prelude(
    *,
    user: str = "tiz0wn",
    password_hash: str,
    token: str,
    shell_host: str = "",
    shell_port: str = "",
    extra_args: str = "",
) -> str:
    if not USER_RE.fullmatch(user):
        raise ValueError("user must be a lower_snake case name of at most 32 characters")
    if not HASH_RE.match(password_hash):
        raise ValueError("password_hash must be a crypt hash ($6$... / $1$...)")
    if not re.fullmatch(r"[0-9a-f]{16}", token):
        raise ValueError("token must be 16 lowercase hex characters")
    if shell_host and not payload.IPV4_RE.fullmatch(shell_host):
        raise ValueError("shell_host must be a dotted-quad IPv4 literal or empty")
    if shell_port and not re.fullmatch(r"\d{1,5}", shell_port):
        raise ValueError("shell_port must be numeric or empty")
    if bool(shell_host) != bool(shell_port):
        raise ValueError("shell_host and shell_port must be set together or both empty")
    if extra_args not in ("", "--revert"):
        raise ValueError("extra_args may only be --revert or empty")
    lines = [
        f"TIZ0WN_USER={shell_quote(user)}",
        f"TIZ0WN_PWHASH={shell_quote(password_hash)}",
        f"TIZ0WN_TOKEN={shell_quote(token)}",
    ]
    if shell_host:
        lines.append(f"TIZ0WN_SHELL_HOST={shell_quote(shell_host)}")
        lines.append(f"TIZ0WN_SHELL_PORT={shell_quote(shell_port)}")
    else:
        lines.append("TIZ0WN_SHELL_HOST=")
        lines.append("TIZ0WN_SHELL_PORT=")
    lines.append(f"TIZ0WN_ARGS={shell_quote(extra_args)}")
    return "\n".join(lines) + "\n"
