# NOTICE

The original scripts, documentation and research in this repository are
licensed under the MIT License (see `LICENSE`).

## What this repository does NOT contain

- **No Samsung firmware**, and no part of any firmware image, decrypted or
  otherwise. Firmware is referenced by its official download URL and hash only.
- The managed EGL compute wrapper in `research/mali-cve-2022-46395/managed/`
  adapts `payloads/qn90f/EglComputeContext.cs` from
  [chris-ritsen/samsung-tv-root](https://github.com/chris-ritsen/samsung-tv-root),
  released under the Unlicense (public domain). Q60T ABI and chain code here
  are separate, target-specific work. Other third-party tools are referenced
  by URL and remain under their own licenses.

## Other third-party tools (referenced by URL only)

These are not included or redistributed here; each is governed by its own
upstream license. See the research report's Sources section (§16) for the
full list. Notable ones:

- Synacktiv — `samsung-q60t-exploit` (`firmware/decrypt.py`): historical
  research; used by reference for firmware decryption.
- HinTak/`vdfs-tools` (Samsung-derived, **GPLv2**): VDFS4 unpacker.
- TizenBrew; ardazeytin/`samsung-tizen-tv-debloat`;
  SAWSUBE — see §16.
- Debian, xrdp, xorgxrdp and Fortra Impacket. The disposable Remote PC lab
  installs these from their upstream package sources while building locally;
  their source is not vendored here. Impacket is pinned to `0.13.1` in the
  lab Dockerfile.

Any local patches the author made to a third-party GPLv2 tool are kept
privately and are **not** published in this repository; if ever distributed,
they would be under that tool's license (GPLv2), not MIT.

## Trademarks

Samsung, Tizen, and other product names are trademarks of their respective
owners and are used here for identification and interoperability only. This
project is not affiliated with or endorsed by Samsung.

## Scope

All work here concerns a device the author owns, on a trusted local network.
The Mali chain remains a separate, incomplete research route and has not
produced a root result. On 2026-09-27, a bounded Remote PC/CIFS credential
injection was run once on the exact assessed TV and produced a volatile
`id` marker that was classified as UID 0. It did not install persistence,
modify firmware, or establish an affected-version range. The replacement
one-shot harness is offline by default and has not yet been run live.
