# Launcher feasibility on the Q60T

Offline assessment for the owned GQ55Q60TGUXZG, firmware T-NKLDEUC-2743.0.
`/tmp/tiz-rootfs2` is a system-image extraction, not the TV's writable runtime
state. No Home press, app launch, process close, standby cycle, or RAM comparison
was performed here.

## Vetro mechanism, then the Q60T counterpart

Vetro describes its Q80A launcher as "a glass launcher on the Home key" that
shows "the same apps and icons as Samsung's Home, in the same order"
(`/tmp/vetro/README.md`, Launcher). Its code reads remote evdev nodes without
grabbing them, draws an EFL notification window, and repeatedly closes
`com.samsung.tv.csfs` after a Home press (`/tmp/vetro/dock/src/Program.cs:47-55,
208-243, 593-611`; `/tmp/vetro/app/service/dock.js:160-171, 241-254`). The
catalog reads `.appLayerCache.{1,2}` from the `csfs` data directory, joins it
with the web app and package registries, and selects icons from the icon store
(`/tmp/vetro/app/service/dock-catalog.js:1-53`). Vetro's own service supervises
the dock after boot or a crash; a separate transient systemd unit keeps the
dock outside the SDB agent's standby-sensitive cgroup
(`/tmp/vetro/app/service/dock.js:160-193, 335-356`). Its hard-coded Home code
`63` belongs to its forwarded remote and is not a Q60T key-code measurement.

On the extracted Q60T, `/usr/apps/com.samsung.tv.csfs/tizen-manifest.xml` names
`csfs.dll` as the `dotnet-inhouse` FirstScreen UI app. Its `app-context` rule
routes `XF86Home` to **`com.samsung.tv.csfs`** with
`entry_point:smarthub_key`; `XF86Display` also routes to `csfs`, with
`entry_point:source_key` (lines 5 and 45-53). The same package ID appears in
`/etc/resourced/proc.conf:4` and `/etc/brules.conf:18,43`. Thus this image
still names `csfs` as Home, rather than a different Home package or process.
That is a manifest identity, not a runtime process observation.

The Q60T also has separate packages
`/usr/apps/com.samsung.tv.coba.home/tizen-manifest.xml` and
`/usr/apps/com.samsung.tv.coba.apps/tizen-manifest.xml`, among 32
`com.samsung.tv.coba.*` package directories. Their manifests call them CoBA
Home and Apps components and mark them as FirstScreen external components;
neither manifest contains an `XF86Home` app-context rule. Closing `csfs` might
leave component processes running, so a Q80A-style memory result cannot be
inferred. The extraction's `/opt` is empty: it contains neither the Home-row
cache under `/opt/usr/home/owner/apps_rw/` nor the runtime
`/opt/dbspace/.webappservice.db`, `/opt/dbspace/.pkgmgr_parser.db`, or
`/opt/share/webappservice/apps_icon/all/`. Those paths must be checked on the
TV before claiming the same list or icons.

## Decision table

| Part | Vetro mechanism | Privilege | Q60T evidence and path | Confidence | Decision |
| --- | --- | --- | --- | --- | --- |
| Home-key interception | Read remote evdev without a grab; show an EFL window while the firmware also launches Home. | **Root** for Vetro's evdev and dock process; device-node access and key code must be checked. | `csfs` manifest has the `XF86Home` route. The image has `/usr/lib/libelementary.so.1` and `/usr/lib/libcapi-appfw-app-operation-tv.so.0`; it has no live `/proc/bus/input/devices` or remote event. | High for firmware route; low for interception. | **defer** until read-only key-code, node-access, and window tests on this TV. |
| App list source | Home order from `csfs/data/.appLayerCache.1` or `.2`; title and launch ID from `widgetinfo` in `.webappservice.db`, with package registry fallbacks. | **Root** for Vetro's Home-data and database reads; app permissions on this build unmeasured. | `/usr/apps/com.samsung.tv.csfs/tizen-manifest.xml` identifies Home, but the runtime cache and databases under `/opt` are absent from this extraction. The `home.media` cache fallback in Vetro has no matching package in this image. | Medium for likely `csfs` family; unknown for row schema and installed apps. | **defer** until read-only runtime path and schema checks. Do not present system manifests as the user's Home row. |
| Icon source | Read web app icons from `/opt/share/webappservice/apps_icon/all/<id>/`; fall back to package icons from `.pkgmgr_parser.db`. | **Root** for Vetro's registry and icon reads; a bundled fallback icon needs no root. | Runtime icon store is absent from the extraction. A concrete system-package asset exists at `/usr/apps/org.tizen.usb-launcher-tv/shared/res/org.tizen.usb-launcher-tv.png`; this proves only that a static local icon can be sourced, not Home-row icon parity. | High for that asset; unknown for user-installed icons. | **adopt** a bundled or verified system-package icon fallback for a trial screen. Use the Q60T path above; defer matching Samsung's complete icon set. |
| Samsung Home close | `app_launcher -k com.samsung.tv.csfs` on enable and after each Home press. | **Root** through Vetro's agent. | The Q60T `csfs` manifest and `/etc/resourced/proc.conf:4` support the target ID; the CoBA Home and Apps components are separate packages. No runtime process tree or close/relaunch behavior was measured. | High for target ID; low for effect on this TV. | **defer** until the process tree and reversible close/reopen behavior are observed. |
| Restore on standby/boot | Persistent enabled state, a transient systemd unit for standby survival, and service supervision with restart after boot/crash. | **Root** for `systemd-run`, process management, and agent-driven restart. | The image has systemd and the existing root boot hook (`exploits/tiz0wn-root/payload/boot`), but no Q60T launcher unit or measured wake behavior. The probe app's `on-boot` request is not an observed start (`exploits/tiz0wn-app/docs/BOOT.md`). | Medium for possible routes; low for actual lifecycle. | **defer** until a manual launcher survives or recovers from standby and a cold boot on this TV. |
| Memory claim | Close `csfs` while the small dock runs. Vetro's single Q80A run reported 533 to 662 MB available and `csfs` RSS around 152 MB (`/tmp/vetro/app/docs/PERFORMANCE.md:25-35`). | **Root** to close Home and read per-process counters. | No Q60T before/after sample; the Q60T CoBA split may change which processes remain. | High for the Q80A report; none for a Q60T gain. | **reject** transplanting the 129 MB / 24% Q80A result as a Q60T claim. Measure Q60T RAM separately if the launcher works. |

## Smallest launcher worth trying

One manually started screen with a short, fixed set of verified launch IDs and
local fallback icons, Back to dismiss, and no settings. First confirm the Q60T
Home key code and that an EFL window can receive input. Keep Samsung Home
running for this first functional check; later trials can separately test the
runtime Home row, closing `csfs`, and wake/boot recovery, each with a return to
Samsung Home. The first screen would test the launcher function, not a RAM
benefit or automatic replacement.
