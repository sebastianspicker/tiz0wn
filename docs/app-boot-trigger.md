# App boot trigger audit — Q60T, T-NKLDEUC-2743.0

## Token relay operation

After `app-run.sh bootstrap` has set Host PC IP to `127.0.0.1`, but before the
power cycle, run `sh exploits/tiz0wn-root/live/app-run.sh bridge` with `TV_HOST`
and `HOST_IP` set as for the other app-run phases. This creates an owner-only
local token once at `live/bridge-private.token`, stages the matching TV token and arm
marker through the root agent, starts the relay, and checks its status. Keep
that token file private; the connector needs the same bytes after a reboot.

The bridge phase prints the connector command. Run it in a terminal and leave
it running, then use its printed `sdb connect 127.0.0.1:<port>` command in
another terminal. The connector binds only Mac loopback, starts at port 26102,
and chooses the next free port if needed. The TV relay listens on 26103 by
default. With the marker and valid token present, the root boot hook requests
the relay after the agent start request; it does not wait for the app.

`app-run.sh stop` stops the relay and removes its arm marker along with the app
fallback marker. To restore direct SDB access, set Host PC IP to the Mac again
and power-cycle.

Static audit of the two binaries copied to `/tmp/boot-audit/` on 2026-11-04.
No command was sent to the TV for this audit. The copied binaries are ARM ELF
files; the manager is SHA-256 `482a0bc015e5c0b88a3fab15c3ebaa6b6d0106cb0b14af96202363b48a2fac26`
and the launcher is SHA-256
`230c0aad0c3b6168381f0a6b9a9611acfe9248a45526aa8dd2d727ca1a730caa`.
"Proven by disassembly" below means the copied ELF's imports, strings, option
table, and ARM instructions, not observed execution. The unit and database
facts are the read-only collection in `/tmp/boot-audit/evidence.md`.

## Decision

**Write the per-user `app_onboot` row for `tiz0wnprob.Service` and keep
`app_launcher -s` as fallback.** The first pass below could not find the
reader; the follow-up section finds it in `libamd` (`is_onboot`, 1 s service
poller). Do not change any other row. The supplied manager binary has no visible
boot-app row enumerator or SQL. Its `webapp` test belongs to a named boot job,
not a scan of `package_app_info`. The collected live invocation of
`app_launcher -s` returned a PID with the service's `app_exec` path, but the
first boot worker timed out at its own readiness check before invoking the
launcher. The worker's monotonic deadline correction is T-73; a cold-boot app
start after that correction remains unobserved. **[proven by disassembly for
the manager and launcher; collected runtime fact for the explicit invocation;
inferred decision]**

The discriminating missing observation is a trace of the actual boot-app
enumerator on this firmware: its library or executable, SQL/manifest reader,
user-ID selection, and a controlled cold boot with this existing service row.
The staged files do not establish that changing the row starts a web service.
**[inferred]**

## Existence and placement

| Item | Collected result | Basis |
| --- | --- | --- |
| `/usr/bin/app-boot-manager` | Present; 85,208-byte copied ELF | Collected binary; proven by disassembly |
| `app-boot-manager.service` | Present, static and finished at collection time | Proven by unit file; collected `systemctl` state |
| `/usr/bin/app_launcher` | Present; 22,252-byte copied ELF | Collected binary; proven by disassembly |
| Global `/opt/dbspace/.pkgmgr_parser.db` | Present, 394 system-app rows; no `tiz0wnprob` row | Collected DB evidence |
| User `/opt/dbspace/user/5001/.pkgmgr_parser.db` | Present; owns `tiz0wnprob.Main` and `tiz0wnprob.Service` | Collected DB evidence |
| Boot-app enumeration library and exact DB schemas | Not staged as readable artifacts; neither can be audited here | Collection boundary |

The unit contains `DefaultDependencies=no`,
`ConditionPathExists=!/proc/tztv-bootmode`,
`Environment=LD_USE_LOAD_BIAS=1`, and
`ExecStart=/usr/bin/app-boot-manager`. It has **no** `After=`, `Wants=`, or
`Requires=` directive. Thus this unit does not explicitly order itself after
the app framework or package database. `static` means it has no install enable
link; the supplied evidence does not show which unit pulls it into a boot
transaction. **[proven by unit file; final sentence inferred]**

## What the manager actually reads

The manager contains **no SQL string to quote**: no `SELECT`, `app_onboot`,
`app_autorestart`, `/opt/dbspace`, or `on-boot` literal. Its ELF `NEEDED` list
includes `libpkgmgr-info.so.0`, but **not** `libpkgmgr_parser.so.0` or
`libsqlite3.so.0`. The latter two names occur in the binary's prelink/string
data; their presence is not evidence that this executable calls either one.
The only imported `pkgmgrinfo_appinfo_*` functions are
`get_usr_appinfo`, `get_apptype`, `get_metadata_value`, and
`destroy_appinfo`. There is no imported installed-list/filter/boot-list call.
No call in this executable enumerates rows by `app_onboot='true'`, and it
does not inspect `app_component` in its visible package-info path. **[proven
by disassembly; negative result limited to this executable]**

At `job_mgr_add_job+0x738` (VA `0x175fe`), the manager passes constant `21`
to `tzplatform_getuid`, then passes the returned UID and an already selected
app ID to `pkgmgrinfo_appinfo_get_usr_appinfo` (VA `0x1760a`). It checks that
one app's `app_type` at `0x1761a`; it does not choose rows from a database at
that point. Constant `21` is an API selector, not literal UID `5001`. The
staged artifacts do not include the platform enum definition or
`libpkgmgr-info.so.0` implementation, so they cannot prove whether this call
resolves the global DB, `/user/5001/`, or both. In particular, the location of
our row does **not** prove that this manager selects it. **[proven by
disassembly for calls and arguments; DB routing unresolved]**

The installed `tiz0wnprob.Service` row is
`webapp|svcapp|app_onboot=false|app_autorestart=false`; the UI row is
`webapp|uiapp` with both flags false. All 14 collected global on-boot rows are
native app types, so none demonstrates this firmware booting a web service.
The manifest `on-boot` and `auto-restart` attributes are installer input; the
manager does not parse a manifest. Whether an installer or a separate boot
service consumes those attributes and whether it migrates either parser DB
remain unknown. The staged evidence gives no `CREATE TABLE` text,
`PRAGMA user_version`, migration, or trigger definition. Therefore there is
no justified exact row write or manifest change for this firmware yet.
**[collected DB evidence; proven by disassembly for the manager's missing
manifest reader; migration and other readers unresolved]**

The Q60B project changed a global native row and its manifest. Vetro changed
a web-service flag on an S90C. Those are useful comparison cases in
`docs/boot-start-evidence-2026-11-04.md`, not proof that this Q60T binary
enumerates our per-user row. **[inferred]**

## `webapp` and the metadata URL

The manager's branch at `0x1761a–0x1765e` compares the selected app's type
with literal `webapp`. Equality jumps straight to `0x1765e`, bypassing
`pkgmgrinfo_appinfo_get_metadata_value`. For a **non-webapp** type, it looks up
`http://samsung.com/tv/metadata/appbootingsupport`; a failed lookup reaches
the `%s appboot unsupported` log at `0x1777c`. No comparison with a metadata
value appears before the branches rejoin. Thus this URL does **not** gate the
`webapp` branch in the copied manager, and this code does not require any
particular WGT manifest value for it. This test only answers whether an
already selected boot job may continue; it does not establish how that job is
selected. **[proven by disassembly]**

## What `app_launcher -s` does

The launcher's GLib option table maps `start` to short option `s` and describes
it as `Execute the application` with argument `APPLICATION ID` (file offset
`0x31ec`). Uppercase `-S` is `status`; `-s` is not a service-component switch.
The launch path resolves the requested ID with
`pkgmgrinfo_appinfo_get_usr_appinfo`, gets its `app_exec`, and calls
`aul_launch_app_for_uid` for the ordinary path (VA `0x121bc–0x121d4`,
`0x120fc–0x12104`). It then prints
`... successfully launched pid = %d with debug %d` on a positive launch PID.
Its GLib main loop waits for its scheduled launch work/callback and can
observe app-death status; that is launch completion, not proof that the web
service is ready to answer HTTP. The collected invocation produced PID 26968
with argv `/opt/usr/home/owner/apps_rw/tiz0wnprob/bin/tiz0wnprob.Service`,
matching the service's registered `app_exec` symlink to `/usr/bin/wrt-service`.
**[proven by disassembly; collected process observation]**

The message `timeout readiness launcher or org.tizen.webappservice` comes
from our own `exploits/tiz0wn-root/payload/boot` readiness loop. It checks the
launcher path and `systemctl is-active --quiet org.tizen.webappservice`
inside its deadline, then logs that text if the checks never pass in time.
It is not an `app_launcher` or `app-boot-manager` diagnostic, and it does not
show a failed `-s` launch. **[proven by repository source]**

## Boundary for a later boot decision

No `UPDATE package_app_info` statement is recommended here. Before one can
be specified, obtain the actual boot-app reader, full schema and version for
both DBs, and evidence that it selects a `webapp`/`svcapp` row for the
platform-resolved user. The existing `app_launcher -s` route has a direct
launch observation and remains the one route supported by this evidence;
automatic cold-boot start still needs a separate observation. **[inferred]**

## Follow-up: the boot reader is the AMD library, not the manager

Second read-only collection, 2026-11-04 18:15Z. The manager alone looked
empty because the enum lives one layer down, in the AUL/AMD extension path.
Copied files (SHA-256 in `/tmp/boot-audit/hashes.txt`):

```text
/usr/lib/libamd.so.1.14.9                         188352 bytes  7947a912...
/usr/share/amd/mod/libamd-mod-boot-tv.so            5572 bytes  8ecb899c...
/usr/share/amd/mod/libamd-mod-appmanager-tv.so     46988 bytes  6fba279b...
/usr/lib/libaul-ex.so.0.1.0                        13388 bytes  17452ede...
```

`/usr/share/amd/conf/amd.conf` begins:

```ini
[configuration]
# Service App OnBoot Interval: 1 sec
service_app_onboot_interval=1000
```

`libamd` imports `pkgmgrinfo_appinfo_is_onboot` and
`pkgmgrinfo_appinfo_is_autorestart`. It calls `is_onboot` at `0xc714` and
branches on the result at `0xc718` (`cbnz r0, 0xc742`); the false path
`__strdup`s a mode string, the true path logs. Adjacent code calls
`is_autorestart` at `0xc698` and stores a byte at `+0x10`. The exported
wrapper is `amd_launch_start_onboot_apps` at `0x1dcfc`.

`libamd` also validates component types, quoting `svcapp`, `uiapp`,
`widgetapp`, `watchapp` and the message `Unknown component type: %s`; its
appinfo loader logs `load appinfo for uid %d failed`, uses
`pkgmgrinfo_appinfo_get_usr_appinfo`, and takes the user id from the caller.

So the flag is read through `libpkgmgr` from `package_app_info.app_onboot` —
the same column the Q60B and Vetro sources write — and a 1-second poller is
configured specifically for **service** apps. The manifest `on-boot` attribute
is still not read by this path.

### Revised decision

Write the single `tiz0wnprob.Service` row in the per-user DB, keep
`app_launcher -s` as the fallback, and prove it with one cold boot. The
remaining gap is empirical (no web service is on-boot on this set), not a
missing control surface.

## Live boot proof, 2026-11-04 18:32Z

One power cycle with devIP `127.0.0.1`, `app_onboot=true`,
`app_autorestart=true`, the `app-start` marker armed, and no host sdb session.
No app was opened.

- port 18735 opened at **+18 s** (worker had already timed out at +30 s of its
  own start; the port was not open yet at that point)
- `GET /run` returned `uid=0(root)`
- the worker logged `timeout readiness launcher or org.tizen.webappservice` at
  `17:32:42Z`, before the platform launch
- `/var/log/appfw/amd/amd.log` shows the boot list, in order, around
  `18:32:54–18:33:03` local:

```text
[149] 18:32:54 SUCCESS: 5001 com.samsung.tv.ondevice
[150] 18:32:55 RESUMING com.samsung.tv.utterance-recommender-core
[152] 18:32:55 LAUNCHING com.samsung.tv.google-assistant
[158] 18:32:57 LAUNCHING com.samsung.tv.bixby-prov
[160] 18:32:57 LAUNCHING com.samsung.tv.easysetup-mediator
[164] 18:32:58 LAUNCHING tiz0wnprob.Service
[165] 18:33:00 SUCCESS: 5306 tiz0wnprob.Service
[166] 18:33:00 LAUNCHING com.samsung.tv.ghservice
```

The service landed between four other `app_onboot=true` services, at the same
cadence, with no `app_launcher` line in `app-start.log`. This is the platform
on-boot list, not the worker and not an autorestart of a previous process.

### Consequences

- The per-user `app_onboot` write is the working persistence mechanism on this
  firmware. `app_autorestart` was not needed for this boot but stays set.
- `org.tizen.webappservice` becomes ready around 48–58 s, later than the
  worker's 30 s budget. The worker is now only a fallback and must either
  match that schedule or stay out of the way. T-78 raises its deadline past
  the platform's and keeps the running check.
- Opening the app is not required after boot. `/run` and `/root` are available
  as soon as the service answers (18735 at +18 s here was the web engine
  listening before the module was fully up; `/run` succeeded once it was).

## Second boot, 19:18Z — worker path also proven

After the sdbd wedge was cleared by a power cycle, the same armed state booted
again with no app opened and no host session:

- `boot.log`: `agent start requested`, `bridge start requested`,
  `app-start worker requested`
- the worker launched at `19:19:07Z` (`attempt=1 rc=0`) and then stood down
- `/cmd` and `/run` both returned root through the relay
- UI `running=false`, `visible=false`
- relay `sdb connect` and `sdb push` succeeded afterwards

So both starters work on separate boots: the platform list (first boot) and
the worker fallback (second boot). They do not double-launch: the worker's
per-iteration running check stands down when the platform wins, and
`app_launcher -s` on a running id is a no-op.
