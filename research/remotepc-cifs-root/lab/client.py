#!/usr/bin/env python3
# pyright: reportMissingImports=false
"""Authenticate to the host-published SMB port with mounted one-shot secrets."""

from pathlib import Path

from impacket.smbconnection import SMBConnection

SECRET_DIR = Path("/run/q60t-secrets")
user = (SECRET_DIR / "username").read_text(encoding="utf-8").strip()
password = (SECRET_DIR / "password").read_text(encoding="utf-8")
share = (SECRET_DIR / "share").read_text(encoding="utf-8").strip()
host = (SECRET_DIR / "host").read_text(encoding="utf-8").strip()
port = int((SECRET_DIR / "smb_port").read_text(encoding="ascii").strip())

connection = SMBConnection("TIZ0WN-LAB", host, sess_port=port, timeout=8)
connection.login(user, password)
names: list[str] = []
for row in connection.listShares():
    value = row["shi1_netname"]
    if isinstance(value, bytes):
        value = value.decode("utf-8", "strict")
    names.append(value.rstrip("\x00"))
connection.logoff()
if share not in names:
    raise SystemExit("configured share absent from authenticated enumeration")
