# Vetro dock versus a whole-screen Q60T UI

Static comparison for the owned Q60T (GQ55Q60TGUXZG, T-NKLDEUC-2743.0).
The Vetro clone at /tmp/vetro was read only. No TV action or Q60T takeover is
claimed here. The [liquid-glass milestone](milestone-liquid-glass-ui.md) includes
home, sources, settings, now-playing, dialogs and OSD.

## What Vetro replaces

| Surface | Vetro's actual behavior | What remains Samsung's |
| --- | --- | --- |
| HOME launcher | A resident, transparent EFL notification window draws Vetro's app row and input panel over the running app. Its source calls it "a glass dock over the running app"; the window is sized to the dock, not a whole-screen UI. It is Vetro's drawing, not a skin on Samsung's dock. [Program.cs](/tmp/vetro/dock/src/Program.cs), lines 10–17 and 818–845. | The system still receives HOME and launches com.samsung.tv.csfs; Vetro closes it after the press. The default Home registration stays installed. [Program.cs](/tmp/vetro/dock/src/Program.cs), lines 47–55 and 207–210; [dock.js](/tmp/vetro/app/service/dock.js), lines 2–11. |
| Apps and sources | The dock reads Samsung's row, registry and icons, then draws its own tiles. It launches apps through app-control with an app_launcher fallback, and sends source change requests to org.tizen.tv-viewer. [dock-catalog.js](/tmp/vetro/app/service/dock-catalog.js), lines 1–10 and 43–53; [Program.cs](/tmp/vetro/dock/src/Program.cs), lines 611–659 and 710–722. | Apps, live TV, source switching and playback remain platform components. |
| Settings and other UI | The Settings tile sends XF86SysMenu; the Samsung Home tile deliberately launches csfs. [dock-catalog.js](/tmp/vetro/app/service/dock-catalog.js), lines 35–40. | Samsung's Settings, volume/picture feedback, dialogs, OSD and playback UI are not redrawn by this dock. |

Vetro's comment says "Nothing else on the TV is changed: no package is disabled
and the default Home is untouched" ([dock.js](/tmp/vetro/app/service/dock.js),
lines 10–11). Its enable path does change Autorun Smart Hub when it was on,
remembering and restoring the value when disabled (same file, lines 74–105,
237–274). That setting affects the boot picture, not the default HOME route.

## Takeover loop and recovery

At boot the Vetro service connects to its root agent, confirms it is enabled,
probes the dock PID and starts the DLL in a transient unit. The dock opens a
hidden EFL notification window and stays resident; the catalog is built from
Samsung's row first. On HOME the evdev observer shows the window while the
system also starts csfs, which the dock kills at 0.15, 0.45, 0.9, 1.6 and 2.8
s. Back, idle or a launch hides it again. A crash leaves HOME on stock Home
and the service retries with bounded backoff; disabling saves `enabled=false`,
stops the unit and restores the prior Autorun value.

The service polls on agent connection and then about every ten seconds
([main.js](/tmp/vetro/app/service/main.js), lines 658–661); it validates that
the PID belongs to its DLL and restarts after boot or crash, with retry delay
capped at five minutes ([dock.js](/tmp/vetro/app/service/dock.js), lines
117–130 and 335–354). The unit avoids the root agent's SDB cgroup, which
Vetro says dies at standby; systemd-run falls back to detached setsid
([dock.js](/tmp/vetro/app/service/dock.js), lines 160–180). The evdev reader
does not grab or swallow HOME. Delayed close can permit a glimpse of stock
Home, and a dead dock leaves that stock path available. The native window
uses elm_win_activate for foreground; a FIFO accepts show/hide/toggle
([Program.cs](/tmp/vetro/dock/src/Program.cs), lines 289–308, 539–560,
826–862).

Vetro's own stated worst case is that "a dead dock hands the Home key straight
back to Samsung" ([dock.js](/tmp/vetro/app/service/dock.js), lines 4–8).
Disabling it first records enabled=false so supervision cannot bring it back,
then stops its unit/PID and restores its prior Autorun choice (same file,
lines 264–274). On the Q60T, a native overlay that stays mapped or consumes
focus after failure could obscure the stock escape; that risk cannot be
dismissed without a crash/exit test and an out-of-band stop path. A web page
that owns the screen would leave Samsung Home visible when its app exits if
the platform returns there, but that return behavior and HOME re-entry also
need a reversible Q60T test. Both candidates need a proven remote-only escape.

app_launcher -k/-s handles Samsung Home and fallback app starts;
app-control handles ordinary launches. AUL is behind the Q60T app_launcher -s
path, which resolves a registered app and calls aul_launch_app_for_uid
([app boot audit](app-boot-trigger.md#what-app_launcher--s-does)). Neither AUL
nor app_launcher alone intercepts HOME here: the physical input observer and
compositor window do that. Vetro passes home code 63 for its forwarded remote;
it is not a Q60T measurement ([dock.js](/tmp/vetro/app/service/dock.js),
lines 27–31, 167–177).

## Host, identity and rendering

Vetro's root agent invokes packaged tvlauncher-dotnet.dll with
/usr/bin/dotnet, HOME=/home/owner, Wayland/EGL variables, and a transient unit
([dock.js](/tmp/vetro/app/service/dock.js), lines 160–180). Its source calls
the dock a root-started .NET process and logs its runtime UID, but does not
pin a SMACK label for that child ([dock.js](/tmp/vetro/app/service/dock.js),
lines 2–8; [Program.cs](/tmp/vetro/dock/src/Program.cs), lines 795–800).
Treat the effective child label as unmeasured here. Our boot service is proven
at UID 5001 with User::Pkg::, while /run returns UID 0 with System context;
that does not establish credentials for a future UI child
([current state](current-state-2026-11-04.md#how-a-boot-runs-now)).

The Q60T base image lacks /usr/bin/dotnet; it has /usr/bin/dotnet-launcher
and a .NET runtime catalog ([prerequisites](archive-root-prereqs.md)).
The [launcher capability audit](dotnet-launcher-caps.md) shows that a direct
DLL selects a CoreRuntime branch, while --standalone still consults AUL
identity. It does not establish a root managed UI process with Vetro's
compositor/input access or retained Linux capabilities. A registered .tpk
is the documented .NET packaging path; its UI and privilege behavior on this
Q60T remain unproven. Vetro's exact start line cannot run as written without
the dotnet host. A possible live overlay providing that host was not checked.

Glass is in generated PNGs (bar, shadow, glow, ring), Design.cs constants,
Layout.cs geometry and Evas objects in Ui/Dock.cs. Registry icons are
processed by IconPrep; Controller owns focus, show/hide and timed motion;
Program drives EFL animation and input ([dock README](/tmp/vetro/dock/README.md),
[Dock.cs](/tmp/vetro/dock/src/Ui/Dock.cs), lines 7–14, 213–245, 405–440;
[Controller.cs](/tmp/vetro/dock/src/Core/Controller.cs), lines 12–39).
The selected design has an opaque tinted bar and image-based highlights.
Its README says blur of content behind the bar was not ported to the native
launcher (lines 20–35). Thus this is no ready-made Chromium 69 backdrop
effect. Reusable ideas are the row/registry separation, focus state machine,
prepared assets and idle animation budget. A web body needs its own
CSS/canvas rendering and on-TV performance proof
([milestone](milestone-liquid-glass-ui.md#hard-problems-to-settle-first)).

## Home order is a separate operation

Vetro's order editor is not how its dock takes HOME. It reads
.appLayerCache.1 and falls back to .2 from the first directory with a cache:
com.samsung.tv.csfs/data, then com.samsung.tv.home.media/data. It parses a
decimal version line, up to 300 entries, then EOFC OBA or EOFCOBA,
retaining the observed version and terminator
([home-order.js](/tmp/vetro/app/service/home-order.js), lines 3–46, 57–64).
It permits only a permutation of current entries. A write snapshots both
caches as .vetro-txn and keeps a first .vetro-bak, builds temporary files,
renames both, then reads back; failure attempts rollback. Restore copies
baseline backups (same file, lines 66–101). Tests cover both terminators,
permutation refusal, partial-rename rollback and baseline restoration
([parse test](/tmp/vetro/app/tests/home-order.test.cjs),
[transaction test](/tmp/vetro/app/tests/home-order-transaction.test.cjs)).
The comments say Home/CoBA must reload to apply a change, but the /home-order
route only writes/reads; it does not itself issue a reload
([main.js](/tmp/vetro/app/service/main.js), lines 609 and 626).

The Q60T firmware identifies csfs as the HOME target, with separate CoBA
components, but the extracted /opt is empty
([Q60T feasibility](launcher-feasibility.md)). Check first, read-only, on
the running set: whether com.samsung.tv.csfs/data exists; which
.appLayerCache.1/.2 exists and its version, terminator and entry grammar;
whether /opt/dbspace/.webappservice.db has widgetinfo with matching IDs;
whether user/global package DBs supply missing app metadata; and whether
/opt/share/webappservice/apps_icon/all/ exists with usable icon files.
Do not infer runtime facts from manifests. If order changes are considered,
separately establish which Home/CoBA process reloads the row and how to
restore exact bytes.

## Q60T applicability

| Part | Assessment | Check that settles it |
| --- | --- | --- |
| Samsung row as catalog source | Reuse idea. Read and join, subject to path/schema verification. | Inspect the runtime cache, .webappservice.db, package registries and icon paths above; compare parsed IDs to the visible row. |
| Focus model and prepared assets | Reuse idea. Logic and budget transfer as concepts, not native code. | Render one focused shelf on Chromium 69 at 720p/1080p; measure frame time and memory on the set. |
| Boot supervision | Reuse idea. This Q60T boots the web service through amd with a worker fallback ([boot proof](app-boot-trigger.md#live-boot-proof-2026-11-04-1832z)); UI startup is separate. | Observe UI app start, foreground, wake and crash recovery on a reversible trial. |
| HOME re-entry, csfs close, foreground | Needs different mechanism. The csfs manifest routes XF86Home to it, but Q60T input events, key code, close effect and compositor policy remain unknown ([feasibility](launcher-feasibility.md)). | Identify actual remote event and app-context behavior; test reversible foreground return and csfs close/relaunch while recording process and screen state. |
| Vetro's root /usr/bin/dotnet DLL line | Impossible here as written with observed base-image host absence. A registered dotnet-launcher app is a different proposal. | Read-only check for a live dotnet overlay; for any launcher proposal prove app identity, UID/SMACK label, window/input access and managed entry. |
| Vetro EFL dock as a Chromium 69 glass implementation | Impossible as direct reuse. Evas/P/Invoke and native assets do not implement a web surface. | Web glass/focus spike determines what can be recreated within browser/GPU budget. |

## Two architectures and first spike

**A. Web page owns the foreground surface.** Extend a separately registered
web UI app, with the proven headless service/agent supplying bounded data and
launch requests. Boot opens the UI; HOME re-enters or re-foregrounds it; Back
and failure leave a route to Samsung Home. This gives the milestone one
whole-screen renderer and a Chromium 69 glass test bed. Evidence still
needed: UI on-boot timing, foreground policy, actual HOME delivery/re-entry,
csfs interaction, remote keys, app/source transitions, native OSD coexistence
and web frame budget. The service boot proof establishes none of these UI
behaviors.

**B. Native overlay owns takeover; web or NUI draws the body.** A small
registered native host could observe HOME and manage a foreground overlay,
with a web view or NUI body for the whole interface. It needs the same
app/source data and reversal path. Evidence still needed: a supported signed
native or .NET package/launch path on Tizen 5.5, permitted UID/SMACK and
compositor window level, readable remote input without trapping HOME,
body-to-host focus/input transfer, boot/wake survival and crash behavior.
dotnet-launcher and present EFL libraries alone do not prove this route.

**First spike:** before drawing the final UI, use one minimal, reversible
foreground web screen with a visible focus target and Back exit. Record what
HOME delivers, whether the screen can return to foreground after Samsung Home
opens, and what a process exit leaves on screen. Separately inspect the actual
remote node/code without assuming 63. A clean HOME re-entry with stock Home
available on exit would undercut the native overlay's extra runtime and input
complexity. If the page cannot regain foreground, that failure is an early
reason to investigate the native host, not to copy Vetro's dock.

For a community port, swap the Home package and app-context target, cache
directory and schema, icon/registry paths, remote nodes and key codes, and
runtime/packaging and compositor assumptions. Keep the engine contracts:
an ordered catalog with fallbacks, explicit focus/navigation states, a
supervised start/hide/return loop, and a reversible stock-Home escape.
