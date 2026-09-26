# evidence/

Raw output and filled-in records. Each script run writes to its own
`runs/<timestamp>-<script>/` directory — immutable, never overwritten; every
raw capture ends with a `# exit code:` line. **Directory is gitignored**
(except this README and `.gitkeep`): it contains device identifiers — serial
number, MAC/IP, DUID, and possibly account tokens in probe responses.

- Written with `umask 077` (owner-only).
- Redact before sharing: share `compatibility-summary.md`, not raw `*.txt`.
- `*-private.*` and `tv-info*.json` are doubly ignored.

## fw-analysis/

Private working notes from a firmware static-analysis session (not tracked; kept for reference).

- `FINDINGS.md` — firmware static-analysis findings F1–F12.
- `PROVENANCE.md` — origin/provenance of the analyzed firmware image.
- `STATE.md` — session state notes from the analysis.
- `decrypt.log` — log of the firmware image decryption steps.
- `apps.tsv` — parsed 387-entry app list (tab-separated `appID<TAB>name`).
- `download-url.txt` — source URL the firmware image was downloaded from.
- `scripts/` — session scripts (`remove-packages.sh`, `sort.py`) kept for reference; see `scripts/README.md` for caveats.

Generalized, tracked versions of those two session scripts (no hardcoded
scratchpad paths) live in the main tree: `scripts/05-remove-apps.sh` and
`scripts/analysis/classify-apps.py`. Public-facing writeup of the findings:
`docs/firmware-analysis.md`.

## Glossary

- **DUID** — device unique identifier; sensitive, kept out of tracked files and out of shared summaries.
- **Immutable run dir** — each script invocation gets its own timestamped `runs/` subdirectory; prior captures are never edited or overwritten, preserving an audit trail.
- **Redaction** — stripping identifiers (serial, MAC, DUID, tokens) before a capture leaves this directory; only `compatibility-summary.md`-style summaries are meant to travel.
- **umask 077** — file-creation mode that grants owner-only read/write, denying group/other access to newly written evidence files.
