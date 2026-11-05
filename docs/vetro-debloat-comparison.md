# Vetro debloat versus the Q60T prototype — static comparison

Scope: one owned `GQ55Q60TGUXZG` on the captured Tizen 5.5 build
`T-NKLDEUC-REL-202607022001`. This is a specification, not a TV run. The
partial live capture is `/tmp/debloat-audit/live-inventory.txt` and
`context.txt`; its `pkgcmd -l` lines are sometimes truncated and its registry
flags are not labelled by database. The older image inventory
([Q60T inventory](debloat-q60t.md)) supplies unit and marker hypotheses.
Neither source proves a package-state change on this set. The T-84 plan exists,
and the T-85 `pkgstate plan` implementation is present as uncommitted work;
their task statuses do not establish independent acceptance.

## Mechanism and decision

> **Live correction 2026-11-05:** on this Q60T `--uid 5001` was a no-op for a
> system app (ok reply, no write); `--global` worked and survived a reboot.
> `pkgstate` now writes `--global`. The decision column below is superseded on
> that point; read `docs/debloat-plan-2026-11-05.md`.

| Question | Vetro code | Our code | Q60T decision |
| --- | --- | --- | --- |
| Write scope | [`main.js`](/tmp/vetro/app/service/main.js) emits `pkgcmd '+(desired?'-D':'-A')+' -t app -n '+id+' --global`; [`quick-settings.js`](/tmp/vetro/app/service/quick-settings.js) loops over IDs with `pkgcmd ... -n "$id" --global`. Its older [`rooting/service/debloat-commands.js`](/tmp/vetro/rooting/service/debloat-commands.js) instead constructs `pkgcmd ... -n "$id" --uid "$u"`, but the app HTTP path above is the compared current action. | [`pkgstate`](../exploits/tiz0wn-root/payload/pkgstate) executes `pkgcmd "$flag" -t app -n "$app" --global`. | ~~Prototype owner-scoped `--uid`.~~ **Corrected live:** owner scope is a no-op for system apps; use `--global`, one app per trial, and verify both flags around it. `system`/`preload` labels describe origin, not scope. |
| State read | [`app-registry.js`](/tmp/vetro/app/service/app-registry.js) selects `COALESCE((SELECT is_disabled FROM package_app_info_for_uid u WHERE u.app_id=a.app_id AND u.uid=OWNER_UID),a.app_disable)` and then overlays the owner's separate per-user database row. Vetro's HTTP path calls this inventory after a global write. | `read_state()` selects the owner's `is_disabled` first, falling back to global `app_disable`. T-85 `plan_row()` reads **both** flags independently and refuses unknown or conflicting values. | Capture the global and owner rows separately before and after. A Vetro effective-state read may hide a changed global flag behind an unchanged per-user override; an effective read alone is not proof of `--global` or `--uid` semantics. |
| Other rows | Both Vetro commands name **one app ID**. `--global` requests the app's global disable flag (`package_app_info.app_disable`); `--uid` requests that app's owner-specific `package_app_info_for_uid.is_disabled`. Neither command names sibling app IDs. Vetro does not read the raw global flag, other users' rows, or siblings after its command; the code cannot establish which of those rows the firmware actually leaves untouched. | `resolve_app()` rejects a package whose lookup returns multiple app IDs. A `--global` action must change `app_disable`; the helper still reads the per-user override and refuses a conflict. | Treat these as scope expectations to verify, not measured Q60T effects. Abort if the owner row does not change as expected, the global row or a sibling changes, or any row is unreadable. Do not claim that `--global` is safer for a system/preload app; this capture cannot prove how this firmware applies either flag. |

Vetro's single-component HTTP route restricts system components to a pinned
`VERIFIED_GLOBAL_IDS` set and verifies the refreshed registry value, then
attempts the inverse global command on error. Its quick-setting group loops
over many app IDs, checks the refreshed inventory, and attempts to restore
changed members. These are application-level compensations, not a database
transaction across app IDs. The Q60T helper preflights app mapping, invokes
one `--uid` command, checks the effective owner state, and appends
`{"id", "app_id", "action", "rc", "utc"}` JSONL. A mismatch is recorded and
refused; it does **not** automatically restore the previous flag. For `--file`,
preflight precedes the first write but later failures can leave earlier rows
changed. Therefore the prototype is **one ID per trial**, with a separately
verified enable reversal; no batch file and no inferred all-or-nothing result.

Vetro's component startup-flag path backs up the original
`app_onboot,app_autorestart` pair per app under `startup-backups`, runs
`BEGIN IMMEDIATE; UPDATE ...; COMMIT;`, then reads the updated field. That SQL
transaction is for **one flag**, not for `pkgcmd` or an entire debloat group.
The backup is created only if absent; the code does not compare an old backup
with the current row before a later update. Our append-only JSONL records
attempts and mismatches with UTC and gives an audit trail, but is not a
pre-state backup or automatic rollback. The prototype should retain Vetro's
immediate readback and explicit restoration attempt as design lessons, and
our durable action record, full preflight, ambiguity refusal and independent
reversal checks. It must report a failed restore as unconfirmed, never as
atomic rollback.

## Catalogue translation and protected anchors

`ADS_PATTERNS` in Vetro's [`debloat.js`](/tmp/vetro/app/service/debloat.js)
tests substrings of the concatenated app and package IDs. A match classifies
a row; it does not prove the same role on this Q60T. The only matching ID in
the supplied *selected* live capture is `org.tizen.acr-service-app`. An ID not
printed there is **not** proved absent from the full registry.

| Vetro pattern | Q60T translation | Disposition for this prototype |
| --- | --- | --- |
| `adplatform` | No matching live ID captured. | Unknown; no target. |
| `acr-service` | `org.tizen.acr-service-app` appears in `pkgcmd -l` as an `rpm` system app, with a `false` app row and inactive `org.tizen.acr-service-app.service`. | Keep this **exact ID** as the first candidate, subject to the batch gate below. |
| `ad-web-framework` | No matching live ID captured. | Unknown; no target. |
| `adplayer` | No matching live ID captured. | Unknown; no target. |
| `targeted-ad` | No matching live ID captured. | Unknown; no target. |
| `canalysis` | No matching live ID captured; the offline marker map has `canalysis-service.service`, which is not a live app mapping. | Unknown; no target. |
| `analytics` | No matching live ID captured; a broad substring alone is insufficient. | Drop the broad match from the Q60T prototype. |
| `nvision-analysis` | No matching live ID captured. | Unknown; no target. |
| `contents-recognition` | The capture's **process** `/usr/bin/contents-recognition-service` (PID 2580) is not a `pkgcmd -l` app row. | Unknown association; protect it from a guessed action and resolve its relationship to ACR first. |
| `vision-data-recognition` | No matching live ID captured. | Unknown; no target. |
| `com.samsung.tv.iacr` | No matching live ID captured. | Unknown; no target. |
| `screen-analysis` | No matching live ID captured. | Unknown; no target. |
| `PRIVACY_PATTERNS: privacy` | No matching live ID captured; a privacy screen can also be the control for consent. | Drop the broad match from the prototype; preserve any such UI until its role is proved. |

Vetro's hard exclusions and gates are also **not** Q60T target evidence:

- `com.samsung.tv.coba.adagent` and its `.*` app/package descendants are
  protected by Vetro's `isProtected()`, explicit `validateTargets()`, component
  action availability and quick-setting exclusion. Vetro says Smart Hub Home
  loads `ResourceAdvertise` from that package. Our `pkgstate` rejects the same
  exact ID and descendants. Keep the protection even though the supplied live
  capture does not enumerate this anchor.
- `vetrotvapp` and descendants are protected in Vetro's component actions and
  excluded from its quick-setting groups. For a Q60T port, replace this with
  **the port's own controller app/service IDs** and protect its recovery path.
- Vetro's quick-setting area groups skip every `role === 'keep'`; its
  component toggle requires a known boolean state and either a removable user
  app or a pinned verified system ID. Uninstall additionally requires a
  removable non-system package and no protected sibling. These are gates, not
  evidence that a Q80A role holds here.
- Vetro deliberately omits `org.tizen.ambientapp` from its verified toggle
  list because a Q80A boot script may retry its launch indefinitely. The Q60T
  image inventory already marks it unknown/keep; leave it protected pending
  this set's boot-path proof. Vetro's quick-setting tests also exclude the
  assistant hub and Voice Guide TTS from the fixed voice list; do not import
  its area-wide voice switch.
- Our additional Q60T anchors are the CoBA Home family (`coba.home`,
  `coba.apps`, `coba.setting`, `coba.smartthings`, `coba.ambientcontentart`),
  `com.samsung.tv.csfs`, `ContentServiceManager`,
  `org.tizen.content-tiles-provider`, `org.tizen.easysetup-daemon`,
  `org.tizen.ssoservice`, `com.samsung.tv.built-in-app-upgrader`, and the
  Home/store, TV and DRM playback, input, network, security and update paths.
  These are protected by the Q60T plan's default keep rule and feature gates,
  even where `pkgstate` has no hardcoded ID check. Keep the existing recovery
  channel available. Preserve `com.samsung.tv.pdss-client`, preview updater
  and downloader, context-aware agent, voice onboarding, ambient app and
  `com.samsung.tv.bleproximity` while their roles remain unknown.

## Q60T-first three-tier catalogue

All rows are **package-state proposals**, never uninstall proposals. “None
captured” means only the supplied limited process sample. Each ID must first
match the complete live `pkgcmd -l` package and app mapping; `pkgstate plan`
must report `ready`, with matching owner/global flags and no ambiguity. A unit
name from the offline image is a hypothesis until its live fragment,
`ExecStart`, conditions and process ownership agree.

| Tier | Captured package and app IDs | Unit / process or absence in capture | Deciding check |
| --- | --- | --- | --- |
| **Prototype now** | `org.tizen.acr-service-app` → same app ID, `false` | `org.tizen.acr-service-app.service` inactive, MainPID 0; separate `contents-recognition-service` PID 2580 has unknown ownership. | Resolve PID 2580's relationship, require exact one-app mapping and both flags, then run the single trial below. |
| **Prototype after evidence** | `com.samsung.tv.multiscreen` → same app ID, `false` | Matching unit inactive; no matching process in limited capture. Offline negative conditions: `/home/owner/share/multiviewnotsupport` and `/tmp/multiview_disable_preloading`. | Read live unit conditions and both marker states; test casting and Multi View while preserving markers. |
| **Prototype after evidence** | `org.tizen.ScreenMirroring-daemon` → same app ID, `false` | Matching unit inactive; no matching process in limited capture. | Confirm live launch/process path; controlled discovery and mirror-session check. |
| **Prototype after evidence** | `org.tizen.multi-assistant-service` → same app ID, `false` | Unit active with MainPID 0; matching command PID 2607. | Reconcile unit/PID; test microphone, voice and accessibility behavior. |
| **Prototype after evidence** | `com.samsung.tv.nfc-monitor` → same app ID, `false` | Unit active, MainPID and matching command PID 1857. | Check NFC discovery/pairing and ordinary remote/Bluetooth pairing. |
| **Prototype after evidence** | `com.samsung.tv.waapp-contents-provider` → same app ID, `false` | Unit failed, MainPID 0, yet matching command PID 2940. | Reconcile failed unit with live process; test wireless-audio browse and playback. |
| **Prototype after evidence, parked** | `ug-hbbtv-efl` → **no app ID printed**; `org.tizen.hbbtv-service` is only an offline manifest hypothesis. | `hbbtv-service.service` failed; separate `hbbtv_app` PID 3417 has unknown package ownership. | Full live app mapping and PID ownership, then broadcast/HbbTV feature check; otherwise no action. |
| **Prototype after evidence, parked** | `com.samsung.google-cal-sync` → same app ID, `false` | No matching unit in offline image or limited live capture; no process captured. | Establish a complete launch/process path and controlled sync check. |
| **Prototype after evidence, parked** | `com.samsung.tv.coss` → `com.samsung.tv.coss` and `.provider.d2d`, both `false`. | Unit inactive; no matching process in limited capture. | Current helper refuses this ambiguous package; keep both app rows unchanged until a separately reviewed multi-app design and full content-sharing checks exist. |
| **Prototype after evidence, parked** | `com.samsung.calendar-account-manager` → primary and `.alert`, both `false`. | No matching unit in offline image or limited live capture; no process captured. | Same ambiguity refusal; establish alert/account behavior and an independently reviewed multi-app design first. |
| **Community / other models** | Vetro's Q80A `VERIFIED_GLOBAL_IDS`: `com.samsung.tv.acr`, `com.samsung.tv.canalysis-service`, `com.samsung.tv.vision-data-recognition-service`, `com.samsung.tv.contents-recognition-dbmgr`, `com.samsung.tv.nvision-analysis-dbmgr`; plus its Alexa, Google and Bixby quick-setting IDs. **None is a captured Q60T package/app row here.** | Units and markers unestablished on this set. | Each owner supplies a complete local `pkgcmd -l`/registry/unit/process inventory, exact feature checks and reversal proof before any ID enters that model's catalogue. No inherited “verified” label. |

The Q60T prototype's **data** are model/build identity; exact package-to-all-app
mapping and package type (`rpm`/`tpk`, system/preload/removable); owner UID and
both registry flags; unit names, fragments, launch commands and conditions;
marker paths and volatility; protected anchors; feature checks and expected
reversal state. A community port replaces and verifies those data. The
**engine** remains exact-ID validation, full mapping and conflict preflight,
owner-scoped single-app `pkgcmd`, readback, append-only records, refusal on
ambiguity or mismatch, one-trial reversal and verification. It does not
silently convert a model catalogue into an area-wide switch or uninstall path.

## The one prototype batch

Batch 1 contains **only `org.tizen.acr-service-app`**, and only after the
separate PID 2580 relationship and the full package/app, owner/global flag and
unit mapping are resolved. Before a later authorized trial, save model/build,
recovery reachability, full `pkgcmd -l` rows, owner UID, both flags, the
unit's live properties and a complete relevant process list. Record Home,
store, YouTube, DRM, remote input, network and ordinary viewing baselines.
The current capture does not satisfy all these gates; **no action is admitted
from it alone**.

The proposed trial uses the current helper's single-app owner-scoped disable,
then requires a successful JSONL record, owner disabled readback, unchanged
global and sibling rows, no ACR service process or launch under controlled
viewing, and all baseline features passing. An already inactive unit is not
positive evidence. If a controlled launch cannot show the effect, record
“effect unproven” and reverse. Any mapping, flag, process, unit or feature
mismatch aborts immediately. A provisional pass still needs a reboot check
with recovery available, exact owner-scoped enable reversal, readback and the
same feature checks; because the baseline unit was inactive, repeat after a
second reboot before calling reversal proven. Stop after this one row. No TV
command was run for this comparison.
