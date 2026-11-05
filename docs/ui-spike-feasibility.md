# Q60T web UI feasibility: static audit and first spike

Scope: the owned `GQ55Q60TGUXZG`, firmware `T-NKLDEUC-2743.0`. This is a
paper audit of a **foreground web application**, not a claim that a web page
can become a compositor overlay or replace Samsung Home. No TV command was
run. The existing [probe page](../exploits/tiz0wn-app/index.html) handles Enter
only; it has no exit, visibility, or HOME path. The
[service](../exploits/tiz0wn-app/service/service.js) serves that page and
probe endpoints, and its `onStart`/`onStop` manage HTTP listeners, not the UI
window. The [milestone](milestone-liquid-glass-ui.md) and
[Vetro comparison](vetro-ui-dock-comparison.md) set the target and the native
takeover contrast.

## CSS capability on the assumed Chromium 69 engine

The version column predicts **stock Chrome 69** parsing, not this Samsung
build's rendering or GPU speed. Run the tests inside the packaged UI, not a
desktop browser. `CSS.supports` checks whether a value parses; the spike must
also inspect pixels, clipping and frame times. Set a plain opaque card first,
then add each optional layer only after its probe succeeds. In the table,
`S(p,v)` means `window.CSS && CSS.supports(p, v)`.

| Feature | Chrome 69 expectation | Runtime detection | Glass fallback |
| --- | --- | --- | --- |
| `backdrop-filter` | Disabled by default; Chrome enables it in 76 | `S('backdrop-filter','blur(8px)')` **and** visual check | Never depend on it: use a prepared blur or static texture. |
| `-webkit-backdrop-filter` | Do not assume it is enabled in 69 either | `S('-webkit-backdrop-filter','blur(8px)')` **and** visual check | Same static or duplicate layer; a parsed prefix alone is insufficient. |
| `filter: blur()` | Available | `S('filter','blur(8px)')` | Use a pre-blurred bitmap; otherwise a tinted translucent fill. |
| `mask-image` / `-webkit-mask-image` | Prefixed masking available; unprefixed form is not the safe 69 target | Test `S('mask-image','linear-gradient(black,transparent)')` and `S('-webkit-mask-image','linear-gradient(black,transparent)')` separately | Use `overflow:hidden` with `border-radius`, or an alpha PNG for decorative fades. No mask on text. |
| `mix-blend-mode` | Available | `S('mix-blend-mode','screen')` | Precompose highlights into a texture or use normal alpha; do not need a blend pass. |
| CSS custom properties | Available | `S('--glass-alpha','0.75')`; also read a test `var()` value with `getComputedStyle` | Duplicate literal declarations for essential colour and size. |
| `@supports` | Available | `typeof CSS.supports === 'function'`; confirm a small stylesheet `@supports` rule applies | Class set by JS capability probes, with base CSS always usable. |
| `will-change` | Available | `S('will-change','transform')` | Omit the hint; animate only transform/opacity and measure. Hint only the focused/moving element, not all six cards. |
| `image-rendering` | Available, including `pixelated` | `S('image-rendering','pixelated')` | Default sampling or ship an asset at display size; avoid pixelated text/art. |
| `conic-gradient()` | Added in Chrome 69 | `S('background-image','conic-gradient(red,blue)')` | A baked highlight PNG or linear gradient. |
| `radial-gradient()` | Available | `S('background-image','radial-gradient(circle,white,transparent)')` | Linear gradient or flat tinted colour. |
| `prefers-reduced-motion` | **Absent** until Chrome 74 | With `matchMedia`, test both `(prefers-reduced-motion: reduce)` and `(prefers-reduced-motion: no-preference)`; both false means unsupported or unknown | Provide an in-app motion-off switch; keep default focus motion short and never require motion to show focus. |

Do not treat `matchMedia('(prefers-reduced-motion: reduce)').matches === false`
alone as proof of a no-preference setting. An unsupported media feature also
returns false. The CSS defaults must remain legible when any feature probe
lies or a GPU path fails. Chrome's release notes place
[`backdrop-filter` in 76](https://web.dev/articles/backdrop-filter),
[`conic-gradient()` in 69](https://developer.chrome.com/blog/new-in-chrome-69/),
and [`prefers-reduced-motion` in 74](https://developer.chrome.com/blog/new-in-chrome-74/).
The prefixed masking route follows
[Chrome's masking guidance](https://developer.chrome.com/docs/modern-web-guidance/guides/visual-design/complex-shapes).

## Glass without a live backdrop filter

1. **Blurred duplicate:** Put a second, layout-aligned copy of the *page's own*
   static background beneath each card, crop it with the card's rounded
   `overflow:hidden` box, and apply a fixed `filter:blur(8px)` to that copy.
   Expand the blur source beyond the crop to avoid dark edges. Fix source
   image, card positions, scale, blur radius and crop geometry at layout time.
   Move focus with a separate transform/opacity layer; never animate the blur
   radius or recapture the source per frame. A changed page background needs a
   deliberate new render. Each duplicate can require an offscreen surface and
   blur pass; six large copies plus their textures can consume bandwidth and
   memory. It cannot blur live TV or another app behind the web window.
2. **Static blurred image and gradients:** Ship a small pre-blurred, reusable
   texture or a resolution-specific atlas, then tint each card with translucent
   linear/radial gradients. Fix bitmap resolution, crop/nine-slice geometry,
   card bounds and tint at layout time. The fixed texture has download/package
   and decoded-bitmap cost, but no runtime blur pass. It looks less tied to
   changing content; swap a prepared texture only when the theme changes.

Both techniques get the **specular rim** from a 1 px light border plus a
top/edge highlight gradient (or baked edge PNG), and **noise** from a small,
low-alpha tiled PNG inside the rounded crop. Neither requires masking or
`mix-blend-mode`; bake those effects into the asset if either path is costly.
For a 1080p TV GPU, **start with the static texture/gradient stack**. A single
full-screen RGBA surface is about 8 MiB before extra buffers; six filtered
copies can add costly intermediate surfaces. That is a cost model, not a Q60T
benchmark. If the static stack fails the visual bar, test the fixed duplicate
only within a bounded card area.

## HOME, exit and lifecycle map

Labels mean: **proven-by-engine-version** = expected CSS/runtime capability
from Chrome 69; **proven-by-API** = documented Tizen/Samsung contract;
**unproven-here** = requires a reversible observation on this Q60T. Engine
version alone proves no HOME or compositor behavior.

| Transition | Claim and evidence status | Spike observation needed |
| --- | --- | --- |
| Page chooses Exit | `tizen.application.getCurrentApplication().exit()` terminates the current web app and its content **[proven-by-API]**. On relaunch, JS state resets **[proven-by-API]**. It does not name the next foreground app. | Which picture appears: Samsung Home, TV/source, previous app, or blank; time until usable remote focus. **[unproven-here]** |
| Remote Back / long Exit | Back is delivered automatically as a DOM `keydown`; a short Back can run the explicit Exit action **[proven-by-API]**. Samsung documents long Return/Exit as forced termination **[proven-by-API]**; whether it can break a hung Q60T page and what screen follows are **[unproven-here]**. | Verify both with the physical remote and record the post-exit surface. |
| HOME while UI is foreground | Samsung's platform owns HOME. TV web apps have no `tizenhwkey` event, and no documented web HOME interception or HOME lifecycle callback **[proven-by-API]**. Whether a DOM key event or `visibilitychange` arrives on this set, and whether csfs opens, are **[unproven-here]**. | Log key/visibility/unload timestamps and film the screen; do not register or swallow HOME. |
| UI hidden by another app or HOME | `visibilitychange` reports hide/resume when multitasking applies; hidden JS is paused **[proven-by-API]**. Low-memory models may terminate instead **[proven-by-API]**. | Does the page hide, die, resume, or reload? Does focus return? **[unproven-here]** |
| Service and relaunch | Tizen exposes `getAppsContext()` and `launch()` as application-management APIs **[proven-by-API]**; context presence is not foreground visibility. Their availability and foreground effect from this service, and any future UI relaunch path, are **[unproven-here]**. The current service's static code has no UI watcher or relaunch route, and its proven service boot path says nothing about UI boot. | Record whether an external launch request foregrounds an existing/hidden UI, creates a new instance, or is ignored. Keep supervision disabled in the first exit test so it cannot defeat escape. |
| Page hangs | A blocked JS loop cannot run its Back handler, Exit button, heartbeat or visibility handler **[proven-by-engine-version]**. Whether system HOME/long Exit still works and whether the WRT closes it are **[unproven-here]**. | Verify a remote-only escape with a deliberately stalled, disposable spike page before any takeover. |

Samsung documents [termination](https://developer.samsung.com/smarttv/develop/guides/fundamentals/terminating-applications.html),
[visibility and paused background JS](https://developer.samsung.com/smarttv/develop/guides/fundamentals/multitasking.html),
[application contexts and launch](https://developer.samsung.com/smarttv/develop/api-references/tizen-web-device-api-references/application-api.html),
and [no TV-web `tizenhwkey`](https://developer.samsung.com/smarttv/develop/guides/user-interaction/user-interaction.html).
Its [FAQ says overlay apps are unsupported](https://developer.samsung.com/smarttv/develop/faq/other-features.html);
the foreground web page cannot use Vetro's notification-window level.

## Focus, keys, and failure escape

In a packaged TV web app, arrows, Enter and Back are mandatory keys delivered
without registration. `keydown` should log `key`, `keyCode`, repeat, target,
focus target and timestamp; use names for navigation where reliable and the
documented Back code `10009` as a recorded candidate, not a hardcoded device
fact. Query `tizen.tvinputdevice.getSupportedKeys()`, and register *only* the
extra keys used by the spike, such as `MediaPlayPause`, with
`registerKey`/`registerKeyBatch` and the `tv.inputdevice` manifest privilege.
Registration can suppress a key's default action; `preventDefault()` applies
only to a DOM event that actually arrives. Do not register HOME, Power, volume,
channel, Source, or Exit for this test. In particular, leave Exit's system
behavior intact. The physical remote, its short/long Back or Exit, repeat rate,
and native OSD routing must be measured; a desktop keyboard is insufficient.
[Samsung's remote guide](https://developer.samsung.com/smarttv/develop/guides/user-interaction/remote-control.html)
lists automatic and optional keys, and its
[FAQ](https://developer.samsung.com/smarttv/develop/faq/user-interaction.html)
warns that registered keys can lose default behavior and that HOME/Power are
platform functions.

The viewer's planned remote path is **Back → visible Exit → `exit()`**, with
HOME and long Return/Exit left to the system. A JS hang removes the first
path. The other two are *candidate* escape paths until observed on this set;
keep Samsung Home enabled and do not arm boot relaunch or Home suppression in
the spike. If the remote cannot clear a hung page, this architecture fails the
remote-only recovery requirement. Vetro instead reads evdev without grabbing
HOME, shows a native notification window, closes Samsung Home after it starts,
and leaves stock Home as the fallback when its dock dies
([takeover comparison](vetro-ui-dock-comparison.md#takeover-loop-and-recovery),
[native source](/tmp/vetro/dock/src/Program.cs)). A foreground web page has
neither that window level nor that crash fallback by construction.

## Exact reversible spike and abort signals

Build **one foreground screen** at 1080p and 720p with **six cards** in one
shelf, one obvious geometric **focus ring** independent of colour, a
**glass on/off** control that switches between the static texture stack and
plain cards, a visible **capability line** showing every table probe and
visibility state, and a dedicated **Exit** action that calls `exit()`. Include
a manual motion-off control. Do not add boot takeover or a service relaunch
loop. Keep the stock launcher available throughout. A separate bounded hang
trial may freeze only the disposable page after the normal Exit path is proven.

Record, for each resolution and glass setting: `requestAnimationFrame` deltas
for idle and 30 seconds of repeated focus moves (median, p95, p99, count over
one and two measured display intervals), first usable focus time, visible
clipping/contrast, and decoded-image or process memory if available. Record
the key map for arrows, Enter, Back, long Return/Exit, HOME and the chosen
optional key, including which reached DOM, which moved focus, and which were
retained by the platform. Record exact screen and app state after Back/Exit,
HOME, relaunch request, and a JS hang, with timing and `visibilitychange` /
`unload` logs where they occur. An absent log during a hang is inconclusive;
pair it with screen/video and external state observation.

**Abort the web-foreground takeover idea** if HOME cannot return to the UI
without a race or repeated Samsung Home flash; if Exit does not reach a usable
stock surface; if HOME or long Return/Exit cannot clear a hung page with the
remote alone; if relaunch steals focus after Exit; or if the static stack
causes sustained missed frames/focus latency versus plain cards. For the last
gate, use the measured display interval as the baseline and flag more than 5%
of focus-motion deltas above 1.5× that interval over 30 seconds, or any focus
response over 100 ms; confirm a failure on a second run before rejecting the
renderer. If CSS feature detection and rendered pixels disagree, disable that
layer. Stop at these measurements and decisions; no full UI design follows
from this audit.
