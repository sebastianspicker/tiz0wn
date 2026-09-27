# Samsung Q60T: Debloating, SDB Access, Rooting and Firmware Research

**Target:** Samsung GQ55Q60TGUXZG
**Installed firmware:** T-NKLDEUC-2743.0, BT-S
**Research date:** 25 September 2026
**Assessment type:** Public-source research, review of the supplied photographs, and selected source-code inspection.
**Live-device status:** No connection to the television, exploit execution, application removal, firmware extraction, or performance measurement was performed for this report.

> **Principal conclusion:** There is a credible route to investigate **partial application debloating without root**, and there are genuine published Samsung rooting techniques. However, this research did not establish a working, model-specific full-debloat or root procedure for **GQ55Q60TGUXZG running T-NKLDEUC-2743.0**. The useful next step is a controlled storage/performance baseline and read-only SDB inventory — not a bulk uninstall script or an older firmware flash.

> **Editorial note (rewrite pass, 2026-09-26):** This document is unchanged in substance from the 25 September 2026 original; it has been restructured and tightened for a security-researcher audience, with an evidence ledger added up front. One factual pointer has been added: §2.4 states that the firmware archive was "not downloaded or decrypted" *at the time of this research*. A companion document, [`firmware-analysis.md`](firmware-analysis.md), dated one day later, subsequently downloaded, hash-verified and decrypted that exact image and disassembled the historical root primitive. That later work is summarized and cross-referenced from §11; it does not change any conclusion in this document, and no finding from it has been imported into this document's own evidence base below.

> **Later result (2026-09-27):** Subsequent work traced Remote PC SMB
> credentials into a privileged `mount.smb.sh` shell boundary and demonstrated
> one bounded `id` command as UID 0 on the exact 2743.0 owner-controlled TV.
> That result postdates this preserved research snapshot; see
> [`research/remotepc-cifs-root/`](../research/remotepc-cifs-root/) and
> [`From debloating to tiz0wn`](from-debloating-to-tiz0wn.md).

## Contents

- [TL;DR and evidence ledger](#tldr-and-evidence-ledger)
1. [Executive findings](#1-executive-findings)
2. [Device identification and evidence limits](#2-device-identification-and-evidence-limits)
3. [Determine what is actually slow](#3-determine-what-is-actually-slow)
4. [Reversible cleanup with the ordinary menus](#4-reversible-cleanup-with-the-ordinary-menus)
5. [What SDB, developer mode and a shell actually provide](#5-what-sdb-developer-mode-and-a-shell-actually-provide)
6. [Read-only SDB investigation](#6-read-only-sdb-investigation)
7. [Controlled removal of unwanted applications](#7-controlled-removal-of-unwanted-applications)
8. [TizenBrew and other application-level alternatives](#8-tizenbrew-and-other-application-level-alternatives)
9. [Review of publicly available debloating tools](#9-review-of-publicly-available-debloating-tools)
10. [Rooting research and compatibility analysis](#10-rooting-research-and-compatibility-analysis)
11. [A firmware-specific reverse-engineering plan](#11-a-firmware-specific-reverse-engineering-plan)
12. [Recovery, persistence and hardware boundaries](#12-recovery-persistence-and-hardware-boundaries)
13. [Network isolation and external-player strategy](#13-network-isolation-and-external-player-strategy)
14. [Recommended investigation roadmap](#14-recommended-investigation-roadmap)
15. [Evidence templates and final assessment](#15-evidence-templates-and-final-assessment)
16. [Sources and provenance](#16-sources-and-provenance)
- [Glossary](#glossary)

---

## TL;DR and evidence ledger

Tizen debloating is not one operation. It splits into at least six independent
intervention levels — ordinary menu cleanup, SDB (Smart Development Bridge)
management commands, TizenBrew/sideloading, the `sdk`-account shell reachable
through a published SDB vulnerability, root/execution-policy bypass, and full
firmware/OS replacement — each with a different evidence base and a different
wall. On
the exact target of this report, **GQ55Q60TGUXZG running T-NKLDEUC-2743.0, no
working full-debloat or root procedure exists as of this research.** ADB is
the wrong mental model throughout: this platform is Tizen 5.5 / Chromium M69,
controlled through SDB, and Android tooling/debloat lists do not transfer
(§1.2). Nothing below was tested against a physical device — everything is
public-source research, review of supplied photographs, and inspection of
publicly available source code.

The table grades each load-bearing claim in this document. **First-hand/high**
means the researcher directly inspected the primary artifact (vendor
documentation, or the actual source file cited) and the claim follows
directly from it. **Inferred/medium** means the claim combines multiple
sourced facts or reasons from documented platform architecture.
**Hedged/low** means a single third-party report — often on different
hardware or firmware — is being extrapolated to this target with an explicit
caveat. **Untested** means the report proposes a procedure or hypothesis that
was deliberately not executed.

| # | Finding | Grade | Basis |
|---|---|---|---|
| 1 | Debloating splits into distinct, non-interchangeable intervention levels (menu cleanup → SDB management → `sdk` shell → root → OS replacement) | Inferred/medium (analytical framework, not a device test) | §1.1, §5.2 |
| 2 | ADB/Android tooling and debloat lists do not apply to this Tizen platform | First-hand/high (vendor's own platform documentation) | §1.2 [S02] [S03] |
| 3 | Ordinary-menu app removal and cache/data clearing exist as supported operations, but some preinstalled apps cannot be removed this way | First-hand/high (Samsung's own support documentation) | §4.2–4.3 [S07] [S08] |
| 4 | Partial non-root app enumeration/removal via SDB is possible even with the ordinary shell disabled | Hedged/low — single first-person report on a **2018 UE55NU7400 / Tizen 4.0**, not reproduced on this target | §1.3, §7.1 [S24] |
| 5 | A published SDB command-injection vulnerability (SVE-2025-50109) yields an `sdk`-account shell on some Tizen 5.5–9 builds | Inferred/medium — vendor-tested on a different Tizen 5.5 model (UN43TU700DFXZA); 2743.0 status unverified | §10.3 [S15] |
| 6 | A historical Q60T root chain (Synacktiv) reached UID 0 and bypassed UEP (unsigned-execution protection) via a browser entry point and `/dev/sdp_mem` | Hedged/low for present applicability — demonstrated on a different firmware family (T-NKLAKUC 2201.0, 2021/2022); source of the decryptor inspected first-hand but not run against this image | §10.2 [S16] [S17] [S18] |
| 7 | Modern volatile root chains exist for QN90B and QN90F | Untested/not-applicable here — maintainer explicitly scopes these to different hardware and firmware families | §10.4 [S22] [S23] |
| 8 | A reviewed third-party debloating tool (SAWSUBE) defaults unknown packages to "safe to remove" and can fall back to the first connected SDB device | First-hand/high — direct source inspection at a pinned revision | §9.2 [S25] |
| 9 | No working full-debloat or root procedure exists for GQ55Q60TGUXZG/2743.0 | This document's own explicit conclusion — a stated absence of evidence, not a claim of impossibility | §15.4–15.5 |
| 10 | The firmware archive was not downloaded or decrypted for this report | Self-reported limitation; see editorial note above and §11 for the subsequent, separately documented empirical follow-up | §2.4 |

**What would move each wall** is addressed inline: §5.3 (closed ordinary shell is not a complete inventory of access), §7.4 (an exit code of 0 is not evidence of removal — verify the after-state), §10.5–10.6 (a 2026-dated advisory tested elsewhere does not confirm this firmware), and §11.3 (decrypting a container is not authenticating a modified one, still less booting it).

---

## 1. Executive findings

### 1.1 The answer is more nuanced than "Tizen cannot be debloated"

There are several distinct levels of intervention. Treating them as one operation causes misleading advice:

| Intervention | What it can accomplish | Status for this television |
|---|---|---|
| Ordinary settings and app cleanup | Remove supported apps, clear accumulated data, reduce automatic Smart Hub entry | Appropriate first investigation; availability of individual controls must be checked |
| SDB management commands | Inventory apps and potentially remove an app that the ordinary interface will not delete | Credible, model-dependent lead; not tested on 2743.0 |
| TizenBrew and sideloading | Run alternative applications or modified web frontends | Within the project's stated platform-generation support; not a system debloater |
| An `sdk`-level shell | Inspect resources that this account and its security context can access | Public SDB vulnerability exists; exact-firmware exposure unknown |
| Root and execution-policy bypass | Investigate protected processes and services | Demonstrated on historical Q60T firmware and other newer Samsung models; no validated port established here |
| Replacement firmware or another operating system | Replace substantial parts of the Samsung software stack | No usable, verified Q60T/2743.0 installation and recovery path established |

The evidence underlying these distinctions is discussed in Sections 5–12. Samsung documents the ordinary management/development tools; the more extensive access claims come from named researchers and project maintainers, not from a test on this television. [S03] [S04] [S08] [S15] [S16] [S20] [S22]

### 1.2 ADB is not the right interface

Samsung identifies this generation as a **Tizen** platform. Its TV development workflow uses **SDB** (Smart Development Bridge, the Tizen counterpart to Android's `adb`), not Android Debug Bridge. Android package commands, APK-based launchers, Magisk procedures and Android debloat lists therefore do not constitute a procedure for this TV. Similar command-line appearances do not make the operating systems interchangeable. [S02] [S03]

### 1.3 The most useful new finding is partial management access

A first-person report on a **2018 UE55NU7400 / Tizen 4.0** describes successful application enumeration and package removal despite ordinary shell access being disabled. That is evidence against the blanket claim that "closed shell means no useful SDB commands." It is **not** confirmation that every protected app on this Q60T is removable. [S24]

### 1.4 Modern Samsung rooting is real, but model specificity matters

The 2026 `samsung-tv-root` project documents working chains for specific **QN90B and QN90F** devices. It does not provide a Q60T profile. Its existence improves the research landscape; it does not justify selecting another model's exploit profile for this television. [S22]

### 1.5 Separate the daily-use goal from the research goal

The recommended daily-use direction is to minimize Smart Hub involvement, remove only positively identified optional applications, and compare an offline-TV/external-player arrangement. The research direction is to establish capabilities and exact firmware provenance before attempting privileged access.

These goals can coexist. A successful experiment is not merely "root obtained": it should leave a working television, a measurable improvement, and a clear way back.

---

## 2. Device identification and evidence limits

### 2.1 What the photographs establish

| Field | Observed value | Evidential meaning |
|---|---|---|
| Model code | `GQ55Q60TGUXZG` | Exact target, rather than an approximate Q60-series match |
| Software version | `T-NKLDEUC-2743.0, BT-S` | Installed firmware family and displayed version |
| e-Manual version | `NIKDVBEUT-3.4.0` | Manual identifier, not the operating-system version |
| Sub-Micom version | `T-NLINTV-1005` | Additional component version, not the main Linux build |
| Interface language | German | German menu paths are appropriate |
| Device Care | Visible in the Support menu | A useful starting point for storage and troubleshooting |

The serial number, network addresses, Bluetooth identifiers and service-specific device IDs in the photographs are deliberately omitted. They are unnecessary for public compatibility research.

The event log shows entries labelled as CEC commands. Those entries do **not** establish an unwanted background workload. Likewise, the entries dated 1970 do not, by themselves, prove firmware corruption or compromise. The screenshots are identification evidence, not a performance trace.

### 2.2 What Samsung currently lists

The exact-model Samsung support page identifies this as a **55-inch Q60T from 2020**. Its download metadata lists `T-NKLDEUC.zip`, version **2743.0**, with a file-modification date of **15 September 2026** and a displayed size of **1286.57 MB**. The installed version matches that listing on the research date. [S01]

The listing date is not necessarily the firmware's compilation date or first over-the-air availability date. It also does not establish which individual vulnerabilities were fixed. Recommending "update to the latest firmware" without noticing that match would add little value.

Samsung's generation table maps **2020 TVs to Tizen 5.5 and Chromium M69**. This is the appropriate platform baseline, but it is not a live measurement of this TV's kernel, browser binary, security backports or exact patch state. A firmware number such as 2743.0 is not a Tizen major-version number. [S02]

### 2.3 Information still missing

The following must be measured rather than guessed: writable storage availability; installed application inventory; what operations are slow; cold-versus-warm behavior; SDB capabilities; running processes; exact kernel and architecture; memory pressure; and whether the latest firmware changed responsiveness.

In particular, this report does not invent a RAM capacity, processor model, mainboard part number, recoverable flash layout, or "safe Samsung services" list from the Q60T product name.

### 2.4 Research limitations

Primary sources were prioritized: Samsung's own documentation, original security research, maintainer documentation, and selected source files. Source inspection is distinguished from maintainer-reported hardware tests.

The firmware archive itself was **not downloaded or decrypted** for this report. Samsung's model page exposed the manual filenames and download metadata, but the model-specific manual PDFs were not successfully retrieved for page-by-page inspection. Menu guidance therefore uses accessible Samsung support articles and acknowledges model/version differences.

*(Editorial note: a companion document, [`firmware-analysis.md`](firmware-analysis.md), dated 26 September 2026 — the day after this research — subsequently obtained the exact archive, verified it against the download page, decrypted it, and performed static analysis including disassembly of the historical root driver. See §11 below for the cross-reference; the empirical results live in that document, not this one.)*

The Synacktiv research presentation was examined, including relevant diagram pages. No firmware-recovery method was validated on physical hardware. No speedup percentage is claimed.

---

## 3. Determine what is actually slow

### 3.1 Do not equate an installed app with a running workload

An unwanted application can occupy storage without consuming meaningful CPU time while idle. Conversely, one malfunctioning service or repeatedly failing network request could matter more than many dormant apps. Deleting icons is therefore not a performance diagnosis. Installed is not the same evidentiary category as running.

Separate five hypotheses for this investigation:

| Hypothesis | Observation that would support it | What would not establish it |
|---|---|---|
| Accumulated application data/storage pressure | Manage Storage is constrained, or a targeted cleanup repeatedly improves behavior | A long app list alone |
| Smart Hub/network dependency | Home improves substantially offline while basic controls remain responsive | One unusually fast launch |
| A particular app | Settings and HDMI work normally, but one application is consistently slow | Assuming all Tizen components are slow |
| Persistent system/firmware problem | Basic controls remain slow after a cold restart and controlled offline testing | A single stalled streaming service |
| Input-path or hardware problem | Delay changes with the input method, or persists outside Smart Hub under simplified conditions | The age of the television alone |

These are proposed diagnostic tests, not findings about this device.

### 3.2 Establish a small, repeatable baseline

The methodological point, not the exact click-timing procedure, is what matters here: measure the same operations (open Settings, change volume, open Home, switch HDMI source, launch the suspect app, cold restart) before and after each intervention, at a fixed number of warm/cold repetitions per operation. A phone recording of the remote action and screen is an adequate practical timer; the goal is repeatability, not laboratory precision.

Record the **median and range**, not a persuasive-looking percentile derived from a handful of trials. An application that fails to load is a failure, not a fast response. Keep the remote, source device, network arrangement and test order stable; record whether the TV was freshly restarted or had been in use for hours; avoid repeated full factory resets as a benchmarking technique.

### 3.3 Compare online and genuinely offline conditions

First compare the normal configuration with the TV disconnected from both Ethernet and Wi-Fi, using an HDMI source that can continue independently. Test basic controls and Home, not whether an internet application can stream while offline.

**Offline is not the same experiment as firewalled.** A firewall that silently drops requests can push the application down a different timeout/retry path than a genuinely disconnected network. Treat improvement or regression under blocking as an observed result for that condition, not a universal prediction.

Where possible, use an **A–B–A comparison**: baseline, intervention, then restore the baseline. A repeatable change is stronger evidence than a single "feels faster" observation immediately after rebooting.

### 3.4 Interpret the result before escalating

If only Home and streaming apps are slow, focus on application data, network-dependent behavior and bypassing Smart Hub. If volume, Settings and source switching are also consistently slow, application deletion may not address the cause — that warrants a simpler operating configuration and further diagnostics before any destructive software modification.

---

## 4. Reversible cleanup with the ordinary menus

### 4.1 Cold restart — not merely standby

Power off normally, disconnect the mains plug for approximately a minute, reconnect, and test. Samsung distinguishes this non-erasing restart from a factory reset. Never disconnect power during an actual firmware update. [S11] [S13]

A temporary improvement after restart is worth recording, but it does not identify which component was responsible. It is not a permanent debloat result.

### 4.2 Inspect storage before removing anything

Menu path (German UI, as photographed): **Einstellungen → Unterstützung → Gerätepflege → Speicher verwalten**.

Record the displayed free space, application sizes, and which apps expose **Details anzeigen**, **Cache leeren**, **Daten löschen** or deletion. Samsung documents this general workflow, but its current cache article illustrates newer software; individual controls may differ on this Q60T. [S07]

Start with a problematic optional application. Clearing cache targets temporary files; clearing application data is more disruptive and may remove saved setup and logins — preserve credentials first. Do not repeatedly clear useful caches merely to maximize the free-space display. [S07]

### 4.3 Remove genuinely optional applications

Path: **Home → Apps → Einstellungen/App-Einstellungen → application → Löschen**, where available. Samsung notes that some preinstalled applications cannot be removed through the normal interface. Removing an item from the Home row is not the same as uninstalling it. [S08]

Choose applications you recognize and do not need; preserve an easy reinstall path before removal. App auto-update and firmware updating are separate controls — changing one is not proof that the other has been disabled. [S08] [S13]

### 4.4 Reduce automatic Smart Hub entry

Under **Einstellungen → Allgemein → Smart-Funktionen**, switch off automatic Smart Hub startup and automatic startup of the last-used app. Samsung documents these controls for this style of interface. They change startup behavior, not ownership of the operating system or all background execution. [S09]

This is especially useful when an HDMI player provides the everyday interface. Removing shortcuts is a usability improvement, not memory recovered.

### 4.5 Handle a broken application before resetting everything

For a recommended app with a greyed-out Delete button, Samsung's troubleshooting article suggests **Reinstall** where offered — a repair experiment, not removal. A **Smart Hub reset** is a later option because it signs out all the apps, not only the troublesome one. [S10]

Path: **Unterstützung → Eigendiagnose → Smart Hub zurücksetzen**, with Eigendiagnose possibly nested inside Gerätepflege. Use the current on-screen path and your own PIN; Samsung's default is `0000` unless changed. Record settings and login requirements first. [S10]

A **full factory reset** is more disruptive and should follow, not precede, the simpler tests. Samsung says it removes downloaded apps, accounts and settings. Its developer FAQ also distinguishes a full reset — which can change the **DUID** (device unique identifier) — from a Smart Hub reset. That can matter for development certificates tied to a device identifier. [S11] [S12]

### 4.6 Optional services: change supported settings, not undocumented internals

Review the TV's actual privacy, personalization, voice and recommendation settings, and disable optional features not in use through the available ordinary interface. For Samsung TV Plus, use a displayed hide/disable option if present; an ordinary-menu action is not assumed to uninstall the underlying component.

Do not disable accessibility functions merely because they sound like background services, and do not change panel type, region, hotel mode, service-menu watchdogs or undocumented "Instant On" flags as generic speed tweaks. No exact-firmware evidence was established that such changes safely address the reported symptom.

---

## 5. What SDB, developer mode and a shell actually provide

### 5.1 Development access is not administrator access

Samsung's official workflow allows a computer to connect to a developer-enabled TV and deploy applications. Application signing and privilege checks still apply. Declaring a sensitive API in an application's manifest does not itself grant the corresponding privilege; Samsung requires the appropriate certificate level. [S03] [S05] [S06]

Normal certificate setup uses author and distributor certificates. Keep signing material private and backed up. The ability to sign your own application does not mean you can sign Samsung firmware or obtain platform-wide administrator privileges. [S05]

### 5.2 There are multiple independent access boundaries

For research purposes, use the following model — this is the analytical spine of the rest of this document:

| Boundary | Question to establish | Why it matters |
|---|---|---|
| Network connection | Can the intended computer reach the intended TV? | A connection failure is not an exploit result |
| SDB command dispatcher (`sdbd`, the on-device SDB daemon) | Which management requests are accepted? | Installation/listing paths may differ from ordinary shell access |
| Process identity | Is execution under an app account, `sdk`, or UID 0? | A shell prompt does not prove root |
| Security context | Which labels, capabilities and device permissions apply? | Unix identity alone may not determine access |
| Native-execution policy | Can the intended executable run? | The published research treats UEP separately from UID 0 |
| Persistent modification | Can changes survive reboot safely? | Volatile root is not an unlocked boot chain |
| Firmware/boot acceptance | Will the device accept and boot a modified image? | Decryption is not authorization to install |

This is an analytical framework derived from the distinct boundaries visible in Samsung's development documentation and the published exploit work. The exact state of each boundary on this TV remains to be established. [S03] [S06] [S17] [S18] [S23]

*(Terminology: "security context" here covers whatever combination of Linux capabilities, discretionary permissions and Tizen's mandatory-access-control layer applies to a given process. Tizen's platform security architecture is generally built from a SMACK-based (Simplified Mandatory Access Control Kernel) labeling layer plus Cynara, a privilege-checking service that authorizes API/resource access against a process's installed privileges. Neither component's specific configuration on this TV was inspected for this report; they are named here only to make the generic "security context" row concrete.)*

### 5.3 "Shell closed" is not "nothing works"

Bishop Fox demonstrated consumer TVs where a normal SDB shell was blocked and a root-enable request was denied, yet package-installation handling remained reachable. An older-model debloating report separately describes a working application-list dispatcher. Test the relevant capability instead of treating the ordinary-shell result as a complete inventory of access. [S15] [S24]

Conversely, an accepted management request does not imply unrestricted file access. A capability flag indicating file **push** does not promise arbitrary **pull**, and an accepted uninstall does not prove that system partitions are writable.

### 5.4 Local remote-control APIs are another interface entirely

An integration that changes volume or launches apps is not automatically a debuggable shell or firmware-management API. Home Assistant's Samsung integration is relevant to local control, not evidence that a TV can be rooted or its platform packages removed. [S30]

---

## 6. Read-only SDB investigation

### 6.1 Preparation and network scope

Use a trusted computer and official Samsung/Tizen development tools. Avoid arbitrary repackaged SDB binaries or installer scripts that immediately execute downloaded code. There is no need to expose the TV to the internet for another person to investigate it.

Find the TV's current address through its menu or your router's client list. Keep these two addresses distinct:

| Setting | Correct meaning |
|---|---|
| TV IP used by `sdb connect` | The television's address |
| Host PC IP in Developer Mode | The investigating computer's address |

Enable Developer Mode from **Apps/App Settings**, enter **12345** using the physical or on-screen numeric keypad, set the computer's address, confirm, and restart the TV. Samsung documents this procedure. It is not the service menu. [S03]

Use a trusted network segment. The developer-host address restriction is not a substitute for isolating an untrusted LAN. Never port-forward development or remote-control ports from the internet.

### 6.2 Explicit-target connection

The following commands are a **proposed collection procedure**, not commands executed during this report. The example IP is not an address inferred from the photographs. Use Bash on Linux/macOS, or translate the variables to PowerShell on Windows.

```bash
# Set these to your actual installed tool and television address.
SDB="/absolute/path/to/tizen-studio/tools/sdb"
TV_IP="192.168.50.25"   # Example only: replace it.
TV_SERIAL="${TV_IP}:26101"

# Keep raw logs private: they may contain device identifiers.
umask 077
mkdir -p tv-evidence

"$SDB" version > tv-evidence/sdb-version.txt 2>&1
"$SDB" connect "$TV_SERIAL"
"$SDB" devices
```

Check that the listed device corresponds to the intended TV, and use its exact SDB serial in later commands — the TCP serial commonly takes the `IP:26101` form shown above. **Do not fall back to the first connected device.** Samsung's CLI documentation explicitly distinguishes target names and serial selectors. [S03] [S04]

### 6.3 Query capabilities and the management application list

After confirming the target:

```bash
"$SDB" -s "$TV_SERIAL" capability \
  > tv-evidence/capability.txt 2>&1

# Community-observed TV management command; may be unsupported on this build.
"$SDB" -s "$TV_SERIAL" shell 0 applist \
  > tv-evidence/applist.txt 2>&1
```

The `capability` and `shell 0 applist` combination is documented in the older-device investigation, not guaranteed by this report for 2743.0. Preserve the raw response. A refusal or unsupported command is useful evidence; do not compensate with a bulk script that guesses installed applications. [S24]

Potential capability flags include `intershell_support`, `sdbd_rootperm`, `rootonoff_support`, `filesync_support` and `appcmd_support`. Interpret them as observations of this connection, not proof that every command in a similarly named category behaves identically. [S24]

If a command hangs, stop it rather than starting an unbounded retry loop. Do not add exploitation, uninstall or filesystem-write commands to this first session.

### 6.4 Optional HTTP identity check

The older-device guide documents a local information endpoint that may return model and developer-mode details:

```bash
# Optional, read-oriented probe against your own TV only.
# A timeout or absent endpoint is not proof that the TV is inaccessible by SDB.
curl --connect-timeout 3 --max-time 5 \
  "http://${TV_IP}:8001/api/v2/" \
  > tv-evidence/tv-info-private.json
```

Do not upload that JSON wholesale: responses may contain identifying information. Endpoint availability on this exact firmware is unverified. The necessary identification can also be read from the ordinary menus. [S24]

### 6.5 End the session deliberately

For a one-off diagnostic session, disable Developer Mode afterward and restart if required. Confirm that the development connection is no longer available.

There is an important exception for an intentionally installed tool with runtime development-service requirements: follow that tool's documented configuration rather than assuming it will continue working with Developer Mode disabled. TizenBrew's manual installation instructions include a change to the developer host address discussed in §8. [S21]

---

## 7. Controlled removal of unwanted applications

### 7.1 The practical opportunity

An ordinary-menu deletion restriction and the behavior of the development package manager are not necessarily identical. The older NU7400 investigation reports removing preinstalled apps through SDB. That justifies checking this Q60T's behavior, but not assuming that every rejection can or should be bypassed. [S24]

The initial scope should be **one recognizable, optional, reinstallable application**. It should not be the launcher, app store, account framework, tuner, settings application or an unidentified Samsung/Tizen service.

### 7.2 Important correction: application ID and package ID are not interchangeable

There is a genuine documentation/tooling trap:

| Interface | Identifier described by the relevant source |
|---|---|
| Direct `sdb uninstall` in the NU7400 report | Package ID |
| Samsung's TV-specific `tizen uninstall -p` documentation | **Application ID**, despite the option being called `--pkgid` |
| Generic debloat-tool implementations | May send a package ID and assume their installed CLI handles it |

Samsung explicitly distinguishes its TV CLI behavior from the common Tizen CLI. A guide that says "always strip the app suffix" or "all `-p` arguments are package IDs" is therefore not a reliable universal procedure. [S04] [S24] [S25]

Before using either route, establish the tool version, the actual identifier mapping and the command's semantics. A disposable application of your own, with a known manifest and a tested reinstall path, is a better way to validate the toolchain than experimenting on a platform package.

Do not derive IDs by blindly splitting at the first dot. Package and application relationships must come from actual metadata. Multiple application components can belong to one package; removing the package may affect more than the visible app.

### 7.3 Removal templates — not a ready-made removal list

These lines are intentionally commented out. They are alternative interfaces, not a sequence to run until one succeeds.

```bash
# Direct SDB route as reported on a different TV:
# "$SDB" -s "$TV_SERIAL" uninstall "VERIFIED_PACKAGE_ID"

# Samsung TV-specific CLI route, according to its official documentation:
# "/absolute/path/to/tizen" uninstall \
#   -s "$TV_SERIAL" -p "VERIFIED_APPLICATION_ID"
```

Use only the route whose behavior has been established for your toolchain and target. There is no responsible prewritten list of exact Q60T/2743.0 package deletions in this report because the actual installed inventory and dependencies are not yet available. [S04] [S24]

### 7.4 What qualifies as a successful removal

Check the raw tool result, refresh the real inventory where possible, inspect the TV interface, and compare storage. Then test the remaining applications, Settings, input selection, sound and the functions in regular use.

Repeat relevant checks after a normal restart and after reconnecting to the normal network. Some removals may not remain effective through future app provisioning, updates or resets; permanence must be observed, not inferred from a single success message.

If no live inventory is available, record that limitation. "The command returned zero" is weaker evidence than "the intended app is absent, storage changed, required functions work, and it remained absent after the defined checks."

### 7.5 A conservative classification policy

Use a positive allowlist: **identified optional application + known package relationship + no required shared function + known restoration route**. Unknown means do not remove.

Samsung/Tizen naming prefixes can justify caution, but a random-looking store identifier does not prove that a package is expendable. Account extensions and other infrastructure can also be packaged as applications. Do not treat a short blocklist as a dependency analysis.

---

## 8. TizenBrew and other application-level alternatives

### 8.1 What TizenBrew changes

TizenBrew provides an application environment for custom apps and modified web experiences, including TizenTube. It is useful when the goal is to replace a particular app experience, not to remove the entire Samsung operating system. [S20]

The installation documentation states support for **Tizen 3.0 / 2017 and newer**, placing the Q60T generation within its stated range. That is a project compatibility statement, not a recorded installation on this exact firmware. The preferred route is **TizenBrew Installer Desktop**; the former USB Demo Package route is marked deprecated because the required Samsung service was shut down. [S21]

### 8.2 Developer-mode configuration is part of the design

The desktop setup begins with the investigating computer as Host PC IP. The manual and rebuilding instructions subsequently set that value to **`127.0.0.1`**. This distinction matters: localhost is not the computer's address, and changing it can prevent the computer from reconnecting until the configuration is changed again. Follow the currently selected installation method. [S21]

Do not claim that turning Developer Mode off is always compatible with the installed workflow. Conversely, do not leave external development access enabled indefinitely without a reason.

The docs describe an additional Samsung-account/certificate flow for Tizen 7 and newer. Do not generalize that specific installer requirement to every older installation, or confuse it with Samsung's normal application-signing requirements. [S05] [S21]

### 8.3 Performance expectations

An alternative app could improve the particular experience it replaces, but the project does not establish a general Smart Hub speedup for this TV. Installing several alternatives can also add storage and runtime components.

Select one application with a clear purpose, measure it, and remove unused experiments. A custom frontend is not automatically a replacement browser engine or a way to increase hardware resources.

### 8.4 A useful non-root development route

For an application you own and can launch in debug mode, Samsung's Web Inspector exposes web layout, JavaScript, memory and network diagnostics. It is useful for attributing slowness inside that application; it is not a blanket profiler for every protected TV process. Samsung also notes that startup precedes inspector attachment, which limits observation of initial launch behavior. [S14]

That makes a small diagnostic app a possible research tool, but not a reason to build an elaborate new launcher before identifying the real bottleneck.

---

## 9. Review of publicly available debloating tools

### 9.1 An older-device guide is useful evidence, not a universal specification

The `ardazeytin/samsung-tizen-tv-debloat` report is valuable because it distinguishes restricted SDB from an ordinary Linux shell. Its test device is a NU7400, not this Q60T. The guide also acknowledges that it did not directly measure the space recovered through shell commands. [S24]

Use it to formulate testable questions. Do not inherit its broader package-safety rules, recovery assumptions or statements about every retail Samsung TV. A report on a different firmware can identify a mechanism worth checking without establishing your result.

### 9.2 SAWSUBE: selected source review uncovered relevant safeguards that are missing

Source inspected: `backend/services/debloat_service.py` at revision `db3d943dbad8803deaedcd8c5b5644995302debf`.

The following are observations of that file, **not a full security audit or a claim of malicious intent**. [S25]

| Observed implementation | Practical concern |
|---|---|
| The scan function returns a bundled app catalogue | The list is not proof of the apps installed on the connected TV |
| Connection failure can still lead to catalogue results | A populated screen is not proof of a successful device query |
| Serial resolution can fall back to the first connected SDB device | Multiple connected devices create a wrong-target risk |
| Unknown entries can default to `safe_to_remove=True` | Unknown should not be classified as safe without evidence |
| Removal invokes `tizen uninstall` with stored identifiers | It does not itself supply root or a protected-service bypass |
| Success can be inferred from return text/code without refreshed inventory | Reported success needs independent after-state verification |

These are reasons not to use this revision as an unattended, trusted Q60T debloater. A safer implementation would fail on target ambiguity, distinguish catalogue suggestions from measured inventory, default unknown packages to blocked, and require explicit approval plus verification for each change.

### 9.3 Similar names and impressive interfaces are weak compatibility evidence

The TPTRoot repository found during searching targets **Tizen phones**, with a reported Z1/DirtyCow path — not a Q60T TV solution. [S26]

Likewise, this investigation did not establish a compatible SamyGO installation or an Android/custom-Linux image for the exact target. That is an evidence gap, not a claim that future porting is impossible.

Evaluate tools by exact target coverage, inspected behavior, recovery design and reproducible results — not screenshots, stars, an "AI-assisted" label, or a large catalogue of package names.

---

## 10. Rooting research and compatibility analysis

### 10.1 Evidence map

| Research path | Reported target or scope | Access demonstrated by the source | Status for GQ55Q60TGUXZG / 2743.0 |
|---|---|---|---|
| Synacktiv Q60T chain | Historical Q60T research presented in 2021/2022 | Browser entry, kernel escalation, root and execution-policy work | Same product family, but no established current-firmware compatibility |
| Bishop Fox SDB injection | Tested Tizen 5.5/7/8/9 environments, including physical TVs | Command execution as `sdk` | Relevant entry-point lead; not verified here |
| QN90B chain | QN55QN90BAFXZA, T-PTMAKUC-1602.3 | Volatile root through a device-driver memory primitive | Different firmware family and hardware assumptions |
| QN90F chain | Specific QN90F devices, firmware 1203.0/1301.0 | Volatile root using a Mali-G510 path | Different target; not a Q60T exploit profile |
| New Q60T port combining an available entry point with a compatible escalation | Proposed investigation only | Nothing demonstrated on this TV | Requires separate evidence for every stage |

The rows summarize the named authors' results. None was reproduced on this television during this investigation. [S15] [S16] [S17] [S22] [S23]

### 10.2 Synacktiv: the strongest historical match to the product family

Synacktiv published an actual Q60T exploit repository, including an example that reaches UID 0, firmware-analysis tooling and presentation material. Its firmware-decryption example uses **T-NKLAKUC_2201.0**, a different firmware family from the European **T-NKLDEUC**. An example archive used for decryption is not necessarily the build used to validate every exploit stage. [S16]

The presentation describes a **V8 entry point associated with CVE-2020-6383**, a kernel escalation involving **`/dev/sdp_mem`**, and separate handling of Samsung's **UEP (unsigned-execution protection)**. It also discusses security-context constraints. Those details are valuable starting points for comparative analysis, not universal payload parameters. [S17]

For a present-day port, verify whether the relevant component still exists, whether its implementation remains vulnerable, whether the starting process can access it, and whether the target architecture and memory assumptions match. A device node name alone answers none of the latter questions.

Do not copy historical addresses or offsets into a current build. The difference between a useful research lead and a working exploit is the evidence that makes each assumption valid for the target.

### 10.3 Bishop Fox: a newer initial-access lead, but not root

Bishop Fox's **24 February 2026** advisory describes **SVE-2025-50109**, command injection through SDB package-installation handling. Preconditions include Developer Mode and access from the configured development-host address. Its physical-device testing includes a **UN43TU700DFXZA with Tizen 5.5**. The demonstrated account is `sdk`, not root. [S15]

The publication does not verify `T-NKLDEUC-2743.0`. Neither "published in 2026" nor "tested on Tizen 5.5" resolves whether the code on this particular TV is vulnerable.

An eventual bounded proof of this entry point should establish only the intended harmless result, record the actual identity, and clean up its temporary state. A successful callback would establish command execution — not safe system debloating, persistence or unrestricted native execution.

**A preflight that uses injected commands is active exploitation.** It should not be described as a read-only version check just because the commands executed afterward only read metadata.

### 10.4 QN90B/QN90F: important developments, not interchangeable exploits

The newer `chris-ritsen/samsung-tv-root` project documents a shared SDB entry point followed by target-dependent escalation: a **`/dev/sdp_pqe_fdet`** path on QN90B and a **Mali-G510 r48p0 / CVE-2025-0072** path on QN90F. Its root state is volatile; a computer can reacquire it after the TV restarts. [S22]

The QN90B reproduction note is especially useful conceptually: it specifies firmware-family, architecture, kernel, device-access and memory-layout requirements. It also treats UEP as a distinct boundary, with its fixed-address operation restricted more narrowly than root acquisition. [S23]

For this Q60T, the conclusion is straightforward: **do not select `qn90b`, select `qn90f`, or bypass their compatibility checks merely to see what happens**. The useful contribution is the methodology and separation of stages — not an available Q60T target.

### 10.5 Historical patch evidence argues against version-name shortcuts

Samsung's public security history lists V8 and driver patches affecting the **T-NKLDEUC** family, including entries under August 2021. Later entries also describe changes to debug-information and command exposure. The short bulletin descriptions do not establish a precise patch map for the current binary. [S19]

This is why an old Chromium baseline does not mean all vulnerabilities from that Chromium era remain exploitable. Conversely, a recently dated firmware download does not prove that a particular research path is closed.

Searching the vendor bulletin for the number `50109` can also return **SVE-2019-50109**, which is not **SVE-2025-50109**. Preserve the full identifier. No exact public mapping from the newer SDB advisory to firmware 2743.0 was established in this review. [S15] [S19]

### 10.6 A defensible Q60T research hypothesis

A possible investigation is:

**working low-privilege entry point → verified access to an applicable kernel surface → target-correct escalation → individually tested, reversible changes**.

The attractive hypothesis is that a newer SDB entry point might replace the historical browser entry point. However, changing the starting account can change permissions and security labels. A driver accessible to a browser process in one build might be inaccessible to `sdk` in another.

Treat this as a sequence of falsifiable questions. If the first candidate escalation is patched or inaccessible, record that finding and investigate another specific, evidence-supported candidate rather than trying unrelated payloads at random.

---

## 11. A firmware-specific reverse-engineering plan

**Status update (editorial, not part of the original 25 September research):** the plan below was written before the archive existed on disk. Steps 11.1–11.4 have since been executed empirically and documented separately in [`firmware-analysis.md`](firmware-analysis.md), dated 26 September 2026 — one day after this document. That companion document independently obtained the exact `T-NKLDEUC.zip` build, hash-verified it, decrypted `upgrade.msd` using Synacktiv's published decryptor (§11.3 below), extracted the VDFS4 rootfs, and disassembled the historical `sdp_mem`/`sdp_hwmem` root primitive (§11.5's driver-comparison question). Its headline conclusion — the firmware's AES key is unrotated (a confidentiality finding, not a root or signature break) and the arbitrary-physical-memory primitive is closed at the driver level by a whitelist-containment and kernel-region-intersection check — does not change any statement in this document; if anything it confirms §11.3's prediction that decryption and authentication are separate questions, and that a driver comparison (§11.4) rather than a version string would be needed to resolve access. The plan text below is preserved as originally written, since it correctly anticipated what that later work would need to establish.

### 11.1 Start with the exact, official artifact

Obtain the firmware through the support page for **GQ55Q60TGUXZG**, not a forum mirror or another region's similarly named model. Record the displayed version, URL, retrieval date, archive size and a locally calculated hash. The current listing is described in §2. [S01]

Example host-side hashing commands after downloading the file:

```bash
# Linux:
sha256sum T-NKLDEUC.zip

# macOS alternative:
shasum -a 256 T-NKLDEUC.zip
```

These commands had not been run on an actual firmware archive at the time of this report. A hash identifies the file you examined and detects later changes; without an independently trusted reference, it is not by itself proof of authenticity.

An unversioned filename can later point to a different release. Record embedded metadata as well as the download-page label. Preserve an untouched copy and analyze a separate working copy.

### 11.2 Inspect before executing or extracting broadly

Use an isolated analysis environment. Review archive members, lengths, compression ratios and paths before extraction. Reject unexpected traversal paths and impose extraction-size limits. Do not execute firmware files merely because their names resemble ordinary Linux programs.

The immediate objective is an artifact inventory:

| Artifact or property | Question | Useful result |
|---|---|---|
| Outer archive | Which members and paths are present? | Exact container inventory |
| Firmware metadata | Which family, version and internal build are identified? | A target-specific fingerprint |
| Container header | Does it match a supported parser format? | Evidence for or against tool applicability |
| Cryptographic descriptors | What is encrypted and what is signed? | Separate confidentiality and authenticity boundaries |
| Extracted executables, if legitimately obtained | Architecture, dependencies, relevant functions? | Static analysis inputs |
| Kernel and drivers, if available | Versions and actual access-check implementation? | Candidate-specific compatibility evidence |

This was a proposed work plan at the time of this report; the corresponding cells were not populated with results here because the archive had not been acquired. (See the editorial status note above for the subsequent, separately documented work that did populate them.)

### 11.3 What the existing decryptor establishes — and what it does not

Source inspection of Synacktiv's `firmware/decrypt.py` shows a parser expecting **`MSDU11`** (the magic/format identifier of Samsung's firmware container), AES-related processing, and descriptors including **`SecureDowngradeDesc`** and **`OURSAValidationDesc`** — type-length-value (TLV) encoded records within the decrypted header. The source is useful for understanding the historical container. It had not been validated against this current archive at the time of this report. [S18]

A matching header would establish only an initial format resemblance. The key material, descriptor layout, integrity checks or packaging may differ. A parser exception is not proof of an unbreakable format, and successful output is not proof that every byte has been authenticated or interpreted correctly.

Keep three questions separate:

**Can the contents be read? Can a modified package be authenticated? Will the device boot and operate correctly after accepting it?**

These are different problems. Decrypting or re-encrypting a firmware payload does not supply Samsung's signing authority or establish a supported route to flash it.

### 11.4 Compare the relevant implementation, not only version strings

A useful static investigation would prioritize the components involved in the proposed access path: SDB request dispatch and installation handling; the vulnerable operation described by the advisory; candidate kernel-driver access checks; and execution/security-policy configuration.

For a suspected kernel path, document architecture, module or built-in placement, device permissions, applicable security labels, and the exact operation that would be exercised. A reused product name or a shared Linux version is insufficient.

Where a known vulnerable and known fixed implementation can be obtained, compare the relevant function and bounds/permission checks. Absence of an informative version string is not an excuse to claim that two binaries are equivalent.

Samsung's historical patch records can prioritize what to inspect, but should not replace the binary comparison. [S19]

### 11.5 Investigate system overhead only after obtaining suitable visibility

Even a successful root port should first be used for **observation**, not deletion. Record the process tree, resource usage over a bounded interval, startup relationships, service dependencies and existing persistent configuration. Collect only what is needed; account tokens and DRM secrets are not part of a performance baseline.

For every proposed component change, answer:

| Question | Required evidence |
|---|---|
| Is the component actually active? | A process/service observation, not only an installed package |
| Does it contribute meaningful overhead? | Repeated CPU, memory, I/O or latency evidence |
| What depends on it? | Callers, service relationships or controlled functional testing |
| Can it be changed temporarily? | A non-persistent setting or narrowly scoped reversible operation |
| Does the change improve the original symptom? | Before/after measurements using the same protocol |
| Can the change be undone from outside the broken interface? | A validated recovery path appropriate to that change |

A stopped service that continuously restarts, or leaves callers waiting, might make the TV worse. "Samsung-branded" is not an architectural role and is not a removal criterion.

### 11.6 Native applications and firmware replacement are different projects

An alternative application can use the existing system's display and playback infrastructure. Replacing the operating system would additionally require a usable boot path and working support for the panel, graphics, video decoding, sound, input, power management and any other retained functions.

No tested custom-OS image or full replacement procedure for this exact configuration was established. A generic ARM Linux image, Android image or firmware from a different TV is not a substitute for that missing integration work.

---

## 12. Recovery, persistence and hardware boundaries

### 12.1 A factory reset is not a universal undo button

Samsung documents resets of user settings and Smart Hub data, but its developer FAQ explicitly says **firmware downgrade and forced firmware updates are not supported**. A factory reset is not a return to the software version shipped in 2020. [S11] [S12]

Do not assume that a USB upgrade will reinstall the same version, repair arbitrary root-level changes, restore boot metadata or recover a non-booting television. A supported update mechanism and an emergency recovery mechanism are different capabilities.

### 12.2 Match the rollback to the action

| Proposed action | Rollback to prepare before proceeding |
|---|---|
| Disable an ordinary setting | Record its previous value and the path back |
| Clear cache | Accept regeneration; record that it is not restoration of deleted cached content |
| Clear app data | Credentials and a known reconfiguration path |
| Remove an optional application | Verify that it can actually be reinstalled on this model/region |
| Install a development app | Know its identity, signing material and removal method |
| Temporarily stop a service | A validated restart/reboot path and access that remains available |
| Modify persistent system files | A tested, appropriate restoration method, not merely a backup file |
| Change firmware or boot state | Model-specific recovery evidence before any write |

This table is a decision rule, not an assurance that the latter recovery capabilities exist on this TV.

### 12.3 Prefer volatile experiments over boot modifications

The newer root research demonstrates a useful distinction between volatile access and a host that reacquires access. That approach avoids claiming a permanent bootloader unlock. [S22] [S23]

For a first Q60T investigation, persistent boot hooks should be avoided entirely. A short-lived experiment that disappears after a restart is easier to bound than an unsupported system service that runs on every boot. Nevertheless, "volatile" does not make a kernel write harmless — it still needs target-correct validation.

### 12.4 Service-menu shortcuts are not the recommended path

Do not substitute undocumented service-menu settings for a supported app cleanup. Settings affecting panel configuration, region, calibration, power behavior or recovery can have consequences unrelated to bloatware. This review did not establish a safe collection of such changes for this exact model and firmware.

Keep **Anynet+/HDMI-CEC** separate from internet smart services when evaluating what to retain. The event log already shows CEC-labelled activity; it does not justify switching off a useful control path.

### 12.5 Hardware work is a separate escalation

Board identification, serial-console research and flash analysis could be useful if software-only investigation reaches a well-defined limit. They require the **actual board revision**, measured electrical characteristics and a recovery plan; the retail model name does not provide a verified header pinout.

A serial header, if present, is not proof of an interactive root console or an unlocked bootloader. Do not assume a voltage, pin assignment or write-capable flash procedure from a photograph of a similar board.

Opening a television also exposes a mains-powered device with potentially hazardous stored energy. It is not justified merely to clear application cache. Such work belongs on an appropriate bench, preferably with a spare board and someone competent in television power-supply safety.

---

## 13. Network isolation and external-player strategy

### 13.1 The lowest-complexity way to avoid most Smart Hub interaction

The subject of this research owns an **Apple TV** and uses a **Flint 2/OpenWrt-based network**; their current connection to this television is not assumed.

A practical trial is to use the Apple TV as the application platform, turn off Samsung's automatic Smart Hub/last-app entry, and disconnect the television itself from the network, keeping the external player's network access intact. Apple documents television/receiver power and volume control through its remote, including HDMI-CEC where supported and IR alternatives. [S09] [S28]

This bypasses the Samsung app experience. It does not remove Tizen, improve every TV menu, or prove that all local Samsung background processing has stopped.

### 13.2 An HDMI source alone does not establish privacy

The 2024 research paper *Watching TV with the Second-Party* observed automatic content recognition (**ACR**) activity on Samsung/LG test televisions, including HDMI use. It also found that opting out stopped ACR-server traffic in its experiments. These were particular tested configurations, not an examination of this German Q60T/2743.0. [S27]

The practical implication is to review optional viewing-information and advertising consent settings and measure traffic if the TV remains online. An external player plus an online television is not equivalent to an offline television.

### 13.3 Choose between fully offline and selectively networked operation

| Mode | Appropriate use | Tradeoff |
|---|---|---|
| TV physically/network-configured offline | HDMI display with no TV network features needed | Simplest boundary; TV internet and LAN features unavailable |
| TV retains LAN access but has no WAN forwarding | Local control or a local media workflow is required | Requires correct per-device/routed policy and validation |
| TV remains online with selective filtering | Samsung streaming apps are still required | More dependencies, exceptions and ongoing maintenance |

Define the desired router policy before writing configuration; its current firmware, zones, IPv6 routing and the television's active interface were not inspected for this report, so this report does not supply a guessed UCI/nftables script.

GL.iNet documents client blocking by MAC address. Do not assume that a generic **Block client** button means "deny WAN but retain SDB and all LAN services" — verify its actual effect in the installed router software. [S29]

### 13.4 Proposed policy for a LAN-only research setup

The following is a design target, not deployed configuration:

| Traffic | Proposed treatment |
|---|---|
| TV to internet | Deny both IPv4 and IPv6 forwarding |
| Trusted investigation computer to TV | Allow only the required local services during the session |
| Other untrusted devices to TV | Restrict; do not rely solely on the configured developer IP |
| TV to local DNS/time/media services | Permit only deliberately chosen dependencies |
| Apple TV and other household devices | Leave their independent policies unchanged |
| Internet to TV development/control ports | No forwarding |

Account for both wired and wireless interfaces so that reconnecting through the other one does not silently defeat the intended boundary. Also verify existing connections after policy changes; do not use an empty short log as the sole proof that no traffic can leave.

### 13.5 DNS blocking is not package removal

A DNS blocklist can prevent some destinations from resolving. It does not uninstall an app, disable its local code or prove a reduction in memory use. Direct-address connections and permitted alternative paths require separate consideration.

A blanket Samsung-domain blocklist can also interfere with login, app provisioning or updates; some failure paths may produce more retries or longer waits. Treat those effects as things to measure rather than a reason to promise a speedup.

Start with per-TV observations and one narrowly scoped change. A fully offline HDMI-display setup is easier to reason about than an ever-growing collection of unverified domains.

### 13.6 Keep an intentional maintenance path

Samsung documents USB firmware updating for televisions without a usable internet connection. Use the exact model's official instructions and artifact when an update is deliberately chosen. [S13]

Do not automatically reconnect the TV indefinitely just to check for updates, or intentionally retain a vulnerable internet-exposed configuration to preserve a research exploit. Research access and everyday exposure should be managed separately.

---

## 14. Recommended investigation roadmap

### Phase A — Establish the symptom and baseline

**Inputs:** The television as currently configured; Manage Storage; a short list of required functions.

**Work:** Record storage and app sizes; distinguish basic-control latency from Home/app latency; perform a genuine cold restart; compare online and offline HDMI operation.

**Completion evidence:** A short results table, photographs of relevant non-identifying storage screens, and a concrete statement such as "Settings is responsive but Home is slow online." Avoid a conclusion phrased only as "the whole TV is bad."

**Decision:** If the daily-use problem is solved by a simpler configuration, further reverse engineering becomes optional rather than a prerequisite for using the TV.

### Phase B — Ordinary cleanup and one change at a time

**Inputs:** Phase A observations and the actual menu options.

**Work:** Clear a relevant cache, remove optional apps through the supported UI, change automatic startup behavior, and retest. Use a Smart Hub reset only when the evidence suggests a persistent app-environment problem and login recovery is prepared. [S07] [S08] [S09] [S10]

**Completion evidence:** Before/after results and a record of each change. Do not bundle ten interventions into an unexplained "optimization."

### Phase C — Read-only development capability inventory

**Inputs:** A trusted computer, exact TV address and installed official development tools.

**Work:** Follow §6. Record tool version, capabilities and real app-list output. Establish whether the management dispatcher works independently of ordinary shell access.

**Completion evidence:** Raw logs retained privately and a redacted compatibility summary. An unsupported app-list command is a valid result.

**Stop condition:** Ambiguous device identity, unexpected target selection, or a tool that offers only a static catalogue instead of evidence from the device.

### Phase D — A single controlled optional-app removal

**Inputs:** Positive identification of an optional app, resolved package/application identifiers, and a real restoration path.

**Work:** Validate tool semantics using a disposable development app when necessary. Remove one selected optional app, then verify inventory, storage, behavior and persistence under the defined reboot/network checks. [S04]

**Completion evidence:** A precise app-specific result. Do not convert one success into a universal removal list.

**Stop condition:** Uncertain dependencies, unexpected disappearance of other components, or no way to restore the selected application.

### Phase E — Exact-firmware static analysis

**Inputs:** Official archive, immutable original copy, calculated hash and an isolated analysis environment.

**Work:** Establish format, build information and parser applicability; inspect relevant components; compare specific vulnerability conditions. No TV writes are needed for this stage.

**Completion evidence:** A compatibility matrix with concrete supporting artifacts. "This looks like a Q60T firmware" is not sufficient.

*(As noted in §11, this phase has since been executed and documented in [`firmware-analysis.md`](firmware-analysis.md).)*

### Phase F — Bounded active research, only after the preceding evidence

**Inputs:** An explicitly chosen entry point, known prerequisites, cleanup procedure and acceptable recovery risk.

**Work:** Establish only the initial access claimed, capture identity/context, then assess escalation separately. If root is obtained, begin with resource observation and a reversible experiment — not system-file deletion.

**Completion evidence:** Exact model/build, method, access level, limitations, changes made and recovery outcome.

**Stop condition:** Failed compatibility checks, unstable behavior, unbounded memory operations, or an operation whose recovery depends on an untested assumption.

---

## 15. Evidence templates and final assessment

### 15.1 Device and collection record

Keep raw identifiers private. A shareable record can use this structure:

```text
Date:
Model: GQ55Q60TGUXZG
Displayed firmware: T-NKLDEUC-2743.0, BT-S
Network mode: online / physically offline / LAN-only
Required functions:
Slow operations:
Manage Storage free space:
Largest optional apps:
SDB tool version:
Exact target verified: yes / no
Capability query: succeeded / refused / unsupported / not tested
Application enumeration: live result / refused / unsupported / not tested
Normal shell: not tested / closed / available
Actions performed:
Rollback performed or available:
Identifiers and credentials redacted: yes / no
```

Do not replace "not tested" with an assumed result. Keep a successful enumeration distinct from a preloaded catalogue.

### 15.2 Performance record

| State | Operation | Trials | Median | Range | Failures | Notes |
|---|---|---:|---|---|---:|---|
| Baseline | Open Settings | — | Not measured | Not measured | — | |
| Baseline | Open Home | — | Not measured | Not measured | — | |
| Cold restart | Open Home | — | Not measured | Not measured | — | |
| TV offline | Open Home | — | Not measured | Not measured | — | |
| After one cleanup | Relevant operation | — | Not measured | Not measured | — | |
| Restored baseline | Same operation | — | Not measured | Not measured | — | |

A useful result explains the conditions and preserves failures. There is no defensible numerical speedup estimate for this TV before these measurements exist.

### 15.3 App-change record

```text
Visible application name:
Application ID and source of that identity:
Package ID and source of that relationship:
Other components in the same package:
Why this app is optional:
How reinstall was verified:
Tool/interface and version:
Exact target selected:
Before-state evidence:
Approved operation:
Raw result:
After-state evidence:
Storage change, if measurable:
Basic TV functions checked:
Result after restart and network reconnection:
Restoration outcome, if performed:
```

### 15.4 What would justify stronger conclusions

A successful `capability`/`applist` session would justify describing those commands as supported on this exact build. A verified single-app uninstall would justify an app-specific removal procedure. A working `sdk` shell would justify an initial-access finding. Verified UID 0 and applicable security-policy access would justify a rooting finding.

A **full-debloat recommendation** would require considerably more: identified unwanted active components, dependency analysis, measurable benefit, repeatable behavior and a recovery design. None of those should be inferred solely from a root prompt.

### 15.5 Final recommendation

For immediate usability, prioritize the ordinary cleanup, disable automatic Smart Hub entry, and test the television as an offline HDMI display with an external player. For native-app debloating, the most promising next investigation is the **restricted SDB management path**, with correct identifier handling and a single-app scope. [S04] [S08] [S09] [S24] [S28]

For deeper control, there is enough genuine prior work to justify a firmware-specific research effort. The historical Q60T chain, newer SDB entry point and modern Samsung root projects provide concrete starting points. They do **not yet establish a working full-debloat solution for GQ55Q60TGUXZG / T-NKLDEUC-2743.0**. [S15] [S16] [S22]

The unresolved items are exact device capabilities, actual firmware behavior, component dependencies and measured overhead — not a lack of conceivable research paths.

---

## 16. Sources and provenance

All sources below were accessed or inspected for this report on **25 September 2026**. A current project README is a maintainer statement, not independent reproduction. Links to mutable branches may change after this report; the SAWSUBE review is explicitly pinned to a revision.

| Ref. | Primary source | Role and limitation |
|---|---|---|
| [S01] | Samsung Germany — GQ55Q60TGUXZG support | Exact model and embedded download metadata; archive itself not analyzed |
| [S02] | Samsung Developer — Web Engine Specifications | Model-year platform baseline, not live patch-state evidence |
| [S03] | Samsung Developer — TV Device | Official developer-mode and device-connection workflow |
| [S04] | Samsung Developer — Command Line Interface | TV-specific install/run/uninstall semantics and device selectors |
| [S05] | Samsung Developer — Creating Certificates | Application signing and certificate workflow |
| [S06] | Samsung Developer — Privileges Q&A | Certificate-level/API privilege requirements |
| [S07] | Samsung Germany — App-Daten und Cache löschen | Supported cleanup concept; current screenshots are not Q60T-specific |
| [S08] | Samsung UK — Manage apps on a Smart TV | Ordinary removal, preinstalled-app limitations, app updating |
| [S09] | Samsung Ireland — Activate/deactivate Smart Hub | Startup behavior controls for the relevant menu style |
| [S10] | Samsung UK — Apps not working or loading | Reinstall and Smart Hub reset guidance |
| [S11] | Samsung UK — Restart or factory reset | Cold restart and destructive reset distinction |
| [S12] | Samsung Developer — Device Information and Firmware Q&A | Unsupported downgrade/forced updates; reset/DUID distinction |
| [S13] | Samsung UK — Update Smart TV software | Supported online and USB update workflow |
| [S14] | Samsung Developer — Web Inspector | Application-level debugging capabilities and limits |
| [S15] | Bishop Fox — Samsung Tizen OS, versions through 9.0 | Original SVE-2025-50109 advisory, published 24 February 2026 |
| [S16] | Synacktiv — samsung-q60t-exploit | Historical exploit repository and decryption example |
| [S17] | Synacktiv — Rooting Samsung Q60T Smart TV, Sthack 2022 | Original technical presentation; relevant diagram pages inspected |
| [S18] | Synacktiv — firmware/decrypt.py | Source inspection only; not run on the 2743.0 archive |
| [S19] | Samsung TV Security Updates | Official historical patches; no exact 2743.0 mapping established |
| [S20] | TizenBrew — project README | Project purpose and application-level scope |
| [S21] | TizenBrew — installation documentation | Stated compatibility, current preferred route and localhost configuration |
| [S22] | chris-ritsen — samsung-tv-root README | Maintainer-reported QN90B/QN90F tests; not Q60T support |
| [S23] | chris-ritsen — QN90B reproduction note | Explicit compatibility boundaries and separate UEP handling |
| [S24] | ardazeytin — samsung-tizen-tv-debloat README | First-person NU7400 observations; not an exact-target validation |
| [S25] | SAWSUBE — debloat_service.py, pinned revision | Selected source review of catalogue, targeting, classification and removal behavior |
| [S26] | AstFast — TPTRoot README | Confirms this search lead concerns Tizen phones, not the target TV |
| [S27] | Anselmi et al. — Watching TV with the Second-Party | Original ACR measurement research; not this exact device/firmware |
| [S28] | Apple — Use the Apple TV remote to control TV/receiver | Power/volume control options; actual household setup not inspected |
| [S29] | GL.iNet — Block client devices | Vendor-documented client blocking; not an audit of your router rules |
| [S30] | Home Assistant — Samsung Smart TV integration | Local control integration; not root or package-management evidence |

[S01]: https://www.samsung.com/de/support/model/GQ55Q60TGUXZG/
[S02]: https://developer.samsung.com/smarttv/develop/specifications/web-engine-specifications.html
[S03]: https://developer.samsung.com/smarttv/develop/getting-started/using-sdk/tv-device.html
[S04]: https://developer.samsung.com/smarttv/develop/getting-started/using-sdk/command-line-interface.html
[S05]: https://developer.samsung.com/smarttv/develop/getting-started/setting-up-sdk/creating-certificates.html
[S06]: https://developer.samsung.com/smarttv/develop/faq/privileges.html
[S07]: https://www.samsung.com/de/support/tv-audio-video/app-daten-und-cache-loeschen/
[S08]: https://www.samsung.com/uk/support/tv-audio-video/how-do-i-manage-apps-on-my-smart-tv/
[S09]: https://www.samsung.com/ie/support/tv-audio-video/how-to-activate-or-deactivate-the-smart-hub/
[S10]: https://www.samsung.com/uk/support/tv-audio-video/my-tv-apps-wont-open/
[S11]: https://www.samsung.com/uk/support/tv-audio-video/how-to-reset-my-samsung-tv/
[S12]: https://developer.samsung.com/smarttv/develop/faq/device-information-and-firmware.html
[S13]: https://www.samsung.com/uk/support/tv-audio-video/how-do-i-update-the-software-on-my-samsung-smart-tv/
[S14]: https://developer.samsung.com/smarttv/develop/getting-started/using-sdk/web-inspector.html
[S15]: https://bishopfox.com/blog/samsung-tizen-os-version-through-9-0
[S16]: https://github.com/synacktiv/samsung-q60t-exploit
[S17]: https://www.synacktiv.com/sites/default/files/2022-05/Sthack2022_Rooting_Samsung_Q60T_Smart_TV.pdf
[S18]: https://github.com/synacktiv/samsung-q60t-exploit/blob/main/firmware/decrypt.py
[S19]: https://samsungtvbounty.com/securityUpdates
[S20]: https://github.com/reisxd/TizenBrew
[S21]: https://github.com/reisxd/TizenBrew/blob/main/docs/README.md
[S22]: https://github.com/chris-ritsen/samsung-tv-root
[S23]: https://github.com/chris-ritsen/samsung-tv-root/blob/master/docs/research-notes/QN90B_REPRODUCTION.md
[S24]: https://github.com/ardazeytin/samsung-tizen-tv-debloat
[S25]: https://github.com/WB2024/SAWSUBE/blob/db3d943dbad8803deaedcd8c5b5644995302debf/backend/services/debloat_service.py
[S26]: https://github.com/AstFast/TPTRoot/blob/main/README.md
[S27]: https://arxiv.org/abs/2409.06203
[S28]: https://support.apple.com/guide/tv/atvbbe2477c9
[S29]: https://docs.gl-inet.com/router/en/4/tutorials/how_to_block_client_devices/
[S30]: https://www.home-assistant.io/integrations/samsungtv/

---

## Glossary

- **SDB (Smart Development Bridge)** — Tizen's device-control protocol and CLI tool (`sdb`), analogous to Android's `adb`; used throughout §5–§7 for capability queries and app management. Not interchangeable with ADB (§1.2).
- **sdbd** — the SDB daemon running on the TV that receives and dispatches `sdb` commands (§5.2's "SDB command dispatcher" row); its behavior (which commands it accepts) is independent of whether an ordinary interactive shell is enabled (§5.3).
- **Capability flags** — named boolean/enum fields returned by `sdb capability` (e.g. `intershell_support`, `sdbd_rootperm`, `rootonoff_support`, `filesync_support`, `appcmd_support`) describing what a given `sdbd` build permits (§6.3). Observed per-connection, not guaranteed to generalize.
- **UEP (Unsigned-Execution Protection)** — Samsung's code-execution-authenticity control, treated in the published research as a boundary distinct from UID/root (§5.2, §10.2, §10.4).
- **SMACK (Simplified Mandatory Access Control Kernel)** — the Linux Security Module commonly underlying Tizen's mandatory access-control labeling; named here only as background for the generic "security context" boundary in §5.2. Its specific configuration on this TV was not inspected.
- **Cynara** — Tizen's privilege-checking service, which authorizes API/resource access against a process's installed privileges; likewise named only as background for §5.2's "security context" row, not independently verified here.
- **DUID (device unique identifier)** — a per-device identifier that a full factory reset can change, distinct from a Smart Hub reset; relevant to development-certificate binding (§4.5).
- **ACR (automatic content recognition)** — the on-screen-content-fingerprinting feature discussed in §13.2; independently measured (on different hardware) to stop generating server traffic when its opt-out is used.
- **`sdk` account** — the non-root process identity yielded by the published SDB command-injection vulnerability (SVE-2025-50109); a shell under this account is initial access, not root (§5.2, §10.3).
- **MSDU** — the magic/format identifier (`MSDU11`) of Samsung's firmware container format, as documented in Synacktiv's `decrypt.py` (§11.3).
- **TLV descriptor** — a type-length-value encoded record; the decrypted firmware header's internal structures (e.g. `SecureDowngradeDesc`, `OURSAValidationDesc`) are described as such records (§11.3).
- **VDFS4** — Samsung's proprietary read-only filesystem format referenced in the firmware-analysis follow-up as the format of the main rootfs image; not analyzed in this document itself (§11, editorial note).
- **cred struct / mmap / physmem / sdp_hwmem** — kernel-level terms belonging to the historical Q60T root primitive (an arbitrary physical-memory-mapping driver, originally `/dev/sdp_mem`, later renamed `sdp_hwmem`) discussed in §10.2 and revisited empirically in the companion firmware-analysis document referenced from §11. This document did not itself disassemble the driver; see `firmware-analysis.md` for that first-hand result.
