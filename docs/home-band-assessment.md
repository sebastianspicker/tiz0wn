# Replacing the Home-button band with a glass surface

Assessment and trial scaffolding for the owned Q60T (`GQ55Q60TGUXZG`,
`T-NKLDEUC-2743.0`). No TV command was run for this document. It builds on the
[Vetro dock comparison](vetro-ui-dock-comparison.md), the
[launcher feasibility](launcher-feasibility.md), the
[web UI feasibility](ui-spike-feasibility.md) and arn0-tv's Home-button guide.

## Verdict

We can make the Home button open our glass surface with the live picture
behind it **when that picture is a TV channel or an HDMI input**. We cannot do
it over a running app (Netflix, YouTube): that is Samsung's own case and needs
a native overlay, which is unproven on this set.

A web app, once foregrounded, can only keep the TV's main video source behind
itself, through `tizen.tvwindow.show(..., 'MAIN', 'BEHIND')`. Samsung's band
(`com.samsung.tv.csfs`) draws over a running app because it is a native
FirstScreen surface, not a web page. There is no Chromium-69 route to blur or
sample another app's output.

## Three routes

| Route | Picture kept behind | Needs | Status on the Q60T |
| --- | --- | --- | --- |
| **A. Point Home at our web app; show a transparent band** | TV channel or HDMI input only | Set the `main` app-control operation and `db/appfw/home_appid` from `com.samsung.tv.csfs` to our app, with a saved baseline and read-back. We have root (more than arn0's UID 901). | arn0 proved the method on Tizen 6.5. The keys and the `csfs` `XF86Home` app-context rule need checking on 5.5. |
| **B. Native overlay (Vetro-style)** | Anything, including apps | A native/.NET process allowed to draw above apps, read raw remote input and survive standby | No `/usr/bin/dotnet`; `dotnet-launcher --standalone` still needs an app identity; window-layer and input rights unmeasured. |
| **C. Restyle `csfs`/CoBA in place** | Anything | Editing signed system files on a read-only rootfs | **Reject.** Milestone rules it out; signature and RO-fs block it. |

Route A is the only one with a credible, reversible path here, and only for the
TV/HDMI case. This document scaffolds route A and records what route B would
still need.

## Liquid glass over live video — limits on any route

- **No backdrop blur.** Chromium 69 has no `backdrop-filter`, and the video is
  a separate hardware plane beneath the web layer, so the browser cannot blur
  or read it. Over a source, the glass is translucent tinted fill, 1 px rims
  and shadows — the same token surface, minus the nebula.
- **No photo background in band mode.** `home.html#band` hides `.backdrop`;
  only the bottom strip is drawn, over the live source.
- **Unverified on the TV:** whether the picture shows at all behind the
  transparent page. `home.html`'s **Live TV** setting exercises exactly
  this `BEHIND` call; the 2026-11-05 handoff still lists it as unverified. It is
  the first thing a trial settles.

## What this change adds (all behind flags, all reversible)

### `home.html#band` — the trial surface

- A `band` mode (URL hash `#band`, armed flag in `localStorage`), rendered as
  one bottom strip: the Apps and Inputs rows only. Header, tools row, controls,
  and photo backdrop are hidden by the `.band` class.
- On entry it calls `tvwindow.show(..., 'MAIN', 'BEHIND')` so the source stays
  visible; `Back` calls `getCurrentApplication().hide()` instead of the exit
  sheet, handing the screen back to whatever was behind.
- **Escape tiles**, present even if the app list fails to load: **Samsung
  Home** (launches `com.samsung.tv.csfs`) and, in band mode, **Full home**
  (opens the normal `home.html`). This is assessment step 5 — a remote-only way
  back to Samsung's menus is always on screen.
- **Lifecycle logging** for the trial: `visibilitychange`, the requested
  app-control operation, and any unrecognised key code are written to the
  diagnostics line (and `console.log`). The line is forced visible in band
  mode because the controls that normally toggle it are hidden. This is how
  we learn what a real Home press delivers and whether the band returns to the
  foreground, without registering or swallowing HOME.
- The **Opens to** setting (Home / Band) arms/disarms the mode. App start
  forwards from `index.html` to `home.html`, or straight to `home.html#band`
  when armed (and so does a remapped Home).

The full (non-band) home screen is unchanged in behaviour: rails above the
tools row, `Back` opens the quit sheet, no `tvwindow` call on start.

Covered by `exploits/tiz0wn-app/tests/launcher.test.js` (full home and band
mode, escape tiles, `BEHIND` on entry and on resume, `Back` hides the app) and
the band-redirect case in `tests/run.js`. The background image is served from
the loopback origin (`/assets/eso1006a-1920.jpg`), also asserted in `run.js`.

### `homestate` — reversible Home-target helper

`exploits/tiz0wn-root/payload/homestate` (content-invoked, shell, same shape as
`pkgstate`/`unitstate`):

- `query` — read-only. Prints the Home keys, the `main` operation, whether a
  baseline exists and which app DBs are present. Writes nothing.
- `baseline` — saves the current values once; never overwrites an existing
  baseline.
- `apply APPID` — refuses unless the live state equals the saved baseline and
  no apply is already recorded; writes only `db/appfw/home_appid` and the
  `main` operation, each with read-back; on any failure rolls both back to the
  baseline and reports (`URGENT:` if the rollback itself fails).
- `status` — labels each value baseline / applied / drift.
- `restore` — refuses a value that is neither the baseline nor the applied
  target (something else edited the keys — look first), else restores and
  clears the applied marker.

Keys and the operation are taken from arn0's `Query.cs`/`Control.cs`. The
`main` operation needs a native call, so `homestate` shells out to a small
assembly (below); without it, `apply` changes only `db/appfw/home_appid` and
says so. Guards: validated app IDs, atomic baseline write, a JSONL audit log.
Covered by `exploits/tiz0wn-root/tests/test_homestate.py` with fake
`vconftool` and `dotnet-launcher` (round trip, refusals, both rollback paths,
the helper-absent path).

### `HomeOperation.dll` — the native primitive

`exploits/tiz0wn-app/payload/HomeOperation.cs` (+ `.csproj`,
`.runtimeconfig.json`): `get` reads and `set APPID` writes the app that
receives the `main` operation, via `app_operation_set_current_app` and the
`aul`/`bundle` calls from arn0's `Control.cs`. Same build and invocation shape
as `UepControl.dll` (`netstandard2.0`, `netcoreapp3.0` runtimeconfig,
`dotnet-launcher --standalone`). It guards on the firmware string, validates
the app ID, prints the read-back value, and refuses cleanly if a native library
or entry point is missing. `--self-test` runs offline (passes locally).

## Trial order (each step reversible, A only)

1. **Picture check, no system change.** Install the WGT, watch an HDMI input,
   open the app, set **Live TV** to On. No picture ⇒ route A is dead,
   only B remains.
2. **Read-only query.** `homestate query` through the root agent's `/cmd`. Save
   the baseline off the TV (`homestate baseline`, copied elsewhere).
3. **Band layout.** Set **Opens to** to Band; confirm app start opens `home.html#band`
   with the source behind and the rails usable. No Home remap yet.
4. **Remap trial.** `homestate apply <our app id>`. Press Home from TV, from
   HDMI and from a store app. Record from the diagnostics line and a filmed
   screen: picture survival, band latency, whether `csfs` flashes, what a second
   Home press does, the real Home key code. Then `homestate restore`.
5. **Keep only with escapes proven:** the Samsung Home tile, a `/cmd` restore,
   and (optionally) a boot-hook marker that restores the baseline if the app
   fails to start.

`tiz0wnprob.Main` also hosts the root service. If the remap proves out, give the
UI a **separate app ID** so a UI crash cannot take Home and the root service
down together.

## What route B would still need (not built here)

A signed native/.NET package on Tizen 5.5 with a permitted UID/SMACK label and
a compositor window level above apps; raw remote input without trapping HOME;
body-to-host focus transfer; and boot/standby/crash survival. `dotnet-launcher`
and the present EFL libraries alone do not establish these. See
[the Vetro comparison](vetro-ui-dock-comparison.md) for the first spike.

## Risks

- The remap can stop Home reaching Samsung's own menus. Do not apply without a
  saved baseline and a tested `restore`, and keep the Samsung Home tile.
- `BEHIND` composition over a source is unverified on this firmware; step 1
  gates everything.
- A firmware update can change the keys or the app-context routing; re-run
  `query` after any update.
- The `main`-operation native call may be refused for our UID/label even with
  root; `homestate` then degrades to the `home_appid` key alone, which may not
  be sufficient on its own.
