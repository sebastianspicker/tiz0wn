# Q60T foreground UI system

Import [`ui/tokens.css`](../exploits/tiz0wn-app/ui/tokens.css) before a new screen's CSS. Use `:root` for light and put `.dark` on the document element for dark. Pick the roles below and use `var(--ui-…)` values; never hardcode a hex colour in a screen. This contract describes the approved foreground spike, not a system overlay.

## Palette

| Role | Token | Light | Dark |
| --- | --- | --- | --- |
| Canvas top / bottom | `--ui-canvas-top`, `--ui-canvas-bottom` | `#eceef0` / `#dfe2e5` | `#0d0f12` / `#16191d` |
| Background forms | `--ui-form-one`, `--ui-form-two` | `rgba(255,255,255,.34)` / `rgba(185,191,197,.28)` | `rgba(255,255,255,.08)` / `rgba(91,106,120,.22)` |
| Glass fill top / bottom | `--ui-fill-top`, `--ui-fill-bottom` | `rgba(255,255,255,.30)` / `rgba(246,248,250,.16)` | `rgba(255,255,255,.13)` / `rgba(255,255,255,.05)` |
| Glass fill mid | `--ui-fill-mid` | `rgba(255,255,255,.22)` | `rgba(255,255,255,.09)` |
| Rim / inset highlight | `--ui-rim`, `--ui-highlight` | `rgba(255,255,255,.9)` / same | `rgba(255,255,255,.20)` / same |
| Soft rim (glass edge) | `--ui-rim-soft` | `rgba(255,255,255,.55)` | `rgba(255,255,255,.12)` |
| Primary ink | `--ui-ink` | `#14171a` | `#f2f4f6` |
| Clock / overlay ink | `--ui-clock-ink` | `#ffffff` | `#ffffff` |
| Dark surface / rim / ink | `--ui-dark-base`, `--ui-dark-rim`, `--ui-dark-ink` | `rgba(0,0,0,.58)` / `rgba(255,255,255,.26)` / `#ffffff` | same |
| Dark surface gloss / secondary / focus | `--ui-dark-gloss`, `--ui-dark-secondary`, `--ui-dark-accent` | `rgba(255,255,255,.10)` / `rgba(255,255,255,.72)` / `#8ec3dc` | same |
| Flat dark surface | `--ui-dark-flat` | `rgba(0,0,0,.80)` | same |
| Secondary ink | `--ui-secondary` | `#4c545c` | `#b3bac1` |
| Meta ink | `--ui-meta` | `#6f7780` | `#858d95` |
| Focus and selection | `--ui-accent` | `#2f6f8f` | `#8ec3dc` |
| Shadow colour | `--ui-shadow` | `rgba(28,32,38,.10)` | `rgba(0,0,0,.45)` |
| Flat card / canvas | `--ui-flat-card`, `--ui-flat-canvas` | `#f6f7f8` / `#e4e6e9` | `#1c2025` / `#0d0f12` |
| Confirm veil | `--ui-veil` | `rgba(28,32,38,.28)` | `rgba(0,0,0,.45)` |
| Band source scrim | `--ui-source-scrim-bottom` | `rgba(0,0,0,.9)` | `rgba(0,0,0,.9)` |
| Glass base (under fill, over photo) | `--ui-glass-base` | `rgba(246,248,250,.42)` | `rgba(13,15,18,.50)` |

Check secondary text against the **composed** fill and the background behind it in both themes. Require contrast ≥ 4.5:1. If it fails, darken a form or raise fill alpha until it passes; the CSS values alone do not prove contrast over arbitrary content. Check meta text at its rendered size and context too.

## Type and layout

Use `--ui-font` (`"Inter", -apple-system, "Segoe UI", Arial, sans-serif`) for the interface. Home bundles Inter 300 and 500 (Latin subset, `assets/inter-*.woff2`, SIL OFL 1.1 in `assets/inter.license`) with `@font-face`; pages without it fall back to the system stack. Inter needs less tracking than Arial: index items use `-.012em`, the clock `-.045em`, uppercase labels `.16em`. The spike's diagnostic line uses the existing `--ui-font-diagnostic` system monospace stack. Use only weights 300 and 500.

| Role | Size | Weight | Leading | Tracking | Use |
| --- | --- | --- | --- | --- | --- |
| Display | 44 px | 300 | 1.12 | `-.02em` | Page heading and hero title |
| Card title | 26 px | 500 | 1.05 | normal | Standard card and confirm title |
| Body | 18 px | 300 | 1.4 | normal | Base copy; controls use 500 and 1.3 |
| Status | 16 px | 300 | 1.4 | normal | Selection or measurement result |
| Meta | 13 px | 500 | 1.2 | `.14em` | Uppercase eyebrow; card subtitles use 16 px, 300, 1.1 |
| Diagnostic | 11 px | regular | 1.3 | normal | Bottom diagnostic line only |

Use the 4 / 8 / 12 / 16 / 24 / 30 / 44 px spacing tokens and an outer margin of 6 vh / 6 vw. The spike uses 12, 16, 24 and 30 px as layout spaces; 4, 8 and 44 px are scale slots with no current spacing use. Its other measured offsets remain local to their components: card subtitle 5 px, control horizontal padding 22 px, bottom line gap 20 px, confirm padding 40 px and title bottom margin 28 px. Do not replace these with a nearby scale value while reproducing the spike.

Use radii 26 px for cards and the confirm sheet, 34 px for the hero and 24 px for control pills. The confirm button uses its measured 14 px radius. The rim is 1 px. Keep every interactive target at least 44 px high.

## Shared states and focus

- **Rest:** show the glass fill, rim and rest elevation. The flat setting substitutes `--ui-flat-card` and hides decorative forms and grain.
- **Focus:** draw a 2 px `--ui-accent` outline at 3 px offset (`--ui-dark-accent` on the dark surfaces). Add at least one non-colour change: the spike lifts a card 6 px, scales it to 1.028 and increases its shadow. On home, focus never changes tile size: the focused item goes to full opacity and gains a 3 px white underline, the same for every row. Home focus uses white rather than the accent because it reads better from a distance; the accent marks the active row label and live inputs.
- **Selected:** use the accent rim, set `aria-pressed="true"`, and update the status line. The spike changes the subtitle to “Selected”; on home a selected tool stays at full opacity. Selection persists when focus moves.
- **Disabled:** keep the component's geometry and label, remove it from remote focus and activation, and reduce its visual emphasis without relying on colour alone. The spike has no disabled example; do not infer a new palette colour from it.

## Hero card

The hero is optional. When used, span two grid columns and rows at the spike's 30 vh height; clip its content at 34 px radius. Use the 44 px display title and a 16 px secondary subtitle. Apply the shared rest, focus, selected and disabled rules. The hero remains a button with a minimum 44 px target.

## Standard card

Use the three-column grid's 16 vh row, 24 px gap, 30 px inner padding and 26 px radius. Put the 26 px title above a single-line, 16 px secondary subtitle. Use `--ui-elevation-rest` (`0 10px 24px`) and `--ui-elevation-focus` (`0 16px 34px`) with the theme shadow colour. Apply the shared states; selected keeps a 1 px accent border.

## Home row

Home is a typographic index on a two-column grid inside a `7vw` margin. The top left holds the clock (5.5 rem, 300, line height .82 to trim the empty descender space) with the date centred under it; the `tiz0wn` eyebrow sits top right. The lower part is the index: one row per kind (Apps, Inputs, Tools, Settings), each with an uppercase label in a `9vw` column and its items as text, all at one size (`calc(.9rem + .55vw)`, about 25 px at 1080p, 300, 44 px line). There are no tiles, cards or pills, and no monograms: apps show their full name, preceded by the native icon only when it loads.

Hierarchy comes from brightness alone. Idle rows sit at 46 % opacity, the row holding focus at 72 % with its label in `--ui-dark-accent` (the document element carries `at-<zone>`), and the focused item at 100 % with a 3 px white underline. One caption line under the index, in the item column, shows the focused item's caption (a tool's description, an input's state); its captions are visually hidden in the row but still read out with the item.

The tools are the four home fixtures (Root status, Archive root, Debloat, Console) once, as a static row in `.shelf`; there are no clones and no transform. Items space with a `1.75vw` right margin (flexbox `gap` is unsupported on the TV's Chromium 69) and rows wrap rather than overflow.

Start on the first card, then on the first app once the list arrives. Left and Right move within a row and clamp at both ends; Up and Down move between rows. Focus uses `focus({preventScroll:true})`, with a guarded fallback for older engines. Enter on a tool opens `tools.html#<id>`.

## Background and launcher rows

The home backdrop is `assets/eso1006a-1920.jpg`, a 1920 px copy of the 4000 px original (Orion Nebula, ESO/J. Emerson/VISTA, CC BY 4.0). The credit is not shown on screen; it lives in `assets/eso1006a.license`, which ships in the package. Black gradients shade the bottom (the index), the left and the top (the clock); the sky between stays bright. All home type is white with a soft shadow. The flat setting replaces the photo with `--ui-dark-flat`; the Source background hides it; the band keeps its own scrim over the live source: `--ui-source-scrim-bottom` (.9) up to 30 % height, gone by 62 %, so every band text tone keeps 4.5:1 over a white frame (checked in `test_wgt.py`). The band fades in (opacity) on arrival, marks the main source's input "Now playing", shows Diagnostics only when that setting is On, and shows the photo only when there is no source (`.no-source`).

The Apps row lists up to seven consumer apps from `tizen.application.getAppsInfo`, sorted by name, plus a final Samsung Home escape; Enter launches. The Inputs row lists HDMI ports from `systeminfo` `VIDEOSOURCE`; Enter sets the source, then opens `org.tizen.tv-viewer`. A connected port (`.live`) gets an accent dot after its name. Both rows are adapted from arn0-tv. In the band the app limit is six so both escapes fit. Rows with no items stay hidden, label included, and are skipped by Up/Down.

## Control pill

Settings are the index's last row, set 3 vh apart at 1.15 rem because they are utility, not content; the name "pill" survives only as the class. They start folded into one item that summarises the current state (`Light  ·  Nebula  ·  Live TV off`, `aria-expanded="false"`). Enter opens them in place and focuses the first; Back folds them again before it would open the quit sheet. Each setting is its name as text with its value in `data-value`, drawn after the name at 55 % opacity: Theme (Light, Dark), Wallpaper (Nebula, Plain), Live TV (Off, On, Unavailable), Opens to (Home, Band), Diagnostics (Off, On), and two actions with no value: Probe (opens the old probe page at `/#probe`) and Quit.

The app opens to this home on the **packaged** origin: once the service answers, the packaged `index.html` replaces itself with `home.html` (or `home.html#band` when Opens to is Band). Home must stay there: on the Q60T the loopback origin `http://127.0.0.1:18735` has no `tizen` object at all (no app list, inputs, `tvwindow`, launch or remote keys; seen 2026-11-07). Tools and the probe need the service, whose API accepts only the loopback Origin, so home opens them at `http://127.0.0.1:18735/tools.html#<id>` and `http://127.0.0.1:18735/`. Back returns to home. A toggle exposes its state with `aria-pressed`.

## Status line

Put one 16 px secondary white line below the caption line, in the item column, with `aria-live="polite"`. Keep it on one line and truncate overflow. It reports selection or the frame sample; it is not focusable, selectable or a disabled target. On the full home it stays empty until there is a message, because the caption line already describes the focus; in the band it reads "Choose an app or input."

## Confirm sheet

Use the themed veil and a centred 480 px sheet, bounded by 6 vw margins, with 40 px padding and a 26 px radius. Layer the glass gradient over the flat card fill, retain the 1 px rim and inset highlight, and use the rest elevation. The title is 26 px medium. The action buttons use 18 px medium text, 12 px vertical / 30 px horizontal padding, a 14 px radius, and the shared focus outline. Rest, focus and disabled apply to actions; selection is the explicit confirmed action, not a latched visual state. Return focus to the invoking control on cancel.

Home's quit sheet drops the card for the index's own language: the flat dark veil, the question "Quit tiz0wn?" at 3.2 rem / 300, and two text choices (Stay, Quit) with the index focus underline.

## Diagnostic line

Use 11 px secondary white text in the spike's system monospace stack. Keep each entry to one line with overflow truncation; `aria-live="polite"` is optional. It is read-only and has no focus, selected or disabled interaction state. Because the band hides the controls, the line is shown automatically there; the trial event sits before the theme fields so truncation keeps it visible.

## Glass and motion

Home has no surfaces: its items are text on the shaded photo. The spike keeps the light glass fill below. Put grain on **one grid-level layer**, behind interaction and above cards: one repeating 64 × 64 tile at `--ui-grain-opacity: .035`, with `pointer-events: none`. Hide that layer in flat mode. Do not put a grain layer on each card.

Animate transform and opacity only. Use `--ui-motion-focus: 200ms` and `--ui-motion-easing: cubic-bezier(.22,.61,.36,1)` for focus; no bounce. Controls and dialog buttons lift `translateY(-.375rem) scale(1.035)`. Home and tools items never transform, and their brightness steps and underline change instantly: the Q60T flickered the photo on row moves until per-item opacity transitions were removed and the active-row class moved from `<html>` to `#index` (which change mattered was not isolated); keep both. Home and tools never scroll the document (on tools, `main` scrolls), for the same reason. The only fade is the band's arrival. The 240 ms token is a reserved scale slot from the brief: the approved spike has no 240 ms transition. Keep motion optional and never require it to recognize focus or selection.

Do not use CSS `filter` or `backdrop-filter`, a second accent, a font other than the bundled Inter, an icon font, a weight above 500, or full-bleed colour blocks. Keep the background forms behind the grid and keep text contrast on the composed surface.
