# Plan: the Home-key menu in the typographic design, over the live picture

Status: **stage 0 passed; stage 3 (the Home remap) is blocked on this firmware, 2026-11-07.** The menu itself works on the TV when launched as the app; the Home key still opens Samsung's `csfs`. Nothing on the TV's Home routing was changed. (the TV
runbook is below). No TV command has been run for it yet. It builds on
[the Home-band assessment](home-band-assessment.md) (routes A–C, `homestate`,
`HomeOperation.dll`), [the launcher feasibility](launcher-feasibility.md) and
[the UI system](ui-system.md) (the typographic index now used by `home.html`).

## Goal

Pressing **Home** on the remote shows our minimalist index over the live
picture instead of Samsung's band. The picture keeps playing behind it. OK
opens an app or input, Back returns to the picture, and Samsung Home stays one
press away.

## What we can and cannot do

| Picture behind the menu when Home is pressed | Achievable? | Why |
| --- | --- | --- |
| TV channel or HDMI input | **Yes, by route A** | A foreground web app can keep the main source on screen with `tizen.tvwindow.show(…, 'MAIN', 'BEHIND')`. |
| A running app (Netflix, YouTube) | **No, not by route A** | Only a native overlay can draw above another app. Samsung's `csfs` does that as a native FirstScreen surface (route B, unproven here). |

So route A is the plan. On the Q60T, `csfs` owns `XF86Home` through its
`app-context` rule (`entry_point:smarthub_key`). Route A points the Home target
(`db/appfw/home_appid` and the `main` app-control operation) at our app, with
a saved baseline and a tested restore. `homestate` and `HomeOperation.dll`
already implement that, offline-tested only. Route C, editing `csfs` itself,
stays rejected: it means signed files on a read-only rootfs.

## Stage 0 — device facts (read-only, about 15 minutes, gates everything)

Nothing is changed on the TV in this stage.

1. **Picture behind the page.** Install the current WGT, watch an HDMI input,
   open the app, then Settings → **Live TV → On**. If the picture does not
   show behind the transparent page, route A is dead: stop and fall back to
   the route B spike.
2. **Home target.** Run `homestate query` through the agent's `/cmd` and save
   the output off the TV.
3. **What Home delivers.** With Diagnostics on, press Home while our app is in
   front. Record from the diagnostics line whether a key code or a
   `visibilitychange` arrives, and film the screen.
4. **Process tree.** Run `ps` for `csfs` and the `coba.*` components before
   and after a Home press, to see what keeps running.

## Stage 1 — the band designed for live video (offline, in this repo)

`home.html#band` already exists as a trial surface. It needs these design
changes before it can be the Home menu.

- **Legibility over any picture.** The photo's shading cannot be assumed: a
  ski race or a white menu screen can sit behind the text. Make the band scrim
  a fixed bottom gradient (about 80 % black at the edge to 0 at 55 % height)
  and keep the soft text shadow. Check it against three frames rendered in the
  screenshot harness: white, mid-grey and a busy sports frame. Every row label
  and idle item must stay at contrast ≥ 4.5:1 against the composed scrim.
- **Same index, two rows.** Apps and Inputs only, with the same row labels,
  brightness steps, underline focus and caption line as the full home. No
  clock: the picture is the content.
- **The current input marked.** Read the main source (`tvwindow.getSource`)
  and mark that input as "Now playing" in the caption line. A connected input
  keeps its accent dot.
- **Arrival and departure.** Fade the index in (opacity, 200 ms) on
  `visibilitychange → visible`, and fade it out before `hide()` on Back. No
  transforms, so Chromium 69 stays smooth over the video plane.
- **Diagnostics off by default.** The trial log stays behind the Diagnostics
  setting. The band forces it on today; that stops once stage 3's
  measurements are in.
- **Escapes kept:** Samsung Home (launches `com.samsung.tv.csfs`) and Full
  home (opens the full index with Tools and Settings) stay the last two Apps.
- **Tests:** extend `launcher.test.js` for the source caption, the fade
  classes and the Back path. Add the three contrast frames to the harness.

## Stage 2 — a separate app for the menu

`tiz0wnprob.Main` also hosts the root service. If Home points at it, a UI
crash takes Home and the root service down together. Give the menu its own
app ID (for example `tiz0wnhome.Main`) that reuses `home.html` and
`ui/tokens.css`.

- Either a second application in the same package, or a second small package
  built by `build.sh`. Which one this WGT layout and Tizen 5.5 allow is
  unverified, so check the second-application form first.
- The menu app talks to the service over the existing loopback page server.
  Because it runs on its own origin, verify the CORS/origin rules first.
- Keep the probe app unchanged as the recovery tool.

## Stage 3 — the remap trial (reversible, on the TV)

1. `homestate baseline`, then copy the baseline off the TV.
2. `homestate apply tiz0wnhome.Main`.
3. Press Home from a TV channel, from HDMI 2 and from a store app. For each,
   record:

   | Measure | Target |
   | --- | --- |
   | Picture survives behind the menu | Yes on TV and HDMI |
   | Home press → index visible | < 500 ms |
   | `csfs` flashes first | No, or under 1 frame |
   | Second Home press | Closes the menu (or opens Samsung Home) |
   | Back | Returns to the picture with focus intact |
   | Home from a store app | Our full home on the nebula, never a black page |

4. `homestate restore` and confirm Samsung Home is back. Decide from the table.

Home pressed during a store app is the one case route A cannot cover well.
The menu should detect it (no main source playing, or another app in
`getAppsContext`) and open the full home on its own backdrop. It must not
show a transparent page over a black hole.

## Stage 4 — make it permanent, with recovery

- **Boot hook:** if the menu app fails to start within 30 s after boot,
  restore the baseline Home target automatically (`homestate restore`), and
  log it.
- **Remote-only escape:** Samsung Home in the Apps row; Settings → Probe →
  restore control. Add an out-of-band `/cmd homestate restore` path that
  does not depend on the menu UI.
- **After every firmware update:** run `homestate query` again; the keys and
  the `app-context` routing can change.
- **Not in scope:** route B (a native overlay above running apps). It needs a
  signed native package with a window layer above apps and raw remote input.
  It would be a separate spike, following
  [the Vetro comparison](vetro-ui-dock-comparison.md).

## Stop rules

- Stop at stage 0 if the picture does not show behind the page.
- Never apply the remap without a saved baseline, a tested `restore` and the
  Samsung Home tile on screen.
- Stop the trial if Home ever lands on a screen with no remote-only way back.

## Acceptance

Home from TV or HDMI shows the index over the playing picture in under half
a second. Back returns to the picture. Samsung Home is reachable in one move.
A menu crash, a reboot or a firmware update always leaves Home working,
whether through our menu or through Samsung's.

## Findings on the TV (2026-11-07)

- **The loopback origin has no `tizen` object.** Live TV reported "no tizen object on http://127.0.0.1:18735". The home page had always run there, so on the TV it could never list apps or inputs, show the source (`tvwindow`), launch apps or register keys. Home now stays on the packaged origin (`widget://tiz0wnprob`); only tools and the probe, which need the service's loopback-only API, open on `http://127.0.0.1:18735`. The picture check (stage 0, step 1) therefore only becomes meaningful from this build on.
- **Stage 0 gate passed.** With home on the packaged origin, the app list and HDMI inputs load, and **Live TV shows the HDMI picture behind the transparent page** (`tvwindow.show(…, 'MAIN', 'BEHIND')`). Route A works on this set.
- **Photo flicker on row moves is gone** after two changes together: no per-item opacity transitions, and the active-row class moved from `<html>` to `#index`. Which one mattered was not isolated.
- **Stage 3 is blocked: the remap method does not exist on Tizen 5.5.** Both parts were ported from arn0-tv on Tizen 6.5:
  - `vconftool get db/appfw/home_appid` and `db/appfw/startup_appid` return "No such file or directory" on this build; `db/appfw/booting_appid_backup` exists (`org.tizen.tv-viewer`) and `db/first_screen/type` is `com.samsung.tv.csfs`.
  - `HomeOperation.dll get` exits 1; dlog shows `EntryPointNotFoundException: Unable to find an entry point named 'aul_get_default_app' in shared library 'libaul.so.0'`.
  - The safety chain held: `homestate query` reported the three values as unreadable, `homestate baseline` refused to save ("a value is unreadable; baseline not saved"), so `apply` and `trial` cannot run. Staged on the TV and inert: `homestate`, `HomeOperation.dll`, `HomeOperation.runtimeconfig.json` in `/opt/usr/share/tvroot`.
  - Not pursued further here. Any next attempt starts from how Tizen 5.5 resolves `XF86Home` (the `csfs` `app-context` rule), measured read-only, and needs its own reversible baseline and restore before anything is written.
- `csfs` runs as one process (about 156 MB RSS), started with `entry_point` `cold_booting`; no CoBA component processes were running.
- `app-boot` run directly through `/cmd` exceeded its 60 s deadline twice; run in the background with a log it finished within 25 s. `home-trial.sh arm` uses the background form.

## Decisions taken (2026-11-07)

| Question | Decision | Reason |
| --- | --- | --- |
| Scope | TV and HDMI only. Home pressed during a store app shows the band over the main source; if there is no source, the nebula returns (`.no-source`). | Behind our page the main window still holds the tuner or HDMI, so the band is not over a black hole. No native overlay exists (route B). |
| Separate menu app (stage 2) | **Deferred**: Home points at `tiz0wnprob.Main` for the trial. | The root service already runs as its own `tizen:service` process with `auto-restart`, so a UI crash does not stop it. A second package needs a second signing and install path, which adds risk for no measured gain. Revisit if the trial shows Home resuming on the wrong page. |
| Close `csfs` after Home | **No.** | Unmeasured on the Q60T, and Samsung Home is the escape. |
| Diagnostics in the band | Off unless Settings → Diagnostics is On (persisted as `ui-home-diagnostics`). | The trial turns it on from the full home; normal use stays clean. |
| Permanent remap | **Not yet.** The trial always restores. The boot guard ships to the TV only before a permanent apply. | Nothing stays changed until the measurements say it works. |

## What is built (offline, tested)

- **Band for live video** (`home.html`, `ui/tokens.css`):
  - a near-opaque lower third (`--ui-source-scrim-bottom` .9 up to 30 % height, gone by 62 %);
  - band row labels at 80 %;
  - opacity fade-in on arrival and on every return;
  - the main source's input captioned "Now playing";
  - Diagnostics persisted;
  - the photo backdrop only when there is no source.

  `test_wgt.py` computes WCAG contrast for every band text tone over a white frame (idle items, labels, caption ≥ 4.5:1); `launcher.test.js` covers "Now playing" and stored Diagnostics.
- **Boot guard** (`payload/homestate guard`, called by `payload/boot` right after its run-once lock, only when `home.applied` exists, so no later early exit can skip it): if the app's page server (port 18735, read from `/proc/net/tcp`) is not listening within 300 s of boot, it restores Samsung's Home target and logs it. Four tests in `test_homestate.py`.
- **TV runbook script** (`exploits/tiz0wn-root/live/home-trial.sh`):
  - phases `check`, `stage`, `baseline`, `trial`, `status` and `restore`;
  - `trial` restores on Enter, Ctrl-C, a lost terminal, or after 15 minutes;
  - `test_home_trial.py` covers those paths and the refusal to apply when Home is not at its baseline.

## TV runbook

Run from the Mac with `TV_HOST` and `HOST_IP` set, as for `app-run.sh`.

1. `AUTHOR_PASSWORD=… live/app-run.sh install` installs this version and re-arms the boot flags.
2. `live/home-trial.sh check` is read-only. Then do the picture check it prints. If there is no picture, stop.
3. `live/home-trial.sh stage` pushes `homestate` and `HomeOperation.dll`.
4. `live/home-trial.sh baseline` saves the Home target on the TV and as `live/home-baseline-private.txt` (git-ignored).
5. In the app, set Settings → Opens to → Band, and Diagnostics → On.
6. `live/home-trial.sh trial`. Press Home from TV, HDMI and a store app, fill in the stage 3 table, then press Enter to restore.
7. Only after a good table: stage the updated `payload/boot` with the guard, reboot once with the remap applied, and confirm the guard log (`home-guard.log`). Then decide on keeping it.

## Open questions for the owner

1. Is the TV/HDMI-only scope acceptable, with the full home shown for Home
   pressed during a store app?
2. Second application in the same package, or a separate package for the
   menu?
3. Should the menu close `csfs` after a Home press to free memory, as Vetro
   does? This is deferred until the Q60T process tree from stage 0 is known.
