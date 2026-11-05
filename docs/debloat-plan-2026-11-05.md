# Q60T live-registry debloat plan — 2026-11-05

Planning only for the owned lab TV; no command in this plan has been run on it.
The evidence is `/tmp/debloat-audit/live-inventory.txt` and `context.txt`.
Those files report Tizen 5.5.0, build `T-NKLDEUC-REL-202607022001`, and 128
running service apps. The older [image inventory](debloat-q60t.md),
[marker map](debloat-markers.md), [setting map](debloat-quick-settings.md), and
[verification sheet](debloat-verify.md) supply hypotheses and checks, not live
registry state. The owner uses none of screen mirroring, HbbTV, NFC, wireless
audio, calendar, or voice assistants. No captured row is disabled; `pkgstate`
has not been tried on this set. A `false` registry line and a disabled systemd
unit file do not establish the same thing. The capture does not label every
registry value by database, so both per-user `is_disabled` and global
`app_disable` must be read back before a trial.

The table uses `—` for no matching unit in the offline inventory or no process
in the **limited capture**, not proof of absence. RSS values are KiB. Every
unit, app mapping, flag, and process association below must be checked again
immediately before its row; a changed build or mismatch stops that row.
`pkgstate` acts on **one app ID**, even when given a package ID. Its
`pkgcmd -D -t app -n APP --uid UID` does not cover a sibling app row, and the
current `resolve_app` refuses packages with multiple app IDs. A proposed
revert is executable only after the matching disable has passed preflight.

| Live package ID | All captured app IDs; flags | Unit and captured state | Captured process / PID / RSS | Expected user-visible effect; feature check | Exact proposed revert and admission |
| --- | --- | --- | --- | --- | --- |
| `org.tizen.acr-service-app` | `org.tizen.acr-service-app:false` | `org.tizen.acr-service-app.service`: loaded, inactive, static, MainPID 0 | No named ACR process in package sample; `contents-recognition-service` PID 2580, 22024 KiB appears in top RSS and needs ownership check. | Viewing recognition may stop on later launch; normal TV viewing and recommendations still work. Do not claim telemetry stopped from unit state alone. | `pkgstate enable org.tizen.acr-service-app`; admit only if PID 2580 is shown unrelated or its relationship is understood. |
| `org.tizen.multi-assistant-service` | `org.tizen.multi-assistant-service:false` | `org.tizen.multi-assistant-service.service`: loaded, active, unit file disabled, MainPID 0 | Matching command PID 2607, 8136 KiB; determine why systemd MainPID is 0. | Voice assistants may stop; test remote microphone, voice input, and accessibility behavior. | `pkgstate enable org.tizen.multi-assistant-service`; first prove the running process belongs to this app and can be observed after the change. |
| `com.samsung.tv.multiscreen` | `com.samsung.tv.multiscreen:false` | `com.samsung.tv.multiscreen.service`: loaded, inactive, unit file disabled, MainPID 0 | No matching process in limited capture. | Casting or Multi View may stop; explicitly test both even though the owner does not use them. | `pkgstate enable com.samsung.tv.multiscreen`; record both live marker states. If the separate `/home/owner/share/multiviewnotsupport` control was used, its reversal is **remove that marker and reboot**, not this command. |
| `org.tizen.ScreenMirroring-daemon` | `org.tizen.ScreenMirroring-daemon:false` | `org.tizen.ScreenMirroring-daemon.service`: loaded, inactive, unit file disabled, MainPID 0 | No matching process in limited capture. | Screen mirroring may stop; try discovery and a mirror session. | `pkgstate enable org.tizen.ScreenMirroring-daemon`; require live unit and app mapping to match. |
| `com.samsung.tv.coss` | `com.samsung.tv.coss:false`; `com.samsung.tv.coss.provider.d2d:false` | `com.samsung.tv.coss.service`: loaded, inactive, unit file disabled, MainPID 0 | No matching process in limited capture. | Content sharing or device-to-device discovery may stop; test both. | **Hold; no executable revert with current `pkgstate`.** It rejects the ambiguous package, including the primary app ID. A future reviewed two-app transaction must name and read back both app IDs; reverse its successful writes in reverse order on partial failure. Do not touch either row now. |
| `com.samsung.tv.nfc-monitor` | `com.samsung.tv.nfc-monitor:false` | `com.samsung.tv.nfc-monitor.service`: loaded, active, unit file disabled, MainPID 1857 | Matching command PID 1857, 12476 KiB. | NFC discovery/pairing may stop; test NFC setup, plus ordinary remote and Bluetooth pairing. | `pkgstate enable com.samsung.tv.nfc-monitor`; require the same PID/command association at preflight. |
| `com.samsung.tv.waapp-contents-provider` | `com.samsung.tv.waapp-contents-provider:false` | `com.samsung.tv.waapp-contents-provider.service`: loaded, **failed**, unit file disabled, MainPID 0 | Matching command PID 2940, 7768 KiB despite failed unit. | Wireless-audio content browsing may stop; test wireless-audio pairing, browse, and playback. | `pkgstate enable com.samsung.tv.waapp-contents-provider`; failed unit alone is not a pass while PID 2940 or a successor still runs. |
| `ug-hbbtv-efl` | **No app ID printed in live capture.** Offline manifest suggests `org.tizen.hbbtv-service`; unverified live. | `hbbtv-service.service`: loaded, **failed**, unit file disabled, MainPID 0 | Separate `/usr/apps/org.tizen.hbbtv/bin/hbbtv_app` PID 3417, 51536 KiB in top RSS; ownership/relationship unknown. | HbbTV interactive broadcast may stop; test a broadcast channel and its interactive service. | **Hold until live app mapping and PID 3417 ownership are established.** Then `pkgstate enable ug-hbbtv-efl` only if the package resolves uniquely and the disable actually affected the intended app. The `hbbtv_app` process cannot be assigned to this package by name alone. |
| `com.samsung.google-cal-sync` | `com.samsung.google-cal-sync:false` | No matching unit in offline image; none reported live. | No matching process in limited capture. | Google calendar sync may stop; test account sign-in and a controlled calendar sync. | `pkgstate enable com.samsung.google-cal-sync`; **hold** until a complete process/launch-path check supplies positive evidence. |
| `com.samsung.calendar-account-manager` | `com.samsung.calendar-account-manager:false`; `com.samsung.calendar-account-manager.alert:false` | No matching unit in offline image; none reported live. | No matching process in limited capture. | Calendar account management or alerts may stop; test account access and a controlled alert. | **Hold; no executable revert with current `pkgstate`.** It rejects the ambiguous package. A future reviewed two-app transaction must name and read back both app IDs; no action on `.alert` separately now. |

## Batch ladder

These are **trial queues**, never `--file` disable sets. Run exactly one row at
a time, restore and verify its original state before admitting the next row,
and keep the recovery channel available. A later row is skipped if its gate is
unmet; do not replace it with a guessed app ID or systemd mask. Thus any
failure belongs to the single row under trial. Save each row's before, action,
after, reboot, and reversal records independently.

| Batch | Ordered, independently reversible trials | Boundary and reason |
| --- | --- | --- |
| 1 — inactive background | `org.tizen.acr-service-app` only | The captured unit is inactive and has no direct user control path. Identify the separate content-recognition process first. This is the first actionable row. Calendar rows remain parked because the capture has no unit/process proof and one has two app IDs. |
| 2 — inactive optional paths | `com.samsung.tv.multiscreen`, then `org.tizen.ScreenMirroring-daemon`, each fully reversed before the next. `com.samsung.tv.coss` is parked at this boundary. | Both units are inactive, but casting/mirroring are user-facing, so they follow batch 1. COSS has two app IDs and the present helper cannot change or reverse the package as one transaction. |
| 3 — running or failed services | `org.tizen.multi-assistant-service`, `com.samsung.tv.nfc-monitor`, `com.samsung.tv.waapp-contents-provider`, then `ug-hbbtv-efl`, **one row per separate observation and reversal cycle**. | Active processes come after inactive units. Failed units with live processes come last because the unit verdict is misleading. HbbTV remains parked until its app and process mapping are proved. If a trial fails, end the batch; do not advance to the next row. |

`com.samsung.google-cal-sync` and `com.samsung.calendar-account-manager` are
outside the executable ladder pending a complete live launch/process map and,
for the latter, a multi-app transaction design. They are tabled so the absence
of a unit does not silently turn into a disable recommendation. The three
queues do not constitute one combined safe list.

### Gates and evidence for every batch

Before **each row**, save: build/model and recovery reachability; full
`pkgcmd -l` package and app lines (without truncation); owner UID; package to
app mapping in the global registry; both the owner's per-user `is_disabled`
and global `app_disable` values for **every** app row; `pkgstate list` and the
last log line; the unit's LoadState, ActiveState, SubState, MainPID,
UnitFileState, FragmentPath, ExecStart and conditions where a unit exists; a
complete relevant process command-line/PID/RSS search; and the six baseline
checks from [the verification sheet](debloat-verify.md): Home, app store,
YouTube playback, DRM playback, remote input, network. Capture the row's
feature check before changing anything. Confirm exactly one installed package
and that the target app is enabled. Do not use a top-RSS excerpt as a negative
process check. For MultiScreen, also save both marker existence results;
package-state control must not add or remove a marker.

1. **Batch 1:** Pre-state must show the same inactive ACR unit, one exact app,
   and a resolved relationship for PID 2580. Pass only with a successful
   `pkgstate` disable record and disabled-state readback, no ACR service
   process or launch under a controlled viewing check, and all seven feature
   and common checks. Because it starts inactive, an unchanged unit is not
   evidence of suppression; if a controlled launch cannot be observed, record
   “effect unproven” and reverse. Abort on any mapping, process, readback, or
   feature mismatch.
2. **Batch 2:** Pre-state must reproduce each inactive unit, single app ID,
   and (for MultiScreen) both markers and live condition lines. Require a
   controlled casting/Multi View or mirroring attempt to show the targeted
   path cannot start after disable, with the package readback, record, and all
   common checks passing. A still-running related process, different unit
   conditions, any failed feature check, or a change to either marker aborts
   that row. Do not enter COSS without a separately reviewed multi-app plan.
3. **Batch 3:** Pre-state must identify the active process despite MainPID 0
   for voice, match PID 1857 to NFC, and reconcile each failed unit with its
   still-running process. For voice, NFC, and wireless audio, pass only if the
   intended app's disabled readback and record match, the related process
   stops or a controlled relaunch is refused, and common plus feature checks
   pass. A failed unit alone never passes. HbbTV additionally needs the live
   package/app mapping and proof whether PID 3417 belongs to that package;
   otherwise skip it. Any unknown app, surviving process without an explained
   relationship, failed readback, or user regression aborts immediately.

For **each** successful trial, check immediately, then reboot with recovery
available to test whether the package state and feature result persist; do not
infer persistence from the old MultiScreen marker result. Run its exact enable
revert, read back the package/app and feature state, then **reboot again before
declaring reversal proven** when the baseline unit was inactive, failed, or
active but did not restart on enable. Recheck the same unit/process and common
features after that boot. A pre-existing failed unit need not become healthy;
it must return to its recorded baseline behavior, including its process if
that process was related. If reversal fails, stop the ladder and use the
retained recovery path. RSS deltas are measured only for the same identified
process; otherwise report them as unmeasured. A package still present in
`pkgcmd -l`, or a reboot by itself, never satisfies the pass rule.

## Dry-run contract for a future `pkgstate plan`

`pkgstate plan disable|enable ID` and `pkgstate plan disable|enable --file
IDS.txt` should print a deterministic, machine-readable preflight for every
input line: requested package ID, resolved **complete** app-ID set, owner UID,
per-user and global flags per app, current effective state, proposed
`pkgcmd -D` or `-A -t app -n APP --uid UID`, and either `ready` or a precise
refusal reason (unknown, ambiguous, protected, already in target state,
conflicting flags, unreadable registry, or missing dependency). It should
identify whether a package is multi-app and refuse to present a single-app
command as package-wide coverage. It may report external unit/process checks
as **required but not proven**, not invent a process result from registry data.
Print no secrets. A successful plan is an inspection result, never a claim
that a live disable works or that reboot persistence is established.

The dry run must not invoke mutating `pkgcmd`, create or append the JSONL log,
write a state file, alter either registry, touch markers, stop/start/mask a
unit, or change a process. It may use only read-only database and package
queries. For `--file`, cap input at 65536 bytes and 32 nonempty lines, then
validate the entire file before any per-row action: exact syntax and ID
allowlist, no blank/malformed/protected or duplicate IDs, every package
present and mapped, all app IDs known, all
per-user/global states readable, consistent action direction, and no overlap
through two names for the same app. Emit the complete proposed sequence only
if all lines pass; otherwise fail the **whole** plan with line-specific errors
and no apply-ready partial list. An eventual executor must repeat this
preflight immediately before its first write and stop on drift. The current
`pkgstate` lacks `plan`; these are requirements for a future change, not a
command available for this run.

## Non-goals

No uninstall, image edit, runtime mask, or automatic reboot. Do not touch
CoBA, `com.samsung.tv.coba.adagent`, or Home/store/DRM/input/network anchors.
Do not call `app_disable` or `pkgcmd -D -t app` for an unknown app ID. Do not
touch `provider.d2d` or `.alert` as separate experiments: the current
single-app `pkgcmd` call does **not** cover those sibling rows, and no atomic
multi-app reversal is established.

## Live corrections, 2026-11-05 10:24Z

Three assumptions from the offline table did not survive the live set.

1. **ACR is not driven by the app unit.** `org.tizen.acr-service-app.service`
   is only `app_launcher -s …` and sits inactive. The actual daemons are
   separate static units: `acr.path` (path trigger), `acr.service`
   (`/usr/bin/acr`, pid 3883) and `contents-recognition-service.service`
   (`/usr/bin/contents-recognition-service`, pid 2585), both active and
   `System::Privileged`. The package manifest lists only the app exec. A
   package disable therefore does not stop recognition. ACR needs unit
   control, not package state, or both.
2. **NFC is also a direct-binary unit.** `com.samsung.tv.nfc-monitor.service`
   runs `/usr/apps/.../nfc-monitor` itself, not `app_launcher -s`, so a
   package disable does not stop the running unit either. Same class as ACR.
3. **`--uid` is a no-op for these system apps; `--global` works.** On
   `org.tizen.multi-assistant-service`, `pkgcmd -D -t app -n ID --uid 5001`
   printed `val[ok]` but wrote no per-user row and left `app_disable=false`;
   `pkgstate` correctly failed its own readback. Re-running with `--global`
   set `app_disable=true` and the platform stopped the process within seconds.
   No per-user row appeared in either case.

So the T-86 decision "prototype owner-scoped `--uid`" is now corrected for
system apps: use `--global`, and keep the per-user read only as an override
indicator. `pkgstate` must be updated before the next row.
T-88 implements this correction; see the [global-scope readback rule](debloat-verify.md#common-readback-and-pass-rule).

### First live trial, `org.tizen.multi-assistant-service`

Performed by hand to test the mechanism, not yet a `pkgstate` run:

- pre: unit active, process pid 2634 (8276 KiB), `app_disable=false`
- `--uid 5001` disable: `ok`, then no state change, `pkgstate` recorded rc=1
- `--global` disable: `app_disable=true`, process gone within seconds, still
  gone after 20 s
- Home (`csfs`) launched, HTTP loopback 200, internet ping up
- unit still reports `ActiveState=active` with `MainPID=0` — the unit state is
  not a usable pass signal for this row

Pending: reboot persistence, then `--global -A` reversal and a second boot.

### Trial result (round trip)

Completed on the same boot sequence:

1. pre-state captured (unit active, pid 2634, global `false`)
2. `--global` disable, readback `true`, process gone, still gone at 20 s
3. common checks still passed (Home launch, loopback HTTP 200, internet)
4. **reboot**: after boot the global flag was still `true` and the process was
   absent; `pkgstate list` reported `disabled`
5. `--global -A` revert, readback `false`, the app returned when launched

So the mechanism and its persistence are proven on this set with `--global`.
The reversal's own boot persistence is the only outstanding confirmation.
`pkgstate` was corrected to `--global` and its live `plan` output now reads
`scope=global` and the exact global command.

### What this means for the catalogue

- Rows whose unit is `app_launcher -s <app id>` are the ones package state can
  actually stop (`multi-assistant`, `ScreenMirroring`, `multiscreen`).
- Rows whose unit runs a binary directly (`nfc-monitor`) or whose daemons are
  separate units (`acr`) need unit control, or will survive a disable.
- `org.tizen.acr-service-app` is not a useful first row; keep it as a unit
  trial with `acr.path`/`acr.service`/`contents-recognition-service.service`.

### Reversal persistence confirmed

Second reboot: `app_disable=false`, the service was running again, and
`pkgstate list` reported `enabled`. The row is fully restored; both
directions survive boot.

## Prototype status

`org.tizen.multi-assistant-service` is the completed prototype row. It proves,
on this set:

- global scope is the working lever; owner scope is a no-op for system apps
- a disable stops the app and survives a reboot
- the enable reversal restores the app and survives a reboot
- Home, loopback HTTP and internet stay up
- the unit state is not a pass signal (`active` with `MainPID=0`)

The catalogue below is therefore **Q60T-validated only for this one class**
(`app_launcher -s` units). Binary-hosted and separate-daemon rows still need
their own trial. Community ports must re-derive the unit class per model.

## Unit-class prototype: ACR (second trial)

`acr.path`, `acr.service` and `contents-recognition-service.service` were
trialled through the new `unitstate` helper, not package state.

Round trip:

1. `unitstate off` all three → `Masked=yes`, inactive, no process
2. reboot → boot hook re-masked all three (`masks=3 stopped=0 failed=0`),
   still inactive, no process
3. `unitstate on` all three → unmasked, path/reactivation brought all three
   back active
4. reboot → empty off-list, hook logged `entries=0`, all three active

Two defects surfaced and were fixed before the result:

- systemd 231 reports a runtime mask as `LoadState=masked` and
  `UnitFileState=bad`; detection moved to `LoadState`
- at ~1 s the manager can still be starting: masking got 1 of 3. The hook now
  retries each mask five times and stops a unit it lost the race to; `on` also
  retries a start that races an unmask

So the unit class is proven and reversible, but the boot hook is timing
sensitive by nature: a slow boot can still land a mask after a start, which is
why the stop follows it. This is the correct lever for ACR, NFC and any future
daemon row; package state remains for `app_launcher -s` rows only.

### Revised catalogue split

| Class | Lever | Proven rows |
| --- | --- | --- |
| `app_launcher -s` app | `pkgstate` global | `multi-assistant` |
| separate or direct unit | `unitstate` off-list | `acr.path`, `acr.service`, `contents-recognition-service` |
| direct-binary unit | `unitstate` (not yet run) | `nfc-monitor` candidate |
| multi-app package | neither yet | COSS, calendar |

## Unit-class prototype: NFC (third trial)

`com.samsung.tv.nfc-monitor.service` runs its binary directly, so it belongs to
the unit class despite being an app package. Round trip: `unitstate off` →
masked, inactive, no process; reboot → hook `masks=1`, still inactive; `on` →
active again; reboot with an empty off-list → active (`MainPID=1645`).

The direct-binary class is proven too. Package state would not have stopped it.

## Package-class prototype: ScreenMirroring (fourth trial)

`org.tizen.ScreenMirroring-daemon` is an `app_launcher -s` row but its unit was
already `failed` before the trial (`app_launcher` exit 255), so the observable
is availability, not a process.

- disable → `app_disable=true`, launcher answers
  `not available for the user 0`
- reboot → still `true`, still refused
- enable → `false`, launcher answers `... launch failed` again (the app's own
  pre-existing failure)
- reboot → still `false`, same failed baseline

So the flag round-trips; the app itself does not start on this build and must
not be counted as a working mirroring feature until that is fixed.

## Package-class prototype: MultiScreen (fifth trial)

`com.samsung.tv.multiscreen` is an `app_launcher -s` row, unit inactive, no
marker files present.

- disable → `app_disable=true`, launcher refuses `not available for the user 0`
- reboot → still disabled and refused
- enable → `false`, launcher starts it again (pid 8299)
- reboot → still `false`, still launches (pid 3104)

Clean round trip. The `multiviewnotsupport` marker is absent, so the state came
from the package flag, not a marker.

## Where the ladder stands

Proven and reverted: `multi-assistant-service`, ACR (3 units), `nfc-monitor`,
`ScreenMirroring-daemon` (flag only; app has a pre-existing failure),
`multiscreen`.

Parked: `com.samsung.tv.coss` and `com.samsung.tv.calendar-account-manager`,
both multi-app packages. They need a transaction that names and reads back both
app IDs, which `pkgstate` does not express yet.

## Cross-package transaction: COSS (sixth trial)

`com.samsung.tv.coss` and `com.samsung.tv.coss.provider.d2d` are **separate
packages** whose IDs look like siblings, so T-90's multi-app branch never
fires. They were trialled through the now-transactional `--file` path, under
one tx id.

- disable both → both `app_disable=true`, one tx, launcher refuses
- reboot → both still true, still refused
- enable both → both false, launcher starts again
- reboot → both false, starts again

The ids file was put in `/tmp` first and vanished on reboot; keep batch files
under `/opt/usr/share/tvroot`.

The transactional `--file` path is the right vehicle for any feature that spans
packages. `--file` order is the apply order, rollback is reverse and bounded,
and the report names every restored app.

Remaining ladder row: `com.samsung.tv.calendar-account-manager` plus its
`.alert` package.

## Multi-app package transaction: calendar (seventh trial)

Live IDs differ from the offline table: the package is
`com.samsung.calendar-account-manager` (no `tv`) and it maps to two app rows,
`…` and `….alert`. The launcher already answered "not available" at baseline,
so the flags are the observable.

- plan → both apps listed, `decision=ready`
- disable via the package → both `app_disable=true`, one tx
- reboot → both still true, still refused
- enable via the package → both false

T-90's multi-app branch works and reverts both rows. Revert boot confirmation
is the remaining step.

Revert boot confirmed: both calendar flags `false` after the boot.

## Ladder complete

All seven trialled targets are at baseline and verified after their final boot:

- every `app_disable` `false`
- `units.off` empty
- `acr.path`, `acr.service`, `contents-recognition-service.service` and
  `nfc-monitor.service` loaded and active

The executable ladder is therefore finished. What remains is catalogue
breadth for other owners, not another Q60T trial: re-derive unit classes per
model, keep the protected anchors, and never batch a row whose unit class or
app mapping is unproven.
