# Boot start: outside evidence, 2026-11-04

Read-only GitHub research on one owned lab TV. No TV command was run for this
file; the only live facts quoted are already in this repo's records.

## Why this file exists

The profile.d hook now runs at boot and requests the app-start worker, but the
worker reported `timeout readiness launcher or org.tizen.webappservice`. The
first hypothesis (epoch-zero wall clock) is fixed offline in T-73, but the
worker design itself was written by us, not copied from a proven set. Two
independent projects boot a TV-side agent without a host and both use
`app-boot-manager`, not a hand-rolled `app_launcher` poll. This file records
what they actually do, what applies to KantSu2, and what stays unproven.

## Source 1 — `levkropp/samsung-tv-root-untethered` (Q60B / NKLB, Tizen 6.5)

Fork of `chris-ritsen/samsung-tv-root`. Title: "Samsung untethered root for
2022-2026 Samsung QN90 and Q60 TVs". Claims untethered boot-time self-root on
`QN55Q60BAFXZC` / `T-NKLBAKUC-1720.7`.

Mechanism, quoted from `boot-agent/README.md`:

> The boot trigger — `package_app_info.app_onboot` in
> `/opt/dbspace/.pkgmgr_parser.db` (plain SQLite on rw `/opt`) plus the
> matching `on-boot="true"` manifest attribute. `app-boot-manager.service`
> launches the app through `aul` into the launchpad .NET pool at every boot.
> Both `svcapp` and `uiapp` components boot this way

Deploy step:

```sql
UPDATE package_app_info SET app_onboot='true', app_nodisplay='false',
  app_component='uiapp' WHERE app_id='com.samsung.tv.ghservice';
```

They squat an installed app (`com.samsung.tv.ghservice`), replace its IL, and
flip the same manifest element from `service-application` to `ui-application`
with `on-boot="true"`. They did **not** isolate whether `app-boot-manager`
reads the DB row, the manifest, or both:

> I did not isolate whether `app-boot-manager` reads the DB row, the manifest,
> or both — I flipped both and it boots.

Their chain does not depend on our archive route: app IL (empty `CapEff`, label
`User::Pkg::`) → raw TCP `127.0.0.1:26101` → CNXN replay → appinstall
injection (label `System`) → `cat script | bash` → signed dotnet. They state a
boot app cannot exec capped dotnet directly:

> the loaded policy in `smackfs/load` grants `x` on `System::Tools` (the
> dotnet label) to `System`, `User`, `_`, `User::Shell`, `System::TEF`,
> `System::Privileged` — not to `User::Pkg::*`

Two more transferable facts:

- UEP rejects `bash <file>` but accepts `cat <file> | bash`, including as root.
- `sdbd` caches the developer host IP at startup; a live flip does nothing.

## Source 2 — `andrearicci93/vetro` issue #4 and PR #29 (S90C, Tizen 7.0)

Vetro is a web app (`config.xml` + web service) whose service self-roots
through loopback sdb — the closest architecture to ours. Fresh installs register
the service with `app_onboot=false` and `app_autorestart=false` even though
`config.xml` declares both `true`; the service then never starts after reboot.

Manifest:

```xml
<tizen:service id="vetrotvapp.svc" auto-restart="true" on-boot="true">
```

Repair once root is connected, from `app/service/component-actions.js`:

```sh
mkdir -p /home/owner/share/vetro/startup-backups
backup=/home/owner/share/vetro/startup-backups/<app_id>
[ -f "$backup" ] || sqlite3 -readonly DB "SELECT app_onboot,app_autorestart FROM package_app_info WHERE app_id='<app_id>';" > "$backup"
sqlite3 -bail DB "BEGIN IMMEDIATE; UPDATE package_app_info SET app_onboot='true' WHERE app_id='<app_id>'; COMMIT;"
sqlite3 -readonly DB "SELECT app_onboot FROM package_app_info WHERE app_id='<app_id>';"
```

Measured boot times on S90C (from PR #29), full restarts, only the service flag
changed:

| on-boot / auto-restart | Service started |
| --- | --- |
| false / false | not within 160 s and 180 s (two boots) |
| true / false | 54 s |
| true / true | 59 s |

So `app-boot-manager` on a 2023-era web-service app starts the service about a
minute after boot. Vetro writes only its own service row and leaves the UI row
alone.

## What this means for the Q60T (KantSu2)

1. `app_launcher -s` from our profile.d worker is a fallback, not the platform
   mechanism. `app-boot-manager` already knows how to wait for the framework
   and launch an on-boot component; we should use it and keep the worker only
   as a repair path.
2. The app build must carry `on-boot="true"` and `auto-restart="true"` on the
   service element, because installers drop them from the DB and may also read
   the manifest.
3. The DB write needs the Vetro discipline: backup once, `BEGIN IMMEDIATE`,
   single row, single flag per statement, read-back.
4. Two facts are still unproven on KantSu2 and must be checked before another
   power cycle: whether `/opt/dbspace/.pkgmgr_parser.db` and
   `app-boot-manager.service` exist, and whether the manager launches a **web**
   service app at all. The Q60B proof used `dotnet-inhouse`; the Vetro proof
   used a web service app on Tizen 7.0. KantSu2 sits between those.

## Follow-on improvement the same source suggests

With Host PC IP parked at `127.0.0.1`, the Mac can no longer reach `sdbd`.
Both projects accepted that trade. `levkropp` later added a token-gated
loopback relay on `26103` so the host CLI keeps working while devIP stays
`127.0.0.1`. That would end our own `.165`/`127.0.0.1` toggling and is
independent of the boot trigger.

## Limits

- No claim that any of this works on `GQ55Q60TGUXZG` / `T-KTSU2DEUC`.
- Neither project tested a Q60T, KantSu2, Tizen 5.5/6.0, or our package id.
- The Vetro timings are one device and two boots.
- The Q60B chain reaches root through `dotnet`; ours uses `capsh` + signed bash
  because the managed host drops capabilities here.
