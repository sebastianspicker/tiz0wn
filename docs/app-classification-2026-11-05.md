# Installed app classification — 2026-11-05

Static classification for the owned Q60T. No device command or state change was made. The staged `full-packages.txt` has **331 package records and one `pkgcmd` timing footer**, although the prior inventory calls it 332 rows. Counts below use package records. The capture contains **six** `q60t*` transports, rather than the five described in the earlier brief. All global app disable flags were reported false in the inventory.

Evidence key: `P` is the exact package ID, type and live `pkgcmd -l` name in `/tmp/debloat-audit/full-packages.txt`; `M/id.xml` is `/tmp/tiz-rootfs2/usr/share/packages/id.xml` from the partial firmware extraction; `U/name.service` is a matching file in `/tmp/tiz-rootfs2/usr/lib/systemd/system/`. `M absent` and `U absent` mean absent from that partial extraction, **not** absent on the live TV. Running state comes from `docs/app-inventory-2026-11-05.md`, `/tmp/debloat-audit/context.txt`, and `/tmp/debloat-audit/live-inventory.txt`; “not shown” means the limited snapshots cannot establish absence. The snapshot is not a complete process-to-package join. Vetro `debloat.js` is a Q80A candidate pattern list only; it cannot establish a Q60T tier or action. `com.samsung.tv.coba.adagent` is a protected Smart Hub dependency despite its name.

> **Removal reality, 2026-11-05:** `pkgcmd -u` works on **wgt** packages only.
> tpk/rpm preloads answer `Operation not allowed [-4]`; they stay
> disable-only. 33 wgt rows across tiers 1–3 were removed; the rest are
> flag candidates. Reinstall for wgt is the store; nothing here is a rollback.

A recognizable `P` name supports a **purpose tier**, including viewer apps and feature shells; it does not prove that disabling the package is harmless or that a store listing can restore it. `4a` is a separate keep bucket within tier 4. Coverage check: 8 + 29 + 37 + 116 + 124 + 8 + 9 = **331 unique package IDs**; the timing footer is excluded. Cross-references below do not add records.

| Tier | Count |
| --- | ---: |
| 1. Tracking / ads / telemetry | 8 |
| 2. Trial / shell / commercial | 29 |
| 3. Regional / partner / feature apps | 37 |
| 4. Core keep, other platform | 116 |
| 4a. Samsung TV framework, keep by default | 124 |
| 5. Ours / research | 8 |
| 6. Named but unclear / hold | 9 |
| **Total package records** | **331** |

## 1. Tracking / ads / telemetry

| Package ID | P name / type | Evidence and class | Safe action |
| --- | --- | --- | --- |
| `org.tizen.acr-service-app` | acr-service-app (RPM) | `M/org.tizen.acr-service-app.xml`; `U/org.tizen.acr-service-app.service` launches `app_launcher -s`. Its package unit was inactive in the capture, but separate recognition daemons were active. | Package disable alone does not stop recognition. The separately proven reversible unit class covers `acr.path`, `acr.service`, and `contents-recognition-service.service`; check processes afterward. |
| `com.samsung.tv.ad-web-framework` | Ad Web Framework (TPK) | P name identifies an ad, analytics or recognition component; package-to-unit/runtime join is unproved. TPK app; `pkgstate` candidate. | Hold until live app ID, dependencies, running state and reversible restore are checked; no uninstall. |
| `com.samsung.tv.adplayer` | AdPlayer (TPK) | P name identifies an ad, analytics or recognition component; package-to-unit/runtime join is unproved. TPK app; `pkgstate` candidate. | Hold until live app ID, dependencies, running state and reversible restore are checked; no uninstall. |
| `adplatform` | Ad Player (WGT) | P name identifies an ad, analytics or recognition component; package-to-unit/runtime join is unproved. WGT app; `pkgstate` candidate. | Hold until live app ID, dependencies, running state and reversible restore are checked; no uninstall. |
| `com.samsung.tizen.samsung-analytics` | samsung-analytics (TPK) | P name identifies an ad, analytics or recognition component; package-to-unit/runtime join is unproved. TPK app; `pkgstate` candidate. | Hold until live app ID, dependencies, running state and reversible restore are checked; no uninstall. |
| `com.samsung.tv.contents-recognition-dbmgr` | contents-recognition-dbmgr (TPK) | P name identifies an ad, analytics or recognition component; package-to-unit/runtime join is unproved. TPK app; `pkgstate` candidate. | Hold until live app ID, dependencies, running state and reversible restore are checked; no uninstall. |
| `com.samsung.tv.canalysis-service` | canalysis-daemon (TPK) | P name identifies an ad, analytics or recognition component; package-to-unit/runtime join is unproved. TPK app; `pkgstate` candidate. | Hold until live app ID, dependencies, running state and reversible restore are checked; no uninstall. |
| `com.samsung.tv.pisa-service` | pisa-service (TPK) | P name identifies an ad, analytics or recognition component; package-to-unit/runtime join is unproved. TPK app; `pkgstate` candidate. | Hold until live app ID, dependencies, running state and reversible restore are checked; no uninstall. |

## 2. Trial / shell / commercial

Existing hotel, demo, shop and manual shells remain here. `adplatform` (Ad Player) is counted once in tier 1; its commercial shell role also makes it a tier 2 candidate. The capture contains `org.tizen.nagsam-app` (nagsam-mmi), **not** a separate `org.tizen.nagsam` package.

| Package ID | P name / type | Class and evidence | Admission before a reversible disable |
| --- | --- | --- | --- |
| `org.tizen.demo-player-tv` | Demo Player (RPM) | RPM app / `pkgstate` candidate; `M/org.tizen.demo-player-tv.xml`: UI; Demo Player; `U absent`. | Confirm installed app IDs, no active dependency, current state and restore route; then read back a one-package trial. |
| `org.tizen.ep-hotel-protocolui` | ephotel-protocolui (RPM) | RPM app / `pkgstate` candidate; `M/org.tizen.ep-hotel-protocolui.xml`: UI; ephotel-protocolui; `U absent`. | Confirm installed app IDs, no active dependency, current state and restore route; then read back a one-package trial. |
| `org.tizen.remote-service-logging-debug-menu` | Remote Service Debug Menu (RPM) | RPM app / `pkgstate` candidate; P name identifies a promotion, consent, care or diagnostic shell; preserve support access if used. | Confirm exact app ID, whether it runs or backs a current feature, and a working re-enable/recovery route before trial. |
| `com.samsung.TVDeviceCare` | TVDeviceCare (RPM) | RPM app / `pkgstate` candidate; P name identifies a promotion, consent, care or diagnostic shell; preserve support access if used. | Confirm exact app ID, whether it runs or backs a current feature, and a working re-enable/recovery route before trial. |
| `com.samsung.tv.built-in-app-info-viewer` | BuiltInAppInfoViewer (TPK) | TPK app / `pkgstate` candidate; P name identifies a promotion, consent, care or diagnostic shell; preserve support access if used. | Confirm exact app ID, whether it runs or backs a current feature, and a working re-enable/recovery route before trial. |
| `org.tizen.ep-hotel-channellist` | ep-hotel-channellist (RPM) | RPM app / `pkgstate` candidate; `M/org.tizen.ep-hotel-channellist.xml`: UI; ep-hotel-channellist; `U absent`. | Confirm installed app IDs, no active dependency, current state and restore route; then read back a one-package trial. |
| `org.tizen.ep-hotel-channel` | ep-hotel-channel (RPM) | RPM app / `pkgstate` candidate; `M/org.tizen.ep-hotel-channel.xml`: UI; ep-hotel-channel; `U absent`. | Confirm installed app IDs, no active dependency, current state and restore route; then read back a one-package trial. |
| `org.tizen.AgingApp` | AgingApp (RPM) | RPM app / `pkgstate` candidate; P name identifies a promotion, consent, care or diagnostic shell; preserve support access if used. | Confirm exact app ID, whether it runs or backs a current feature, and a working re-enable/recovery route before trial. |
| `org.tizen.internal-demo-player-tv` | Internal Demo Player (RPM) | RPM app / `pkgstate` candidate; `M/org.tizen.internal-demo-player-tv.xml`: UI; Internal Demo Player; `U absent`. | Confirm installed app IDs, no active dependency, current state and restore route; then read back a one-package trial. |
| `org.tizen.emanual-app` | emanual (RPM) | RPM app / `pkgstate` candidate; `M/org.tizen.emanual-app.xml`: UI; emanual; `U absent`. | Confirm installed app IDs, no active dependency, current state and restore route; then read back a one-package trial. |
| `org.tizen.ep-hotel-factory` | ep-hotel-factory (RPM) | RPM app / `pkgstate` candidate; `M/org.tizen.ep-hotel-factory.xml`: UI; ep-hotel-factory; `U absent`. | Confirm installed app IDs, no active dependency, current state and restore route; then read back a one-package trial. |
| `com.samsung.tv.hdmi-troubleshooting` | hdmi-troubleshooting (RPM) | RPM app / `pkgstate` candidate; P name identifies a promotion, consent, care or diagnostic shell; preserve support access if used. | Confirm exact app ID, whether it runs or backs a current feature, and a working re-enable/recovery route before trial. |
| `org.tizen.ephotel-cloning` | cloning (RPM) | RPM app / `pkgstate` candidate; `M/org.tizen.ephotel-cloning.xml`: UI; cloning; `U absent`. | Confirm installed app IDs, no active dependency, current state and restore route; then read back a one-package trial. |
| `org.tizen.ep-hotel-popup-ui` | ephotel-remote (RPM) | RPM app / `pkgstate` candidate; `M/org.tizen.ep-hotel-popup-ui.xml`: UI; ephotel-remote; `U absent`. | Confirm installed app IDs, no active dependency, current state and restore route; then read back a one-package trial. |
| `com.samsung.ep.hotel-quicksetting-editor` | QuickEditorApp (TPK) | TPK app / `pkgstate` candidate; `M/com.samsung.ep.hotel-quicksetting-editor.xml`: UI; QuickEditorApp; `U absent`. | Confirm installed app IDs, no active dependency, current state and restore route; then read back a one-package trial. |
| `org.tizen.smarthub-connection-test` | Smarthub Connection Test (RPM) | RPM app / `pkgstate` candidate; P name identifies a promotion, consent, care or diagnostic shell; preserve support access if used. | Confirm exact app ID, whether it runs or backs a current feature, and a working re-enable/recovery route before trial. |
| `org.tizen.remote-shop-care-hub` | Remote Shop Content Management (RPM) | RPM app / `pkgstate` candidate; `M/org.tizen.remote-shop-care-hub.xml`: UI; Remote Shop Content Management; `U absent`. | Confirm installed app IDs, no active dependency, current state and restore route; then read back a one-package trial. |
| `EJZZ9Mr6D2` | e-Manual (WGT) | WGT app / `pkgstate` candidate; P name identifies a promotion, consent, care or diagnostic shell. | Confirm exact app ID, whether it runs or backs a current feature, and a working re-enable/recovery route before trial. |
| `org.tizen.nagsam-app` | nagsam-mmi (RPM) | RPM app / `pkgstate` candidate; P name identifies a promotion, consent, care or diagnostic shell; preserve support access if used. | Confirm exact app ID, whether it runs or backs a current feature, and a working re-enable/recovery route before trial. |
| `com.samsung.ep.hotelfs` | Hotel csfs (TPK) | TPK app / `pkgstate` candidate; `M/com.samsung.ep.hotelfs.xml`: UI; Hotel FirstScreen; `U absent`. | Confirm installed app IDs, no active dependency, current state and restore route; then read back a one-package trial. |
| `org.tizen.request-support` | RequestSupport (RPM) | RPM app / `pkgstate` candidate; P name identifies a promotion, consent, care or diagnostic shell; preserve support access if used. | Confirm exact app ID, whether it runs or backs a current feature, and a working re-enable/recovery route before trial. |
| `samsung-easy-support` | Samsung Easy Support (RPM) | RPM app / `pkgstate` candidate; P name identifies a promotion, consent, care or diagnostic shell; preserve support access if used. | Confirm exact app ID, whether it runs or backs a current feature, and a working re-enable/recovery route before trial. |
| `org.tizen.ep-hotel-security` | ep-hotel-security (RPM) | RPM app / `pkgstate` candidate; `M/org.tizen.ep-hotel-security.xml`: UI; ep-hotel-security; `U absent`. | Confirm installed app IDs, no active dependency, current state and restore route; then read back a one-package trial. |
| `tv6pbVMQFF` | Privacy Choices (WGT) | WGT app / `pkgstate` candidate; P name identifies a promotion, consent, care or diagnostic shell. | Confirm exact app ID, whether it runs or backs a current feature, and a working re-enable/recovery route before trial. |
| `yL49PNFmjW` | Samsung Promotion (WGT) | WGT app / `pkgstate` candidate; P name identifies a promotion, consent, care or diagnostic shell. | Confirm exact app ID, whether it runs or backs a current feature, and a working re-enable/recovery route before trial. |
| `org.tizen.ep-hotel-alarm` | EP Hotel Alarm (RPM) | RPM app / `pkgstate` candidate; `M/org.tizen.ep-hotel-alarm.xml`: UI; EP Hotel Alarm; `U absent`. | Confirm installed app IDs, no active dependency, current state and restore route; then read back a one-package trial. |
| `ep-hotel-protocol` | ep-hotel-protocol (RPM) | direct unit candidate; `M/ep-hotel-protocol.xml`: UI; ep-hotel-protocol; `U/ep-hotel-protocol.service`. | Confirm installed app IDs, no active dependency, current state and restore route; then read back a one-package trial. |
| `com.samsung.ep.hotel-popup` | HotelPopupApp (TPK) | TPK app / `pkgstate` candidate; `M/com.samsung.ep.hotel-popup.xml`: UI; HotelPopupApp; `U absent`. | Confirm installed app IDs, no active dependency, current state and restore route; then read back a one-package trial. |
| `qtMHjALHus` | TVDeviceCare (WGT) | WGT app / `pkgstate` candidate; P name identifies a promotion, consent, care or diagnostic shell. | Confirm exact app ID, whether it runs or backs a current feature, and a working re-enable/recovery route before trial. |

## 3. Regional / partner / feature apps

The live `P` name identifies each viewer-facing streaming, catch-up, music, gaming or brand app below, regardless of package origin. “Safe to disable” here means a **conditional, reversible per-app trial** after the listed admission check; it is not an uninstall recommendation. Store reinstall applies only after the exact listing and account route are confirmed; otherwise retain the bundled package recovery path. AirPlay and Alexa are user features, not bloat. The ID `My5jIduosH` is named MagentaTV in `P`; the capture does not name a separate My5 app.

| Package ID | Exact P name | Class | Safe-to-disable and recovery note |
| --- | --- | --- | --- |
| `g0nt8dscFO` | MagentaTV - 1. Generation | WGT viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `NeV3gZvFmN` | Couchplay Games | WGT viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `KbRHmu0vrC` | RTL+ | WGT viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `MCmYXNxgcu` | Disney+ | WGT viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `X1pKpFCiUu` | Pluto TV | WGT viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `com.samsung.tv.aria-video` | Apple TV | TPK viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; retain bundled recovery. |
| `yPSlpvfeTf` | ZDF | WGT viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `PK700Cupra` | CUPRA | WGT viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `HVPOP9POZU` | ePop-2020-Nike | WGT viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `SrAoJxGQUf` | ARD Mediathek – Streaming für alle | WGT viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `com.samsung.tv.google-assistant` | google-fullscreen-app | TPK feature app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; retain bundled recovery. |
| `NRi6kdBYJ0` | Apple AirPlay | WGT feature app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `SSS02MyT3r` | Brand.TV | WGT viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `AQKO41xyKP` | Amazon Alexa | WGT feature app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `org.tizen.netflix-app` | Netflix | TPK viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; retain bundled recovery. |
| `com.samsung.tv.airplay-app` | airplay-app | TPK feature app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; retain bundled recovery. |
| `vbUQClczfR` | Rakuten TV | WGT viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `8HwqClkwtp` | DAZN | WGT viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `GHI3a0zMSx` | Xbox | WGT viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `com.samsung.tv.tvPlusDeeplinker` | Samsung TV Plus | TPK feature app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; retain bundled recovery. |
| `cg2m3QSB89` | Joyn | WGT viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `My5jIduosH` | MagentaTV - DE: TV und Streaming | WGT viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `AkhP5nCr24` | Explore Google Assistant | WGT feature app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `Y9sxevvNCT` | Sportworld | WGT viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `com.samsung.tv.alexa-client` | alexa-fullscreen-app | TPK feature app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; retain bundled recovery. |
| `IpIKeB3u2B` | HD+ | WGT viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `TCVAAnsPTa` | Audi | WGT viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `org.tizen.apple.apple-music` | Apple Music | TPK viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; retain bundled recovery. |
| `com.samsung.tv.tvplus` | tvplus | TPK viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; retain bundled recovery. |
| `9Ur5IzDKqV` | YouTube | WGT viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `rJeHak5zRg` | Spotify - Music and Podcasts | WGT viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `aLlph042JZ` | ARTE | WGT viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `ndmbVBabXx` | waipu.tv – Live TV-Streaming | WGT viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `9FhM0cODbY` | TikTok | WGT viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `B5vuvi1Oky` | BILD LIVE | WGT viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `Mo5FtpAjGy` | WOW | WGT viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; verify store listing for reinstall, else use bundled recovery. |
| `org.tizen.primevideo` | Prime Video | TPK viewer app; `pkgstate` per-app candidate | Safe to disable only if unused and its exact app ID, runtime and re-enable are checked; retain bundled recovery. |

## 4. Core keep — other platform packages

These are named system, setup, input, playback, content, network, security or recovery components. The prior manifest-backed core rows remain in this bucket unless they match the `4a` rule. The other rows have a recognizable `P` name or package role, so they are kept by default; name-based placement does not establish a complete dependency map. `org.tizen.bmplayer` (Music TV) has a matching service unit and remains a playback component here. The WGTs named Apps and App Launcher remain store/navigation shells, not partner apps.

| Existing manifest-backed core IDs | Count |
| --- | ---: |
| `ContentServiceManager`, `com.samsung.ep.coba.hotel`, `com.samsung.tizen.samsung-service-manager`, `com.samsung.tizen.update-client`, `org.tizen.AVControl`, `org.tizen.NetworkSetting-Tizen`, `org.tizen.ScreenMirroring-daemon`, `org.tizen.UsbSyncDisplay`, `org.tizen.automation-alert`, `org.tizen.automation-app`, `org.tizen.automation-viewer`, `org.tizen.btapp`, `org.tizen.btappui`, `org.tizen.channel-list`, `org.tizen.channel-manager`, `org.tizen.channel-search`, `org.tizen.chromium-efl`, `org.tizen.content-tiles-provider`, `org.tizen.easysetup-UI`, `org.tizen.easysetup-daemon`, `org.tizen.epg`, `org.tizen.function-osd`, `org.tizen.hdmicec`, `org.tizen.litewebappservice`, `org.tizen.mycontent-photo-player-tv`, `org.tizen.mycontent-video-player-tv`, `org.tizen.picture-test`, `org.tizen.pvrplayer`, `org.tizen.pvrrecorder`, `org.tizen.registerav`, `org.tizen.registertv`, `org.tizen.screen-reader`, `org.tizen.sound-test`, `org.tizen.sso`, `org.tizen.sso-menu`, `org.tizen.ssoservice`, `org.tizen.tv-viewer`, `org.tizen.ug-load`, `org.tizen.usb-launcher-tv`, `org.tizen.video-player-tv`, `org.tizen.volume-setting`, `org.tizen.webappservice-commui`, `org.tizen.wizard` | 43 |

- **Additional RPM platform/feature packages (51):** `capi-bnr-tv`, `com.samsung.calendar-account-manager`, `com.samsung.google-cal-sync`, `com.samsung.video-test`, `content-grab-service`, `ep-event-manager`, `hdmicec-service`, `ise-default-tv`, `org.tizen.5-way-function`, `org.tizen.NetworkSpeaker`, `org.tizen.RunningApps`, `org.tizen.RunningAppsService`, `org.tizen.SMSourceAPP`, `org.tizen.ScreenMirroring-app-tv`, `org.tizen.SmartRC`, `org.tizen.alert-syspopup`, `org.tizen.autofilld`, `org.tizen.bmplayer`, `org.tizen.bt-settings-external-controller`, `org.tizen.btaudiolist`, `org.tizen.cloning`, `org.tizen.connection-guide-app`, `org.tizen.dpm-syspopup`, `org.tizen.ep-boot-manager`, `org.tizen.ep-system-manager`, `org.tizen.factory`, `org.tizen.heremaps-uc`, `org.tizen.homesetting`, `org.tizen.isf-kbd-mode-changer`, `org.tizen.mbr-app`, `org.tizen.mbr-daemon`, `org.tizen.menu`, `org.tizen.multi-assistant-service`, `org.tizen.photo-player-tv`, `org.tizen.provider-resetpsid`, `org.tizen.pvrrecorder-syspopup`, `org.tizen.register-device-ux`, `org.tizen.reminder`, `org.tizen.remote-management`, `org.tizen.remotepc`, `org.tizen.schedule-manager`, `org.tizen.sealayer`, `org.tizen.smart_security`, `org.tizen.smarthub-reset`, `org.tizen.stand-by-scan`, `org.tizen.tv.ci-app`, `org.tizen.voice-onboarding`, `org.tizen.welcome-mode`, `org.tizen.widget_viewer_sdk`, `ug-hbbtv-efl`, `ug-ttxUG-efl`.
- **Additional TPK platform/feature packages (19):** `com.samsung.tizen.autofill-app`, `com.samsung.tizen.content-continuity`, `com.samsung.tizen.content-panel`, `com.samsung.tizen.samsung-account`, `com.samsung.tizen.samsung-cloud`, `com.samsung.tizen.samsung-pass-agent`, `com.samsung.tizen.smartthings-client`, `com.samsung.tizen.smartthings-thing`, `csapi-tv-tizenfx`, `lib-ariafw-tv`, `org.tizen.ambientapp`, `org.tizen.browser`, `org.tizen.chromium-efl-upgrade`, `org.tizen.cloud-launcher`, `org.tizen.pvod-appfw`, `org.tizen.tts-engine-vd-DVB`, `org.tizen.voice-app`, `org.tizen.voice-client`, `samsunghealth-service-tv`.
- **Additional WGT platform/feature packages (3):** `30IKH0OX8U`, `Ja2mti1oVw`, `aQjWjLsPaO`.

### 4a. Samsung TV framework — keep by default

Prefix rule: every captured `com.samsung.tv.*` package that is not a named viewer/feature app in tier 3 or a name-based ad/diagnostic candidate in tier 1–2 is framework **keep by default**. This includes CoBA service/preload members and applies whether the partial extraction has a manifest or unit. The table groups the exact covered IDs; no group is a disable list. The exceptions moved out are listed immediately after it. `csfs`, `store`, `content-*`, `ssu`, `appsvc`, `aul`, and `mde-*` remain protected even when a name sounds optional.

| Group | Count | Covered package IDs |
| --- | ---: | --- |
| CoBA (`com.samsung.tv.coba.*`) | 35 | `com.samsung.tv.coba.adagent`, `com.samsung.tv.coba.ambient`, `com.samsung.tv.coba.ambientcontentabout`, `com.samsung.tv.coba.ambientcontentapp`, `com.samsung.tv.coba.ambientcontentart`, `com.samsung.tv.coba.ambientcontentroutine`, `com.samsung.tv.coba.ambientcontentsoundwall`, `com.samsung.tv.coba.ambientsetting`, `com.samsung.tv.coba.ambienttv`, `com.samsung.tv.coba.apps`, `com.samsung.tv.coba.dhcategory`, `com.samsung.tv.coba.edenview`, `com.samsung.tv.coba.home`, `com.samsung.tv.coba.home-notification`, `com.samsung.tv.coba.livetv`, `com.samsung.tv.coba.mobilebff`, `com.samsung.tv.coba.msview`, `com.samsung.tv.coba.multiscreen`, `com.samsung.tv.coba.mvcontents`, `com.samsung.tv.coba.mvicon`, `com.samsung.tv.coba.mviotcamera`, `com.samsung.tv.coba.mvmobile`, `com.samsung.tv.coba.mvpictureinpicture`, `com.samsung.tv.coba.mvscreensize`, `com.samsung.tv.coba.mvsound`, `com.samsung.tv.coba.privacy_app`, `com.samsung.tv.coba.remoteworkspace`, `com.samsung.tv.coba.samsungaccount`, `com.samsung.tv.coba.search`, `com.samsung.tv.coba.setting`, `com.samsung.tv.coba.setting.devicemanager`, `com.samsung.tv.coba.setting.devicemanager.res`, `com.samsung.tv.coba.setting.res.normal`, `com.samsung.tv.coba.smartthings`, `com.samsung.tv.coba.source` |
| Content, sharing, store, update and app framework | 38 | `com.samsung.tv.CSAccount`, `com.samsung.tv.CSBilling`, `com.samsung.tv.ContentsBrowser`, `com.samsung.tv.ContentsBrowserDetail`, `com.samsung.tv.SAFCommonPlugin`, `com.samsung.tv.account-extra-service`, `com.samsung.tv.ambient-support`, `com.samsung.tv.ambientfte`, `com.samsung.tv.aria-engine`, `com.samsung.tv.artpaint-tpl`, `com.samsung.tv.billing-helper`, `com.samsung.tv.bt-mdemanager`, `com.samsung.tv.cms-service`, `com.samsung.tv.contentimageapp`, `com.samsung.tv.coss`, `com.samsung.tv.coss.provider.d2d`, `com.samsung.tv.csfs`, `com.samsung.tv.csft-service`, `com.samsung.tv.csfw.provider.ftp`, `com.samsung.tv.csfw.provider.local`, `com.samsung.tv.easysetup-mediator`, `com.samsung.tv.gallery`, `com.samsung.tv.knox-browser`, `com.samsung.tv.knox-browser-autofill`, `com.samsung.tv.mde-framework`, `com.samsung.tv.multiscreen`, `com.samsung.tv.mycontents`, `com.samsung.tv.photo-tpl`, `com.samsung.tv.photo8K-tpl`, `com.samsung.tv.photoblueline1-tpl`, `com.samsung.tv.preview-downloader`, `com.samsung.tv.preview-updater`, `com.samsung.tv.safLaunchBridge`, `com.samsung.tv.store`, `com.samsung.tv.swu-ui`, `com.samsung.tv.tvkey-preview`, `com.samsung.tv.waapp-contents-provider`, `com.samsung.tv.weather-viewer` |
| Other TV services, setup and UI | 51 | `com.samsung.tv.DeviceGraphDaemon`, `com.samsung.tv.action-planner-service`, `com.samsung.tv.aispeaker-oobe-app`, `com.samsung.tv.antenna-selection`, `com.samsung.tv.aoc-enabler`, `com.samsung.tv.app-selector`, `com.samsung.tv.autolayout-tpl`, `com.samsung.tv.autosetup-channel-list`, `com.samsung.tv.av-sync-service`, `com.samsung.tv.bixby-context-client`, `com.samsung.tv.bixby-prov`, `com.samsung.tv.bixbycapsuleviewer`, `com.samsung.tv.bleproximity`, `com.samsung.tv.broadcastingmenu`, `com.samsung.tv.built-in-app-upgrader`, `com.samsung.tv.cnvoice`, `com.samsung.tv.cnvoice-assistant`, `com.samsung.tv.cobalt`, `com.samsung.tv.commonsearch`, `com.samsung.tv.context-aware-agent`, `com.samsung.tv.csa`, `com.samsung.tv.dotnet-policy-checker`, `com.samsung.tv.fuzzy-search-engine`, `com.samsung.tv.ghdaemon`, `com.samsung.tv.ghservice`, `com.samsung.tv.hybrid-aot-manager`, `com.samsung.tv.intelligent-action-app`, `com.samsung.tv.iot-dashboard`, `com.samsung.tv.iot-service-home-cctv_FLUX`, `com.samsung.tv.iot-service-notification`, `com.samsung.tv.iot-service-vhome_FLUX`, `com.samsung.tv.mybixby`, `com.samsung.tv.nfc-monitor`, `com.samsung.tv.notification-app`, `com.samsung.tv.notification-serviceapp`, `com.samsung.tv.ondevice`, `com.samsung.tv.ondevice-voice`, `com.samsung.tv.pdss-client`, `com.samsung.tv.quickpanel`, `com.samsung.tv.remote-workspace`, `com.samsung.tv.screeneffectorapp`, `com.samsung.tv.sealayer`, `com.samsung.tv.searchall`, `com.samsung.tv.shortcut`, `com.samsung.tv.slive-daemon`, `com.samsung.tv.tv-scheduler`, `com.samsung.tv.utterance-recommender-service`, `com.samsung.tv.vd-sc-client-service`, `com.samsung.tv.vif`, `com.samsung.tv.vision-data-recognition-service`, `com.samsung.tv.voiceassistant-music` |

**Moved-out prefix exceptions (13):** `com.samsung.tv.ad-web-framework`, `com.samsung.tv.adplayer`, `com.samsung.tv.airplay-app`, `com.samsung.tv.alexa-client`, `com.samsung.tv.aria-video`, `com.samsung.tv.built-in-app-info-viewer`, `com.samsung.tv.canalysis-service`, `com.samsung.tv.contents-recognition-dbmgr`, `com.samsung.tv.google-assistant`, `com.samsung.tv.hdmi-troubleshooting`, `com.samsung.tv.pisa-service`, `com.samsung.tv.tvPlusDeeplinker`, `com.samsung.tv.tvplus`. Their names and classes appear in tiers 1–3; `com.samsung.tv.coba.adagent` and `com.samsung.tv.coba.privacy_app` stay in 4a.

## 5. Ours / research

| Package ID | Name | Manifest | Matching unit | Running state | Reason to keep / hold |
| --- | --- | --- | --- | --- | --- |
| `GCyQjAzWhP` | app | `M absent` | `U absent` | not shown (limited snapshots) | User-installed Web IDE template, installed 2026-11-04; likely ours. |
| `q60t046395` | Q60T Mali chain transport | `M absent` | `U absent` | not shown (limited snapshots) | Q60T research transport; not factory bloat. |
| `q60t044828` | Q60T bounded JIT-write validator transport | `M absent` | `U absent` | not shown (limited snapshots) | Q60T research transport; not factory bloat. |
| `q60t04482m` | Q60T managed JIT write transport | `M absent` | `U absent` | not shown (limited snapshots) | Q60T research transport; not factory bloat. |
| `q60t04482n` | Q60T managed JIT write transport | `M absent` | `U absent` | not shown (limited snapshots) | Q60T research transport; not factory bloat. |
| `q60td60928` | Q60T Mali diagnostic transport | `M absent` | `U absent` | not shown (limited snapshots) | Q60T research transport; not factory bloat. |
| `q60td60929` | Q60T Mali diagnostic transport | `M absent` | `U absent` | not shown (limited snapshots) | Q60T research transport; not factory bloat. |
| `tiz0wnprob` | tiz0wn local probe | `M absent` | `U absent` | not shown (limited snapshots) | Our local probe service. |

## 6. Named but unclear / hold

These names still do not establish a viewer feature or a specific platform role. Hold them; no package disable is recommended. All other captured names are assigned above.

| Package ID | P name / type | Reason to hold |
| --- | --- | --- |
| `rct-service` | rct-service (RPM) | Name or launch role is ambiguous in the partial evidence; obtain manifest and process mapping before any action. |
| `com.samsung.ep-plateau-info` | com.samsung.ep-plateau-info (RPM) | Name or launch role is ambiguous in the partial evidence; obtain manifest and process mapping before any action. |
| `p2p-asm-UI` | p2p-asm-UI (RPM) | Name or launch role is ambiguous in the partial evidence; obtain manifest and process mapping before any action. |
| `com.samsung.ep-plateau-agent` | com.samsung.ep-plateau-agent (RPM) | Name or launch role is ambiguous in the partial evidence; obtain manifest and process mapping before any action. |
| `org.tizen.rct-app` | rct-app (RPM) | Name or launch role is ambiguous in the partial evidence; obtain manifest and process mapping before any action. |
| `mobilebff` | MobileBFF (TPK) | Name or launch role is ambiguous in the partial evidence; obtain manifest and process mapping before any action. |
| `ZODRT12q2l` | web-account-extension (WGT) | Name or launch role is ambiguous in the partial evidence; obtain manifest and process mapping before any action. |
| `WykOS4t4F0` | cmsWebApp (WGT) | Name or launch role is ambiguous in the partial evidence; obtain manifest and process mapping before any action. |
| `comss` | comss (RPM) | Name or launch role is ambiguous in the partial evidence; obtain manifest and process mapping before any action. |

## First five package-level disable candidates

These are **candidates**, not an instruction to disable them now. For each, first map the exact package to its installed app ID and check that no active unit or feature depends on it; record the current global app state, confirm `pkgstate` can re-enable it and read it back, and keep a recovery package or verified store route. A one-package reversible trial is admitted only after its individual check. The ACR daemon-control feature is separate and is not counted as a package-level candidate.

| Order | Package ID | Class | Specific admission check |
| --- | --- | --- | --- |
| 1 | `adplatform` | WGT Ad Player; `pkgstate` per-app candidate | Confirm it is the visible Ad Player app rather than a shared ad service; verify no running dependency and re-enable readback. |
| 2 | `yL49PNFmjW` | WGT Samsung Promotion; `pkgstate` per-app candidate | Confirm the promotion app is unused on this TV, has no launch dependency, and re-enables with readback. |
| 3 | `tv6pbVMQFF` | WGT Privacy Choices; `pkgstate` per-app candidate | Check consent/privacy settings remain reachable and the package re-enables with readback. |
| 4 | `qtMHjALHus` | WGT TVDeviceCare; `pkgstate` per-app candidate | Check device-care access and any scheduled maintenance path are unaffected; verify re-enable readback. |
| 5 | `EJZZ9Mr6D2` | WGT e-Manual; `pkgstate` per-app candidate | Confirm the owner does not use the manual and that its exact store or bundled restore route is available. |

## Do not touch

- `com.samsung.tv.coba.adagent`: Smart Hub loads ResourceAdvertise from it; Vetro also explicitly protects it.
- `com.samsung.tv.coba.*`, `com.samsung.ep.coba.hotel`, `com.samsung.tv.csfs`, `com.samsung.tv.store`: Home, apps, settings and presentation dependencies.
- `com.samsung.tv.content-*`, `com.samsung.tv.ssu*`, `com.samsung.tv.appsvc*`, `com.samsung.tv.aul*`, `com.samsung.tv.mde-*`: framework families; retain absent specific dependency evidence.
- Content, SSO, network, input, audio/video and software-update anchors in tier 4: needed for ordinary TV use or recovery.
- `tiz0wnprob`, `GCyQjAzWhP`, and the six `q60t*` packages: owner/research packages, not factory debloat targets.

## Safe to install and recovery

YouTube (`9Ur5IzDKqV`), Spotify (`rJeHak5zRg`), the public broadcasters ZDF (`yPSlpvfeTf`) and ARD (`SrAoJxGQUf`), and Apple AirPlay (`NRi6kdBYJ0`) are **present in the package list**. Their names establish presence, not a verified publisher signature or safe reinstall path. Use the TV store only after confirming the exact listing and account route. Tier 3 can use store reinstall after that route is demonstrated; bundled TPK features need their matching package. Tier 1–2 system packages need a verified matching archive. No uninstall is recommended.

## Needs a live look (maximum ten)

- `adplatform`: WGT Ad Player app ID, runtime and reversible class.
- `yL49PNFmjW`: Samsung Promotion dependencies and restore.
- `tv6pbVMQFF`: Privacy Choices settings path and restore.
- `qtMHjALHus`: DeviceCare schedule and restore.
- `EJZZ9Mr6D2`: e-Manual store or bundled recovery.
- `com.samsung.tv.ad-web-framework`: ad framework manifest, unit and dependents.
- `com.samsung.tv.adplayer`: AdPlayer manifest, unit and dependents.
- `com.samsung.tizen.samsung-analytics`: analytics app and unit mapping.
- `com.samsung.tv.canalysis-service`: recognition unit and process mapping.
- `NRi6kdBYJ0`: AirPlay feature app and recovery; preserve if used.

The 331 records now include 37 named viewer/partner/feature apps and 124 Samsung TV framework packages kept by default. Tier 1–2 contain 37 purpose-based ad, trial or shell candidates, subject to their individual checks; 9 named but unclear packages remain on hold. This is a static purpose classification, not a live dependency or store-recovery proof.
