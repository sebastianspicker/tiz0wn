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
| Secondary ink | `--ui-secondary` | `#4c545c` | `#b3bac1` |
| Meta ink | `--ui-meta` | `#6f7780` | `#858d95` |
| Focus and selection | `--ui-accent` | `#2f6f8f` | `#8ec3dc` |
| Shadow colour | `--ui-shadow` | `rgba(28,32,38,.10)` | `rgba(0,0,0,.45)` |
| Flat card / canvas | `--ui-flat-card`, `--ui-flat-canvas` | `#f6f7f8` / `#e4e6e9` | `#1c2025` / `#0d0f12` |
| Confirm veil | `--ui-veil` | `rgba(28,32,38,.28)` | `rgba(0,0,0,.45)` |

Check secondary text against the **composed** fill and the background behind it in both themes. Require contrast ≥ 4.5:1. If it fails, darken a form or raise fill alpha until it passes; the CSS values alone do not prove contrast over arbitrary content. Check meta text at its rendered size and context too.

## Type and layout

Use `--ui-font` (`-apple-system, "Segoe UI", Arial, sans-serif`) for the interface. The spike's diagnostic line uses the existing `--ui-font-diagnostic` system monospace stack. Use only weights 300 and 500.

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
- **Focus:** draw a 2 px `--ui-accent` outline at 3 px offset. Add at least one non-colour change: the spike lifts a card 6 px, scales it to 1.028 and increases its shadow. The home carousel uses an accent rim, deeper shadow and `z-index: 3`; focus never changes tile size. Keep border width at 1 px.
- **Selected:** use the accent rim, set `aria-pressed="true"`, and update the status line. The spike changes the subtitle to “Selected”; the home carousel keeps its meta line. Selection persists when focus moves.
- **Disabled:** keep the component's geometry and label, remove it from remote focus and activation, and reduce its visual emphasis without relying on colour alone. The spike has no disabled example; do not infer a new palette colour from it.

## Hero card

The hero is optional. When used, span two grid columns and rows at the spike's 30 vh height; clip its content at 34 px radius. Use the 44 px display title and a 16 px secondary subtitle. Apply the shared rest, focus, selected and disabled rules. The hero remains a button with a minimum 44 px target.

## Standard card

Use the three-column grid's 16 vh row, 24 px gap, 30 px inner padding and 26 px radius. Put the 26 px title above a single-line, 16 px secondary subtitle. Use `--ui-elevation-rest` (`0 10px 24px`) and `--ui-elevation-focus` (`0 16px 34px`) with the theme shadow colour. Apply the shared states; selected keeps a 1 px accent border.

## Home carousel

Use an endless track with three consecutive sets of the seven home fixtures. Each set is a flex row and the outer sets have `aria-hidden="true"`; each clone has a unique suffixed id and class. Use a `2vw` gap both within and between sets, 12 px vertical shelf padding and `6vw` horizontal padding. Each card uses `flex: 0 0 18vw`, `box-sizing: border-box` and a 26 vh height, with the same 26 px radius and existing inner padding. The viewport clips the track. Use no negative margins, tile scaling or native scrolling. Each card holds its bottom-left label at 1.15 rem and one secondary meta line at .72 rem. Keep the controls and status line below the carousel.

Start on index 7, the first card of the middle set. `.viewport` is the positioned, clipped flex child; `.shelf` stays unpositioned so each card's `offsetLeft` uses the viewport as its offset parent. On each cursor move, compute `offsetFor(cardLeft, inset) => -(cardLeft - inset)`, using the active card's `offsetLeft` and `inset = (viewport.clientWidth - card.offsetWidth) / 2`. This places the focused tile at the center and leaves the preceding tile fully visible at a wrap seam. Translate the track by that offset with a 240 ms ease. After the transform transition ends, or after a 260 ms fallback, normalise an index in the third set by subtracting 7 and one in the first set by adding 7. Apply that identical visual position with transition disabled for one frame. On resize, reapply the offset without transition. Left and Right continue through the adjacent copy in either direction. Focus uses `focus({preventScroll:true})`, with a guarded fallback for older engines, so focusing a transformed tile does not scroll the page. Focus uses the accent rim, deeper focus shadow, `z-index: 3` and the shared outline without changing tile size; Up moves to the header and Down to the controls.

The [host render harness](../exploits/tiz0wn-app/tests/render/README.md) checks 1920×1080 and 3840×2160 after initial focus, four Right moves, a right wrap, and three Left moves from the first tile. It asserts 17.9–18.1 vw tile width, 1.6–2.6 vw adjacent gaps, no intersection or page scroll, centered focus, and both seam tiles fully visible. The host run measured 18.0 vw card width, 2.0 vw adjacent gaps, under 0.4 px focus-center error, zero scroll and zero scroll events at both sizes. The wrap seam measured 38.4 px at 1080p and 76.8 px at 4K. Those values correspond to 345.6/691.2 px cards and a 384/768 px tile step. Centering moves the active tile's left edge from the old 6 vw inset to 41 vw: a 672 px shift at 1080p and 1344 px at 4K. The harness writes screenshots to `docs/shots/`, which is git-ignored.

## Control pill

Use a 48 px height, 24 px radius, 22 px horizontal padding, 18 px medium text, 1 px rim and `--ui-elevation-control` inset highlight plus `0 8px 24px` shadow. Apply the shared focus and disabled rules. A toggle exposes selected state with its visible On/Off label and `aria-pressed`; an action has no latched selection.

## Status line

Put one 16 px secondary line below the carousel, with `aria-live="polite"`. Keep it on one line and truncate overflow. It reports selection or the frame sample; it is not focusable, selectable or a disabled target.

## Confirm sheet

Use the themed veil and a centred 480 px sheet, bounded by 6 vw margins, with 40 px padding and a 26 px radius. Layer the glass gradient over the flat card fill, retain the 1 px rim and inset highlight, and use the rest elevation. The title is 26 px medium. The action buttons use 18 px medium text, 12 px vertical / 30 px horizontal padding, a 14 px radius, and the shared focus outline. Rest, focus and disabled apply to actions; selection is the explicit confirmed action, not a latched visual state. Return focus to the invoking control on cancel.

## Diagnostic line

Use 11 px `--ui-meta` text in the spike's system monospace stack. Keep each entry to one line with overflow truncation; `aria-live="polite"` is optional. It is read-only and has no focus, selected or disabled interaction state.

## Glass and motion

Compose glass from a 150-degree three-stop `--ui-fill-top` → `--ui-fill-mid` (55%) → `--ui-fill-bottom` gradient, a 1 px soft rim (`--ui-rim-soft`) carrying a 1 px inset top highlight (`--ui-highlight`), and the themed shadow. The inset highlight rides on top of `--ui-elevation-rest` / `--ui-elevation-focus` for cards, and is already part of `--ui-elevation-control` for pills. Put grain on **one grid-level layer**, behind interaction and above cards: one repeating 64 × 64 tile at `--ui-grain-opacity: .035`, with `pointer-events: none`. Hide that layer in flat mode. Do not put a grain layer on each card.

Animate transform and opacity only. Use `--ui-motion-focus: 200ms` and `--ui-motion-easing: cubic-bezier(.22,.61,.36,1)` for focus; no bounce. Controls and dialog buttons lift `translateY(-.375rem) scale(1.035)`. Carousel tiles never transform (it would break the centred-track geometry), so their focus and selection read through the accent rim, inset highlight and deeper shadow only. The 240 ms token is a reserved scale slot from the brief: the approved spike has no 240 ms transition. Keep motion optional and never require it to recognize focus or selection.

Do not use CSS `filter` or `backdrop-filter`, a second accent, a new font or icon font, a weight above 500, or full-bleed colour blocks. Keep the background forms behind the grid and keep text contrast on the composed surface.
