# App persistence design (offline, 2026-11-04)

Target: owned Q60T, `T-NKLDEUC-2743.0`. No TV contact in these passes. The live
app `/run` already returns `uid=0(root)`; this work removes the runtime
dependencies that killed `/root` and designs boot persistence without a
Partner-level certificate or USB stick.

## Evidence chain

| Pass | Finding | Outcome |
| --- | --- | --- |
| T-65 | Node v4.4.3 has no `Buffer.alloc`/`Buffer.from`; the service shims them. The `/root` path's only unexercised dependencies are gzip, runtime key generation, `openssl` and signing. | Choose a prebuilt signed archive; use the persistent root agent to start the app. |
| T-66 | A prebuilt tar removes zlib, openssl, key generation and signing from the TV. | WGT builds a deterministic `archive.tar.gz` plus RSA signature; `/root` only copies them. Node 4.9 replay returns 200 with no openssl. |
| T-67 | The Node suite's uncaught reset was a mock-server race, not the service. | Mock waits for acknowledgment; ten consecutive runs pass. |
| T-68 | The WGT fixtures predated the archive artifacts and omitted the icon. | Twelve WGT tests pass, one negative per artifact; ten Node runs pass. |
| T-69 | Boot start can be delegated to the already-persistent root agent. | `payload/app-start` arms a marker; boot hook retries `app_launcher -s` three times, five seconds apart, inside a 30 s worker. Icon is packaged. |

## Archive design

- `payload/archive-launch.sh` is static and writes
  `/tmp/tiz0wn-archive-launch.log`.
- `builder/make_archive.py` emits a USTAR member with mode 0700 and mtime 0,
  gzips with mtime 0, signs the gzip with `archive-key.pem`, and verifies the
  signature with `archive.pub.pem`.
- The WGT carries the tar, signature and public key. The private key is
  build-only.
- `/root` writes the per-package names and `public.pem`, then starts the
  launcher. No runtime crypto signing.
- Archive hash at this revision:
  `dfdad17debc71dd40d3e73b14d5eef7673716c7b70e385dcdf3b17e8549ac32b`.
  Signature length 256 bytes.

Regenerate the archive whenever `launch.sh` changes; regenerate the key only on
deliberate rotation.

## Boot design

`on-boot="true"` is absent. Tizen documents Partner level; the installed
certificate is a Samsung author/distributor pair, not a Partner distributor.

Instead:

1. The existing `profile.d` hook starts the root agent after `/opt` is ready.
2. If `$D/app-start` exists, the hook waits up to 30 s for the webappservice and
   `/usr/bin/app_launcher`, then calls
   `/usr/bin/app_launcher -s tiz0wnprob.Service`.
3. Three attempts, five seconds apart. Every result goes to
   `$D/app-start.log`; boot never waits beyond the worker deadline.
4. `app-run install` arms the marker through the agent after a successful
   install. `app-run stop` removes it.

This uses the already-proven hook/agent persistence and needs no entitlement.

## Live boot result

Two separate boots proved both starters. The platform `amd` list launched the
service from the per-user `app_onboot` row at +48–58 s in a cold boot with no
app opened and `/run` returned root; the worker had timed out first at 30 s, so
its deadline was raised and it now stands down when the platform wins. On the
second boot the worker instead launched the service at +47 s and stood down.
They do not double-launch. See `docs/app-boot-trigger.md` and
`docs/current-state-2026-11-04.md`.

Boundaries: an install re-registers both flags as false, so the repair job
must follow every install; an OTA replaces the profile.d hook; the device
still needs Developer Mode and a self-signed certificate.

## Live result

`/root` returned `rc=0`; `capsh` + `sdbd-tarlauncher` ran the archive and wrote
`launch-ok`. The managed launcher was removed from this path because it cleared
all capabilities before managed code.

## Test outcomes

- full payload suite: 93 pass
- WGT suite: 13 pass
- archive suite: 18 pass
- Node replay: ten consecutive pass
- `make -C exploits/tiz0wn-root verify`: pass
- ShellCheck, `sh -n`, Ruff on touched files, `git diff --check`: pass
- Real local WGT build with `PROFILE=tv_research`: pass
- WGT check: pass, SHA-256
  `28bbfa173f7c813272c3ff1af7d2bbb065e8346d0a7aad025ce01f722461cb19`

## What remains unproven

- ~~`/root` on the TV after the prebuilt change.~~ Live: `rc=0`, after replacing the managed host with `capsh`.
- `app_launcher -s` from the boot hook after a cold boot.
- The service surviving standby/boot and reconnecting.
- Whether an app restart is enough after a service crash.

## Next live order (separate approval)

1. Install the final WGT, bootstrap SMACK, stop host SDB.
2. `/run` (must still return `uid=`).
3. `/root` (must return `launch-ok` and `exit=0` in `launcher.log`).
4. Arm `app-start`, power-cycle, observe the boot log and `/state`.
5. Only then call persistence proven.

Any failure stops before the next number.
