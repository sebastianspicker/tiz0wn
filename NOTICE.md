# NOTICE

The original scripts, documentation and research in this repository are
licensed under the MIT License (see `LICENSE`).

## What this repository does NOT contain

- **No Samsung firmware**, and no part of any firmware image, decrypted or
  otherwise. Firmware is referenced by its official download URL and hash only.
- **No third-party tool source code.** The tools used or discussed are
  referenced by URL and remain under their own licenses.

## Third-party tools (referenced by URL only)

These are not included or redistributed here; each is governed by its own
upstream license. See the research report's Sources section (§16) for the
full list. Notable ones:

- Synacktiv — `samsung-q60t-exploit` (`firmware/decrypt.py`): historical
  research; used by reference for firmware decryption.
- HinTak/`vdfs-tools` (Samsung-derived, **GPLv2**): VDFS4 unpacker.
- TizenBrew; chris-ritsen/`samsung-tv-root`; ardazeytin/`samsung-tizen-tv-debloat`;
  SAWSUBE — see §16.

Any local patches the author made to a third-party GPLv2 tool are kept
privately and are **not** published in this repository; if ever distributed,
they would be under that tool's license (GPLv2), not MIT.

## Trademarks

Samsung, Tizen, and other product names are trademarks of their respective
owners and are used here for identification and interoperability only. This
project is not affiliated with or endorsed by Samsung.

## Scope

All work here concerns a device the author owns, on a trusted local network.
Nothing here is a working exploit against current firmware.
