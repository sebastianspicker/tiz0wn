# Remote PC/CIFS credential injection to UID 0

Status: live-validated on one owner-controlled Samsung GQ55Q60TGUXZG running
`T-NKLDEUC-2743.0`; the fresh harness in this directory has passed its offline
and Mac-local tests but has not been run against the TV.

## Finding in one page

Remote PC accepts a username and password for an RDP profile. When Shared
Folder is opened, the application enumerates SMB shares and sends the selected
credentials into Samsung's privileged mount service. The application writes
raw lines resembling these to a temporary file:

```text
username=<user input>
password=<user input>
smbpath=<selected share>
```

The shipped `mount.smb.sh` reads those lines, substitutes their contents into
the mount argument string, and executes the result with root
`/bin/bash -c`. The privileged service validates the credential-file path and
mount argument shape, but not the shell safety of the file contents. A command
substitution in either credential therefore crosses from the Remote PC UI into
a root shell evaluation.

The bounded proof used the password form only:

```text
$(/usr/bin/id>/tmp/<fresh-marker>)
```

One deliberate Shared Folder click produced one fresh SMB share enumeration.
A fresh, combined predicate then checked that the marker was a regular file,
owned by UID 0, and began with `uid=0(root) gid=0(root)`. Its result was encoded
through exactly two SDB pushes, avoiding a target-file read or an invalid
one-push existence inference.

See [DISCLOSURE.md](DISCLOSURE.md) for the report and
[LIVE-CHECKPOINT.md](LIVE-CHECKPOINT.md) for the exact handoff boundary.

## Exact assessed artifacts

| Artifact | SHA-256 |
|---|---|
| Official firmware archive | `cb717ed98daf9580eb5b84bccbad5adac82f75dd021ed028f1ee1bb6c4abde32` |
| Local rootfs tar | `a54c6b8e4ac739c92edda4b75a87ff42b7a100c9a974c85da0acbd8b9f337ce6` |
| `mount.smb.sh` | `37aaf2f05bf714332a6bf8f14b543ac9584a1b9a051341674a74fc0dd753c57e` |
| `ps_agent` | `402885bce04ca3a04c2cb322cbe83dd96d05e17457717b4627a85b0fdb004c33` |
| `remotepc_uilauncher` | `b87e23127fe04cfab9e2c43468a99a4c4aa0b852fd5923de17104c3cf9d872da` |
| `remotepc_rdp` | `5d5b8277b20cae7ec993be7ff8f556a5f04cdff07109beb025c0e377f4dff9e4` |
| `org.tizen.remotepc.xml` | `7b0539507d10019635e502876a7c48446a2112f6c0d9b48f706afb797e9c0659` |

These hashes and conclusions bind the work to build 2743.0. Samsung source
history, the first affected release, a fixed release, and backport status are
unknown.

## Harness modes

The implementation is
[`host/one_shot_proof.py`](host/one_shot_proof.py). It has three mutually
exclusive modes.

### 1. Default: static audit only

```bash
make -C research/remotepc-cifs-root dry-run
```

This verifies the entire rootfs tar hash, five pinned members, and the reviewed
shell anchors inside `private/fw-analysis/work/rootfs.tar`. It does not read
`config/tv.env`, open a socket, invoke Docker or SDB, or contact the TV.

### 2. Local lab: Mac only

```bash
make -C research/remotepc-cifs-root test
make -C research/remotepc-cifs-root lab-test
```

The build can download the digest-pinned Debian base, Debian packages, and
Impacket `0.13.1`. The resulting services bind only `127.0.0.1:13389` and
`127.0.0.1:11445`. A second, host-networked container connects back through
those Mac-published ports and performs:

- an RDP X.224 negotiation, direct PAM and published-port XRDP rejection of an
  incorrect password, and then a full FreeRDP login and XRDP/Xorg/xterm session
  with the exact payload-shaped credential;
- an authenticated SMB2 share enumeration with the exact payload-shaped
  password;
- checks that the payload was not evaluated on the Mac or in either container;
- RDP certificate extraction; and
- unconditional exact-name container removal followed by closed-port checks.

The password is passed through root-only temporary files mounted read-only
into the containers. The primary container installs it through `chpasswd`
stdin before XRDP starts; the SMB server reads it directly and FreeRDP reads it
from stdin. The self-test rejects the password if it appears in any container
process argument. Every run builds a frozen snapshot of the allowlisted
context, verifies the live source stayed identical around the build, captures
the build's immutable image ID, checks its embedded snapshot digest, and runs
that exact ID. Reusing a pre-existing image is deliberately unsupported.

### 3. Live: interactive, exact target only

Do not run this mode until reviewing the diff, tests, and
[LIVE-CHECKPOINT.md](LIVE-CHECKPOINT.md). It requires a private
`config/tv.env` containing the exact model, firmware, SDB serial, Developer
Mode host address, and SHA-256 of the API's exact `device.id` value.

After an explicitly authorized read-only `scripts/03-tv-info.sh` capture, hash
the private response without printing its raw identifier:

```bash
python3 research/remotepc-cifs-root/host/one_shot_proof.py \
  --device-json evidence/runs/<run>/tv-info-private.json
```

Copy the printed hash into `TV_ID_SHA256`; keep the JSON and real value
gitignored.

The command is intentionally cumbersome:

```bash
python3 research/remotepc-cifs-root/host/one_shot_proof.py \
  --live \
  --confirm TIZ0WN-REMOTEPC-CIFS-ROOT-ONE-SHOT-2743 \
  --ack-saved-profile I-ACCEPT-A-TEMPORARY-SAVED-REMOTE-PC-PROFILE \
  --ack-no-retry ONE-TRIGGER-ONE-CLASSIFICATION-NO-RETRY
```

Live mode then enforces this order:

1. Verify the full local rootfs hash and pinned firmware artifacts.
2. Parse `tv.env` without sourcing or evaluating it.
3. Require the exact API identity hash, model, Developer Mode host binding,
   same-/24 private addresses, reviewed SDB binary, and exact SDB `device`
   state.
4. Require a manual exact-firmware confirmation from the TV's About screen.
5. Refuse occupied ports and bind the disposable lab only to `HOST_IP` on
   TCP 3389 and 445. Historical relay port 1445 must also be free.
6. Pass full local RDP/Xorg and exact-credential SMB tests through the
   host-published ports.
7. Display a one-time private form card. The user—not the harness—fills and
   visually verifies Remote PC/RDP, the fields, and the shared-folder setting.
8. Observe exactly one new successful RDP login.
9. Open one bounded window for one physical Shared Folder click and require
   exactly one fresh `NetrShareEnum Level: 1` event.
10. Consume one combined UID-0 predicate and exactly two SDB pushes. There is
    no retry path, including when SDB returns an error string with status 0.
11. Stop and remove both exact-name containers in `finally`, close ports
    3389/445/1445, and make one read-only API/SDB health check.

SIGINT and SIGTERM enter the same cleanup path. The TV marker, SDB gate, and
classification stage are intentionally never read, rewritten, removed, or
reused by the harness.

## Why two pushes

An SDB push to a missing destination can create a regular file at that path,
so one successful push cannot distinguish "predicate created a directory"
from "destination was absent." The classifier uses this shape:

1. The target predicate creates a fresh stage directory only when all three
   UID-0 marker conditions hold.
2. The first push succeeds either into that directory or by creating a file at
   the absent path.
3. The second push to `<stage>/attest` succeeds only when `<stage>` was already
   a directory. `Not a directory` or `No such file or directory` means no
   proof; any other result is terminal and ambiguous.

No classifier result is retried.

## Explicit non-goals

- No SMB share-name injection route.
- No TV UI, pointer, key, or Remote PC field automation.
- No persistent root shell, service, firmware write, package change, or UEP.
- No affected-version claim beyond 2743.0.
- No automatic target cleanup: deleting the saved Remote PC profile and
  revoking the allowed validation device are visual, manual tasks.

Use only on a device you own. Never expose TCP 445, 3389, 26101, or TV control
interfaces outside a trusted local network.
