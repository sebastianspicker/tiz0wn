# Security

## Reporting

This repository documents a vulnerability the author found on their own
television. It was reported to Samsung on 2026-09-29 and is published here four
weeks later, after the vendor's advertised grace period passed without a
statement, a fix or a CVE assignment.

Two things follow from that:

- Samsung has not confirmed the finding, so the affected-version range is
  unknown. Only one exact build and one device were tested.
- Anything published here may later be contradicted by the vendor. Corrections
  are welcome as issues.

To report a problem in this repository's tooling rather than in the TV, open an
issue. To report the TV bug to Samsung, use their product security channel; you
do not need this repository for that.

## What is public and what is not

Public: the chain, the scripts, the measurements, the offset arithmetic, the
rollback path, the live session record.

Not public: no firmware image, no device identifiers. Addresses, the model
string, the MAC, the crypt salt and the test password are placeholders, and
`evidence/` is gitignored. See `NOTICE.md` for the placeholder convention.

## Dependencies and trust

- The sink, the builder and the payloads are plain shell and Python with no
  third-party packages.
- The firmware tooling used offline (Synacktiv's decryptor, `vdfs-tools`) is
  referenced by URL and not vendored, so its licensing stays its own.
- The lab uses Debian, xrdp and Impacket, installed from upstream at build time.

## Running it on your own TV

Read `exploits/tiz0wn-root/LIVE-RUN-2026-10-29.md` first. The short version:

- Re-derive the offset from your own image. Do not reuse `704753664`; it is
  this image's alone.
- Confirm the two-block window hash on the metal before trusting anything.
- Keep the backup. Rollback needs it.
- Expect a full power cycle, not standby, before the hook can run.
- Read the honest-limits section. Root is not a shell with tools, because UEP
  refuses every unsigned binary.

Nothing here writes unless a vendor hash matches first, so a wrong offset fails
before it damages anything. The failure mode to respect is a half-applied
account patch, which is recoverable from the backup but not automatic.
