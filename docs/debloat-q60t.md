# Q60T background package inventory (offline)

Target: `GQ55Q60TGUXZG`, `T-NKLDEUC-2743.0`. This is an inventory of the
partial base-rootfs extraction at `/tmp/tiz-rootfs2`, not a read of the TV's
current package database. The extraction has zero-byte binaries and does not
include the writable `/opt` app registry. No package or unit was changed.

The image's package list is `/usr/share/packages/*.xml`: 205 XML names, of
which 204 are readable manifests; `org.tizen.menu.xml` is empty and cannot
establish a package record. The 204 manifest IDs group as 101 `org.tizen.*`,
32 `com.samsung.tv.coba.*`, 43 other `com.samsung.tv.*`, 12 other
`com.samsung.*`, and 16 other IDs. `/usr/apps/` has additional directories,
but a directory name alone is not proof of a registered package. The table
selects background candidates and a few dependency anchors from the readable
manifests; it is not a claim that the other manifests are safe to remove.

Roles use Vetro's `tracking`, `not-used` (its "Not used at home"), `optional`,
and `keep` vocabulary ([Vetro `README.md`, Debloater section](https://github.com/andrearicci93/vetro/blob/main/README.md#debloater)).
`unknown` is this inventory's conservative addition. Vetro's catalog comes
from a Q80A, so its package decisions were not copied here. `disable` means a
*proposed reversible package state change* to validate on this Q60T; it is not
an instruction to edit an image or a report that package-state control works.
`uninstall` is not recommended for any row: most listed manifests say
`removable="false"`, and no reinstall artifact is in this extraction.

In the table, `M/name.xml` expands to `/usr/share/packages/name.xml` and
`U/name.service` to `/usr/lib/systemd/system/name.service` in the extraction.
The manifest path is written in every row. A unit is counted only when its
active `ExecStart` names the package/app ID or launches it through a matching
wrapper. `Kill-switch` means a negative `ConditionPathExists=!…` in that
unit; a positive condition is recorded but is not a kill-switch. The rank puts
identified tracking first, then unused features, then optional features;
within a role, a matching startup unit precedes a manifest-only service app.
Ranks 1–10 are the ten proposed reversible **disable** rows, subject to the
unit checks below. Only rank 3 has an already verified on-device reversal
([F15](firmware-analysis.md#findings)).

| Rank | Package ID | Role | Action | Observed path or service | Purpose and evidence | Kill-switch |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | `org.tizen.acr-service-app` | tracking | disable | `M/org.tizen.acr-service-app.xml`; `U/org.tizen.acr-service-app.service` | Manifest calls it `acr-service-app`; unit starts that service app. ACR denotes automatic content recognition. | No |
| 2 | `org.tizen.multi-assistant-service` | not-used | disable | `M/org.tizen.multi-assistant-service.xml`; `U/org.tizen.multi-assistant-service.service` | Manifest says `Multi Assistant Service`; unit launches the same ID for voice assistants. | No; positive `/tmp/AFTER_PRODUCTION` condition |
| 3 | `com.samsung.tv.multiscreen` | optional | disable | `M/com.samsung.tv.multiscreen.xml`; `U/com.samsung.tv.multiscreen.service` | Unit starts MultiScreen in background; [F15](firmware-analysis.md#findings) verified its marker, stop, and reboot reversal on this TV. | Yes: `!/home/owner/share/multiviewnotsupport`; also `!/tmp/multiview_disable_preloading` |
| 4 | `org.tizen.ScreenMirroring-daemon` | optional | disable | `M/org.tizen.ScreenMirroring-daemon.xml`; `U/org.tizen.ScreenMirroring-daemon.service` | Manifest declares a Screen Mirroring service app; unit launches it. Keep if screen mirroring is used. | No |
| 5 | `com.samsung.tv.coss` | optional | disable | `M/com.samsung.tv.coss.xml`; `U/com.samsung.tv.coss.service` | Manifest describes a Content Sharing Service Framework; unit wrapper launches its service app. Keep if content sharing is used. | No; positive `/run/.wm_ready` condition |
| 6 | `com.samsung.tv.nfc-monitor` | optional | disable | `M/com.samsung.tv.nfc-monitor.xml`; `U/com.samsung.tv.nfc-monitor.service` | Manifest and unit both name NFC Monitor; unit runs its app binary after Bluetooth framework. | No |
| 7 | `com.samsung.tv.waapp-contents-provider` | optional | disable | `M/com.samsung.tv.waapp-contents-provider.xml`; `U/com.samsung.tv.waapp-contents-provider.service` | Manifest describes a wireless-audio music contents provider; unit launches that service app. | No |
| 8 | `ug-hbbtv-efl` | optional | disable | `M/ug-hbbtv-efl.xml`; `U/hbbtv-service.service` | Manifest maps package `ug-hbbtv-efl` to service app `org.tizen.hbbtv-service`; unit launches that app. Keep if HbbTV is used. | No |
| 9 | `com.samsung.google-cal-sync` | optional | disable | `M/com.samsung.google-cal-sync.xml`; service app in manifest | Manifest calls it Google Calendar Sync TV App. No matching startup unit was found; confirm whether it runs before changing state. | No unit found |
| 10 | `com.samsung.calendar-account-manager` | optional | disable | `M/com.samsung.calendar-account-manager.xml`; service app in manifest | Manifest declares an account-manager service app. Calendar account support is optional only if unused; no matching startup unit was found. | No unit found |
| — | `com.samsung.tv.bleproximity` | optional | keep | `M/com.samsung.tv.bleproximity.xml`; service app in manifest | Manifest declares a Bluetooth proximity service app and says `removable="true"`; no startup unit or reinstall artifact was found. Keep pending a unit inventory and recovery route. | No unit found |
| — | `com.samsung.tv.pdss-client` | unknown | keep | `M/com.samsung.tv.pdss-client.xml`; service app in manifest | Manifest says Personal Data Sync Service; its data flow and dependencies are not established by the text. | No unit found |
| — | `com.samsung.tv.preview-updater` | unknown | keep | `M/com.samsung.tv.preview-updater.xml`; `U/com.samsung.tv.preview-updater.service` | Manifest says preview updater; unit's `preview-updater.sh` launches the app. Whether this is an ad feature or Home dependency is unproven. | No |
| — | `com.samsung.tv.preview-downloader` | unknown | keep | `M/com.samsung.tv.preview-downloader.xml`; app path in manifest | Manifest names `LiveRecommendDownloader.dll`, but declares a UI app and no matching startup unit was found. Do not infer background tracking from its name. | No unit found |
| — | `com.samsung.tv.context-aware-agent` | unknown | keep | `M/com.samsung.tv.context-aware-agent.xml`; app path in manifest | Manifest declares a UI app; no matching startup unit or purpose evidence was found. | No unit found |
| — | `org.tizen.voice-onboarding` | unknown | keep | `M/org.tizen.voice-onboarding.xml`; app path in manifest | Manifest names voice onboarding but declares a UI app; no matching startup unit was found. | No unit found |
| — | `org.tizen.ambientapp` | unknown | keep | `M/org.tizen.ambientapp.xml`; app path in manifest | Manifest declares an Ambient UI app; no matching startup unit was found. | No unit found |
| — | `com.samsung.tv.coba.smartthings` | keep | keep | `M/com.samsung.tv.coba.smartthings.xml`; app path in manifest | CoBA SmartThings component is part of the core Home family; preserve the `com.samsung.tv.coba.*` package by default. | No unit found |
| — | `com.samsung.tv.coba.ambientcontentart` | keep | keep | `M/com.samsung.tv.coba.ambientcontentart.xml`; app path in manifest | CoBA Ambient Art component; preserve the core CoBA package by default even when Ambient is unused. | No unit found |
| — | `com.samsung.tv.coba.home` | keep | keep | `M/com.samsung.tv.coba.home.xml`; app path in manifest | Manifest calls it CoBA Home Component; core Home anchor. | No unit found |
| — | `com.samsung.tv.coba.apps` | keep | keep | `M/com.samsung.tv.coba.apps.xml`; app path in manifest | CoBA Apps component; core app navigation/store anchor. | No unit found |
| — | `com.samsung.tv.coba.setting` | keep | keep | `M/com.samsung.tv.coba.setting.xml`; app path in manifest | CoBA Settings component; core control anchor. | No unit found |
| — | `com.samsung.tv.csfs` | keep | keep | `M/com.samsung.tv.csfs.xml`; app path in manifest | Manifest describes FirstScreen; Home dependency anchor. | No unit found |
| — | `ContentServiceManager` | keep | keep | `M/ContentServiceManager.xml`; `U/ContentServiceManager.service` | Manifest and unit identify the content service manager; dependencies were not shown safe to remove. | No |
| — | `org.tizen.content-tiles-provider` | keep | keep | `M/org.tizen.content-tiles-provider.xml`; `U/org.tizen.content-tiles-provider.service` | Manifest and unit identify a content tiles provider; unit follows `content-db-provider.service`. Preserve the Tizen content path. | No |
| — | `org.tizen.easysetup-daemon` | keep | keep | `M/org.tizen.easysetup-daemon.xml`; `U/org.tizen.easysetup-daemon.service` | Manifest declares setup daemon and unit launches it; preserve setup and network provisioning. | No |
| — | `org.tizen.ssoservice` | keep | keep | `M/org.tizen.ssoservice.xml`; `U/org.tizen.ssoservice.service` | Manifest declares SSO service and unit launches it; preserve account/security support. | No |
| — | `com.samsung.tv.built-in-app-upgrader` | keep | keep | `M/com.samsung.tv.built-in-app-upgrader.xml`; `U/com.samsung.tv.built-in-app-upgrader.service` | Manifest describes the built-in .NET app upgrade manager; preserve app maintenance. | No |
| — | `com.samsung.tv.aoc-enabler` | keep | keep | `M/com.samsung.tv.aoc-enabler.xml`; `U/com.samsung.tv.aoc-enabler.service` | Unit starts only under positive `/tmp/b2btv_mode`; exact role is unclear, so keep. | No; positive B2B condition |

## How to confirm on the unit

1. Read the live installed package IDs and app IDs. Compare them with the
   manifest IDs above; in particular, confirm `ug-hbbtv-efl` versus its
   `org.tizen.hbbtv-service` app ID. Treat absent or changed IDs as unmatched.
2. Read each candidate unit's live `LoadState`, `UnitFileState`, `ActiveState`,
   `FragmentPath`, conditions, and `ExecStart`; overlays may differ from this
   base image. Check whether manifest-only service apps actually run.
3. Record current feature use (mirroring, HbbTV, NFC, wireless audio, calendar,
   voice) and current process/RSS state before choosing one candidate.
4. Check that the package-state control can be reversed and that a recovery
   channel remains available. Test one `disable`, read back the package and
   unit states, reboot, and re-enable/read back before considering another.
5. For MultiScreen specifically, compare the live unit's conditions with
   [F15](firmware-analysis.md#findings); removal of its existing marker plus a
   reboot is the documented reversal. Do not infer the same marker behavior
   for the other units.
