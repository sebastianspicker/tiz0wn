# Installed app inventory — 2026-11-05

Read-only capture on the owned Q60T (`T-NKLDEUC-2743.0`), through `POST /cmd`.
No package state was changed; every `app_disable` is `false`.

## Totals

| Measure | Count |
| --- | ---: |
| `pkgcmd -l` rows | 332 |
| system packages | 329 |
| user packages | 2 |
| disabled apps | 0 |
| currently running app processes | 12 |

## User packages

| Package | Type | Name | Version |
| --- | --- | --- | --- |
| `tiz0wnprob` | wgt | tiz0wn local probe | 1.0.0 |
| `GCyQjAzWhP` | wgt | `app` | 1.0.0 |

`GCyQjAzWhP` is not ours and has a generic name. It is the only unknown user
package; worth identifying before any cleanup.

## Families

The system list is dominated by Samsung TV framework, not viewer apps.

| Prefix | Count |
| --- | ---: |
| `com.samsung.tv.*` | 137 |
| `com.samsung.tizen.*` | 11 |
| `com.samsung.ep.*` (hotel) | 4 |
| 8 random `[A-Za-z0-9]{10}` web apps | 8 |
| everything else (one-offs, `org.tizen.*`) | remainder |

The 137 `com.samsung.tv.*` entries are mostly CoBA/Smart Hub components,
service helpers and preload modules. A package count is therefore not a menu
count; most are invisible.

## Running app processes, by RSS

| PID | RSS KiB | Process |
| ---: | ---: | --- |
| 605 | 188188 | `com.samsung.tv.csfs` (Home) |
| 3212 | 60284 | `com.samsung.tv.multiscreen` |
| 3620 | 48372 | `org.tizen.hbbtv` (`hbbtv_app`) |
| 604 | 35976 | `org.tizen.tv-viewer` |
| 1831 | 33872 | `slive-provider-daemon` |
| 5379 | 25632 | `org.tizen.netflix-app` |
| 2140 | 21956 | `org.tizen.voice-app` |
| 2641 | 19000 | `com.samsung.tv.dotnet-policy-checker` |
| 2633 | 18236 | `easysetup-daemon` |
| 5318 | 18012 | `mde-framework` |
| 882 | 17736 | `bms-service` |

`multiscreen` and `hbbtv` are only running because they were started during the
trial reverts and never stopped. They are not baseline processes.

## Removed 2026-11-05

33 `wgt` packages from classification tiers 1–3 were uninstalled; after the
following reboot the count stayed 299, the removed IDs stayed absent and the
kept anchors remained. Original: after the
inventory (`pkgcmd -l` 332 → 299), each with a JSONL snapshot in
`pkgstate.jsonl` and a copy under `/opt/usr/share/tvroot/uninstall-backup/`
for `adplatform`. tpk/rpm rows could not be removed (`-4`) and remain.

## After the reboot, 2026-11-05 15:50

Verified: `pkgcmd -l` 299, 53 app rows disabled across 41 packages, Home
running, anchors present, `/run` root. Both states persist.

One caveat: `com.samsung.tv.airplay-app` still runs because its unit starts the
binary directly; a package disable cannot stop that class. The same applies to
any direct-unit row and needs `unitstate`, as with NFC.

## Where this matters

- The debloat targets trialled earlier are all back at baseline.
- Any further debloat should start from this list, not from package names.
- `GCyQjAzWhP` and the eight random-named web apps are the least understood
  user-space entries.
