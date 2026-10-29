# NOTICE

The original scripts, documentation and research in this repository are
licensed under the MIT License (see `LICENSE`).

## What this repository does NOT contain

- No Samsung firmware, and no part of any firmware image, decrypted or
  otherwise. Firmware is referenced by its official download URL and hash only.
- No third-party source is vendored. Tools are referenced by URL and stay under
  their own licenses.

## Third-party work used or investigated

Three routes to root on this TV generation exist, published within weeks of each
other. They combine rather than compete, and this one reuses what the others
proved:

- metaljay (issue #1), first public root on the generation. Reused here: the
  method shape for the `profile.d` block swap (same-size replacement, byte-exact
  backup of the containing blocks, one-command rollback), the kernel symbol table
  for the family, and two corrections (`kill -47` to PID 1 is halt, not reboot;
  the `T-*-REL-<date>` build stamp is the firm identifier, not the `2743.0`
  version string). No code copied.
- cfloinc, [`samsung-q70t-tizen-root`](https://github.com/cfloinc/samsung-q70t-tizen-root)
  (MIT), the Q70T writeup and `persistent-hook/` kit. Reused here: the
  content-invocation rule `sh -c "$(cat …)"`, which exists because UEP hooks
  script file loading; and the negative result that archive-root fails without
  `/usr/bin/dotnet`. Method credit, MIT-compatible.
- Luminger, `samsung-tv-usb-root` (AGPL-3.0), the USB route used by metaljay.
  Referenced, not vendored.
- chris-ritsen/`samsung-tv-root` (Unlicense) and its levkropp fork, and
  gtalusan's kmod recipe. Investigated for the fallback routes.

The distinction matters: "used" means code or method from it is in the chain;
"investigated" means it informed a decision that was then not taken. Neither
person is responsible for this repo's mistakes, and none of this repo's Q60T
values are theirs.

## Other third-party tools (referenced by URL only)

These are not included or redistributed here; each is governed by its own
upstream license. See the research report's Sources section for the full list. Notable ones:

- Synacktiv, `samsung-q60t-exploit` (`firmware/decrypt.py`): historical
  research; used by reference for firmware decryption.
- HinTak/`vdfs-tools` (Samsung-derived, GPLv2): VDFS4 unpacker.

Any local patches the author made to a third-party GPLv2 tool are kept
privately and are not published in this repository; if ever distributed,
they would be under that tool's license (GPLv2), not MIT.

## Trademarks

Samsung, Tizen, and other product names are trademarks of their respective
owners and are used here for identification and interoperability only. This
project is not affiliated with or endorsed by Samsung.

## Scope

All work here concerns a device the author owns, on a trusted local network.
On 2026-09-27 one credential injection
ran and produced a volatile `id` marker classified as UID 0. Follow-up work took
the same trigger to persistent root on 2026-10-29: one same-size block patch in
the read-only rootfs, hash-gated and backed up before being written, a boot hook
that fires once per boot, and a root login for the existing `sdk` account.
Persistence was proven over three full power cycles. Details, measurements and
limits are in
[`exploits/tiz0wn-root/LIVE-RUN-2026-10-29.md`](exploits/tiz0wn-root/LIVE-RUN-2026-10-29.md).

All of it was measured on one exact build. No affected-version range is claimed
and no firmware is redistributed.

The model and firmware are named openly. Addresses, the MAC, the crypt salt and
the test password are placeholders so the harness stays runnable after cloning.
RFC 5737 documentation addresses are used where an example has to parse as IPv4.

### Placeholder convention

Named openly: the model `GQ55Q60TGUXZG` and firmware `T-NKLDEUC-2743.0`.

| Placeholder | Meaning |
|---|---|
| `<TV_HOST>` | the television's LAN address |
| `<HOST_IP>` | the investigating computer's LAN address |
| `<BROADCAST_IP>` | that LAN's broadcast address, for Wake on LAN |
| `<TV_MAC>` | the television's MAC address |
| `<SALT>`, `<TV_ROOT_PASSWORD>` | crypt salt and the chosen account password |

