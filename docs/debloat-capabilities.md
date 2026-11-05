# Q60T debloat capabilities — static survey, 2026-11-05

Scope: the owned Q60T on `T-NKLDEUC-2743.0`. This is a survey of the staged
2026-11-05 captures, not a new TV trial. The seven-target package/unit ladder
was restored to baseline; see [the live plan](debloat-plan-2026-11-05.md).
`/tmp/debloat-audit/capabilities.txt` and `capabilities2.txt` are the command
and registry evidence below. Vetro source is from `/tmp/vetro/app/service/` and
describes a different Q80A build unless stated otherwise. A command's presence,
a registry column, and a measured feature effect are three different claims.

## Evidence boundary

- **Proven here:** `pkgstate` global `app_disable` round trips survived reboot
  for the named app-class trials; `unitstate` runtime masks plus its boot off-list
  round tripped for the named unit-class trials. The capture found `pkgcmd` and
  `buxton2ctl`, 105 `svcapp` and 289 `uiapp` rows, 162 true `app_nodisplay`
  rows, 15 non-system removable package rows, and a read-only `/etc/hosts`.
  `touch /etc/hosts` failed. These inventory facts do not prove new levers.
- **Proven by Vetro on another model:** its Q80A HbbTV observation says the
  menu value alone left the app running; after a stop it relaunched within four
  seconds, while stopping the HbbTV service first kept it off for the 40-second
  observation. Its Q80A menu values were Off `19` and On `20`.
  See `hbbtv.js`. Those timings, values and restart paths are not Q60T results.
- **Inferred or unknown:** every other prospective effect below, including
  Q60T launch/menu consumers of display flags, Q60T feature-key semantics,
  `pkgcmd -r` recovery, and DNS-blocking effectiveness. Vetro's code or a
  Q80A firmware string is evidence of a candidate, not Q60T behavior.

## Lever matrix

“Covered” names a tool that can already make the stated change; it does not
mean the lever was validated for a new target. Persistence refers to the
change itself, not to whether a stopped process later restarts.

| Lever | Granularity | Persistence | Reversal | Evidence status | Conflict with our tools | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| `pkgcmd -u -n PKG` uninstall; `-r -t TYPE -n PKG` reinstall | Whole package and all its components/data relationship | Uninstall is durable if accepted; reinstall outcome unknown | `-r` is advertised, but the capture shows no package source or successful storeless reinstall. A verified matching signed package archive and a tested install/reinstall route would be needed before treating it as recoverable. | **Here:** help syntax and 15 `package_system=false`, `package_removable=true` rows. **Unknown:** actual uninstall/reinstall and data retention. | Bypasses `pkgstate`'s per-app readback and transaction log; could remove the registry rows that `pkgstate` needs. Vetro `component-actions.js` offers uninstall on its model. | High: missing archive, dependencies, data or store account can make reversal impossible. |
| `pkgcmd -k -n PKG` kill; Vetro's `app_launcher -k APP` stop | Running package or one app process, respectively | Transient; restart source and delay are target-specific | Start the exact app if known, or allow its supervisor/boot to restart; neither is guaranteed on Q60T | **Here:** `-k` help only. **Vetro Q80A:** HbbTV relaunches via its service; `quick-settings.js` stops enabled group members after disabling flags. | A kill alone leaves `pkgstate` flags and `unitstate` masks unchanged; it cannot stand in for either. | Medium: can interrupt work or be immediately undone by a supervisor. |
| `pkgcmd -c -t TYPE -n PKG` clear data; `-g -T 1 -n PKG` data-size query | Package user data | Durable data deletion | Restore a verified package-data backup, if one exists; activation/reinstall is not a data restore | **Here:** help syntax only; no before/after sizes or high-data package rows in the captures. `-T 1` is the advertised data-size category, not measured reclaim. | `pkgstate` and `unitstate` preserve data; neither logs or reverses a clear. | High: account state, settings and app data may be lost for little storage gain. |
| `package_app_info.app_nodisplay` | One app's display metadata | Registry value presumably durable; no Q60T write/boot proof | Restore the exact saved value, if a write and consumer are validated | **Here:** 162 true rows. **Vetro:** `app-registry.js` reads it as `show`; `dock-catalog.js` instead reads `widgetinfo.is_hidden`. The Q60T Samsung launcher/menu consumer is not identified. | No current writer. If proven, a separate display-state tool should own backed-up, read-back changes; `pkgstate` owns activation. | Medium: a hidden entry can become hard to find without changing whether it runs; direct registry edits risk inconsistency. |
| `package_disable` versus `app_disable` versus `app_support_disable` | `app_disable` is per app ID; granularity of the other two is unproved | Only `app_disable` boot persistence is measured | `pkgstate enable` reverses only global `app_disable` for resolved app IDs | **Here:** global `app_disable` was read back and affected launcher availability on named trials. The captures do not identify consumers or even a reliable readback query for `package_disable` or `app_support_disable`; unlabelled flag counts cannot establish them. | `pkgstate` uses `package_app_info.app_disable` and checks per-user `is_disabled` conflicts. Do not write other flags behind it. | High for unproved flags: mismatched package/app state or silent no-op. |
| `pkgcmd -D/-A -t app --global` on `svcapp` versus `uiapp` | One app ID; `pkgstate` also handles a package resolving to two to four app IDs | Proven for the named app-class rows across reboot; no kind-specific conclusion | `pkgstate enable` with per-app readback and the documented second-boot check | **Here:** 105 `svcapp`, 289 `uiapp` rows in the capture; no joined same-package type/behavior sample. Existing Q60T trials show an `app_launcher -s` class can be disabled, while direct-binary/daemon units need `unitstate`. Whether disabling only an `svcapp` leaves its sibling UI usable (or the converse) is unknown. | Already covered by `pkgstate`; unit-backed components need `unitstate`, with their own baseline. Do not assume a package-wide result from one app row. | Medium: a UI may launch but fail through a disabled dependency, or an independently started service may keep running. |
| Buxton2/vconf feature keys | One key, possibly one user or system namespace | Likely stored, but no Q60T feature-key boot check | Restore exact recorded type/value only after proving a read/write path | **Here:** `/usr/bin/buxton2ctl` exists, but `buxton2ctl list system` returned nothing; `app_control` and `vconf` binaries were absent. This does not establish whether `vconftool` is present. The only key used by our Q60T tooling is `db/sdk/develop/ip`, which is a development IP, not debloat. **Vetro Q80A:** `privacy.js` reads `db/Canalysis-service/recognition_status`, `db/acr/reset`, `db/adagent/psid`, `db/menu/system/data-service_do-not-track`, and `db/TCF/TVPlus/TCFEnabled`; `hbbtv.js` uses `db/menu/system/data-service`; `quick-wins.js` uses `db/menu/support/softwareupdate/autoupdate`. None is a proven Q60T ACR/ads/voice/ambient gate. | No current feature-key writer. `quickstate` maps app IDs only; Vetro's Q80A vconf writes are separate. | Medium to high: consent or update values are not equivalent to stopping a component; wrong type/value may change user settings. |
| `hostsfilter` exact-host block through `/etc/hosts` | Exact hostname, in each mount namespace successfully entered | `/opt` backup and filtered file persist; bind mounts are volatile and need a controller after reboot | `hostsfilter restore` unmounts its marked binds; verify every affected namespace | **Here:** `/etc/hosts` is read-only. **Code:** `payload/hostsfilter` saves PID 1's original into `/opt`, writes `0.0.0.0` and `::` exact-name lines, then bind-mounts the filtered file over `/etc/hosts` per namespace. No Q60T resolver/traffic result is captured. Vetro `local-dns.js` uses a similar bind approach on Q80A and states that custom DNS, cache or direct IP can bypass it. | Already covered by `hostsfilter`. `pkgstate` and `unitstate` act at different layers; their success cannot prove DNS suppression. | Medium: partial namespaces, wrong hostnames, or blocking a needed endpoint can break features; hostname scope is narrower than service shutdown. |
| `.webappservice.db` (`widgetinfo`) and `/opt/share/webappservice/apps_icon` | Web-app tile metadata or individual icon files, not a package process | `/opt` edits could persist, but no Q60T edit proof | Restore byte-exact DB/file backups and cache state, if ever validated | **Here:** the `apps_icon` directory exists. **Vetro Q80A:** `dock-catalog.js` reads `widgetinfo` ID/title/Tizen ID/`is_hidden` and icons for its dock. Q60T schema, Samsung Home's consumer, and cache response are unmeasured. | Neither `pkgstate` nor `quickstate` touches these paths. Removing a tile or icon is not a package disable. | High: broken Home entries or database integrity for no proven background-work reduction. |
| Vetro startup flags `app_onboot` / `app_autorestart` | One app row | Registry-backed; Q60T boot trigger is documented for our own service, not as a general debloat lever | Restore both saved values; Vetro `component-actions.js` backs them up before direct SQL updates | **Here:** `docs/boot-start-evidence-2026-11-04.md` proves `app_onboot` matters to our app. **Vetro:** direct registry edit with readback. General Q60T feature effect unproved. | Direct SQL bypasses `pkgstate` and can conflict with `unitstate` boot masking or recovery startup. | High for protected/boot-critical apps; flag alone may not stop an active process. |
| Vetro HbbTV brake, MultiScreen preload marker, Ambient stop, update/menu settings | Per feature, with separate marker, process and key states | HbbTV brake is tmpfs and Vetro reapplies it; MultiScreen preload marker is under app data; Ambient stop needs boot reapplication; key persistence on Q60T unknown | Restore the captured key, marker and process state for the particular feature | **Vetro Q80A:** `hbbtv.js` combines key, `/tmp/hbbtv_do-not-relaunch`, service and app stops; `quick-wins.js` describes `disable_preloading`, Ambient stop and auto-update key. **Here:** the Q60T ladder separately proved a MultiScreen package flag with no marker. None of Vetro's combined controls has a Q60T effect trial. | `quickstate` marks HbbTV/updates/promotions as settings-only and emits no ID for the latter two. A separate settings controller would be needed; do not conflate a marker with `pkgstate`. | Medium to high: multiple states can disagree, and a restarted supervisor can undo a process-only change. |
| Vetro leftover installer-file cleanup | Individual `.wgt`, `.tpk`, `.rpm` files directly under two owner staging directories | File deletion durable | Only an independently retained copy restores a deleted installer | **Vetro:** `leftovers.js` lists and removes matching files, then measures free space. No Q60T staging inventory or size result is supplied. | No current tool. Deleting staged installers could destroy the only local candidate for storeless package recovery. | High until archives are inventoried; this is storage cleanup, not service debloat. |

### What the captures do and do not identify

The removable list includes `org.tizen.cloud-launcher`, two Chinese voice
packages, weather, YouTube, AirPlay, SmartTV, IoT and template packages. The
15 rows establish eligibility flags, not safe removal, whether they are in
use, or a recovery source. Neither capture contains per-package data-size
results, so there is no evidence-based `-c` priority order. If storage were the
goal, the relevant rows would be those with measured nonzero data size and a
verified data backup, not simply large package binaries.

For feature-key discovery on this build, `buxton2ctl list system` is a negative
result, not an empty keyspace. A future static survey can extract declared
storage candidates from the model's menu metadata and firmware strings as
Vetro's `menu-settings.js` does, then test read-only, per-key queries and types
on the Q60T before any write. The captured Q60T data names no verified key
that gates ACR, ads, voice or Ambient. In particular, a PSID or consent key
being readable would not prove that it suppresses ads or recognition.

Vetro's `blocklist.js` labels its hostname groups as firmware, reported or
unverified on the Q80A; it explicitly says blocking effects were not tested.
Those names are not Q60T traffic evidence. Its `privacy.js` reads consent and
recognition state, but does not disable anything. Its `app-facts.js` is a
Q80A manifest-derived dependency/catalogue aid, not a Q60T behavior map.

## Ranked next prototypes

1. **Per-component `svcapp`/`uiapp` split through `pkgstate`.** First identify
   one optional Q60T package with both kinds by a read-only registry join and
   record both app IDs, global/per-user flags, unit launch paths and baseline
   UI/service behavior. Trial one app ID at a time with `pkgstate`, read back,
   reboot, restore and recheck the sibling. **Abort** on any sibling flag
   change, an unexplained surviving/respawned process, a UI regression, or a
   failed readback/reversal. Without a suitable joined pair, no trial is
   admitted.
2. **Transient kill/respawn map for one optional app.** With the exact package,
   process and supervisor recorded, measure a single `pkgcmd -k` stop and its
   process/feature state over a bounded observation and one reboot, then
   restore the baseline if needed. **Abort** if the target mapping is unclear,
   a needed feature fails, or the process cannot be accounted for. This would
   determine whether kill has any practical effect beyond the existing flags.
3. **Exact-host DNS trial with `hostsfilter`.** First observe a Q60T request for
   one nonessential, exact hostname and save namespace/hosts baselines; apply
   one entry, verify resolution and the intended feature boundary in every
   affected namespace, then restore. **Abort** on a namespace warning, failed
   restore, store/update/network regression, or no observable DNS effect.

## Do not use yet

- **Uninstall/reinstall:** the 15 removable flags do not provide a signed
  package archive or a proven storeless `-r` route. Vetro's staging cleanup
  could remove a possible archive before its value is known.
- **Clear data or delete leftovers:** no measured data-size payoff and no
  verified backup/recovery path in these captures.
- **Direct `/etc/hosts` edits:** the rootfs is read-only. Use only the existing
  reversible bind-mount helper for a future, measured exact-host trial.
- **Direct package/webapp registry or icon edits:** `package_disable`,
  `app_support_disable`, `app_nodisplay`, `widgetinfo` and icon consumers are
  not validated as Q60T debloat controls; a display change is not a stop.
- **Blind Buxton/vconf or Vetro Q80A settings writes:** listing returned no
  keys here, `vconf` is absent, and the named Q80A keys have no proven Q60T
  ACR/ads/voice/Ambient effect. Keep consent and update choices distinct from
  service suppression.
