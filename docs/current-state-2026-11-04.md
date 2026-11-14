# Current state — 2026-11-04 evening

One owned `GQ55Q60TGUXZG` (Q60T, KantSu2, `T-NKLDEUC-2743.0`). Everything below
is on that one set; nothing is claimed for another model or firmware.

> **Superseded in part.** This is the 2026-11-04 snapshot. On 2026-11-05 the
> debloat ladder below was followed by 33 `wgt` removals and 41 `tpk`/`rpm`
> disables (53 app rows), verified over two reboots; see
> [`HANDOFF-2026-11-05.md`](HANDOFF-2026-11-05.md). On 2026-11-07 the paused UI
> shipped its typographic home; the Home-band trial followed on 2026-11-08. See
> the README's [TV menu](../README.md#tv-menu) and
> [Home-band](../README.md#replacing-samsungs-home-band) sections.

> **Last check, 2026-11-05 09:40Z:** after standby/wake, no reboot (uptime
> 9172 s), `/run` and `/cmd` return root, flags `true/true`, relay running,
> app service alive. **Device status:** recovered at 19:19Z. A clean boot started the agent, the
> relay and the service without an app opened; `/cmd` and `/run` return root
> and the relay carries `push`. The earlier wedge needed one power cycle; see
> [`HANDOFF-2026-11-04.md`](HANDOFF-2026-11-04.md).

## What works, verified live

| Capability | Evidence |
| --- | --- |
| App route reaches root | `GET /run` returns `uid=0(root) … context="System"`; app page on `18735`, API on `18734` |
| Archive route | `GET /root` returns `rc=0`, `launch-ok`, through `capsh` + signed bash |
| Root survives boot | `amd` launches `tiz0wnprob.Service` from the per-user `app_onboot` row at +48–58 s, with no app opened; `/run` then returns root |
| App survives boot without the worker | proven on the first boot; the worker had already timed out |
| Worker path | proven on the second boot: launched at +47 s, then stood down |
| Persistent root agent | profile.d hook starts it every boot; agent answers jobs |
| Token sdb relay | `sdb push` and `sdb install` work from the Mac through `<TV>:26103` while devIP is `127.0.0.1` |

The boot proof is in `docs/app-boot-trigger.md`; the relay in
`docs/boot-start-evidence-2026-11-04.md` and `docs/app-persistence-design.md`.

## How a boot runs now

```
power on
 -> /etc/profile.d/bash_prompt_custom.sh (raw block) -> /opt/usr/share/tvroot/boot
 -> SMACK app rules reloaded into load2
 -> root agent started (job channel under /opt/usr/share/tvroot/cmd)
 -> bridge started if /opt/usr/share/tvroot/bridge{,.token,.sh} are valid
 -> app-start worker (fallback only, 90 s, stands down if the service appears)
 -> amd boot list reads package_app_info.app_onboot at ~48–58 s
 -> org.tizen.webappservice -> tiz0wnprob.Service (uid 5001, label User::Pkg::)
 -> service listens 18734; /run and /root give root through TV-local sdbd
```

## State that must survive an install

A `tizen install` re-registers the service row with `app_onboot=false` and
`app_autorestart=false`. After every install
(`exploits/tiz0wn-root/live/app-run.sh install|arm`) the flags have to be
restored. `app-run.sh install` does it automatically; a bare `tizen install`
does not.

Check and repair, through the agent:

```sh
db=/opt/dbspace/user/5001/.pkgmgr_parser.db
sqlite3 -readonly "$db" \
  "SELECT app_onboot,app_autorestart FROM package_app_info WHERE app_id='tiz0wnprob.Service';"
sh /Users/sebastian/Projects/Git/tiz0wn-codex/exploits/tiz0wn-root/payload/app-boot
```

## UI

As of this snapshot, paused. A glass/focus/exit spike was approved and a fixture
home shell existed, but the carousel overlapped on the TV while a headless
Playwright harness passed. The cause was **flex `gap` unsupported in Chromium
69**; the later fix and the shipped typographic home are in the README's
[TV menu](../README.md#tv-menu) section. Details:
[`HANDOFF-2026-11-04.md`](HANDOFF-2026-11-04.md).

## Debloat

The reversible ladder is complete: seven targets trialled, verified across a
boot in both directions, and reverted. State on 2026-11-04 was baseline — every
`app_disable=false`, `units.off` empty, all four affected units loaded and
active. On 2026-11-05 the batch was applied: 33 `wgt` removed and 41
`tpk`/`rpm` disabled (53 app rows); see
[`HANDOFF-2026-11-05.md`](HANDOFF-2026-11-05.md) for the applied state and
reversal paths.

Two levers exist and are not interchangeable:

| Target class | Lever | Proven |
| --- | --- | --- |
| `app_launcher -s` app | `pkgstate --global` | multi-assistant, ScreenMirroring, multiscreen |
| daemon or direct-binary unit | `unitstate` off-list (runtime masks, re-applied at boot) | ACR (3 units), nfc-monitor |
| multi-app package | `pkgstate` single-ID transaction | calendar (2 apps) |
| cross-package feature | `pkgstate --file` transaction | COSS (2 packages) |

Traps recorded: `--uid` is a no-op here; unit masks need `LoadState`; the boot
hook races systemd and must retry then stop; batch files belong in `/opt`.
`docs/debloat-plan-2026-11-05.md` is the full record.

## Single-client rule

`sdbd` serves one loopback client. The app probe and a Mac sdb session cannot
be upstream together, even through the relay. Close `sdb` before `/cmd`, and
close `/cmd` before opening `sdb`. An idle connector does not block. Full
detail and failure modes: `docs/sdb-relay.md`.

## Access paths, in order of preference

1. **App API** (`192.168.8.234:18734`) with `Origin: http://127.0.0.1:18735`:
   - `POST /cmd` with a shell command (root, 4 KiB command, 16 KiB output, 60 s)
   - `GET /run` fixed `id`, `GET /root` archive proof, `GET /state` diagnostics
   Requires devIP `127.0.0.1`. One probe at a time.
2. **Relay**: start `live/bridge-connect.py`, `sdb connect 127.0.0.1:<port>`.
   Carries `push` and `install`. `shell` is unreliable through it on this
   firmware; use `/cmd` for commands. Kill the sdb server before `/cmd`.
3. **Direct sdb**: only while Host PC IP is the Mac (`.165`). Needed for the
   agent `job.sh` path and `buxton2ctl` writes.
4. **Developer Mode GUI**: Apps → `12345` → Host PC IP. The only way back if
   both the app and the agent are down.

## Known limits

- sdbd wedges after many short sessions; a power-cycle clears it. `sdb
  kill-server` plus a pause sometimes avoids it.
- Host PC IP is a single value. It must be `127.0.0.1` for boot self-root, the
  app probe and the relay; the Mac address only for direct sdb.
- `/cmd` and `/run` share one busy guard; concurrent calls get `409`.
- `/cmd` and an open Mac sdb session are mutually exclusive (one loopback
  client in `sdbd`). `sdb kill-server` first.
- The relay's token is per-device in `live/bridge-private.token` (untracked).
  A wrong token gives an immediate close with no reply.
- `app_autorestart` restarts on death but is not what starts the app at boot;
  `app_onboot` is.
- The worker only covers a boot where the platform list fails. 90 s is a
  deliberate backstop, not a normal path.
- Rootfs is read-only; the hook is a raw profile.d block. An OTA replaces it.
- No USB, no UEP disable, no unsigned native binary is needed for any of this.
