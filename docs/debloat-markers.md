# Q60T firmware condition markers (offline)

Target: `GQ55Q60TGUXZG`, `T-NKLDEUC-2743.0`. This is a read-only inventory of the partial base-rootfs extraction at `/tmp/tiz-rootfs2`, cross-checked against [T-44](debloat-q60t.md). It is not the live unit set or the writable `/opt` app registry. The extracted `/opt` directory is empty and `/prd` is absent. No marker or unit was changed.

`package-equal` means the marker basename exactly equals an ID in the 204 readable `/usr/share/packages/*.xml` manifests. `manual` means a unit exists but has no such marker; the Name match column says whether its basename instead equals the unit service name or neither. `no-unit` means T-44 found no matching startup unit. A `manual` row with `—` for its marker has a unit but no negated condition. These labels describe text equality, not safe actions or a proven persistent path. The `|!` condition is an OR operand, so its presence alone is not a disable switch.

## All negated unit conditions

Paths in Unit are relative to `/tmp/tiz-rootfs2`; each entry quotes the exact normalized condition line (CRLF line endings are omitted). Symlinked `.wants/` references to the same physical unit are counted once. The table includes the separate copies under `/usr/local/BM/EW` and `/usr/share/aul-extension`. There are **47 physical unit files**, **50 negated lines**, and **25 distinct paths**. None of the marker basenames equals a package ID in this extraction: **package-equal 0; manual 47 units; no-unit 0** in this table.

| Package ID in manifests | Unit | Quoted condition | Marker path | Name match | Class |
| --- | --- | --- | --- | --- | --- |
| — | `usr/lib/systemd/system/ac.service:6` | `ConditionPathExists=!/proc/tztv-bootmode` | `/proc/tztv-bootmode` | neither | manual |
| — | `usr/lib/systemd/system/adagent-service.service:3` | `ConditionPathExists=!/opt/usr/share/systemd/system/pisa-service` | `/opt/usr/share/systemd/system/pisa-service` | neither | manual |
| — | `usr/lib/systemd/system/app-boot-manager.service:6` | `ConditionPathExists=!/proc/tztv-bootmode` | `/proc/tztv-bootmode` | neither | manual |
| — | `usr/lib/systemd/system/app-context-manager.service:6` | `ConditionPathExists=!/proc/tztv-bootmode` | `/proc/tztv-bootmode` | neither | manual |
| — | `usr/lib/systemd/system/app-control-service.service:4` | `ConditionPathExists=!/proc/tztv-bootmode` | `/proc/tztv-bootmode` | neither | manual |
| — | `usr/lib/systemd/system/bms.service:5` | `ConditionPathExists=!/opt/usr/share/systemd/system/bms` | `/opt/usr/share/systemd/system/bms` | service name | manual |
| — | `usr/lib/systemd/system/bms.service:6` | `ConditionPathExists=!/proc/tztv-bootmode` | `/proc/tztv-bootmode` | neither | manual |
| — | `usr/lib/systemd/system/bootmode-graphical.service:3` | `ConditionPathExists=!/system_update` | `/system_update` | neither | manual |
| — | `usr/lib/systemd/system/bootmode-graphical.service:4` | `ConditionPathExists=!/run/.standalone` | `/run/.standalone` | neither | manual |
| — | `usr/lib/systemd/system/bootmode-swu-standalone.service:5` | `ConditionPathExists=!/mnt/backup/OS_UPGRADE_FLAG` | `/mnt/backup/OS_UPGRADE_FLAG` | neither | manual |
| — | `usr/lib/systemd/system/bootmode-system-update.service:4` | `ConditionPathExists=!/run/.standalone` | `/run/.standalone` | neither | manual |
| — | `usr/lib/systemd/system/canalysis-service.service:5` | `ConditionPathExists=!/opt/usr/share/systemd/system/canalysis-daemon` | `/opt/usr/share/systemd/system/canalysis-daemon` | neither | manual |
| — | `usr/lib/systemd/system/ci-daemon.service:5` | `ConditionPathExists=!/proc/tztv-bootmode` | `/proc/tztv-bootmode` | neither | manual |
| — | `usr/lib/systemd/system/com.samsung.tv.airplay-service-2.service:3` | `ConditionPathExists=!/opt/usr/share/systemd/system/com.samsung.tv.airplay-service-2` | `/opt/usr/share/systemd/system/com.samsung.tv.airplay-service-2` | service name | manual |
| — | `usr/lib/systemd/system/com.samsung.tv.airplay-service.service:3` | `ConditionPathExists=!/opt/usr/share/systemd/system/com.samsung.tv.airplay-service` | `/opt/usr/share/systemd/system/com.samsung.tv.airplay-service` | service name | manual |
| — | `usr/lib/systemd/system/com.samsung.tv.ghdaemon.service:5` | `ConditionPathExists=!/opt/usr/share/systemd/system/com.samsung.tv.ghdaemon` | `/opt/usr/share/systemd/system/com.samsung.tv.ghdaemon` | service name | manual |
| — | `usr/lib/systemd/system/com.samsung.tv.multiscreen.service:3` | `ConditionPathExists=!/home/owner/share/multiviewnotsupport` | `/home/owner/share/multiviewnotsupport` | neither | manual |
| — | `usr/lib/systemd/system/com.samsung.tv.multiscreen.service:4` | `ConditionPathExists=!/tmp/multiview_disable_preloading` | `/tmp/multiview_disable_preloading` | neither | manual |
| — | `usr/lib/systemd/system/com.samsung.tv.ondevice-voice.service:4` | `ConditionPathExists=!/opt/usr/share/systemd/system/com.samsung.tv.ondevice-voice` | `/opt/usr/share/systemd/system/com.samsung.tv.ondevice-voice` | service name | manual |
| — | `usr/lib/systemd/system/connman.service:4` | `ConditionPathExists=!/proc/tztv-bootmode` | `/proc/tztv-bootmode` | neither | manual |
| — | `usr/lib/systemd/system/coreapp-service.service:5` | `ConditionPathExists=!/proc/tztv-bootmode` | `/proc/tztv-bootmode` | neither | manual |
| — | `usr/lib/systemd/system/dlogutil.service:3` | `ConditionPathExists=!/opt/etc/disable_dlogutil` | `/opt/etc/disable_dlogutil` | neither | manual |
| — | `usr/lib/systemd/system/dotnet-init.service:5` | `ConditionPathExists=!/proc/tztv-bootmode` | `/proc/tztv-bootmode` | neither | manual |
| — | `usr/lib/systemd/system/emergency-log-transmitter.service:4` | `ConditionPathExists=!/tmp/eltlaunch.cond` | `/tmp/eltlaunch.cond` | neither | manual |
| — | `usr/lib/systemd/system/esg-service.service:5` | `ConditionPathExists=!/run/user/5001/esg_block` | `/run/user/5001/esg_block` | neither | manual |
| — | `usr/lib/systemd/system/launchpad-process-pool.service:9` | `ConditionPathExists=!/proc/tztv-bootmode` | `/proc/tztv-bootmode` | neither | manual |
| — | `usr/lib/systemd/system/muse-server.service:3` | `ConditionPathExists=!/run/.standalone` | `/run/.standalone` | neither | manual |
| — | `usr/lib/systemd/system/net-config.service:4` | `ConditionPathExists=!/proc/tztv-bootmode` | `/proc/tztv-bootmode` | neither | manual |
| — | `usr/lib/systemd/system/org.tizen.mbr-daemon.service:3` | `ConditionPathExists=!/run/.standalone` | `/run/.standalone` | neither | manual |
| — | `usr/lib/systemd/system/org.tizen.voice-app.service:5` | `ConditionPathExists=!/opt/usr/share/systemd/system/org.tizen.voice-app` | `/opt/usr/share/systemd/system/org.tizen.voice-app` | service name | manual |
| — | `usr/lib/systemd/system/pisa-service.service:3` | `ConditionPathExists=!/opt/usr/share/systemd/system/pisa-service` | `/opt/usr/share/systemd/system/pisa-service` | service name | manual |
| — | `usr/lib/systemd/system/samsunghealth-service-tv-atoken.service:4` | `ConditionPathExists=!/opt/usr/share/systemd/system/samsunghealth-service-tv` | `/opt/usr/share/systemd/system/samsunghealth-service-tv` | neither | manual |
| — | `usr/lib/systemd/system/samsunghealth-service-tv.service:4` | `ConditionPathExists=!/opt/usr/share/systemd/system/samsunghealth-service-tv` | `/opt/usr/share/systemd/system/samsunghealth-service-tv` | service name | manual |
| — | `usr/lib/systemd/system/scim.service:3` | `ConditionPathExists=!/proc/tztv-bootmode` | `/proc/tztv-bootmode` | neither | manual |
| — | `usr/lib/systemd/system/screen_sharing.service:5` | `ConditionPathExists=!/tmp/ScreenSharing_NOT_SUPPORTED` | `/tmp/ScreenSharing_NOT_SUPPORTED` | neither | manual |
| — | `usr/lib/systemd/system/sddp.service:5` | `ConditionPathExists=!/tmp/SDDP_NOT_SUPPORTED` | `/tmp/SDDP_NOT_SUPPORTED` | neither | manual |
| — | `usr/lib/systemd/system/settings-service.service:4` | `ConditionPathExists=!/proc/tztv-bootmode` | `/proc/tztv-bootmode` | neither | manual |
| — | `usr/lib/systemd/system/slive-provider-daemon.service:5` | `ConditionPathExists=!/opt/usr/share/systemd/system/slive-provider-daemon` | `/opt/usr/share/systemd/system/slive-provider-daemon` | service name | manual |
| — | `usr/lib/systemd/system/stability-monitor.service:7` | `ConditionPathExists=!/proc/tztv-bootmode` | `/proc/tztv-bootmode` | neither | manual |
| — | `usr/lib/systemd/system/swu-auto-upgrade.service:4` | `ConditionPathExists=!/mnt/backup/OS_UPGRADE_FLAG` | `/mnt/backup/OS_UPGRADE_FLAG` | neither | manual |
| — | `usr/lib/systemd/system/swu-core-tv.service:6` | `ConditionPathExists=!/mnt/backup/OS_UPGRADE_FLAG` | `/mnt/backup/OS_UPGRADE_FLAG` | neither | manual |
| — | `usr/lib/systemd/system/swu-service.service:5` | `ConditionPathExists=!/mnt/backup/OS_UPGRADE_FLAG` | `/mnt/backup/OS_UPGRADE_FLAG` | neither | manual |
| — | `usr/lib/systemd/system/swu-verifier-tv.service:6` | `ConditionPathExists=!/opt/backup/OS_UPGRADE_FLAG` | `/opt/backup/OS_UPGRADE_FLAG` | neither | manual |
| — | `usr/lib/systemd/system/sys-kernel-debug-tracing.mount:11` | `ConditionPathExists=!/sys/kernel/debug/tracing/trace` | `/sys/kernel/debug/tracing/trace` | neither | manual |
| — | `usr/lib/systemd/system/systemd-hwdb-update.service:16` | `ConditionPathExists=\|!/usr/lib/udev/hwdb.bin` | `/usr/lib/udev/hwdb.bin` | neither | manual |
| — | `usr/lib/systemd/system/tvs-ht.service:4` | `ConditionPathExists=!/tmp/tvsHTServiceFlagFile` | `/tmp/tvsHTServiceFlagFile` | neither | manual |
| — | `usr/lib/systemd/system/vddebugmenu.service:3` | `ConditionPathExists=!/proc/tztv-bootmode` | `/proc/tztv-bootmode` | neither | manual |
| — | `usr/local/BM/EW/sys/systemd/system/bootmode-graphical.service:3` | `ConditionPathExists=!/system_update` | `/system_update` | neither | manual |
| — | `usr/share/aul-extension/ac.service:6` | `ConditionPathExists=!/proc/tztv-bootmode` | `/proc/tztv-bootmode` | neither | manual |
| — | `usr/share/aul-extension/launchpad-process-pool.service:9` | `ConditionPathExists=!/proc/tztv-bootmode` | `/proc/tztv-bootmode` | neither | manual |

## T-44 package cross-check

Only `com.samsung.tv.multiscreen` has a negated condition among the ten proposed disable rows. Its `/home/owner/share/multiviewnotsupport` marker is the one [F15](firmware-analysis.md#findings) observed surviving a reboot on the owned TV; the second `/tmp` condition is a volatile preloading gate. For the other seven disable rows with units, this image shows **no negated condition**. A runtime mask alone is volatile; any durability of package-state disable must be verified separately on the TV. The final two disable rows have no matching startup unit in T-44.

| Package | Unit | Marker and quoted condition | Class | Action needed |
| --- | --- | --- | --- | --- |
| `org.tizen.acr-service-app` | `usr/lib/systemd/system/org.tizen.acr-service-app.service` | — (no negated condition) | manual | No firmware marker gate; verify package-state persistence separately. Runtime mask is volatile. |
| `org.tizen.multi-assistant-service` | `usr/lib/systemd/system/org.tizen.multi-assistant-service.service` | — (no negated condition) | manual | No firmware marker gate; verify package-state persistence separately. Runtime mask is volatile. |
| `com.samsung.tv.multiscreen` | `usr/lib/systemd/system/com.samsung.tv.multiscreen.service` | `ConditionPathExists=!/home/owner/share/multiviewnotsupport`; `ConditionPathExists=!/tmp/multiview_disable_preloading` | manual | For durable unit suppression, F15 uses `/home/owner/share/multiviewnotsupport`; confirm live condition and reversal first. No marker written here. |
| `org.tizen.ScreenMirroring-daemon` | `usr/lib/systemd/system/org.tizen.ScreenMirroring-daemon.service` | — (no negated condition) | manual | No firmware marker gate; verify package-state persistence separately. Runtime mask is volatile. |
| `com.samsung.tv.coss` | `usr/lib/systemd/system/com.samsung.tv.coss.service` | — (no negated condition) | manual | No firmware marker gate; verify package-state persistence separately. Runtime mask is volatile. |
| `com.samsung.tv.nfc-monitor` | `usr/lib/systemd/system/com.samsung.tv.nfc-monitor.service` | — (no negated condition) | manual | No firmware marker gate; verify package-state persistence separately. Runtime mask is volatile. |
| `com.samsung.tv.waapp-contents-provider` | `usr/lib/systemd/system/com.samsung.tv.waapp-contents-provider.service` | — (no negated condition) | manual | No firmware marker gate; verify package-state persistence separately. Runtime mask is volatile. |
| `ug-hbbtv-efl` | `usr/lib/systemd/system/hbbtv-service.service` | — (no negated condition) | manual | No firmware marker gate; verify package-state persistence separately. Runtime mask is volatile. |
| `com.samsung.google-cal-sync` | — | — (no matching unit) | no-unit | Confirm live unit/process before any state change. |
| `com.samsung.calendar-account-manager` | — | — (no matching unit) | no-unit | Confirm live unit/process before any state change. |
| `com.samsung.tv.bleproximity` | — | — (no matching unit) | no-unit | Keep; no marker action. |
| `com.samsung.tv.pdss-client` | — | — (no matching unit) | no-unit | Keep; no marker action. |
| `com.samsung.tv.preview-updater` | `usr/lib/systemd/system/com.samsung.tv.preview-updater.service` | — (no negated condition) | manual | Keep; no marker action. |
| `com.samsung.tv.preview-downloader` | — | — (no matching unit) | no-unit | Keep; no marker action. |
| `com.samsung.tv.context-aware-agent` | — | — (no matching unit) | no-unit | Keep; no marker action. |
| `org.tizen.voice-onboarding` | — | — (no matching unit) | no-unit | Keep; no marker action. |
| `org.tizen.ambientapp` | — | — (no matching unit) | no-unit | Keep; no marker action. |
| `com.samsung.tv.coba.smartthings` | — | — (no matching unit) | no-unit | Keep; no marker action. |
| `com.samsung.tv.coba.ambientcontentart` | — | — (no matching unit) | no-unit | Keep; no marker action. |
| `com.samsung.tv.coba.home` | — | — (no matching unit) | no-unit | Keep; no marker action. |
| `com.samsung.tv.coba.apps` | — | — (no matching unit) | no-unit | Keep; no marker action. |
| `com.samsung.tv.coba.setting` | — | — (no matching unit) | no-unit | Keep; no marker action. |
| `com.samsung.tv.csfs` | — | — (no matching unit) | no-unit | Keep; no marker action. |
| `ContentServiceManager` | `usr/lib/systemd/system/ContentServiceManager.service` | — (no negated condition) | manual | Keep; no marker action. |
| `org.tizen.content-tiles-provider` | `usr/lib/systemd/system/org.tizen.content-tiles-provider.service` | — (no negated condition) | manual | Keep; no marker action. |
| `org.tizen.easysetup-daemon` | `usr/lib/systemd/system/org.tizen.easysetup-daemon.service` | — (no negated condition) | manual | Keep; no marker action. |
| `org.tizen.ssoservice` | `usr/lib/systemd/system/org.tizen.ssoservice.service` | — (no negated condition) | manual | Keep; no marker action. |
| `com.samsung.tv.built-in-app-upgrader` | `usr/lib/systemd/system/com.samsung.tv.built-in-app-upgrader.service` | — (no negated condition) | manual | Keep; no marker action. |
| `com.samsung.tv.aoc-enabler` | `usr/lib/systemd/system/com.samsung.tv.aoc-enabler.service` | — (no negated condition) | manual | Keep; no marker action. |
