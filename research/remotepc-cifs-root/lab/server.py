# pyright: reportMissingImports=false
"""Run the disposable SMB2 server without putting its password in argv."""

from __future__ import annotations

import re
from pathlib import Path

from impacket import smbserver
from impacket.examples import logger
from impacket.ntlm import compute_lmhash, compute_nthash

SECRET_DIR = Path("/run/q60t-secrets")
SHARE_ROOT = "/srv/q60t-share"

username = (SECRET_DIR / "username").read_text(encoding="utf-8")
password = (SECRET_DIR / "password").read_text(encoding="utf-8")
share = (SECRET_DIR / "share").read_text(encoding="ascii")

if username != "q60t":
    raise SystemExit("invalid fixed lab username")
if re.fullmatch(r"Q6[0-9A-F]{10}", share) is None:
    raise SystemExit("invalid one-shot share name")
if re.fullmatch(r"\$\(/usr/bin/id>/tmp/q60t-rpc-[0-9a-f]{16}\)", password) is None:
    raise SystemExit("invalid literal one-shot password")

logger.init(True, False)
server = smbserver.SimpleSMBServer(listenAddress="0.0.0.0", listenPort=445)
server.addShare(share, SHARE_ROOT, "Disposable tiz0wn validation share", readOnly="yes")
server.setSMB2Support(True)
server.setSMBChallenge("")
server.addCredential(username, 0, compute_lmhash(password), compute_nthash(password))
server.start()
