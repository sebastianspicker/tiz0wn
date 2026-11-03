# Batch 2 report: app route, UEP map and debloat adoption

Date: 2026-11-03. Target: `GQ55Q60TGUXZG`, firmware `T-NKLDEUC-2743.0`.
All work offline; **no TV was contacted**. Everything below is a prepared
route or a static result, not a live claim.

## Why this batch

The proven chain needs a Remote PC trigger, a disposable RDP/SMB host and a UI
interaction. Two adjacent questions were worth a separate pass:

1. Can a self-signed app on the TV reach its own SDB service and use the vendor
   archive launcher for UID 0, with no host and no password field?
2. Can UEP be disabled from that UID 0 without USB, so ordinary tools and
   dropbear become usable?

A third, independent goal was to adopt the reversible debloat mechanisms from
[Vetro](https://github.com/andrearicci93/vetro) without copying its Q80A
package decisions.

## What was established

### The build has the archive chain components

The image names `dotnet-launcher` with `cap_setgid,cap_sys_admin`, a .NET 3.0.0
runtime, `sdbd-tarlauncher`, `/usr/share/sdbd/public.pem` and the SDK staging
path. There is **no `/usr/bin/dotnet`**, so the invocation is
`dotnet-launcher <assembly>`, not upstream's `dotnet <assembly>`.

Full table with offsets and the zero-length-binary caveat:
[`archive-root-prereqs.md`](archive-root-prereqs.md).

### A self-signed WGT can be produced locally

`exploits/tiz0wn-app/build.sh` creates a self-signed author certificate,
signs, and validates the package. A real local build passed. The package
contains the app page, the SDB service, the archive assembly and its runtime
configuration.

Limits: Developer Mode trust and install are untested; `on-boot="true"` is a
request and Tizen documents Partner level for it. The self-signed package may
install and run manually without starting at boot.

### UEP has a single guarded state word

The kernel handler `SfdUepPacketHandler` clears virtual `0xc069342c` after the
parser returns `8`. The header-derived physical address is `0x8069342c`, the
image word is `1`, and its 7-word neighbourhood is recorded. The handler has
no compare-before-write; a direct write reproduces the state transition, not
certificate verification.

Map and disassembly: [`uep-q60t.md`](uep-q60t.md).

### The physical primitive is still the open question

`sdp_hwmem`/`/dev/sdp_mem` has a generic kernel-region reject, but an earlier
contained-range branch reaches the mapping call first. The populated runtime
table is absent from the image, so static work cannot say whether that branch
admits the kernel page holding the UEP word. Seven candidates were reviewed;
all remain `unknown` because the module bodies are zero bytes in the
extraction. `/dev/sdp_mem` is the one worth a live read-only probe.

Audit: [`physical-primitives.md`](physical-primitives.md).

### Debloat can be reversible

Vetro's useful contribution is the mechanism, not its package list:

- `pkgcmd -D/-A` with the real owner UID, resolved at runtime
- a package→app-ID resolution because `-n` takes an app ID
- per-owner `is_disabled` readback, not exit-code trust
- JSON-lines action records
- kill-switch markers and `ConditionPathExists` inventory
- an exact-domain hosts filter bound into every mount namespace
- a role vocabulary and a verification sheet

The Q60T inventory selects 29 packages but recommends no uninstall; only
MultiScreen has a previously verified on-device reversal. Quick settings reduce
to four package groups; firmware update and promotions are settings-only.

Docs: [`debloat-q60t.md`](debloat-q60t.md),
[`debloat-markers.md`](debloat-markers.md),
[`debloat-quick-settings.md`](debloat-quick-settings.md),
[`debloat-verify.md`](debloat-verify.md).

## Payload and transport polish

The live run's two findings are fixed offline:

- a short-argument staging helper sends a file in ≤149-byte SDB injections,
  verifies SHA-256, and only then renames; `q.sh` gained a bounded `--raw` mode
- jobs now publish `<name>.done` only after a complete frame, so callers wait
  for a terminal marker instead of trusting the early channel close

Also: a fixed account day (`20000`) makes the shadow hash deterministic; a
patched no-op reuses one run directory; the agent log rotates at 64 KiB;
dropbear reports `running`/`refused`/`missing`; `ssh-retry` waits for a
successful unsigned canary and UEP `0`.

## Verification

- `make -C exploits/tiz0wn-root verify`: pass — 78+ tests, seven security
  controls, both loopbacks
- app Node replay, 6 app tests, 14 archive tests: pass
- WGT `--check`: pass
- ShellCheck, `sh -n`, Ruff on changed files, `git diff --check`: pass
- independent review T-53: accepted after two rounds

## Limits

- No TV install, no root, no UEP write, no boot observation.
- `.NET 3.0` runtime load from `dotnet-launcher` is unproven.
- The app service depends on local SDB and the SMACK rule from
  `payload/smack-allow`; neither is measured from an app label yet.
- `sdp_mem` kernel reach is unproven; the UEP control has never mapped it.
- Debloat inventory is from the base image, not the live package database.
- Hosts filtering does not cover custom DNS or direct-IP connections.

## Next steps

1. Install the WGT, open it, and confirm the `uid=` line (T-43).
2. Run `physprobe` through the CIFS-root agent first; it is read-only.
3. If `sdp_mem` maps `0x8069342c`, run `UepControl status`, then `disable`,
   then the unsigned canary and `ssh-retry`.
4. Run one archive attempt from `/root` and record `launcher.log`.
5. Only then test cold boot: app `on-boot`, then the `profile.d` fallback.
6. Start debloat with MultiScreen only, verify, reboot, reverse.
