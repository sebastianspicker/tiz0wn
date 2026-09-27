# Q60T debloat — investigation workspace

Reversible-first workspace debloating a personally-owned Samsung
**GQ55Q60TGUXZG** (firmware `T-NKLDEUC-2743.0, BT-S`). Operationalizes the
roadmap in
[`docs/Samsung_Q60T_Debloating_Research_2026-09-25.md`](docs/Samsung_Q60T_Debloating_Research_2026-09-25.md) —
read that first; this is the runbook. For offline firmware static-analysis
results (root feasibility, reproduction steps), see
[`docs/firmware-analysis.md`](docs/firmware-analysis.md).

## Guiding principles

1. **Measure before you cut.** A long app list is not a performance diagnosis (§3).
2. **Read-only until proven necessary.** Inventory access ≠ root ≠ removable (§5).
3. **Explicit target only.** Every sdb call passes `-s "$TV_SERIAL"`; never
   fall back to "the first connected device" (§6.2, §9.2).
4. **One change at a time**, with a recorded rollback path (§12.2).
5. **Evidence is private.** `evidence/` is gitignored; it holds serials/MAC/DUID.

There is no bulk-uninstall list. The `research/` directory contains an
offline-built, firmware-bound Mali reclaim-only probe and separately armed
candidate credential chain. Its native device stages are excluded from the
default build, and its managed runner is inactive without exact profile and
arming gates. The full PoC has never been copied to or run on the TV. On
2026-09-27, the separately built minimal profile verifier passed once through
the guarded host route; that assembly contains no EGL, Mali-device, race,
reclaim, PTE, credential, or payload implementation. The consumed live route
used active SDB command injection and exposes no exploit mode.

## Phase roadmap → repo mapping

| Phase | Goal | Use |
|---|---|---|
| **A** Baseline | Find what's actually slow | `templates/performance-record.md`, `device-record.md` |
| **B** Reversible cleanup | Menus only, one change at a time | `templates/reversible-changes-log.md` |
| **C** Read-only SDB inventory | What can this build do? | `scripts/00`–`03`, `templates/compatibility-summary.md` |
| **D** One controlled removal | Single optional app, verified | `scripts/04-remove-one-app.sh`, `templates/app-change-record.md` |
| **E** Static firmware analysis | Exact 2743.0 findings and reproducible notes | `docs/firmware-analysis.md` |
| **F** Bounded active research | Offline Mali ABI, vendor reclaim probe, and candidate credential chain | `research/mali-cve-2022-46395/` |

Phase F now has an executable managed reclaim probe plus a separately armed credential chain, gated native library, and deterministic offline tests. The probe requires exactly one peer-backed Mali L3 candidate table page, absent before and present after target mapping, without arbitrary PTE, credential, or UEP writes. This is an expected test condition, not an observed TV result: the race, reclaim, GPU page-table path, and credential transaction remain unexecuted. The default build and self-test paths do not access a device. See the [vendor disclosure draft](research/mali-cve-2022-46395/DISCLOSURE-DRAFT.md) for the exact evidence and unexecuted command contract.

The [guarded profile-only deployer](research/mali-cve-2022-46395/host/README.md)
records the completed one-shot profile validation. Its fixed v4 stage is now
consumed on the assessed TV and must not be retried or removed. Do not deploy
workspace build output or invoke an exploit mode on the primary TV.

## Setup

Install `sdb` and locate the TV first. See
[`docs/setup-macos.md`](docs/setup-macos.md): the `.bin` must be run via
`bash`, not double-clicked, and needs Rosetta on Apple Silicon.

```bash
cp config/tv.env.example config/tv.env
$EDITOR config/tv.env          # set SDB path, TV_IP, HOST_IP
```

## Phase C session (read-only)

Enable Developer Mode on the TV (Apps → `12345` → set this host's IP as Host
PC IP → restart the TV; research doc §6.1). Then:

```bash
scripts/00-preflight.sh        # verify sdb, record version
scripts/01-connect.sh          # connect + confirm the intended target
scripts/02-capability.sh       # capability + applist  -> evidence/runs/<ts>-02-capability/
scripts/03-tv-info.sh          # optional local identity probe
# ...review evidence/, fill templates/compatibility-summary.md...
scripts/99-disconnect.sh       # tear down; then disable Developer Mode
```

## Phase D (only after C + a verified target)

```bash
# Supply the identifier YOU verified (app-id vs package-id differ — §7.2).
scripts/04-remove-one-app.sh --route sdb --id <VERIFIED_PACKAGE_ID>
```

Behaviour: snapshots the live app list first (flags whether your ID is
present), requires interactive confirmation, then unconditionally records
the removal command's stdout/stderr/exit code, an after-snapshot, and a
before/after diff — including on failure. Follow with
`templates/app-change-record.md`, including the post-restart permanence
check.

## Script-behaviour invariants

- Each run writes to its own `evidence/runs/<timestamp>-<script>/`; never overwritten.
- Target must appear in `sdb devices` with exactly your serial **and** state
  `device`; `offline`/`unauthorized` or a lookalike IP does not qualify.
- Read-only queries are cut off after `SDB_TIMEOUT` seconds (default 60), no retry.
- Lint: `shellcheck -x scripts/*.sh scripts/lib/*.sh` (config in `.shellcheckrc`).

## Safety / scope

Own television, trusted LAN, only. Never port-forward development or
remote-control ports to the internet (§6.1). Firmware downgrade and forced
updates are unsupported by Samsung — a factory reset does not restore the
2020 software (§12.1).

## Glossary

- **SDB (Smart Development Bridge)** — Tizen's debug/deploy protocol/tooling; `sdb devices`/`sdb shell`/`sdb install` etc.
- **sdbd** — the SDB daemon on the TV; capability flags in Phase C describe what this build's `sdbd` permits.
- **TV_SERIAL** — the device identifier `sdb devices` reports; scripts pin every call to it via `-s`.
- **DUID** — device unique identifier surfaced in some probe responses; treated as sensitive, kept out of tracked files.
- **app-id vs package-id** — Tizen distinguishes the two; removal/verification must use the one the target route (`sdb`/UI) actually expects (§7.2 of the research doc).
- **Capability flags** — fields from `scripts/02-capability.sh` (e.g. `intershell_support`, `rootperm`) indicating what the sdbd build allows.

## License

MIT (see [`LICENSE`](LICENSE)). Third-party tools are referenced by URL only and
kept under their own licenses — see [`NOTICE.md`](NOTICE.md).
