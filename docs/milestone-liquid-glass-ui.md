# Milestone — liquid-glass TV UI (full surface replacement)

Status: future deliverable, not started. Recorded 2026-11-05.

## Goal

Replace the TV's **whole user-facing UI** — home, app and source navigation,
settings and quick actions, now-playing, dialogs and OSD — with one coherent,
sophisticated, minimalist surface in a **liquid glass** idiom at the quality
of the 2026 Apple TV. Deep translucency, large rounded forms, quiet type,
restrained colour, specular edges, motion led by focus. It must feel like a
product at three metres, not a web page, and it must run the TV, not sit beside
it.

Reference for interaction and information architecture, not for code or visual
copying: `wingedpanther/cleanmytv` (Android TV launcher replacement, Kotlin/
Compose, Electron installer). Study the shelf/rail, icon-only art, now-playing,
quick actions, pin/lock, theme packs and focus-as-state. It is Android; Tizen
5.5 web is the target.

A second reference covers the takeover problem: Vetro's native dock draws over
the running app, observes HOME without grabbing it, closes Samsung Home after
the system opens it, and falls back to stock Home on crash. Read
`docs/vetro-ui-dock-comparison.md` before choosing an architecture; it lists
the Q60T checks and the smallest invalidating spike. Vetro is Tizen but a
different generation, so its dotnet host and Home paths are not assumed here.

## What "complete UI" means here

The replaced surfaces are the ones a viewer touches:

- boot/home surface and app grid or shelf
- source list and input switching
- settings, quick actions, volume and picture feedback
- now-playing and media transport
- dialogs, toasts, loading and error states
- screensaver/idle behaviour

Native surfaces still exist underneath (CoBA, `tv-viewer`, `enlightenment`).
The goal is that a viewer never needs to see them. Where a native OSD must
still appear briefly, the replacement dims around it instead of fighting it.

## Why this is its own milestone

It needs an information architecture, an input model, a motion system, a
performance budget, an app/source registry, and a way to become the home
surface on a platform that does not officially let a third-party app replace
Home. That is engineering, not styling.

## Hard problems to settle first

1. **Home takeover.** The app must start at boot, full-screen, and return after
   HOME. Options: keep it foreground and relaunch on HOME, suppress or
   immediately replace the native menu, or leave HOME native and only own the
   idle screen. The current root agent can launch/kill apps; prove the loop
   before design work.
2. **Registry.** Read installed user apps and their localised names/icons from
   the package DB and `/opt/usr/apps`; read sources from the existing vconf/API
   paths. Launch through `aul`/`app_launcher`, not hardcoded binaries.
3. **State.** Foreground app, source, volume, mute, picture mode, network,
   now-playing: which are readable today, which need the root agent, which are
   unavailable. Mark honestly.
4. **Glass on this hardware.** Tizen 5.5 is Chromium 69; `backdrop-filter` is
   not reliable (Chromium 76). Glass must be built from layered translucent
   gradients, pre-blurred backdrop copies under `filter: blur()`, inset/outer
   shadows, 1 px specular rims and masked noise. Prove it on the TV in a spike
   before any screen work.
5. **Input.** Remote arrows, Enter, Back, media keys, long-press; HOME must
   never trap. `tizen.tvinputdevice` registration and key swallowing are part
   of the spike.
6. **Performance.** Low-end GPU at 720p/1080p: fixed blur radii,
   transform/opacity-only animation, no per-frame filter changes, no large
   repaints on focus. A missed budget kills the effect.

## Constraints

- Offline: bundle type and art, no CDN, no analytics, no webfont fetch.
- Readable at three metres; focus never signalled by colour alone.
- The service stays headless; UI never carries root logic.
- Every screen degrades to a plain fallback if the native call fails.
- One boot path, one recovery path: a broken UI must not lock the viewer out.

## Phases

1. **Feasibility spike** — glass card, one shelf, focus motion, and the
   HOME/boot takeover loop on the real TV. Kill or keep each technique here.
2. **Design system** — glass layers, radii, elevation, type scale, icon grid,
   motion spec for focus/enter/back/panel, contrast rules.
3. **Static shell** — home, grid, detail, now-playing, settings, quick actions,
   dialogs; fixture data; full keyboard navigation; 720p and 1080p.
4. **Integration** — real registry, launch, source switch, volume/mute,
   foreground and now-playing state; fallback paths.
5. **Takeover** — boot to the shell, HOME returns to it, native menu suppressed
   or replaced; documented reversal.

## Acceptance

- Viewer can boot, pick a source or app, watch, change volume, open settings
  and return home without seeing the native launcher.
- Focus moves steadily with no dropped frames; glass reads as depth, not grey
  boxes; text stays legible on every layer.
- Back never traps; every action reachable with the remote alone.
- 720p and 1080p lay out without clipping; cold start under two seconds.
- A failed native call degrades visibly, never blocks.
- Reversal to the stock launcher documented and tested.

## Out of scope

- Replacing CoBA binaries or native Tizen internals.
- Porting cleanmytv or adding Kotlin/Compose.
- Root, relay or debloat mechanics beyond status readouts.
