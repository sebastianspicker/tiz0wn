# Q60T quick-setting package map

This offline map targets the owned `GQ55Q60TGUXZG` on `T-NKLDEUC-2743.0`.
Package IDs come only from the [T-44 manifest and unit inventory](debloat-q60t.md).
They are proposed reversible candidates, not a read of the live app registry or
proof that `pkgcmd` suppresses a boot unit on this firmware. Vetro's
[Quick settings](https://github.com/andrearicci93/vetro/blob/main/README.md#debloater),
[group implementation](https://github.com/andrearicci93/vetro/blob/main/app/service/quick-settings.js),
and [package command wrapper](https://github.com/andrearicci93/vetro/blob/main/rooting/service/debloat-commands.js)
inform the grouping; their Q80A catalog is not copied here.

| Group | Purpose | T-44 package IDs | Dependencies and limits | Expected effect | Reversal |
| --- | --- | --- | --- | --- | --- |
| `tracking` | Reduce ACR viewing-data collection. | [`org.tizen.acr-service-app`](debloat-q60t.md) | ACR service only; other ads and telemetry are unclassified here. Keep the store and Home dependency `com.samsung.tv.coba.adagent`. | May stop ACR service on a later launch; RAM and telemetry reduction unmeasured on this TV. | `pkgstate enable org.tizen.acr-service-app`, then verify the package and service. |
| `hbbtv` | Turn off broadcast HbbTV when unused. | [`ug-hbbtv-efl`](debloat-q60t.md) | The manifest package ID differs from service app `org.tizen.hbbtv-service`; confirm the live registry. Broadcast interactive services may stop. | Vetro cites about 22 MB on its Q80A; no Q60T RAM measurement or live disable proof. | `pkgstate enable ug-hbbtv-efl`, then verify broadcast HbbTV. |
| `multiscreen` | Stop MultiScreen background autostart when unused. | [`com.samsung.tv.multiscreen`](debloat-q60t.md) | Keep if Multi View or casting is used. The [vendor unit marker](firmware-analysis.md#findings) is a separate, live-tested control; package disable durability is unverified. | Vetro cites about 15 MB on its Q80A; Q60T RAM effect is unmeasured. | `pkgstate enable com.samsung.tv.multiscreen`, then verify the unit; remove the vendor marker only if that separate control was used. |
| `voice` | Reduce unused assistant services. | [`org.tizen.multi-assistant-service`](debloat-q60t.md) | This one manifest does not establish every assistant component. Voice input, remote microphone, and accessibility behavior require a live check. | May prevent the multi-assistant service from launching; RAM effect unmeasured. | `pkgstate enable org.tizen.multi-assistant-service`, then verify voice features. |
| `updates` | Stop automatic firmware installation. | **Settings only; no package ID.** | Vetro names the vconf setting `db/menu/support/softwareupdate/autoupdate`; a package disable would risk update machinery. | Changing the setting from 1 to 0 would turn off auto update; this map makes no change. | Restore the value recorded before any separate settings change. |
| `promotions` | Suppress promotional notifications. | **Settings only; no package ID.** | Use the TV's **Samsung Promotion** notification setting if present. Its Buxton key and presence on this Q60T are unverified. Home and store packages remain enabled. | Promotional notifications may stop; Home ads are not proven removed. | Restore the prior Samsung Promotion notification choice. |

No package ID is shared between these groups. `quickstate --ids GROUP [GROUP ...]`
prints newline-separated IDs in the fixed group order supplied by the caller,
deduplicating repeated groups and IDs. Settings-only groups print no IDs.
`quickstate --list GROUPS` prints all six mappings and labels the two settings
groups. An unknown group fails before any IDs are printed. The script makes no
state changes; [`pkgstate`](../exploits/tiz0wn-root/payload/pkgstate) is the
separate executor and records each later change.
