# Q60T debloat verification and rollback sheet

For the owned `GQ55Q60TGUXZG` on `T-NKLDEUC-2743.0`. This is an **offline run
sheet**, not a report of a TV run. The package IDs and units come from the
[T-44 inventory](debloat-q60t.md), the marker limit from
[T-46](debloat-markers.md), the six switch names from
[T-47](debloat-quick-settings.md), and the commands from `pkgstate`,
`quickstate`, and `hostsfilter`. The base image does not include the TV's live
`/opt` registry. Stop a group if its live ID, unit, or setting does not match.
Keep a recovery channel available; change one group at a time. Never uninstall.

## Common readback and pass rule

Before any package action, inspect one candidate with `pkgstate plan disable ID`
or `pkgstate plan enable ID`. For a proposed batch, use
`pkgstate plan disable --file IDS.txt` (or `enable`). The plan reads the owner
UID, complete app mapping and both registry flags, and prints one stable line
per ID beginning `plan ID apps=CSV state=STATE decision=ready|REFUSE
reason=TOKEN`. A ready line includes the exact proposed `pkgcmd` arguments.
For these system apps, the state of record is global `app_disable`: the
proposed write is `pkgcmd -D -t app -n APP --global` (or `-A` to enable), and
the plan prints `scope=global`. The per-user flag remains a conflict check,
not a write scope.
For a package with two to four app IDs, the plan lists all IDs in `apps=` and
the ordered global `pkgcmd` sequence on one line. Every app must be enabled,
valid and free of a per-user/global conflict for a disable plan (disabled for
an enable plan); one unready app refuses the whole package. Five or more app
IDs refuse with `reason=too_many`. A multi-app action checks every app before
its first write, writes in ascending app-ID order, and reads back each write.
On failure it reverses changed apps in descending order and reports
`rollback=restored` or `rollback=unconfirmed` with the restored app IDs. A
multi-app package remains a separate trial requiring the live feature and
recovery gates in the [ladder](debloat-plan-2026-11-05.md); an offline ready
plan does not admit it automatically.
For an actual `disable|enable --file IDS.txt` action, the file is one transaction:
the helper preflights every resolved app before writing, applies the lines in
file order, reads back each app, and reverses changed apps in reverse order if
one fails. The report lists confirmed restored app IDs while the command exits
with the original failure code. COSS and calendar each have separate package
IDs for their dotted sibling apps; name both package IDs on separate lines in
an explicitly reviewed file batch. They are not one multi-app package. A
successful offline plan alone does not authorize a live batch.
`--file` accepts at most 65536 bytes and 32 nonempty IDs; any refusal suppresses
the entire ready sequence. A refusal or unknown state exits nonzero. A plan
does not call `pkgcmd`, append the log, change a registry, or act on a unit.
Its `unit` and `unit_active`/`unit_pid`/`unit_load` fields are inspection hints
with `unit_proof=unproven`; they do not establish process ownership or a safe
disable. Recheck all live gates immediately before the actual action.

Use the staged scripts by **content**, as required by this TV's UEP behavior.
Set `PKG`, `QUICK`, and `HOSTSFILTER` to their actual staged script paths before
running any row. On the TV, `pkgcmd` must be available and `pkgstate` must run
as UID 0. These functions illustrate the exact invocation form:

```sh
pkgstate() { sh -c "$(cat "$PKG")" sh "$@"; }
quickstate() { sh -c "$(cat "$QUICK")" sh "$@"; }
hostsfilter() { sh -c "$(cat "$HOSTSFILTER")" sh "$@"; }
package_count() { pkgcmd -l | grep -Fc "pkgid [$1]"; }
unit_state() {
    systemctl show "$1" -p LoadState -p ActiveState -p SubState \
        -p MainPID -p UnitFileState -p FragmentPath -p ExecStart
}
```

For every package row, first run `quickstate --ids GROUP | wc -l` (expected
**1**) and confirm that `quickstate --ids GROUP` prints exactly the ID in the
row. Before **and** after the action, run `package_count ID` (expected **1**:
still registered), `pkgstate list`, and `unit_state UNIT` (expected one loaded
unit with the same fragment and command). Save the complete outputs, not just
the counts. Inspect the unit's `MainPID` and the relevant process list; no
process alone is insufficient. `pkgstate list` reflects recorded actions, and
`pkgcmd -l` proves presence only; neither proves that the unit stopped.
Confirm the package was enabled before changing it using the live registry or
another independent state readback; if its prior state cannot be established,
defer the group. An already stopped unit cannot show a stop caused by this
action; record that baseline and defer the positive claim.

The default record is `/opt/usr/share/tvroot/pkgstate.jsonl` (or
`TIZ0WN_PKGSTATE_LOG` if set). Immediately after each `pkgstate` call, read its
last line. A successful disable has this shape, with the row's exact ID and a
real UTC timestamp; an enable has `"action":"enable"`:

```json
{"id":"org.tizen.acr-service-app","app_id":"org.tizen.acr-service-app","action":"disable","rc":0,"utc":"YYYY-MM-DDTHH:MM:SSZ"}
```

Single-ID records retain that shape. Multi-app and file-batch attempts add `"tx"` (UTC
`YYYYMMDDTHHMMSSZ` plus shell PID), with one record per app. Compensating
writes also have `"revert":true`; their `action` remains the requested
`disable` or `enable`. Review the complete transaction's records and rollback
report rather than only its last line.

The **positive check** for a package row is a successful record plus a live
`inactive`/`dead` unit and `MainPID=0`, with no matching service process after
checking its command line. If disabling only affects a later launch, observe
that transition before passing the row. Record pre and post RSS (same process
and units) only when measurable; leave RAM delta **unmeasured** otherwise.
Any unexpected unit, process, or readback is a failure and triggers reversal.

The **negative check for every row** is to operate Home, app store, YouTube
playback, DRM playback, remote input, and network access. Record a result for
each, plus the row's feature-specific check. A pass requires **record/action
+ positive evidence + every negative check** together. For settings and DNS,
the recorded before/after choice or filter state replaces the package JSON
record. An unchanged `pkgcmd -l` count alone is never a pass. After reversal,
repeat the same pre-state commands and require equality of ID count, recorded
package activation state, unit state and process behavior (or the original setting/filter
state). Where a service was already inactive, compare against that baseline;
do not invent a RAM saving. The append-only log will have new disable and
enable lines, so log text itself is not expected to equal its pre-state. If
enabling does not restart a previously active unit, reboot and repeat the
comparison before declaring reversal complete.

## Direct-binary and separate-daemon units

The live 2026-11-05 correction separates these from package state. ACR uses
`acr.path`, `acr.service`, and `contents-recognition-service.service`; NFC runs
its binary directly from `com.samsung.tv.nfc-monitor.service`. Disabling the
corresponding app does not establish that these units stopped. Inspect each
unit's `LoadState`, `ActiveState`, `UnitFileState`, command and process before
choosing a unit trial. Keep the package and unit records separate.

For a reviewed unit trial, stage `payload/unitstate` under `/opt` and invoke it
by content, as with `pkgstate`. `unitstate off UNIT...` writes one validated
name per line to `$D/units.off` (default `$D=/opt/usr/share/tvroot`), then
applies `systemctl mask --runtime UNIT` before `systemctl stop UNIT` for each
name. The boot hook validates the whole file and reapplies runtime masks after
SMACK setup and before requesting the agent. A runtime mask alone dies on
reboot; persistence depends on that off-list and hook. `unitstate list` prints
each listed name with live `ActiveState` and `Masked` readback. The default
per-unit JSONL record is `$D/unitstate.jsonl` with `unit`, `action`, `rc`, and
`utc` fields.

After an `off`, require a successful record, a masked unit and the expected
process absence; repeat after reboot with recovery available. For reversal,
run `unitstate on UNIT...`, which removes the name atomically, unmasks it at
runtime, and starts it only if installed. Verify the unit and feature baseline
immediately and after another reboot. A pre-existing inactive or failed state
is restored by comparison with its own baseline, not by requiring `active`.
Do not infer package-state success from a unit mask or infer zero telemetry
from process absence.

## Group cards

The `pre` and `post` cells name commands to run immediately around the stated
action. In each package row, also run the common readbacks and six negative
checks above. The post `unit_state` must show a stopped unit for a positive
result; if it does not, reverse and mark the group **not proven**. Do not add a
runtime mask to make an unproven package disable appear successful.
The `tracking` card predates the live ACR correction and is superseded by the
unit-class procedure above. Do not run its package disable as an ACR-daemon test.

| Group | Pre-state and expected count | Exact action and record | Post-state and positive evidence | Reversal and equality |
| --- | --- | --- | --- | --- |
| `tracking` | `quickstate --ids tracking` = `org.tizen.acr-service-app` (1); `package_count org.tizen.acr-service-app` = 1; `unit_state org.tizen.acr-service-app.service`; record ACR process/RSS. | `pkgstate disable org.tizen.acr-service-app`; last JSON line must name this ID, `disable`, `rc:0`. | Repeat count (1), `pkgstate list`, and unit/process readbacks; ACR unit inactive/dead, `MainPID=0`, no ACR process. Verify viewing-data collection behavior only if observable; do not infer zero telemetry. | `pkgstate enable org.tizen.acr-service-app`; require enable `rc:0`, repeat pre commands and ACR behavior. **Volatile:** no firmware marker; a runtime mask, if used separately, needs removal and reboot verification. |
| `hbbtv` | `quickstate --ids hbbtv` = `ug-hbbtv-efl` (1); `package_count ug-hbbtv-efl` = 1; `unit_state hbbtv-service.service`; confirm live app ID `org.tizen.hbbtv-service`. | `pkgstate disable ug-hbbtv-efl`; last JSON line must name this ID, `disable`, `rc:0`. | Repeat count (1), list and unit/process readbacks; `hbbtv-service.service` inactive/dead, `MainPID=0`, no HbbTV service process. Test a broadcast channel and its interactive service. | `pkgstate enable ug-hbbtv-efl`; require enable `rc:0`, repeat pre commands and interactive HbbTV behavior. **Volatile:** no firmware marker; runtime mask does not persist. |
| `multiscreen` | `quickstate --ids multiscreen` = `com.samsung.tv.multiscreen` (1); package count = 1; `unit_state com.samsung.tv.multiscreen.service`; `test -e /home/owner/share/multiviewnotsupport` and record its original result. | `pkgstate disable com.samsung.tv.multiscreen`; last JSON line must name this ID, `disable`, `rc:0`. | Repeat count (1), list and unit/process readbacks; unit inactive/dead, `MainPID=0`, no MultiScreen process. Test casting/Multi View if normally used. | `pkgstate enable com.samsung.tv.multiscreen`; require enable `rc:0`; repeat pre commands and casting/Multi View. The marker's existence must equal its pre-state. **Reboot:** package-state persistence is unverified. The separate F15 vendor marker control needs marker removal **and reboot** for reversal if used; `/tmp/multiview_disable_preloading` is volatile. |
| `voice` | `quickstate --ids voice` = `org.tizen.multi-assistant-service` (1); package count = 1; `unit_state org.tizen.multi-assistant-service.service`; record voice process/RSS. | `pkgstate disable org.tizen.multi-assistant-service`; last JSON line must name this ID, `disable`, `rc:0`. | Repeat count (1), list and unit/process readbacks; unit inactive/dead, `MainPID=0`, no multi-assistant process. Test remote microphone, voice input, and accessibility behavior. | `pkgstate enable org.tizen.multi-assistant-service`; require enable `rc:0`; repeat pre commands and voice behavior. **Volatile:** no firmware marker; runtime mask does not persist. |

The four package groups have **unverified** package-state durability. After an
initial pass, reboot with a recovery path available, repeat the positive and
negative checks, then perform the enable/reversal check. Do not call a runtime
mask persistent. The only previously live-verified marker is MultiScreen's
`/home/owner/share/multiviewnotsupport` ([F15](firmware-analysis.md#findings));
the package disable in this sheet has **not** inherited that proof.

| Group | Pre-state and expected count | Exact action and record | Post-state and positive evidence | Reversal and equality |
| --- | --- | --- | --- | --- |
| `updates` (settings only) | `quickstate --ids updates` prints **0** package IDs. Read **one** Auto Update choice in Settings → Support → Software Update; record its exact before value. Confirm the TV exposes the `db/menu/support/softwareupdate/autoupdate` setting before using it. | If Auto Update is On, choose **Off** in that menu; record `updates: On → Off` with time. If already Off, record no change; there is no disable result to claim. | Read the same menu choice: Off. Check network, store and a manual update check still work, alongside the common negatives. No update service is disabled. | Set the menu to the recorded before value, reread it, and require equality. **Reboot:** reread the choice after reboot before claiming it persists. |
| `promotions` (settings only) | `quickstate --ids promotions` prints **0** package IDs. Locate **Samsung Promotion** under notification settings and record its one current choice. If absent, stop this group. | Turn Samsung Promotion notifications Off in the TV UI; record `promotions: <before> → Off` with time. No Buxton key is known on this Q60T. | Reread the same choice: Off. Observe notification behavior if one is available; run all common negatives. Do not claim Home ads are removed. | Restore the recorded choice and reread it for equality. **Reboot:** reread after reboot before claiming persistence. |
| `dns-filter` (T-48, separate from the six switches) | `hostsfilter status` = `inactive` (0 applied); record `/etc/hosts` contents/namespace count and the exact proposed domains. If already applied, stop and identify its owner first. Package ID count = **0**. | `hostsfilter apply exact.example.com` with each owner-chosen, exact hostname as a separate argument; record command, domains, time, exit code and every namespace warning. Protected suffixes are refused. | `hostsfilter status` = `applied`; no namespace warning; verify each exact hostname resolves to the intended `0.0.0.0` or `::` block entry in affected namespaces. Run store, update check and all common negatives. A PID 1 status alone does not prove every namespace. | `hostsfilter restore`; record exit code and warnings; `hostsfilter status` = `inactive`; compare PID 1 hosts with saved `hosts.original` and verify each affected namespace is unmounted/restored. **Reboot/controller:** binds are volatile; any reapplication needs a controller, and a reboot must be checked separately. |

`exact.example.com` is a placeholder, not a recommended block target. The
filter only covers exact `/etc/hosts` names in namespaces it entered; direct IP,
other DNS paths and namespace entry failures remain outside the proof. Its
protected suffixes include `samsungapps.com`, Samsung cloud time/CDN hosts,
`samsungqbe.cn`, and `svdca.samsungqbe.com`; do not work around a refusal.
After `restore`, retained owner-only `hosts.original` and `hosts.filtered` are
state files, not evidence that a bind is active.

## Do not disable yet: 8 IDs

The six T-44 `unknown` rows stay enabled: `com.samsung.tv.pdss-client`,
`com.samsung.tv.preview-updater`, `com.samsung.tv.preview-downloader`,
`com.samsung.tv.context-aware-agent`, `org.tizen.voice-onboarding`, and
`org.tizen.ambientapp`. The two service-less proposed rows,
`com.samsung.google-cal-sync` and `com.samsung.calendar-account-manager`,
also wait for a live unit/process and recovery path. Keep the core Home,
store, DRM, input, network, security, update machinery and protected
`com.samsung.tv.coba.adagent` enabled. The other T-44 optional candidates
(screen mirroring, content sharing, NFC and wireless audio) have no T-47
group or live verification in this sheet.

## One-page run order

1. Record model/build, recovery path, baseline `pkgcmd -l`, group expansion,
   unit/process state, RSS if measurable, feature use, six negative checks,
   setting choices, and DNS filter status. Resolve any mismatch before action.
2. Choose **one** group. Run its pre commands and record the expected count.
   Execute its exact action once; save the JSON line or settings/filter record.
3. Run the adjacent post commands. Require the positive evidence **and** all
   six negatives plus the feature check. If any fail, reverse now and verify
   pre-state equality; mark the group failed.
4. If it passes, keep that one change for an observation period. Where marked,
   reboot with a recovery path and repeat the checks. A failed reboot check
   triggers reversal; a runtime mask or DNS bind needs its own controller.
5. Only after that group's reversal path is proven, keep or restore it by an
   explicit owner decision, then move to the **next** group. Preserve each
   group's before/action/after/reversal record separately.
